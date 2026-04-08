from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


INFERENCE_MODES = {
    "deductive",
    "abductive",
    "analogical",
    "predictive",
    "retrodictive",
    "heuristic",
}

FACET_TYPES = {
    "paraphrase_of",
    "abstraction_of",
    "specialization_of",
    "reframe_of",
    "decomposition_of",
    "same_claim_different_scope",
    "same_claim_different_timeframe",
}


class InferenceNode(BaseModel):
    inference_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    status: str = "candidate"
    truth_status: str = "unverified"
    forecast_status: Optional[str] = None
    inference_mode: Literal["deductive", "abductive", "analogical", "predictive", "retrodictive", "heuristic"]
    generation_strategy: str = "graph-local"
    generator: str = "rule-based"
    confidence: float = 0.5
    assumptions: list[str] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)
    opposes: list[str] = Field(default_factory=list)
    verification_state: str = "unverified"
    observed_at: Optional[datetime] = None
    asserted_at: Optional[datetime] = None
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    about_time: Optional[str] = None
    forecast_horizon: Optional[str] = None
    retrodiction_window: Optional[str] = None
    verified_at: Optional[datetime] = None
    superseded_at: Optional[datetime] = None
    generated_from_nodes: list[str] = Field(default_factory=list)
    generated_from_edges: list[str] = Field(default_factory=list)
    source_branch: str
    source_commit: str
    source_session: Optional[str] = None
    source_task: Optional[str] = None
    source_terminus_commit: Optional[str] = None
    source_terminus_branch: Optional[str] = None
    model_id: str = "rule-based"
    generating_model_id: Optional[str] = None
    generation_run_id: Optional[str] = None
    prompt_template_id: str
    policy_version: str
    retrieval_context_ids: list[str] = Field(default_factory=list)
    parent_nodes: list[str] = Field(default_factory=list)
    parent_edges: list[str] = Field(default_factory=list)
    verifier_id: Optional[str] = None
    verification_run_id: Optional[str] = None
    ranking_score: Optional[float] = None
    ranking_model_id: Optional[str] = None
    ranking_run_id: Optional[str] = None
    geometry_version: Optional[str] = None
    relatedness_score: Optional[float] = None
    distance_score: Optional[float] = None
    uncertainty: Optional[float] = None

    @model_validator(mode="after")
    def validate_inference(self) -> "InferenceNode":
        if not self.text.strip():
            raise ValueError("text is required")
        if not self.generated_from_nodes and not self.generated_from_edges:
            raise ValueError("inference nodes require derivation provenance")
        if self.inference_mode == "predictive" and not self.forecast_horizon:
            raise ValueError("predictive inferences require forecast_horizon")
        if self.inference_mode == "retrodictive" and not self.retrodiction_window:
            raise ValueError("retrodictive inferences require retrodiction_window")
        return self


class FacetRelation(BaseModel):
    relation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str
    target_node_id: str
    facet_type: Literal[
        "paraphrase_of",
        "abstraction_of",
        "specialization_of",
        "reframe_of",
        "decomposition_of",
        "same_claim_different_scope",
        "same_claim_different_timeframe",
    ]
    same_proposition: bool = False
    shared_core_claim: Optional[str] = None
    directionality: str = "undirected"
    differences: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    source_inference_id: Optional[str] = None
    provenance_commit: str
    source_branch: Optional[str] = None
    ranking_model_id: str
    ranking_run_id: str
    geometry_version: Optional[str] = None
    relatedness_score: float
    distance_score: float
    facet_strength: float
    uncertainty: Optional[float] = None
    generating_model_id: Optional[str] = None
    generation_run_id: Optional[str] = None
    prompt_template_id: Optional[str] = None
    policy_version: Optional[str] = None
    retrieval_context_ids: list[str] = Field(default_factory=list)
    parent_nodes: list[str] = Field(default_factory=list)
    parent_edges: list[str] = Field(default_factory=list)
    verifier_id: Optional[str] = None
    verification_run_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_relation(self) -> "FacetRelation":
        if self.source_node_id == self.target_node_id:
            raise ValueError("facet relation requires distinct nodes")
        if not self.provenance_commit:
            raise ValueError("facet relation requires provenance_commit")
        if not self.ranking_model_id or not self.ranking_run_id:
            raise ValueError("facet relation requires ranking provenance")
        return self
