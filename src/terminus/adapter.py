import pathlib
from collections import defaultdict
from typing import Optional, Any
import os

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
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.url = url
        self.team = os.getenv("TERMINUSDB_TEAM", team)
        self.db = os.getenv("TERMINUSDB_DB", db)
        self.user = user or os.getenv("TERMINUSDB_USER")
        self.password = password or os.getenv("TERMINUSDB_PASSWORD")
        self._client = None
        self._connected = False
        self._active_branch = None
        self._fallback_store = defaultdict(lambda: defaultdict(list))
        self.ensure_branch("main")

    def _get_client(self):
        if not HAS_TERMINUS:
            raise TerminusConnectionError("terminusdb-client not installed")
        if not self.user or not self.password:
            missing_credentials = []
            if not self.user:
                missing_credentials.append("TERMINUSDB_USER")
            if not self.password:
                missing_credentials.append("TERMINUSDB_PASSWORD")
            raise TerminusConnectionError(
                f"TerminusDB credentials must be provided explicitly or via the following environment variables: {', '.join(missing_credentials)}"
            )
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
        return self.write_memory("main", memory)

    def _select_branch(self, client, branch: str) -> None:
        if self._active_branch == branch:
            return

        selectors = ("checkout", "reset")
        for method_name in selectors:
            method = getattr(client, method_name, None)
            if not callable(method):
                continue
            for call in (
                lambda: method(branch=branch),
                lambda: method(branch_name=branch),
                lambda: method(ref=branch),
                lambda: method(branch),
            ):
                try:
                    call()
                    self._active_branch = branch
                    return
                except TypeError:
                    continue
                except Exception as e:
                    raise TerminusConnectionError(f"Cannot select branch {branch}: {e}") from e

        if hasattr(client, "branch"):
            try:
                client.branch = branch
                self._active_branch = branch
                return
            except Exception as e:
                raise TerminusConnectionError(f"Cannot select branch {branch}: {e}") from e

        raise TerminusConnectionError("Connected Terminus client does not support explicit branch selection")

    def _get_branch_client(self, branch: str):
        client = self._get_client()
        self._select_branch(client, branch)
        return client

    @staticmethod
    def _filter_documents(documents: list[dict], filters: Optional[dict] = None) -> list[dict]:
        if not filters:
            return documents
        return [doc for doc in documents if all(doc.get(key) == value for key, value in filters.items())]

    def _query_documents(self, branch: str, doc_type: str, filters: Optional[dict] = None) -> list[dict]:
        local_documents = list(self._fallback_store[branch].get(doc_type, []))
        local_documents = self._filter_documents(local_documents, filters)
        try:
            client = self._get_branch_client(branch)
            docs = client.get_all_documents(graph_type="instance", as_list=True)
            remote_documents = [decode_document(doc) for doc in docs if doc.get("@type") == doc_type]
            remote_documents = self._filter_documents(remote_documents, filters)
            return remote_documents or local_documents
        except TerminusConnectionError:
            return local_documents
        except Exception:
            return local_documents

    def ensure_branch(self, branch: str) -> str:
        self._fallback_store[branch]
        try:
            client = self._get_client()
            try:
                client.create_branch(branch)
            except Exception:
                pass
            self._select_branch(client, branch)
        except TerminusConnectionError:
            pass
        return branch

    def write_memory(self, branch: str, memory: CandidateMemory) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["Memory"].append(memory.model_dump(mode="json"))
        try:
            client = self._get_branch_client(branch)
            doc = encode_document(memory.model_dump(mode="json"))
            doc["@type"] = "Memory"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write memory {memory.memory_id}")
            return True
        except TerminusConnectionError:
            return False
        except Exception:
            return False

    def write_claim(self, branch: str, claim: Claim) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["Claim"].append(claim.model_dump(mode="json"))
        try:
            client = self._get_branch_client(branch)
            doc = encode_document(claim.model_dump(mode="json"))
            doc["@type"] = "Claim"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write claim {claim.claim_id}")
            return True
        except TerminusConnectionError:
            return False
        except Exception:
            return False

    def write_inference_node(self, branch: str, inference_node: InferenceNode) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["InferenceNode"].append(inference_node.model_dump(mode="json"))
        try:
            client = self._get_branch_client(branch)
            doc = encode_document(inference_node.model_dump(mode="json"))
            doc["@type"] = "InferenceNode"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write inference {inference_node.inference_id}")
            return True
        except TerminusConnectionError:
            return False
        except Exception:
            return False

    def write_facet_relation(self, branch: str, relation: FacetRelation) -> bool:
        self.ensure_branch(branch)
        self._fallback_store[branch]["FacetRelation"].append(relation.model_dump(mode="json"))
        try:
            client = self._get_branch_client(branch)
            doc = encode_document(relation.model_dump(mode="json"))
            doc["@type"] = "FacetRelation"
            client.insert_document(doc, graph_type="instance", commit_msg=f"write facet relation {relation.relation_id}")
            return True
        except TerminusConnectionError:
            return False
        except Exception:
            return False

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
        return self._query_documents(branch=branch, doc_type="Memory", filters=filters)

    def query_claims(self, branch: str) -> list[dict]:
        return self._query_documents(branch=branch, doc_type="Claim")

    def query_inference_nodes(self, branch: str) -> list[dict]:
        return self._query_documents(branch=branch, doc_type="InferenceNode")

    def query_facet_relations(self, branch: str) -> list[dict]:
        return self._query_documents(branch=branch, doc_type="FacetRelation")

    def is_available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def has_local_data(self) -> bool:
        return any(any(values for values in branch.values()) for branch in self._fallback_store.values())
