import pytest

from src.inference.models import FacetRelation, InferenceNode
from src.sidecar.service import (
    BranchContextError,
    ManifoldSidecar,
    RankingRequest,
)


class TestInferenceNodeSchema:
    def test_inference_node_requires_generation_provenance(self):
        with pytest.raises(ValueError):
            InferenceNode(
                text="The outage may have originated from the auth service.",
                inference_mode="abductive",
                source_branch="inference/sess-1",
                source_commit="abc123",
                prompt_template_id="tmpl-1",
                policy_version="policy-v1",
            )

    def test_predictive_inference_requires_forecast_horizon(self):
        with pytest.raises(ValueError):
            InferenceNode(
                text="Latency will increase next week.",
                inference_mode="predictive",
                generated_from_nodes=["claim-1"],
                generated_from_edges=["supports:claim-1"],
                source_branch="inference/sess-1",
                source_commit="abc123",
                prompt_template_id="tmpl-1",
                policy_version="policy-v1",
            )


class TestFacetRelationSchema:
    def test_facet_relation_requires_ranking_provenance(self):
        with pytest.raises(ValueError):
            FacetRelation(
                source_node_id="claim-1",
                target_node_id="claim-2",
                facet_type="paraphrase_of",
                provenance_commit="abc123",
            )


class TestManifoldSidecar:
    def test_ranks_inference_candidates(self):
        sidecar = ManifoldSidecar(model_id="sidecar-v1", geometry_version="geo-v1")
        request = RankingRequest(
            branch_name="inference/sess-1",
            ranking_mode="inference_candidate_ranking",
            seed_context={"session_id": "sess-1"},
            candidates=[
                InferenceNode(
                    text="The scheduler backlog may be caused by blocked workers.",
                    inference_mode="abductive",
                    generated_from_nodes=["claim-1"],
                    generated_from_edges=["supports:claim-1"],
                    source_branch="inference/sess-1",
                    source_commit="abc123",
                    prompt_template_id="tmpl-1",
                    policy_version="policy-v1",
                )
            ],
        )

        response = sidecar.rank_inference_candidates(request)
        assert len(response.candidates) == 1
        candidate = response.candidates[0]
        assert candidate.ranking_score > 0
        assert candidate.ranking_model_id == "sidecar-v1"
        assert candidate.ranking_run_id
        assert response.geometry_version == "geo-v1"

    def test_enforces_branch_context(self):
        sidecar = ManifoldSidecar()
        request = RankingRequest(
            branch_name="main",
            ranking_mode="inference_candidate_ranking",
            seed_context={},
            candidates=[],
        )

        with pytest.raises(BranchContextError):
            sidecar.rank_inference_candidates(request)

    def test_ranks_facet_candidates(self):
        sidecar = ManifoldSidecar(model_id="sidecar-v1", geometry_version="geo-v1")
        request = RankingRequest(
            branch_name="inference/sess-1",
            ranking_mode="facet_candidate_ranking",
            seed_context={"session_id": "sess-1"},
            candidates=[
                FacetRelation(
                    source_node_id="claim-1",
                    target_node_id="claim-2",
                    facet_type="paraphrase_of",
                    provenance_commit="abc123",
                    ranking_model_id="seed-model",
                    ranking_run_id="seed-run",
                    relatedness_score=0.0,
                    distance_score=0.0,
                    facet_strength=0.0,
                )
            ],
        )

        response = sidecar.rank_facet_candidates(request)
        assert len(response.candidates) == 1
        relation = response.candidates[0]
        assert relation.relatedness_score > 0
        assert relation.ranking_model_id == "sidecar-v1"
