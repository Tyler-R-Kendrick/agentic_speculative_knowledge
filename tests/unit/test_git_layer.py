import pytest
import pathlib
from src.git_layer.service import GitService


class TestGitService:
    def test_commit_message_formatting(self):
        service = GitService()
        msg = service.format_commit_message("add", "new working item")
        assert msg == "[add] new working item"

    def test_commit_message_various_kinds(self):
        service = GitService()
        for kind in ["add", "update", "delete", "promote"]:
            msg = service.format_commit_message(kind, "summary")
            assert f"[{kind}]" in msg
            assert "summary" in msg

    def test_changed_file_detection(self, tmp_path):
        import git as gitlib
        repo = gitlib.Repo.init(tmp_path)
        repo.config_writer().set_value("user", "name", "Test").release()
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        service = GitService(tmp_path)
        changed = service.get_changed_files()
        assert "test.txt" in changed
