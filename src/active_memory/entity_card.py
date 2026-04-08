import pathlib
from typing import Optional
from src.active_memory.models import EntityCard
from src.active_memory.serializers import YamlSerializer
from src.active_memory.atomic_write import atomic_write_text


class EntityCardWriter:
    def __init__(self, root_dir: pathlib.Path):
        self.root_dir = pathlib.Path(root_dir)
        self.entities_dir = self.root_dir / "active" / "entities"
        self.entities_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entity_id: str) -> pathlib.Path:
        return self.entities_dir / f"{entity_id}.yaml"

    def write(self, card: EntityCard) -> None:
        data = card.model_dump(mode="json")
        content = YamlSerializer.serialize(data)
        atomic_write_text(self._path(card.entity_id), content)

    def read(self, entity_id: str) -> Optional[EntityCard]:
        path = self._path(entity_id)
        if not path.exists():
            return None
        data = YamlSerializer.load(path)
        return EntityCard(**data)

    def list_all(self) -> list[EntityCard]:
        cards = []
        for p in self.entities_dir.glob("*.yaml"):
            data = YamlSerializer.load(p)
            cards.append(EntityCard(**data))
        return cards
