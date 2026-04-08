import pytest
import json
import yaml
import pathlib
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.models import WorkingItem


class TestFileFormatContracts:
    def test_session_yaml_fields(self, tmp_path):
        mgr = SessionManager(tmp_path)
        session = mgr.create_session(current_goal="test")
        session_file = tmp_path / "active" / "session.yaml"
        assert session_file.exists()
        data = yaml.safe_load(session_file.read_text())
        required_fields = ["session_id", "created_at", "last_updated_at", "status"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_working_set_jsonl_format(self, tmp_path):
        appender = WorkingSetAppender(tmp_path)
        item = WorkingItem(item_type="note", content="test content", session_id="sess1")
        appender.append(item)
        ws_file = tmp_path / "active" / "working-set.jsonl"
        assert ws_file.exists()
        lines = [l for l in ws_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        required_fields = ["item_id", "item_type", "content", "timestamp", "session_id"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_journal_jsonl_format(self, tmp_path):
        from src.journal.appender import JournalAppender
        from src.journal.models import JournalEvent
        from datetime import date
        appender = JournalAppender(tmp_path)
        event = JournalEvent(session_id="sess1", mutation_kind="add")
        appender.append(event)
        today = date.today()
        journal_file = tmp_path / "journal" / f"{today.isoformat()}.jsonl"
        assert journal_file.exists()
        lines = [l for l in journal_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        required_fields = ["event_id", "session_id", "timestamp", "mutation_kind", "actor"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
