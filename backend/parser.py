"""Parsing and post-processing for enrichment.

Adds link resolution (follow redirects) and downloads images to local cache with hashes.
"""

import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from PIL import Image

from .schema import ArticleBundle, ImageAsset, LinkItem


def _abs_url(base_url: str, href: str) -> str:
    return href if href.startswith("http") else urljoin(base_url, href)


def _resolve_link(client: httpx.Client, base_url: str, link: LinkItem) -> LinkItem:
    target = _abs_url(base_url, link.href)
    try:
        resp = client.get(target, follow_redirects=True)
        resolved = str(resp.url)
        status = resp.status_code
        title = link.title
        return link.model_copy(
            update={
                "resolved_url": resolved,
                "status_code": status,
                "href": target,
                "title": title,
            }
        )
    except Exception:  # noqa: BLE001
        return link.model_copy(
            update={
                "resolved_url": None,
                "status_code": None,
                "href": target,
                "risk_flags": link.risk_flags + ["fetch_error"],
            }
        )


def _download_image(
    client: httpx.Client, base_url: str, asset: ImageAsset, out_dir: Path
) -> ImageAsset:
    target = _abs_url(base_url, asset.url)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(target).suffix or ".bin"
    filename = hashlib.sha256(target.encode()).hexdigest() + suffix
    path = out_dir / filename

    try:
        with client.stream("GET", target, follow_redirects=True, timeout=15) as resp:
            resp.raise_for_status()
            with open(path, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
    except Exception:  # noqa: BLE001
        return asset.model_copy(update={"url": target, "local_path": None})

    sha256 = _file_hash(path)
    width, height = _image_size(path)
    return asset.model_copy(
        update={
            "url": target,
            "local_path": str(path),
            "sha256": sha256,
            "width": width or asset.width,
            "height": height or asset.height,
        }
    )


def _file_hash(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:  # noqa: BLE001
        return None


def _image_size(path: Path) -> Optional[tuple[int, int]]:
    try:
        with Image.open(path) as img:
            return img.width, img.height
    except Exception:  # noqa: BLE001
        return None


def enrich_bundle(bundle: ArticleBundle, base_url: str) -> ArticleBundle:
    """Resolve links and download images; returns updated bundle."""

    client = httpx.Client(timeout=15)
    links = [_resolve_link(client, base_url, link) for link in bundle.links]

    image_dir = Path("captures/images")
    images = [
        _download_image(client, base_url, asset, image_dir) for asset in bundle.images
    ]

    client.close()

    return bundle.model_copy(
        update={
            "source_url": bundle.source_url or base_url,
            "links": links,
            "images": images,
        }
    )
