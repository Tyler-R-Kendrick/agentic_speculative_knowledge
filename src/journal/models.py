from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class JournalEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changed_files: list[str] = Field(default_factory=list)
    git_commit: Optional[str] = None
    mutation_kind: str
    actor: str = "agent"
    persist_status: str = "pending"
