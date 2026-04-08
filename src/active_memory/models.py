from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
import uuid


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"
    current_goal: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkingItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_type: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityCard(BaseModel):
    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    entity_type: str
    description: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class TaskCard(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
