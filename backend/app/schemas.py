from typing import Literal
from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    document_id: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=20)
    metadata_filter: MetadataFilter = Field(default_factory=MetadataFilter)


class Citation(BaseModel):
    id: str
    filename: str
    chunk_index: int
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    run_id: str
    answer: str
    classification: str
    confidence: float
    route: str
    citations: list[Citation]
    metrics: dict[str, float]
    warnings: list[str] = Field(default_factory=list)


class QueryClassification(BaseModel):
    intent: Literal["document_qa", "summary", "comparison", "unsupported"]
    rewritten_query: str
    reason: str


class VerificationResult(BaseModel):
    grounded: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


class CodeAgentVerificationRequest(BaseModel):
    task: str
    generated_output: str
    required_terms: list[str] = Field(default_factory=list)


class CodeAgentVerificationResponse(BaseModel):
    safe: bool
    constraints_met: bool
    suspicious_patterns: list[str]
    missing_terms: list[str]
