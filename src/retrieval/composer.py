import pathlib
from typing import Optional, Any
from src.retrieval.active_retriever import ActiveRetriever
from src.retrieval.terminus_retriever import TerminusRetriever


class RetrievalComposer:
    def __init__(self, root_dir: pathlib.Path, terminus_retriever: Optional[TerminusRetriever] = None):
        self.active = ActiveRetriever(root_dir)
        self.terminus = terminus_retriever or TerminusRetriever()

    def retrieve(self, include_terminus: bool = False) -> dict[str, Any]:
        session = self.active.get_session()
        working_items = self.active.get_working_set()
        entities = self.active.get_entities()
        tasks = self.active.get_tasks()
        claims = self.active.get_claims()

        result = {
            "session": session.model_dump(mode="json") if session else None,
            "working_items": [i.model_dump(mode="json") for i in working_items],
            "entities": [e.model_dump(mode="json") for e in entities],
            "tasks": [t.model_dump(mode="json") for t in tasks],
            "claims": [c.model_dump(mode="json") for c in claims],
            "terminus_memories": [],
        }

        if include_terminus and self.terminus.is_available():
            result["terminus_memories"] = self.terminus.get_memories()

        return result
