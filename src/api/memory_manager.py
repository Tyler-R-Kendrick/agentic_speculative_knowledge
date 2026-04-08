import pathlib
from typing import Optional, Any
from src.active_memory.layout import initialize_layout
from src.active_memory.session_manager import SessionManager
from src.active_memory.working_set import WorkingSetAppender
from src.active_memory.entity_card import EntityCardWriter
from src.active_memory.task_card import TaskCardWriter
from src.active_memory.models import SessionState, WorkingItem, EntityCard, TaskCard
from src.claims.extractor import ClaimExtractor
from src.claims.writer import ClaimWriter
from src.claims.models import Claim
from src.retrieval.composer import RetrievalComposer
from src.governance.promotion import PromotionEngine
from src.normalization.mapper import ClaimToMemoryMapper


class MemoryManager:
    def __init__(self, root_dir: pathlib.Path = None):
        self.root_dir = pathlib.Path(root_dir) if root_dir else pathlib.Path(".agent-memory")
        initialize_layout(self.root_dir)
        self.session_manager = SessionManager(self.root_dir)
        self.working_set = WorkingSetAppender(self.root_dir)
        self.entity_writer = EntityCardWriter(self.root_dir)
        self.task_writer = TaskCardWriter(self.root_dir)
        self.claim_writer = ClaimWriter(self.root_dir)
        self.claim_extractor = ClaimExtractor()
        self.composer = RetrievalComposer(self.root_dir)
        self.promotion_engine = PromotionEngine()
        self.mapper = ClaimToMemoryMapper()

    def start_session(self, current_goal: Optional[str] = None, metadata: dict = None) -> SessionState:
        return self.session_manager.create_session(current_goal=current_goal, metadata=metadata or {})

    def end_session(self) -> SessionState:
        return self.session_manager.close_session()

    def add_working_item(self, item_type: str, content: str, session_id: str = "", metadata: dict = None) -> WorkingItem:
        session = self.session_manager.load_session()
        sid = session_id or (session.session_id if session else "")
        item = WorkingItem(item_type=item_type, content=content, session_id=sid, metadata=metadata or {})
        self.working_set.append(item)
        return item

    def add_entity(self, name: str, entity_type: str, description: Optional[str] = None, attributes: dict = None, session_id: Optional[str] = None) -> EntityCard:
        card = EntityCard(name=name, entity_type=entity_type, description=description, attributes=attributes or {}, session_id=session_id)
        self.entity_writer.write(card)
        return card

    def add_task(self, title: str, description: Optional[str] = None, priority: int = 0, session_id: Optional[str] = None, metadata: dict = None) -> TaskCard:
        card = TaskCard(title=title, description=description, priority=priority, session_id=session_id, metadata=metadata or {})
        self.task_writer.write(card)
        return card

    def extract_claims(self, text: str, source_ref: Optional[str] = None) -> list[Claim]:
        claims = self.claim_extractor.extract(text=text, source_ref=source_ref)
        self.claim_writer.write_many(claims)
        return claims

    def retrieve_context(self, include_terminus: bool = False) -> dict[str, Any]:
        return self.composer.retrieve(include_terminus=include_terminus)

    def promote_memories(self, context: dict = None) -> list[dict]:
        claims = self.claim_writer.read_all()
        session = self.session_manager.load_session()
        session_id = session.session_id if session else None
        memories = self.mapper.map_many(claims, session_id=session_id)
        results = []
        for m in memories:
            r = self.promotion_engine.promote(m, context=context)
            results.append({"memory_id": r.memory_id, "promoted": r.promoted, "reasons": r.reasons})
        return results
