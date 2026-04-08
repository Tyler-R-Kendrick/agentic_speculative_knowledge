import pathlib
from typing import Optional, Any
from dataclasses import dataclass, field
from src.active_memory.models import WorkingItem
from src.active_memory.working_set import WorkingSetAppender
from src.journal.models import JournalEvent
from src.journal.appender import JournalAppender
from src.claims.extractor import ClaimExtractor
from src.claims.writer import ClaimWriter
from src.inference.generator import InferenceGenerator
from src.manifold_sidecar import ManifoldRankingRequest, ManifoldRankingService
from src.terminus.adapter import TerminusMemoryRepository
from src.terminus.branch_manager import inference_branch_name, session_branch_name
from src.normalization.mapper import ClaimToMemoryMapper


@dataclass
class PipelineResult:
    success: bool = True
    active_memory: Optional[str] = None
    journal_event_id: Optional[str] = None
    git_commit: Optional[str] = None
    claims_extracted: int = 0
    terminus_written: int = 0
    inference_candidates: int = 0
    ranked_inference_candidates: int = 0
    facet_relations_written: int = 0
    inference_branch: Optional[str] = None
    errors: list[str] = field(default_factory=list)


class MutationPipeline:
    def __init__(
        self,
        root_dir: pathlib.Path,
        enable_git: bool = False,
        enable_terminus: bool = False,
        enable_inference: bool = False,
        git_service=None,
        terminus_repo: Optional[TerminusMemoryRepository] = None,
        manifold_service: Optional[ManifoldRankingService] = None,
        sidecar: Optional[ManifoldRankingService] = None,
    ):
        self.root_dir = pathlib.Path(root_dir)
        self.enable_git = enable_git
        self.enable_terminus = enable_terminus
        self.enable_inference = enable_inference
        self.git_service = git_service
        self.terminus_repo = terminus_repo
        self.manifold_service = manifold_service or sidecar

        self.working_set = WorkingSetAppender(root_dir)
        self.journal = JournalAppender(root_dir)
        self.claim_extractor = ClaimExtractor()
        self.claim_writer = ClaimWriter(root_dir)
        self.mapper = ClaimToMemoryMapper()
        self.inference_generator = InferenceGenerator()

    def run(
        self,
        item: WorkingItem,
        mutation_kind: str = "add",
        session_id: str = "",
        extract_claims: bool = True,
    ) -> PipelineResult:
        result = PipelineResult()

        # Step 1: active memory write
        try:
            self.working_set.append(item)
            result.active_memory = item.item_id
        except Exception as e:
            result.errors.append(f"active_memory: {e}")
            result.success = False
            return result

        # Step 2: journal append
        try:
            event = JournalEvent(
                session_id=session_id or item.session_id,
                mutation_kind=mutation_kind,
                changed_files=["working-set.jsonl"],
            )
            self.journal.append(event)
            result.journal_event_id = event.event_id
        except Exception as e:
            result.errors.append(f"journal: {e}")

        # Step 3: git commit (optional)
        if self.enable_git and self.git_service:
            try:
                commit_hash = self.git_service.commit(
                    message=f"[{mutation_kind}] add working item {item.item_id}",
                    files=["working-set.jsonl"],
                )
                result.git_commit = commit_hash
            except Exception as e:
                result.errors.append(f"git: {e}")

        # Step 4: claim extraction
        extracted_claims = []
        if extract_claims:
            try:
                extracted_claims = self.claim_extractor.extract(
                    text=item.content,
                    source_ref=item.item_id,
                )
                self.claim_writer.write_many(extracted_claims)
                result.claims_extracted = len(extracted_claims)
            except Exception as e:
                result.errors.append(f"claims: {e}")

        # Step 5: TerminusDB write (optional)
        if self.enable_terminus and self.terminus_repo:
            try:
                branch = session_branch_name(session_id or item.session_id or "default")
                self.terminus_repo.ensure_branch(branch)
                claims = extracted_claims if extract_claims else self.claim_extractor.extract(
                    text=item.content, source_ref=item.item_id
                )
                memories = self.mapper.map_many(claims, session_id=item.session_id)
                written = 0
                for claim in claims:
                    self.terminus_repo.write_claim(branch, claim)
                for m in memories:
                    m.source_branch = branch
                    if self.terminus_repo.write_memory(branch, m):
                        written += 1
                result.terminus_written = written
            except Exception as e:
                result.errors.append(f"terminus: {e}")

        if self.enable_inference and self.terminus_repo:
            try:
                branch = inference_branch_name(session_id or item.session_id or "default")
                result.inference_branch = self.terminus_repo.ensure_branch(branch)
                source_commit = result.git_commit or result.journal_event_id or item.item_id
                claims = extracted_claims if extracted_claims else self.claim_extractor.extract(
                    text=item.content,
                    source_ref=item.item_id,
                )
                inference_candidates = self.inference_generator.generate_from_claims(
                    claims,
                    source_branch=branch,
                    source_commit=source_commit or item.item_id,
                    session_id=session_id or item.session_id or None,
                )
                result.inference_candidates = len(inference_candidates)

                facet_candidates = self.inference_generator.generate_facet_candidates(
                    claims,
                    provenance_commit=source_commit or item.item_id,
                    source_branch=branch,
                )

                ranked_inference = inference_candidates
                ranked_facets = []
                if self.manifold_service and inference_candidates:
                    try:
                        ranking = self.manifold_service.rank_inference_candidates(
                            ManifoldRankingRequest(
                                branch_name=branch,
                                ranking_mode="inference_candidate_ranking",
                                seed_context={"session_id": session_id or item.session_id},
                                candidates=inference_candidates,
                            )
                        )
                        ranked_inference = ranking.candidates
                        result.ranked_inference_candidates = len(ranked_inference)
                    except Exception as e:
                        result.errors.append(f"sidecar_inference: {e}")

                if self.manifold_service and facet_candidates:
                    try:
                        ranking = self.manifold_service.rank_facet_candidates(
                            ManifoldRankingRequest(
                                branch_name=branch,
                                ranking_mode="facet_candidate_ranking",
                                seed_context={"session_id": session_id or item.session_id},
                                candidates=facet_candidates,
                            )
                        )
                        ranked_facets = ranking.candidates
                    except Exception as e:
                        result.errors.append(f"sidecar_facet: {e}")

                for candidate in ranked_inference:
                    self.terminus_repo.write_inference_node(branch, candidate)
                for relation in ranked_facets:
                    self.terminus_repo.write_facet_relation(branch, relation)
                result.facet_relations_written = len(ranked_facets)
            except Exception as e:
                result.errors.append(f"inference: {e}")

        return result
