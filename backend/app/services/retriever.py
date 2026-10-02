import uuid
from dataclasses import dataclass

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.schemas import MetadataFilter
from app.services.guardrails import assert_tool_allowed
from app.services.llm import get_embeddings


@dataclass
class RetrievedChunk:
    source_id: str
    chunk_id: str
    filename: str
    chunk_index: int
    content: str
    score: float
    tags: list[str]


def retrieve_documents(
    db: Session,
    *,
    query: str,
    top_k: int,
    metadata_filter: MetadataFilter,
) -> list[RetrievedChunk]:
    assert_tool_allowed("retrieve_documents")
    vector = get_embeddings().embed_query(query)
    distance = Chunk.embedding.cosine_distance(vector).label("distance")

    stmt = (
        select(Chunk, Document, distance)
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance)
        .limit(top_k)
    )

    if metadata_filter.document_id:
        try:
            doc_id = uuid.UUID(metadata_filter.document_id)
            stmt = stmt.where(Document.id == doc_id)
        except ValueError:
            return []

    if metadata_filter.source:
        stmt = stmt.where(Document.filename.ilike(f"%{metadata_filter.source}%"))
    if metadata_filter.tags:
        # JSONB containment would be better for a JSONB column. This portable JSON expression
        # keeps the demo schema simple while still providing metadata filtering.
        for tag in metadata_filter.tags:
            stmt = stmt.where(cast(Document.tags, String).ilike(f'%"{tag}"%'))

    rows = db.execute(stmt).all()
    results: list[RetrievedChunk] = []
    for idx, (chunk, doc, dist) in enumerate(rows, start=1):
        results.append(
            RetrievedChunk(
                source_id=f"S{idx}",
                chunk_id=str(chunk.id),
                filename=doc.filename,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=max(0.0, min(1.0, 1.0 - float(dist))),
                tags=doc.tags or [],
            )
        )
    return results
