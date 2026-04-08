import pytest
from datetime import date
from src.active_memory.models import WorkingItem
from src.journal.appender import JournalAppender
from src.persistence.pipeline import MutationPipeline


class TestMutationFlow:
    def test_basic_pipeline_run(self, tmp_path):
        pipeline = MutationPipeline(tmp_path, enable_git=False, enable_terminus=False)
        item = WorkingItem(item_type="note", content="Python is a great programming language for data science.", session_id="sess1")
        result = pipeline.run(item, mutation_kind="add", session_id="sess1")
        assert result.success
        assert result.active_memory == item.item_id
        assert result.journal_event_id is not None

    def test_pipeline_creates_journal_entry(self, tmp_path):
        from datetime import date
        from src.journal.appender import JournalAppender

        pipeline = MutationPipeline(tmp_path)
        item = WorkingItem(item_type="note", content="This is important information about the system.", session_id="sess1")
        result = pipeline.run(item, session_id="sess1")
        appender = JournalAppender(tmp_path)
        events = appender.read_day(date.today())
        assert len(events) >= 1

    def test_pipeline_with_claim_extraction(self, tmp_path):
        pipeline = MutationPipeline(tmp_path)
        item = WorkingItem(
            item_type="observation",
            content="The agent processes information and stores relevant data. Memory systems require careful design.",
            session_id="sess1",
        )
        result = pipeline.run(item, extract_claims=True)
        assert result.success
        assert result.claims_extracted >= 0

    def test_pipeline_records_active_working_set_path_for_journal_and_git(self, tmp_path):
        class FakeGitService:
            def __init__(self):
                self.files = None

            def commit(self, message, files):
                self.files = files
                return "abc123"

        git_service = FakeGitService()
        pipeline = MutationPipeline(tmp_path, enable_git=True, git_service=git_service)
        item = WorkingItem(item_type="note", content="The system stores mutable session notes in active memory.", session_id="sess1")

        result = pipeline.run(item, mutation_kind="add", session_id="sess1")
        events = JournalAppender(tmp_path).read_day(date.today())

        assert result.success
        assert git_service.files == ["active/working-set.jsonl"]
        assert events[-1].changed_files == ["active/working-set.jsonl"]
