import pathlib
from datetime import date, datetime
from src.journal.models import JournalEvent
from src.active_memory.serializers import JsonlSerializer


class JournalAppender:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.journal_dir = self.root_dir / "journal"
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    def _day_path(self, d: date) -> pathlib.Path:
        return self.journal_dir / f"{d.isoformat()}.jsonl"

    def append(self, event: JournalEvent) -> None:
        data = event.model_dump(mode="json")
        d = event.timestamp.date() if hasattr(event.timestamp, "date") else date.today()
        JsonlSerializer.append_line(self._day_path(d), data)

    def read_day(self, d: date) -> list[JournalEvent]:
        rows = JsonlSerializer.read_all(self._day_path(d))
        return [JournalEvent(**row) for row in rows]
