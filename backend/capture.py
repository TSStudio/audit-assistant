"""Page capture utilities using Playwright.

This module renders a page, extracts basic text/links/images, and saves a full-page screenshot.
It intentionally keeps scope narrow for the MVP; enrichment, OCR, and LLM calls happen later.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from .schema import (
    ArticleBundle,
    BoundingBox,
    ImageAsset,
    LinkItem,
    ScreenshotMeta,
    TextBlock,
)


def _to_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _to_bbox(rect: Optional[dict]) -> Optional[BoundingBox]:
    if not rect:
        return None
    try:
        return BoundingBox(
            x=int(rect.get("x", 0)),
            y=int(rect.get("y", 0)),
            width=int(rect.get("width", 0)),
            height=int(rect.get("height", 0)),
        )
    except Exception:
        return None


def _extract_text_blocks_with_positions(page) -> List[TextBlock]:
    blocks: List[TextBlock] = []

    # Prefer elements inside <article>; fallback to general body elements.
    selectors_primary = "article p, article li, article h1, article h2, article h3, article h4, article h5, article h6"
    selectors_fallback = "p, li, h1, h2, h3, h4, h5, h6"

    elements = page.query_selector_all(selectors_primary)
    if not elements:
        elements = page.query_selector_all(selectors_fallback)

    # lasttext = ""
    for idx, el in enumerate(elements):
        try:
            text = (el.inner_text() or "").strip()
            if not text:
                continue
            # if text.strip() == lasttext:
            #     continue
            bbox = _to_bbox(el.bounding_box())
            marked_text = f"##ID:{idx}## {text}"
            blocks.append(
                TextBlock(
                    id=f"t{idx}",
                    text=marked_text,
                    order=idx,
                    bbox=bbox,
                )
            )
            # lasttext = text.strip()
        except Exception:
            continue

    # If nothing collected, fallback to full page text.
    if not blocks:
        try:
            full_text = (page.inner_text("body") or "").strip()
            if full_text:
                blocks.append(TextBlock(id="t0", text=f"##ID:0## {full_text}", order=0))
        except Exception:
            pass

    return blocks


def _extract_links(soup: BeautifulSoup) -> List[LinkItem]:
    links: List[LinkItem] = []
    for idx, tag in enumerate(soup.find_all("a")):
        href = tag.get("href")
        if not href:
            continue
        links.append(
            LinkItem(
                id=f"l{idx}",
                href=href,
                title=(tag.get_text(strip=True) or None),
            )
        )
    return links


def _extract_images(soup: BeautifulSoup) -> List[ImageAsset]:
    images: List[ImageAsset] = []
    for idx, tag in enumerate(soup.find_all("img")):
        src = tag.get("src") or tag.get("data-src")
        if not src:
            continue
        images.append(
            ImageAsset(
                id=f"img{idx}",
                url=src,
                width=_to_int(tag.get("width")),
                height=_to_int(tag.get("height")),
            )
        )
    return images


def _clean_title(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = " ".join(str(raw).split()).strip(" -_|\t\r\n")
    if not text:
        return None

    for suffix in (
        " - 微信公众号",
        " - 微信公众平台",
        "_微信公众平台",
        " | 微信公众号",
        " | 微信公众平台",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip(" -_|")
            break

    if text.startswith("http://") or text.startswith("https://"):
        return None
    return text or None


def _extract_article_title(soup: BeautifulSoup) -> Optional[str]:
    selectors = (
        ("h1.rich_media_title", False),
        ("#activity-name", False),
        ("meta[property='og:title']", True),
        ("meta[name='twitter:title']", True),
        ("title", False),
    )

    for selector, is_meta in selectors:
        tag = soup.select_one(selector)
        if not tag:
            continue
        raw = tag.get("content") if is_meta else tag.get_text(" ", strip=True)
        title = _clean_title(raw)
        if title:
            return title
    return None


def capture_article(
    url: str, viewport: Tuple[int, int] = (600, 800), wait_ms: int = 1500
) -> ArticleBundle:
    """Render the URL and return a structured bundle with basic assets."""

    out_dir = Path(__file__).resolve().parent / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshot_name = f"screenshot-{uuid4().hex}.png"
    screenshot_path = out_dir / screenshot_name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(wait_ms)
            # Scroll to bottom once to trigger lazy loads, then reset to top so bounding boxes are non-negative.
            page.evaluate("() => { window.scrollTo(0, document.body.scrollHeight); }")
            page.wait_for_timeout(400)
            page.evaluate("() => { window.scrollTo(0, 0); }")
            page.wait_for_timeout(300)

            # Capture DOM text segments with positions before closing the page.
            text_blocks = _extract_text_blocks_with_positions(page)

            content = page.content()
            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"Navigation timeout: {exc}")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Capture failed: {exc}")

    soup = BeautifulSoup(content, "html.parser")
    title = _extract_article_title(soup)
    links = _extract_links(soup)
    images = _extract_images(soup)

    screenshots = [
        ScreenshotMeta(id="shot0", filename=str(screenshot_path), scroll_y=0),
    ]

    return ArticleBundle(
        source_url=url,
        title=title,
        text_blocks=text_blocks,
        links=links,
        images=images,
        screenshots=screenshots,
    )
