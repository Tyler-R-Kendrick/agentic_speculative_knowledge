import json
import os
import pathlib
import shutil


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
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
        previous_cwd = pathlib.Path.cwd()
        try:
            os.chdir(REPO_ROOT)
            for notebook_path in NOTEBOOK_FILES:
                notebook = json.loads(notebook_path.read_text())
                namespace = {"__name__": "__main__"}
                for cell in notebook["cells"]:
                    if cell["cell_type"] != "code":
                        continue
                    exec("".join(cell["source"]), namespace)
        finally:
            os.chdir(previous_cwd)
            for demo_path in demo_paths:
                shutil.rmtree(demo_path, ignore_errors=True)
