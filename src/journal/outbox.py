import pathlib
from typing import Callable, Optional
from src.journal.models import JournalEvent
from src.active_memory.serializers import JsonlSerializer


class RetryableOutbox:
    def __init__(self, root_dir: pathlib.Path, max_retries: int = 3):
        self.root_dir = pathlib.Path(root_dir)
        self.outbox_file = self.root_dir / "journal" / "outbox.jsonl"
        self.delivered_file = self.root_dir / "journal" / "delivered.jsonl"
        self.max_retries = max_retries
        self.outbox_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_delivered_ids(self) -> set[str]:
        rows = JsonlSerializer.read_all(self.delivered_file)
        return {row["event_id"] for row in rows}

    def enqueue(self, event: JournalEvent) -> None:
        data = event.model_dump(mode="json")
        data["_retry_count"] = 0
        JsonlSerializer.append_line(self.outbox_file, data)

    def deliver_all(self, handler: Callable[[JournalEvent], bool]) -> dict:
        delivered_ids = self._load_delivered_ids()
        rows = JsonlSerializer.read_all(self.outbox_file)
        results = {"delivered": 0, "failed": 0, "skipped": 0}

        pending = []
        for row in rows:
            event_id = row.get("event_id")
            if event_id in delivered_ids:
                results["skipped"] += 1
                continue
            retry_count = row.pop("_retry_count", 0)
            event = JournalEvent(**{k: v for k, v in row.items() if not k.startswith("_")})
            success = False
            try:
                success = handler(event)
            except Exception:
                pass

            if success:
                results["delivered"] += 1
                JsonlSerializer.append_line(self.delivered_file, {"event_id": event_id})
            else:
                retry_count += 1
                if retry_count < self.max_retries:
                    row_with_retry = event.model_dump(mode="json")
                    row_with_retry["_retry_count"] = retry_count
                    pending.append(row_with_retry)
                    results["failed"] += 1
                else:
                    results["failed"] += 1

        # Rewrite outbox with only pending items
        if self.outbox_file.exists():
            self.outbox_file.unlink()
        for row in pending:
            JsonlSerializer.append_line(self.outbox_file, row)

        return results
