from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .schema import AuditRequest, AuditStatusResponse
from .tasks import get_status, start_audit

app = FastAPI(title="Audit Assistant API")

captures_dir = Path(__file__).resolve().parent / "captures"
captures_dir.mkdir(exist_ok=True)
app.mount("/api/captures", StaticFiles(directory=str(captures_dir)), name="captures")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/audit", response_model=AuditStatusResponse)
def create_audit(request: AuditRequest):
    return start_audit(request.url, checklist=request.checklist)


@app.get("/api/audit/{task_id}", response_model=AuditStatusResponse)
def read_audit(task_id: str):
    status = get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="task not found")
    return status
