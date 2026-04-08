import pathlib
from typing import Optional
from src.active_memory.models import TaskCard
from src.active_memory.serializers import YamlSerializer
from src.active_memory.atomic_write import atomic_write_text


class TaskCardWriter:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.tasks_dir = self.root_dir / "active" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> pathlib.Path:
        return self.tasks_dir / f"{task_id}.yaml"

    def write(self, card: TaskCard) -> None:
        data = card.model_dump(mode="json")
        content = YamlSerializer.serialize(data)
        atomic_write_text(self._path(card.task_id), content)

    def read(self, task_id: str) -> Optional[TaskCard]:
        path = self._path(task_id)
        if not path.exists():
            return None
        data = YamlSerializer.load(path)
        return TaskCard(**data)

    def list_all(self) -> list[TaskCard]:
        cards = []
        for p in self.tasks_dir.glob("*.yaml"):
            data = YamlSerializer.load(p)
            cards.append(TaskCard(**data))
        return cards
