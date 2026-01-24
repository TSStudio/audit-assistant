"""Image analysis: QR detection (no OCR yet)."""

from pathlib import Path
from typing import List

from PIL import Image
from pyzbar.pyzbar import decode

from .schema import ArticleBundle, BoundingBox, QRCodeEntry


def _scan_file(path: Path, image_id: str) -> List[QRCodeEntry]:
    results: List[QRCodeEntry] = []
    if not path.exists():
        return results
    try:
        with Image.open(path) as img:
            decoded = decode(img)
    except Exception:  # noqa: BLE001
        return results

    for idx, item in enumerate(decoded):
        rect = item.rect
        bbox = BoundingBox(
            x=rect.left, y=rect.top, width=rect.width, height=rect.height
        )
        text = None
        try:
            text = item.data.decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            text = None
        results.append(
            QRCodeEntry(
                id=f"qr_{image_id}_{idx}",
                image_id=image_id,
                bbox=bbox,
                decoded_text=text,
                code_type=item.type,
                confidence=None,
            )
        )
    return results


def analyze_images(bundle: ArticleBundle) -> ArticleBundle:
    """Run QR detection on downloaded images and screenshots."""

    qrs: List[QRCodeEntry] = []

    # Scan downloaded images if local_path is available.
    for asset in bundle.images:
        if asset.local_path:
            qrs.extend(_scan_file(Path(asset.local_path), asset.id))

    # Scan screenshots as a fallback surface.
    for shot in bundle.screenshots:
        qrs.extend(_scan_file(Path(shot.filename), shot.id))

    existing = list(bundle.qrcodes)
    existing.extend(qrs)
    return bundle.model_copy(update={"qrcodes": existing})
