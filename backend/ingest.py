"""Upload ingestion utilities.

Convert supported uploaded files into an ``ArticleBundle`` so the downstream
pipeline can reuse existing text/image/QR/LLM processing steps.
"""

from io import BytesIO
from pathlib import Path
from typing import List, Sequence, Tuple
from uuid import uuid4

from docx import Document
from PIL import Image
from pypdf import PdfReader

from .schema import ArticleBundle, ImageAsset, ScreenshotMeta, TextBlock

_TEXT_EXTS = {".txt"}
_DOCX_EXTS = {".docx"}
_PDF_EXTS = {".pdf"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
_REFERENCE_TEXT_EXTS = _TEXT_EXTS | _DOCX_EXTS | _PDF_EXTS


def _split_text_blocks(text: str, max_chars: int = 1200) -> List[TextBlock]:
    cleaned = (text or "").replace("\r", "").strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    for paragraph in cleaned.split("\n"):
        part = paragraph.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            chunks.append(part)
            continue
        start = 0
        while start < len(part):
            chunks.append(part[start : start + max_chars])
            start += max_chars

    blocks: List[TextBlock] = []
    for idx, chunk in enumerate(chunks):
        blocks.append(TextBlock(id=f"t{idx}", text=f"##ID:{idx}## {chunk}", order=idx))
    return blocks


def _decode_txt(content: bytes) -> str:
    encodings = ["utf-8", "utf-8-sig", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            return content.decode(enc)
        except Exception:
            continue
    return ""


def _read_docx_text(content: bytes) -> str:
    doc = Document(BytesIO(content))
    lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(lines)


def _read_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages: List[str] = []
    for page in reader.pages:
        try:
            pages.append((page.extract_text() or "").strip())
        except Exception:
            pages.append("")
    return "\n".join([p for p in pages if p])


def _save_uploaded_image(content: bytes, suffix: str) -> Tuple[str, int, int]:
    out_dir = Path(__file__).resolve().parent / "captures" / "uploads"
    out_dir.mkdir(parents=True, exist_ok=True)

    normalized_suffix = suffix if suffix else ".png"
    filename = f"upload-{uuid4().hex}{normalized_suffix}"
    path = out_dir / filename

    with Image.open(BytesIO(content)) as img:
        rgb = img.convert("RGB")
        width, height = rgb.width, rgb.height
        save_kwargs = {}
        if normalized_suffix.lower() in {".jpg", ".jpeg"}:
            save_fmt = "JPEG"
            save_kwargs = {"quality": 95}
        else:
            save_fmt = "PNG"
            path = path.with_suffix(".png")
        rgb.save(path, format=save_fmt, **save_kwargs)

    return str(path), width, height


def infer_upload_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in _TEXT_EXTS:
        return "txt"
    if ext in _DOCX_EXTS:
        return "docx"
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _IMAGE_EXTS:
        return "image"
    raise ValueError("Unsupported file type. Allowed: txt, docx, pdf, image")


def _safe_extract_reference_text(filename: str, content: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in _TEXT_EXTS:
        return _decode_txt(content)
    if ext in _DOCX_EXTS:
        return _read_docx_text(content)
    if ext in _PDF_EXTS:
        return _read_pdf_text(content)
    return ""


def extract_reference_context(
    files: Sequence[Tuple[str, bytes]],
    *,
    max_chars: int = 12000,
) -> str:
    """Build prompt-ready context text from supplementary files.

    Supported reference formats: txt/docx/pdf.
    """

    parts: List[str] = []
    for name, content in files:
        if not content:
            continue
        text = _safe_extract_reference_text(name, content).strip()
        if not text:
            continue
        parts.append(f"[参考资料: {name}]\n{text}")

    merged = "\n\n".join(parts).strip()
    if not merged:
        return ""
    if len(merged) <= max_chars:
        return merged
    return merged[:max_chars]


def extract_reference_documents(
    files: Sequence[Tuple[str, bytes]],
    *,
    max_chars_per_doc: int = 60000,
) -> List[dict]:
    """Extract reference files as structured documents for RAG retrieval."""

    docs: List[dict] = []
    for name, content in files:
        if not content:
            continue
        text = _safe_extract_reference_text(name, content).strip()
        if not text:
            continue
        if len(text) > max_chars_per_doc:
            text = text[:max_chars_per_doc]
        docs.append({"name": name, "text": text})
    return docs


def is_supported_reference_file(filename: str) -> bool:
    ext = Path(filename or "").suffix.lower()
    return ext in _REFERENCE_TEXT_EXTS


def build_bundle_from_upload(
    filename: str,
    content: bytes,
) -> Tuple[ArticleBundle, str, bool]:
    """Parse uploaded content to a bundle.

    Returns ``(bundle, upload_type, disable_multimodal)``.
    """

    if not content:
        raise ValueError("Empty upload content")

    upload_type = infer_upload_type(filename)
    source_ref = f"upload://{filename or 'unknown'}"
    title = Path(filename).stem or filename or "上传文件"

    if upload_type == "txt":
        text = _decode_txt(content)
        return (
            ArticleBundle(
                source_url=source_ref,
                title=title,
                text_blocks=_split_text_blocks(text),
            ),
            upload_type,
            True,
        )

    if upload_type == "docx":
        text = _read_docx_text(content)
        return (
            ArticleBundle(
                source_url=source_ref,
                title=title,
                text_blocks=_split_text_blocks(text),
            ),
            upload_type,
            False,
        )

    if upload_type == "pdf":
        text = _read_pdf_text(content)
        return (
            ArticleBundle(
                source_url=source_ref,
                title=title,
                text_blocks=_split_text_blocks(text),
            ),
            upload_type,
            False,
        )

    image_path, width, height = _save_uploaded_image(content, Path(filename).suffix)
    bundle = ArticleBundle(
        source_url=source_ref,
        title=title,
        images=[
            ImageAsset(
                id="img0",
                url=source_ref,
                width=width,
                height=height,
                local_path=image_path,
            )
        ],
        screenshots=[
            ScreenshotMeta(
                id="shot0",
                filename=image_path,
                width=width,
                height=height,
                scroll_y=0,
            )
        ],
    )
    return bundle, upload_type, False
