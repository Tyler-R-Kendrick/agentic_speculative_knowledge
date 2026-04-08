from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid


class Claim(BaseModel):
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_ref: Optional[str] = None
    source_file: Optional[str] = None
    source_commit: Optional[str] = None
    claim_text: str
    claim_type: str = "factual"
    decontextualized: bool = False
    ambiguity_flag: bool = False
    confidence: float = 1.0
    entities: list[str] = Field(default_factory=list)
    provenance_span: Optional[str] = None
    observed_at: Optional[datetime] = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
