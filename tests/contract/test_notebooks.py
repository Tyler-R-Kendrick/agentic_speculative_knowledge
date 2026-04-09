import json
import pathlib
import shutil
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
NOTEBOOK_EXECUTION_TIMEOUT_SECONDS = 120
NOTEBOOK_FILES = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))


def notebook_demo_path(notebook_path: pathlib.Path) -> pathlib.Path:
    prefix, separator, _ = notebook_path.stem.partition("_")
    if not separator or not prefix.isdigit():
        raise ValueError(f"Unexpected notebook filename format: {notebook_path.name}")
    return NOTEBOOKS_DIR / f".demo-memory-{prefix}"


class TestExampleNotebooks:
    def test_notebook_demo_path_uses_numeric_prefix(self):
        assert notebook_demo_path(NOTEBOOKS_DIR / "04_example.ipynb") == NOTEBOOKS_DIR / ".demo-memory-04"

    def test_notebook_demo_path_rejects_invalid_filename_format(self):
        try:
            notebook_demo_path(NOTEBOOKS_DIR / "example.ipynb")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError for notebook filename without numeric prefix")

    def test_notebook_files_exist(self):
        assert NOTEBOOK_FILES
        for notebook_path in NOTEBOOK_FILES:
            assert notebook_path.exists(), f"Missing notebook: {notebook_path.name}"

    def test_notebooks_are_valid_json_with_code_cells(self):
        for notebook_path in NOTEBOOK_FILES:
            notebook = json.loads(notebook_path.read_text())
            assert notebook["nbformat"] == 4
            assert notebook["metadata"]["kernelspec"]["name"] == "python3"
            assert any(cell["cell_type"] == "code" for cell in notebook["cells"])

    def test_notebook_code_cells_execute(self):
        try:
            for notebook_path in NOTEBOOK_FILES:
                notebook = json.loads(notebook_path.read_text())
                code = "\n\n".join(
                    "".join(cell["source"])
                    for cell in notebook["cells"]
                    if cell["cell_type"] == "code"
                )
                subprocess.run(
                    [sys.executable, "-c", code],
                    cwd=REPO_ROOT,
                    check=True,
                    timeout=NOTEBOOK_EXECUTION_TIMEOUT_SECONDS,
                )
        finally:
            for cleanup_notebook_path in NOTEBOOK_FILES:
                demo_path = notebook_demo_path(cleanup_notebook_path)
                shutil.rmtree(demo_path, ignore_errors=True)
