import re

try:
    from terminusdb_client import Client as TerminusClient
    HAS_TERMINUS = True
except ImportError:
    HAS_TERMINUS = False


def _sanitize(value: str, allow_slash: bool = False) -> str:
    pattern = r"[^a-zA-Z0-9_/-]" if allow_slash else r"[^a-zA-Z0-9_-]"
    return re.sub(pattern, "-", value).strip("-")


def session_branch_name(session_id: str) -> str:
    return f"session/{_sanitize(session_id)}"


def reflection_branch_name(task_id: str) -> str:
    return f"reflection/{_sanitize(task_id, allow_slash=True)}"


def inference_branch_name(session_id: str) -> str:
    return f"inference/{_sanitize(session_id)}"


def verification_branch_name(run_id: str) -> str:
    return f"verification/{_sanitize(run_id)}"


def user_branch_name(user_id: str) -> str:
    return f"user/{_sanitize(user_id)}"


def team_branch_name(team_id: str) -> str:
    return f"team/{_sanitize(team_id)}"


def incident_branch_name(incident_id: str) -> str:
    return f"incident/{_sanitize(incident_id)}"


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
        return self._create_branch(branch)

    def create_reflection_branch(self, task_id: str) -> str:
        return self._create_branch(reflection_branch_name(task_id))

    def create_inference_branch(self, session_id: str) -> str:
        return self._create_branch(inference_branch_name(session_id))

    def create_verification_branch(self, run_id: str) -> str:
        return self._create_branch(verification_branch_name(run_id))

    def _create_branch(self, branch: str) -> str:
        try:
            client = self._get_client()
            client.create_branch(branch)
        except Exception:
            pass
        return branch
