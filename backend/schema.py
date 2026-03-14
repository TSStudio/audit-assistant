from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Severity(str, Enum):
    info = "info"
    warn = "warn"
    critical = "critical"


class IssueType(str, Enum):
    typo = "typo"
    link = "link"
    qrcode = "qrcode"
    image_text_mismatch = "image_text_mismatch"
    compliance = "compliance"
    layout = "layout"


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class TextBlock(BaseModel):
    id: str
    text: str
    path: Optional[str] = None
    order: Optional[int] = None
    bbox: Optional[BoundingBox] = None


class LinkItem(BaseModel):
    id: str
    href: str
    resolved_url: Optional[str] = None
    status_code: Optional[int] = None
    title: Optional[str] = None
    risk_flags: List[str] = Field(default_factory=list)


class ImageAsset(BaseModel):
    id: str
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    role: Optional[str] = None
    sha256: Optional[str] = None
    local_path: Optional[str] = None


class QRCodeEntry(BaseModel):
    id: str
    image_id: str
    bbox: BoundingBox
    decoded_text: Optional[str] = None
    code_type: Optional[str] = None
    confidence: Optional[float] = None


class OCRText(BaseModel):
    id: str
    image_id: str
    bbox: BoundingBox
    text: str


class ScreenshotMeta(BaseModel):
    id: str
    filename: str
    scroll_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class IssueEvidence(BaseModel):
    text_block_id: Optional[str] = None
    link_id: Optional[str] = None
    image_id: Optional[str] = None
    screenshot_id: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    quote: Optional[str] = None


class Issue(BaseModel):
    id: str
    type: IssueType
    severity: Severity
    evidence: IssueEvidence
    recommendation: Optional[str] = None
    confidence: Optional[float] = None


class ArticleBundle(BaseModel):
    source_url: Optional[str] = None
    title: Optional[str] = None
    text_blocks: List[TextBlock] = Field(default_factory=list)
    links: List[LinkItem] = Field(default_factory=list)
    images: List[ImageAsset] = Field(default_factory=list)
    qrcodes: List[QRCodeEntry] = Field(default_factory=list)
    ocr_texts: List[OCRText] = Field(default_factory=list)
    screenshots: List[ScreenshotMeta] = Field(default_factory=list)


class AuditRequest(BaseModel):
    url: HttpUrl
    checklist: List[str] = Field(default_factory=list)
    fast_mode: bool = False


class AuditStartResponse(BaseModel):
    task_id: str
    status: TaskStatus


class AuditStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[ArticleBundle] = None
    issues: List[Issue] = Field(default_factory=list)
    checklist: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    progress: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="0-100 pipeline progress indicator",
    )
