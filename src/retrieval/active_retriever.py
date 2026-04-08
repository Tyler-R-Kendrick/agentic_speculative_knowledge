import pathlib
from typing import Optional
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.entity_card import EntityCardWriter
from src.active_memory.task_card import TaskCardWriter
from src.claims.writer import ClaimWriter
from src.active_memory.models import SessionState, WorkingItem, EntityCard, TaskCard
from src.claims.models import Claim


class ActiveRetriever:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.session_manager = SessionManager(root_dir)
        self.working_set = WorkingSetAppender(root_dir)
        self.entity_writer = EntityCardWriter(root_dir)
        self.task_writer = TaskCardWriter(root_dir)
        self.claim_writer = ClaimWriter(root_dir)

    def get_session(self) -> Optional[SessionState]:
        return self.session_manager.load_session()

    def get_working_set(self) -> list[WorkingItem]:
        return self.working_set.read_all()

    def get_entities(self) -> list[EntityCard]:
        return self.entity_writer.list_all()

    def get_tasks(self) -> list[TaskCard]:
        return self.task_writer.list_all()

    def get_claims(self) -> list[Claim]:
        return self.claim_writer.read_all()
