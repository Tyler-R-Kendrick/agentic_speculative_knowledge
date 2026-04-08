from __future__ import annotations

from typing import Iterable, Optional

from src.claims.models import Claim
from src.inference.models import FacetRelation, InferenceNode


class InferenceGenerator:
    def __init__(self, generator_id: str = "rule-based-inference-generator", prompt_template_id: str = "inference-template-v1", policy_version: str = "policy-v1"):
        self.generator_id = generator_id
        self.prompt_template_id = prompt_template_id
        self.policy_version = policy_version

    def generate_from_claims(
        self,
        claims: Iterable[Claim],
        *,
        source_branch: str,
        source_commit: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> list[InferenceNode]:
        candidates: list[InferenceNode] = []
        for claim in claims:
            mode = "abductive" if claim.claim_type in {"observation", "factual"} else "heuristic"
            candidates.append(
                InferenceNode(
                    text=f"Inference candidate: {claim.claim_text}",
                    inference_mode=mode,
                    confidence=max(0.3, min(0.95, claim.confidence * 0.9)),
                    assumptions=[f"Derived from claim {claim.claim_id}"],
                    generated_from_nodes=[claim.claim_id],
                    generated_from_edges=[f"derived_from_claim:{claim.claim_id}"],
                    source_branch=source_branch,
                    source_commit=source_commit,
                    source_session=session_id,
                    source_task=task_id,
                    model_id=self.generator_id,
                    generating_model_id=self.generator_id,
                    prompt_template_id=self.prompt_template_id,
                    policy_version=self.policy_version,
                    retrieval_context_ids=[claim.source_ref] if claim.source_ref else [],
                    parent_nodes=[claim.claim_id],
                    parent_edges=[f"derived_from_claim:{claim.claim_id}"],
                    observed_at=claim.observed_at,
                    asserted_at=claim.observed_at,
                )
            )
        return candidates

    def generate_facet_candidates(
        self,
        claims: Iterable[Claim],
        *,
        provenance_commit: str,
        source_branch: str,
    ) -> list[FacetRelation]:
        claims = list(claims)
        relations: list[FacetRelation] = []
        for left, right in zip(claims, claims[1:]):
            if not left.entities or not right.entities:
                continue
            shared = set(left.entities) & set(right.entities)
            if not shared:
                continue
            relations.append(
                FacetRelation(
                    source_node_id=left.claim_id,
                    target_node_id=right.claim_id,
                    facet_type="same_claim_different_scope",
                    same_proposition=False,
                    shared_core_claim=next(iter(shared)),
                    differences=[left.claim_type, right.claim_type],
                    provenance_commit=provenance_commit,
                    source_branch=source_branch,
                    ranking_model_id="pending-ranking",
                    ranking_run_id="pending-ranking",
                    relatedness_score=0.0,
                    distance_score=1.0,
                    facet_strength=0.0,
                    generating_model_id=self.generator_id,
                    prompt_template_id=self.prompt_template_id,
                    policy_version=self.policy_version,
                    parent_nodes=[left.claim_id, right.claim_id],
                    parent_edges=[f"derived_from_claim:{left.claim_id}", f"derived_from_claim:{right.claim_id}"],
                )
            )
        return relations
