from typing import Optional
from src.terminus.adapter import TerminusMemoryRepository


class TerminusRetriever:
    def __init__(self, repo: Optional[TerminusMemoryRepository] = None):
        self.repo = repo or TerminusMemoryRepository()

    def get_memories(self, filters: dict = None) -> list[dict]:
        return self.repo.query_memories(filters=filters)

    def get_memory(self, memory_id: str) -> Optional[dict]:
        return self.repo.get_memory(memory_id)

    def is_available(self) -> bool:
        return self.repo.is_available()
