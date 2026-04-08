import pathlib
from typing import Optional, Any
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
        try:
            client = self._get_client()
            doc = encode_document(memory.model_dump(mode="json"))
            doc["@type"] = "Memory"
            client.insert_document(doc)
            return True
        except TerminusConnectionError:
            return False
        except Exception:
            return False

    def get_memory(self, memory_id: str) -> Optional[dict]:
        try:
            client = self._get_client()
            result = client.get_document(f"Memory/{memory_id}")
            return decode_document(result)
        except TerminusConnectionError:
            return None
        except Exception:
            return None

    def query_memories(self, filters: dict = None) -> list[dict]:
        try:
            client = self._get_client()
            docs = client.get_all_documents(graph_type="instance", as_list=True)
            results = [decode_document(d) for d in docs if d.get("@type") == "Memory"]
            return results
        except TerminusConnectionError:
            return []
        except Exception:
            return []

    def is_available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False
