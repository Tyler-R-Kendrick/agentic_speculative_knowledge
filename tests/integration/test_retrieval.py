import pytest
from src.active_memory.models import WorkingItem, EntityCard, TaskCard
from src.retrieval.active_retriever import ActiveRetriever
from src.retrieval.composer import RetrievalComposer
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.entity_card import EntityCardWriter
from src.active_memory.task_card import TaskCardWriter


class TestActiveRetrieval:
    def test_retrieve_empty(self, tmp_path):
        retriever = ActiveRetriever(tmp_path)
        items = retriever.get_working_set()
        assert items == []
        entities = retriever.get_entities()
        assert entities == []

    def test_retrieve_after_writes(self, tmp_path):
        mgr = SessionManager(tmp_path)
        mgr.create_session(current_goal="test")
        ws = WorkingSetAppender(tmp_path)
        ws.append(WorkingItem(item_type="note", content="hello", session_id="s1"))
        ec = EntityCardWriter(tmp_path)
        ec.write(EntityCard(name="Alice", entity_type="person"))

        retriever = ActiveRetriever(tmp_path)
        session = retriever.get_session()
        assert session is not None
        items = retriever.get_working_set()
        assert len(items) == 1
        entities = retriever.get_entities()
        assert len(entities) == 1

    def test_composer_retrieve(self, tmp_path):
        composer = RetrievalComposer(tmp_path)
        context = composer.retrieve(include_terminus=False)
        assert "session" in context
        assert "working_items" in context
        assert "entities" in context
        assert "tasks" in context
        assert "claims" in context
