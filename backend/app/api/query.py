from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.graph import build_graph
from app.models import QueryRun
from app.schemas import Citation, QueryRequest, QueryResponse
from app.services.guardrails import check_prompt_injection

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_documents(payload: QueryRequest, db: Session = Depends(get_db)):
    guard = check_prompt_injection(payload.question)
    if not guard.allowed:
        raise HTTPException(400, detail={"message": "Request blocked by AI guardrail", "warnings": guard.warnings})

    graph = build_graph(db)
    try:
        state = graph.invoke(
            {
                "question": payload.question,
                "metadata_filter": payload.metadata_filter,
                "top_k": payload.top_k,
                "retry_count": 0,
                "warnings": guard.warnings,
            }
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    sources = state.get("sources", [])
    citations = [
        Citation(
            id=s.source_id,
            filename=s.filename,
            chunk_index=s.chunk_index,
            excerpt=s.content[:320],
            score=round(s.score, 4),
        )
        for s in sources
    ]

    run = QueryRun(
        question=payload.question,
        answer=state.get("answer", ""),
        classification=state.get("classification", "document_qa"),
        confidence=state.get("confidence", 0.0),
        citations=[c.model_dump() for c in citations],
        retrieved_sources=[s.chunk_id for s in sources],
        route=state.get("route", "finalize"),
        metrics=state.get("metrics", {}),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return QueryResponse(
        run_id=str(run.id),
        answer=run.answer,
        classification=run.classification,
        confidence=run.confidence,
        route=run.route,
        citations=citations,
        metrics=run.metrics,
        warnings=state.get("warnings", []),
    )
