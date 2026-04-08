import pytest
import pathlib
from datetime import datetime

from src.active_memory.models import SessionState, WorkingItem, EntityCard, TaskCard, Claim
from src.active_memory.atomic_write import atomic_write_text, atomic_write_bytes
from src.active_memory.serializers import YamlSerializer, JsonlSerializer
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.entity_card import EntityCardWriter
from src.active_memory.task_card import TaskCardWriter
from src.active_memory.checkpoint import CheckpointManager


class TestAtomicWrite:
    def test_atomic_write_creates_file(self, tmp_path):
        target = tmp_path / "test.txt"
        atomic_write_text(target, "hello world")
        assert target.exists()
        assert target.read_text() == "hello world"

    def test_atomic_write_is_atomic(self, tmp_path):
        target = tmp_path / "test.txt"
        atomic_write_text(target, "initial")
        # Simulate overwrite
        atomic_write_text(target, "updated")
        assert target.read_text() == "updated"
        # .tmp should not linger
        assert not target.with_suffix(".txt.tmp").exists()

    def test_atomic_write_overwrites(self, tmp_path):
        target = tmp_path / "existing.yaml"
        atomic_write_text(target, "v1")
        atomic_write_text(target, "v2")
        assert target.read_text() == "v2"

    def test_atomic_write_bytes(self, tmp_path):
        target = tmp_path / "data.bin"
        atomic_write_bytes(target, b"\x00\x01\x02")
        assert target.read_bytes() == b"\x00\x01\x02"


class TestSerializers:
    def test_yaml_round_trip(self):
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        text = YamlSerializer.serialize(data)
        restored = YamlSerializer.deserialize(text)
        assert restored == data

    def test_jsonl_round_trip(self, tmp_path):
        path = tmp_path / "test.jsonl"
        JsonlSerializer.append_line(path, {"id": "1", "value": "a"})
        JsonlSerializer.append_line(path, {"id": "2", "value": "b"})
        rows = JsonlSerializer.read_all(path)
        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[1]["id"] == "2"

    def test_jsonl_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        rows = JsonlSerializer.read_all(path)
        assert rows == []


class TestSessionManager:
    def test_create_session(self, tmp_path):
        mgr = SessionManager(tmp_path)
        session = mgr.create_session(current_goal="test goal")
        assert session.session_id
        assert session.status == "active"
        assert session.current_goal == "test goal"

    def test_load_session(self, tmp_path):
        mgr = SessionManager(tmp_path)
        created = mgr.create_session()
        loaded = mgr.load_session()
        assert loaded is not None
        assert loaded.session_id == created.session_id

    def test_update_session(self, tmp_path):
        mgr = SessionManager(tmp_path)
        mgr.create_session()
        updated = mgr.update_session(current_goal="new goal")
        assert updated.current_goal == "new goal"
        loaded = mgr.load_session()
        assert loaded.current_goal == "new goal"

    def test_close_session(self, tmp_path):
        mgr = SessionManager(tmp_path)
        mgr.create_session()
        closed = mgr.close_session()
        assert closed.status == "closed"
        loaded = mgr.load_session()
        assert loaded.status == "closed"


class TestWorkingSetAppender:
    def test_append_item(self, tmp_path):
        appender = WorkingSetAppender(tmp_path)
        item = WorkingItem(item_type="note", content="test content", session_id="sess1")
        appender.append(item)
        items = appender.read_all()
        assert len(items) == 1
        assert items[0].content == "test content"

    def test_read_all(self, tmp_path):
        appender = WorkingSetAppender(tmp_path)
        for i in range(3):
            item = WorkingItem(item_type="note", content=f"content {i}", session_id="sess1")
            appender.append(item)
        items = appender.read_all()
        assert len(items) == 3

    def test_multiple_items(self, tmp_path):
        appender = WorkingSetAppender(tmp_path)
        item1 = WorkingItem(item_type="note", content="first", session_id="s1")
        item2 = WorkingItem(item_type="task", content="second", session_id="s1")
        appender.append(item1)
        appender.append(item2)
        items = appender.read_all()
        assert items[0].item_type == "note"
        assert items[1].item_type == "task"

    def test_empty_working_set(self, tmp_path):
        appender = WorkingSetAppender(tmp_path)
        items = appender.read_all()
        assert items == []


class TestCheckpointManager:
    def test_save_and_load(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        data = {"step": 1, "value": "hello", "nested": {"a": 2}}
        mgr.save("step1", data)
        loaded = mgr.load("step1")
        assert loaded == data

    def test_list_checkpoints(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save("cp1", {"x": 1})
        mgr.save("cp2", {"x": 2})
        checkpoints = mgr.list_checkpoints()
        assert "cp1" in checkpoints
        assert "cp2" in checkpoints

    def test_checkpoint_not_found(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.load("nonexistent")


class TestEntityCardWriter:
    def test_write_and_read(self, tmp_path):
        writer = EntityCardWriter(tmp_path)
        card = EntityCard(name="Alice", entity_type="person")
        writer.write(card)
        loaded = writer.read(card.entity_id)
        assert loaded is not None
        assert loaded.name == "Alice"

    def test_list_all(self, tmp_path):
        writer = EntityCardWriter(tmp_path)
        writer.write(EntityCard(name="Alice", entity_type="person"))
        writer.write(EntityCard(name="Bob", entity_type="person"))
        cards = writer.list_all()
        assert len(cards) == 2


class TestTaskCardWriter:
    def test_write_and_read(self, tmp_path):
        writer = TaskCardWriter(tmp_path)
        card = TaskCard(title="Fix bug", description="urgent fix")
        writer.write(card)
        loaded = writer.read(card.task_id)
        assert loaded is not None
        assert loaded.title == "Fix bug"

    def test_list_all(self, tmp_path):
        writer = TaskCardWriter(tmp_path)
        writer.write(TaskCard(title="Task 1"))
        writer.write(TaskCard(title="Task 2"))
        tasks = writer.list_all()
        assert len(tasks) == 2
