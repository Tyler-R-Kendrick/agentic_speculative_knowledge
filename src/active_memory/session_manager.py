import pathlib
from datetime import datetime
from typing import Optional

from src.active_memory.models import SessionState
from src.active_memory.serializers import YamlSerializer
from src.active_memory.atomic_write import atomic_write_text
from src.active_memory.layout import initialize_layout


class SessionManager:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.session_file = self.root_dir / "active" / "session.yaml"

    def create_session(self, current_goal: Optional[str] = None, metadata: dict = None) -> SessionState:
        initialize_layout(self.root_dir)
        session = SessionState(current_goal=current_goal, metadata=metadata or {})
        self._save(session)
        return session

    def load_session(self) -> Optional[SessionState]:
        if not self.session_file.exists():
            return None
        data = YamlSerializer.load(self.session_file)
        if not data or "session_id" not in data:
            return None
        return SessionState(**data)

    def update_session(self, **kwargs) -> SessionState:
        session = self.load_session()
        if session is None:
            raise ValueError("No session found")
        kwargs["last_updated_at"] = datetime.utcnow()
        updated = session.model_copy(update=kwargs)
        self._save(updated)
        return updated

    def close_session(self) -> SessionState:
        return self.update_session(status="closed")

    def _save(self, session: SessionState) -> None:
        data = session.model_dump(mode="json")
        content = YamlSerializer.serialize(data)
        atomic_write_text(self.session_file, content)
