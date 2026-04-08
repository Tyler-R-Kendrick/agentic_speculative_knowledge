from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from src.inference.models import FacetRelation, InferenceNode
from src.manifold_sidecar.models import (
    ManifoldBranchContextError,
    ManifoldModelMetadata,
    ManifoldRankingRequest,
    ManifoldRankingResponse,
)


class ManifoldRankingService:
    def __init__(
        self,
        model_id: str = "manifold-ranking-baseline-v1",
        geometry_version: str = "euclidean-baseline-v1",
        embedding_version: str = "text-graph-temporal-v1",
    ):
        self.model_id = model_id
        self.geometry_version = geometry_version
        self.embedding_version = embedding_version

    def rank_inference_candidates(self, request: ManifoldRankingRequest) -> ManifoldRankingResponse:
        self._require_speculative_branch(request.branch_name)
        run_id = self._run_id()
        ranked = []
        for candidate in request.candidates:
            if not isinstance(candidate, InferenceNode):
                continue
            score = self._score_inference(candidate, request.seed_context)
            ranked.append(
                candidate.model_copy(
                    update={
                        "ranking_score": score,
                        "ranking_model_id": self.model_id,
                        "ranking_run_id": run_id,
                        "geometry_version": self.geometry_version,
                        "relatedness_score": max(0.0, min(1.0, score - 0.05)),
                        "distance_score": max(0.0, 1.0 - score),
                        "uncertainty": round(max(0.0, 1.0 - candidate.confidence), 4),
                    }
                )
            )
        ranked.sort(key=lambda item: item.ranking_score or 0.0, reverse=True)
        return ManifoldRankingResponse(
            ranking_mode=request.ranking_mode,
            ranking_model_id=self.model_id,
            ranking_run_id=run_id,
            geometry_version=self.geometry_version,
            candidates=ranked,
        )

    def rank_facet_candidates(self, request: ManifoldRankingRequest) -> ManifoldRankingResponse:
        self._require_speculative_branch(request.branch_name)
        run_id = self._run_id()
        ranked = []
        for candidate in request.candidates:
            if not isinstance(candidate, FacetRelation):
                continue
            relatedness = self._score_facet(candidate, request.seed_context)
            ranked.append(
                candidate.model_copy(
                    update={
                        "ranking_model_id": self.model_id,
                        "ranking_run_id": run_id,
                        "geometry_version": self.geometry_version,
                        "relatedness_score": relatedness,
                        "distance_score": round(max(0.0, 1.0 - relatedness), 4),
                        "facet_strength": round((relatedness * 0.7) + 0.2, 4),
                        "uncertainty": round(max(0.0, 0.35 - (relatedness / 4)), 4),
                    }
                )
            )
        ranked.sort(key=lambda item: item.facet_strength, reverse=True)
        return ManifoldRankingResponse(
            ranking_mode=request.ranking_mode,
            ranking_model_id=self.model_id,
            ranking_run_id=run_id,
            geometry_version=self.geometry_version,
            candidates=ranked,
        )

    def get_current_model_metadata(self) -> ManifoldModelMetadata:
        return ManifoldModelMetadata(
            model_id=self.model_id,
            geometry_version=self.geometry_version,
            embedding_version=self.embedding_version,
            ranking_features=[
                "text_similarity",
                "graph_context",
                "temporal_compatibility",
                "provenance_priors",
            ],
        )

    def _require_speculative_branch(self, branch_name: str) -> None:
        if not (branch_name.startswith("inference/") or branch_name.startswith("verification/")):
            raise ManifoldBranchContextError("ranking requires inference/* or verification/* branch context")

    def _score_inference(self, candidate: InferenceNode, seed_context: dict[str, Any]) -> float:
        text_factor = min(len(candidate.text.split()) / 20.0, 1.0)
        provenance_factor = 0.2 if (candidate.generated_from_nodes or candidate.generated_from_edges) else 0.0
        context_factor = 0.1 if seed_context else 0.0
        score = (candidate.confidence * 0.5) + (text_factor * 0.2) + provenance_factor + context_factor
        return round(min(score, 0.99), 4)

    def _score_facet(self, candidate: FacetRelation, seed_context: dict[str, Any]) -> float:
        shared_factor = 0.2 if candidate.shared_core_claim else 0.0
        context_factor = 0.1 if seed_context else 0.0
        difference_penalty = min(len(candidate.differences) * 0.05, 0.2)
        score = 0.7 + shared_factor + context_factor - difference_penalty
        return round(max(0.0, min(score, 0.99)), 4)

    def _run_id(self) -> str:
        return f"rank-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
