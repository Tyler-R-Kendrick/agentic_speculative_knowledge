import re
from typing import Optional

try:
    from terminusdb_client import Client as TerminusClient
    HAS_TERMINUS = True
except ImportError:
    HAS_TERMINUS = False


def session_branch_name(session_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", session_id)
    return f"session-{safe}"


def feature_branch_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_/-]", "-", name)
    return f"feature/{safe}"


class BranchManager:
    def __init__(self, url: str = "http://localhost:6363", team: str = "admin", db: str = "agent_memory"):
        self.url = url
        self.team = team
        self.db = db
        self._client = None

    def _get_client(self):
        if not HAS_TERMINUS:
            raise RuntimeError("terminusdb-client not installed")
        if self._client is None:
            client = TerminusClient(self.url)
            client.connect(team=self.team, db=self.db)
            self._client = client
        return self._client

    def create_session_branch(self, session_id: str) -> str:
        branch = session_branch_name(session_id)
        try:
            client = self._get_client()
            client.create_branch(branch)
        except Exception:
            pass
        return branch

    def create_feature_branch(self, name: str) -> str:
        branch = feature_branch_name(name)
        try:
            client = self._get_client()
            client.create_branch(branch)
        except Exception:
            pass
        return branch
