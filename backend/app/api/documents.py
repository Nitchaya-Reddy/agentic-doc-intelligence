import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Document
from app.services.document_loader import extract_text
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(default="[]"),
    metadata: str = Form(default="{}"),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")

    try:
        tag_list = json.loads(tags)
        metadata_dict = json.loads(metadata)
        if not isinstance(tag_list, list) or not isinstance(metadata_dict, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(400, "tags must be a JSON array and metadata a JSON object")

    try:
        text = extract_text(file.filename or "upload", file.content_type or "", raw)
        doc, chunks = ingest_document(
            db,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            text=text,
            tags=[str(x) for x in tag_list],
            metadata=metadata_dict,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"id": str(doc.id), "filename": doc.filename, "chunks": chunks, "tags": doc.tags}


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "tags": d.tags,
            "metadata": d.meta,
            "created_at": d.created_at,
        }
        for d in docs
    ]
