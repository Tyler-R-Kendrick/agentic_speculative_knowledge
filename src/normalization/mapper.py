from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid
from src.claims.models import Claim


class CandidateMemory(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: str
    subtype: Optional[str] = None
    content: str
    summary: Optional[str] = None
    confidence: float = 1.0
    salience: float = 0.5
    maturity: int = 0
    access_scope: str = "session"
    observed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_kind: str = "claim"
    source_ref: Optional[str] = None
    source_file: Optional[str] = None
    source_commit: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    claim_ids: list[str] = Field(default_factory=list)


TYPE_MAPPING = {
    "factual": ("fact", None),
    "prescriptive": ("rule", "prescriptive"),
    "procedural": ("procedure", None),
    "relational": ("relation", None),
    "temporal": ("event", "temporal"),
    "causal": ("relation", "causal"),
}


class ClaimToMemoryMapper:
    def map(self, claim: Claim, session_id: Optional[str] = None, task_id: Optional[str] = None) -> CandidateMemory:
        memory_type, subtype = TYPE_MAPPING.get(claim.claim_type, ("fact", None))
        return CandidateMemory(
            memory_type=memory_type,
            subtype=subtype,
            content=claim.claim_text,
            summary=claim.claim_text[:100] if len(claim.claim_text) > 100 else None,
            confidence=claim.confidence,
            observed_at=claim.observed_at,
            source_kind="claim",
            source_ref=claim.source_ref,
            source_file=claim.source_file,
            source_commit=claim.source_commit,
            session_id=session_id,
            task_id=task_id,
            claim_ids=[claim.claim_id],
        )

    def map_many(self, claims: list[Claim], session_id: Optional[str] = None, task_id: Optional[str] = None) -> list[CandidateMemory]:
        return [self.map(c, session_id=session_id, task_id=task_id) for c in claims]
