import pathlib
from typing import Any
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.entity_card import EntityCardWriter
from src.active_memory.task_card import TaskCardWriter


class CurrentContextBuilder:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.session_manager = SessionManager(root_dir)
        self.working_set = WorkingSetAppender(root_dir)
        self.entity_writer = EntityCardWriter(root_dir)
        self.task_writer = TaskCardWriter(root_dir)

    def build(self) -> dict[str, Any]:
        session = self.session_manager.load_session()
        working_items = self.working_set.read_all()
        entities = self.entity_writer.list_all()
        tasks = self.task_writer.list_all()

        return {
            "session": session.model_dump(mode="json") if session else None,
            "working_items": [i.model_dump(mode="json") for i in working_items],
            "entities": [e.model_dump(mode="json") for e in entities],
            "tasks": [t.model_dump(mode="json") for t in tasks],
        }
