import json
import pathlib
from typing import Any
from src.active_memory.serializers import YamlSerializer
from src.active_memory.atomic_write import atomic_write_text


class CheckpointManager:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.checkpoints_dir = self.root_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> pathlib.Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self.checkpoints_dir / f"{safe_name}.yaml"

    def save(self, name: str, data: dict) -> None:
        content = YamlSerializer.serialize(data)
        atomic_write_text(self._path(name), content)

    def load(self, name: str) -> dict[str, Any]:
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint '{name}' not found")
        return YamlSerializer.load(path)

    def list_checkpoints(self) -> list[str]:
        return [p.stem for p in self.checkpoints_dir.glob("*.yaml")]
