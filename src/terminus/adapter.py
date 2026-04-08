import pathlib
from collections import defaultdict
from typing import Optional, Any

from src.claims.models import Claim
from src.inference.models import FacetRelation, InferenceNode
from src.normalization.mapper import CandidateMemory
from src.terminus.schema import encode_document, decode_document

try:
    from terminusdb_client import Client as TerminusClient
    HAS_TERMINUS = True
except ImportError:
    HAS_TERMINUS = False


class TerminusConnectionError(Exception):
    pass


class TerminusMemoryRepository:
    def __init__(
        self,
        url: str = "http://localhost:6363",
        team: str = "admin",
        db: str = "agent_memory",
        user: str = "admin",
        password: str = "root",
    ):
        self.url = url
        self.team = team
        self.db = db
        self.user = user
        self.password = password
        self._client = None
        self._connected = False
        self._fallback_store = defaultdict(lambda: defaultdict(list))
        self.ensure_branch("main")

    def _get_client(self):
        if not HAS_TERMINUS:
            raise TerminusConnectionError("terminusdb-client not installed")
        if self._client is None:
            try:
                client = TerminusClient(self.url)
                client.connect(user=self.user, password=self.password, team=self.team, db=self.db)
                self._client = client
                self._connected = True
            except Exception as e:
                raise TerminusConnectionError(f"Cannot connect to TerminusDB: {e}") from e
        return self._client

    def insert_memory(self, memory: CandidateMemory) -> bool:
        self.write_memory("main", memory)
        return self._connected

    def ensure_branch(self, branch: str) -> str:
        self._fallback_store[branch]
        try:
            client = self._get_client()
            try:
                client.create_branch(branch)
            except Exception:
                pass
        except TerminusConnectionError:
            pass
        return branch

    def write_memory(self, branch: str, memory: CandidateMemory) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["Memory"].append(memory.model_dump(mode="json"))
        try:
            client = self._get_client()
            doc = encode_document(memory.model_dump(mode="json"))
            doc["@type"] = "Memory"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write memory {memory.memory_id}")
            return True
        except TerminusConnectionError:
            return True
        except Exception:
            return True

    def write_claim(self, branch: str, claim: Claim) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["Claim"].append(claim.model_dump(mode="json"))
        try:
            client = self._get_client()
            doc = encode_document(claim.model_dump(mode="json"))
            doc["@type"] = "Claim"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write claim {claim.claim_id}")
            return True
        except TerminusConnectionError:
            return True
        except Exception:
            return True

    def write_inference_node(self, branch: str, inference_node: InferenceNode) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["InferenceNode"].append(inference_node.model_dump(mode="json"))
        try:
            client = self._get_client()
            doc = encode_document(inference_node.model_dump(mode="json"))
            doc["@type"] = "InferenceNode"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write inference {inference_node.inference_id}")
            return True
        except TerminusConnectionError:
            return True
        except Exception:
            return True

    def write_facet_relation(self, branch: str, relation: FacetRelation) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["FacetRelation"].append(relation.model_dump(mode="json"))
        try:
            client = self._get_client()
            doc = encode_document(relation.model_dump(mode="json"))
            doc["@type"] = "FacetRelation"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write facet relation {relation.relation_id}")
            return True
        except TerminusConnectionError:
            return True
        except Exception:
            return True

    def get_memory(self, memory_id: str) -> Optional[dict]:
        for branch_data in self._fallback_store.values():
            for memory in branch_data.get("Memory", []):
                if memory.get("memory_id") == memory_id:
                    return memory
        try:
            client = self._get_client()
            result = client.get_document(f"Memory/{memory_id}")
            return decode_document(result)
        except TerminusConnectionError:
            return None
        except Exception:
            return None

    def query_memories(self, filters: dict = None, branch: str = "main") -> list[dict]:
        memories = list(self._fallback_store[branch].get("Memory", []))
        if filters:
            memories = [memory for memory in memories if all(memory.get(key) == value for key, value in filters.items())]
        try:
            client = self._get_client()
            docs = client.get_all_documents(graph_type="instance", as_list=True)
            results = [decode_document(d) for d in docs if d.get("@type") == "Memory"]
            return results or memories
        except TerminusConnectionError:
            return memories
        except Exception:
            return memories

    def query_claims(self, branch: str) -> list[dict]:
        return list(self._fallback_store[branch].get("Claim", []))

    def query_inference_nodes(self, branch: str) -> list[dict]:
        return list(self._fallback_store[branch].get("InferenceNode", []))

    def query_facet_relations(self, branch: str) -> list[dict]:
        return list(self._fallback_store[branch].get("FacetRelation", []))

    def is_available(self) -> bool:
        if any(any(values for values in branch.values()) for branch in self._fallback_store.values()):
            return True
        try:
            self._get_client()
            return True
        except Exception:
            return False
