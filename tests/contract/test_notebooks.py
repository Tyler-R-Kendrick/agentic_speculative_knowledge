import json
import pathlib
import shutil
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
NOTEBOOK_EXECUTION_TIMEOUT_SECONDS = 60
NOTEBOOK_FILES = [
    NOTEBOOKS_DIR / "01_active_memory_basics.ipynb",
    NOTEBOOKS_DIR / "02_speculative_inference_and_facets.ipynb",
    NOTEBOOKS_DIR / "03_historical_recall.ipynb",
]


class TestExampleNotebooks:
    def test_notebook_files_exist(self):
        for notebook_path in NOTEBOOK_FILES:
            assert notebook_path.exists(), f"Missing notebook: {notebook_path.name}"

    def test_notebooks_are_valid_json_with_code_cells(self):
        for notebook_path in NOTEBOOK_FILES:
            notebook = json.loads(notebook_path.read_text())
            assert notebook["nbformat"] == 4
            assert notebook["metadata"]["kernelspec"]["name"] == "python3"
            assert any(cell["cell_type"] == "code" for cell in notebook["cells"])

    def test_notebook_code_cells_execute(self):
        demo_paths = [
            NOTEBOOKS_DIR / ".demo-memory-01",
            NOTEBOOKS_DIR / ".demo-memory-02",
            NOTEBOOKS_DIR / ".demo-memory-03",
        ]
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
            for demo_path in demo_paths:
                shutil.rmtree(demo_path, ignore_errors=True)
