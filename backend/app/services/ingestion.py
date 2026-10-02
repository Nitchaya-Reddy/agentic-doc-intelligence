from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.services.llm import get_embeddings


def ingest_document(
    db: Session,
    *,
    filename: str,
    content_type: str,
    text: str,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> tuple[Document, int]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    pieces = [x for x in splitter.split_text(text) if x.strip()]
    if not pieces:
        raise ValueError("No readable text found in document")

    embeddings = get_embeddings().embed_documents(pieces)

    doc = Document(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        tags=tags or [],
        meta=metadata or {},
    )
    db.add(doc)
    db.flush()

    for idx, (piece, vector) in enumerate(zip(pieces, embeddings, strict=True)):
        db.add(
            Chunk(
                document_id=doc.id,
                chunk_index=idx,
                content=piece,
                chunk_meta={"filename": filename, "tags": tags or []},
                embedding=vector,
            )
        )
    db.commit()
    db.refresh(doc)
    return doc, len(pieces)
