from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from src.inference.models import FacetRelation, InferenceNode


class ManifoldBranchContextError(ValueError):
    pass


class ManifoldRankingRequest(BaseModel):
    branch_name: str
    ranking_mode: Literal[
        "inference_candidate_ranking",
        "facet_candidate_ranking",
        "bridge_candidate_ranking",
        "validation_priority_ranking",
    ]
    seed_context: dict[str, Any] = Field(default_factory=dict)
    candidates: list[Union[InferenceNode, FacetRelation]] = Field(default_factory=list)
    neighborhood_export: dict[str, Any] = Field(default_factory=dict)


class ManifoldRankingResponse(BaseModel):
    ranking_mode: str
    ranking_model_id: str
    ranking_run_id: str
    geometry_version: str
    candidates: list[Union[InferenceNode, FacetRelation]]


class ManifoldModelMetadata(BaseModel):
    model_id: str
    geometry_version: str
    embedding_version: str
    ranking_features: list[str] = Field(default_factory=list)
