from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import QueryRun
from app.schemas import CodeAgentVerificationRequest, CodeAgentVerificationResponse
from app.services.coding_agent_verifier import verify_generated_output

router = APIRouter(prefix="/api", tags=["evaluation"])


@router.get("/evaluations")
def recent_evaluations(limit: int = 25, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    runs = db.scalars(select(QueryRun).order_by(desc(QueryRun.created_at)).limit(limit)).all()
    return [
        {
            "run_id": str(r.id),
            "question": r.question,
            "classification": r.classification,
            "confidence": r.confidence,
            "route": r.route,
            "metrics": r.metrics,
            "created_at": r.created_at,
        }
        for r in runs
    ]


@router.post("/verify/code-output", response_model=CodeAgentVerificationResponse)
def verify_code_output(payload: CodeAgentVerificationRequest):
    return verify_generated_output(payload.task, payload.generated_output, payload.required_terms)
