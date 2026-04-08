import re
from typing import Optional


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


class EntityLinker:
    def __init__(self):
        self._canonical: dict[str, str] = {}

    def register(self, name: str) -> str:
        norm = _normalize(name)
        if norm not in self._canonical:
            self._canonical[norm] = name
        return self._canonical[norm]

    def link(self, name: str) -> str:
        norm = _normalize(name)
        return self._canonical.get(norm, name)

    def link_entities(self, entities: list[str]) -> list[str]:
        return [self.link(e) for e in entities]

    def extract_and_link(self, text: str) -> list[str]:
        words = text.split()
        entities = []
        for i, w in enumerate(words):
            clean = re.sub(r"[^\w]", "", w)
            if i > 0 and clean and clean[0].isupper() and len(clean) > 2:
                entities.append(self.register(clean))
        return list(dict.fromkeys(entities))
