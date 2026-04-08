import pathlib
from src.active_memory.models import WorkingItem
from src.active_memory.serializers import JsonlSerializer


class WorkingSetAppender:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.working_set_file = self.root_dir / "active" / "working-set.jsonl"

    def append(self, item: WorkingItem) -> None:
        data = item.model_dump(mode="json")
        JsonlSerializer.append_line(self.working_set_file, data)

    def read_all(self) -> list[WorkingItem]:
        rows = JsonlSerializer.read_all(self.working_set_file)
        return [WorkingItem(**row) for row in rows]
