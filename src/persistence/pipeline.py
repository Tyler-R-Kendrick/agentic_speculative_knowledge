import pathlib
from typing import Optional, Any
from dataclasses import dataclass, field
from src.active_memory.models import WorkingItem
from src.active_memory.working_set import WorkingSetAppender
from src.journal.models import JournalEvent
from src.journal.appender import JournalAppender
from src.claims.extractor import ClaimExtractor
from src.claims.writer import ClaimWriter
from src.terminus.adapter import TerminusMemoryRepository
from src.normalization.mapper import ClaimToMemoryMapper


@dataclass
class PipelineResult:
    success: bool = True
    active_memory: Optional[str] = None
    journal_event_id: Optional[str] = None
    git_commit: Optional[str] = None
    claims_extracted: int = 0
    terminus_written: int = 0
    errors: list[str] = field(default_factory=list)


class MutationPipeline:
    def __init__(
        self,
        root_dir: pathlib.Path,
        enable_git: bool = False,
        enable_terminus: bool = False,
        git_service=None,
        terminus_repo: Optional[TerminusMemoryRepository] = None,
    ):
        self.root_dir = pathlib.Path(root_dir)
        self.enable_git = enable_git
        self.enable_terminus = enable_terminus
        self.git_service = git_service
        self.terminus_repo = terminus_repo

        self.working_set = WorkingSetAppender(root_dir)
        self.journal = JournalAppender(root_dir)
        self.claim_extractor = ClaimExtractor()
        self.claim_writer = ClaimWriter(root_dir)
        self.mapper = ClaimToMemoryMapper()

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
        if extract_claims:
            try:
                claims = self.claim_extractor.extract(
                    text=item.content,
                    source_ref=item.item_id,
                )
                self.claim_writer.write_many(claims)
                result.claims_extracted = len(claims)
            except Exception as e:
                result.errors.append(f"claims: {e}")

        # Step 5: TerminusDB write (optional)
        if self.enable_terminus and self.terminus_repo:
            try:
                claims = self.claim_extractor.extract(text=item.content, source_ref=item.item_id)
                memories = self.mapper.map_many(claims, session_id=item.session_id)
                written = 0
                for m in memories:
                    if self.terminus_repo.insert_memory(m):
                        written += 1
                result.terminus_written = written
            except Exception as e:
                result.errors.append(f"terminus: {e}")

        return result
