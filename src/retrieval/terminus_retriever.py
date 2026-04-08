from typing import Optional
from src.terminus.adapter import TerminusMemoryRepository


class TerminusRetriever:
    def __init__(self, repo: Optional[TerminusMemoryRepository] = None):
        self.repo = repo or TerminusMemoryRepository()

    def get_memories(self, filters: dict = None, branch: str = "main") -> list[dict]:
        return self.repo.query_memories(filters=filters, branch=branch)

    def get_memory(self, memory_id: str) -> Optional[dict]:
        return self.repo.get_memory(memory_id)

    def get_inference_nodes(self, branch: str) -> list[dict]:
        return self.repo.query_inference_nodes(branch)

    def get_facet_relations(self, branch: str) -> list[dict]:
        return self.repo.query_facet_relations(branch)

    def is_available(self) -> bool:
        return self.repo.is_available()
