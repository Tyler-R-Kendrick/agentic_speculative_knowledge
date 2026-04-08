import pathlib
from typing import Optional, Any
from src.retrieval.active_retriever import ActiveRetriever
from src.retrieval.terminus_retriever import TerminusRetriever
from src.terminus.adapter import TerminusMemoryRepository


class RetrievalComposer:
    def __init__(
        self,
        root_dir: pathlib.Path,
        terminus_retriever: Optional[TerminusRetriever] = None,
        terminus_repo: Optional[TerminusMemoryRepository] = None,
    ):
        self.active = ActiveRetriever(root_dir)
        self.terminus = terminus_retriever or TerminusRetriever(repo=terminus_repo)

    def retrieve(
        self,
        include_terminus: bool = False,
        include_speculative: bool = False,
        inference_branch: Optional[str] = None,
    ) -> dict[str, Any]:
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
            "speculative_inference": [],
            "facet_relations": [],
        }

        if include_terminus and (self.terminus.is_available() or self.terminus.repo.has_local_data()):
            result["terminus_memories"] = self.terminus.get_memories(branch="main")
            if include_speculative and inference_branch:
                speculative = self.terminus.get_inference_nodes(inference_branch)
                result["speculative_inference"] = sorted(
                    speculative,
                    key=self._ranking_score_key,
                    reverse=True,
                )
                result["facet_relations"] = self.terminus.get_facet_relations(inference_branch)

        return result

    @staticmethod
    def _ranking_score_key(item: dict[str, Any]) -> float:
        score = item.get("ranking_score")
        return score if score is not None else -1.0
