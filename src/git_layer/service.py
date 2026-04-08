import pathlib
from typing import Optional
try:
    import git
    HAS_GIT = True
except ImportError:
    HAS_GIT = False


class GitService:
    def __init__(self, repo_path: pathlib.Path = None):
        self.repo_path = pathlib.Path(repo_path) if repo_path else pathlib.Path(".")
        self._repo = None

    def _get_repo(self):
        if self._repo is None:
            if not HAS_GIT:
                raise RuntimeError("gitpython not installed")
            self._repo = git.Repo(self.repo_path)
        return self._repo

    def commit(self, message: str, files: list[str]) -> str:
        repo = self._get_repo()
        if files:
            repo.index.add(files)
        repo.index.commit(message)
        return repo.head.commit.hexsha

    def get_changed_files(self) -> list[str]:
        repo = self._get_repo()
        changed = []
        for item in repo.index.diff(None):
            changed.append(item.a_path)
        for item in repo.untracked_files:
            changed.append(item)
        return changed

    def get_current_commit(self) -> str:
        repo = self._get_repo()
        try:
            return repo.head.commit.hexsha
        except Exception:
            return ""

    def format_commit_message(self, kind: str, summary: str) -> str:
        return f"[{kind}] {summary}"
