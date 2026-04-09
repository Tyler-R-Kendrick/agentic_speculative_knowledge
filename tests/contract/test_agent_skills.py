import pathlib
import re

import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
SKILL_FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
EXPECTED_SKILLS = {
    "memorize": {
        "notebooks": ["notebooks/01_active_memory_basics.ipynb"],
        "references": [
            "src/api/memory_manager.py",
            "src/active_memory/session_manager.py",
            "tests/unit/test_active_memory.py",
        ],
        "python_imports": [
            "from src.api.memory_manager import MemoryManager",
        ],
    },
    "infer": {
        "notebooks": ["notebooks/02_speculative_inference_and_facets.ipynb"],
        "references": [
            "src/persistence/pipeline.py",
            "src/inference/generator.py",
            "tests/integration/test_inference_flow.py",
        ],
        "python_imports": [
            "from src.persistence.pipeline import MutationPipeline",
            "from src.inference.generator import InferenceGenerator",
        ],
    },
    "recall": {
        "notebooks": ["notebooks/03_historical_recall.ipynb"],
        "references": [
            "src/journal/appender.py",
            "src/retrieval/composer.py",
            "tests/integration/test_retrieval.py",
        ],
        "python_imports": [
            "from src.retrieval.composer import RetrievalComposer",
            "from src.journal.appender import JournalAppender",
        ],
    },
    "reflect": {
        "notebooks": ["notebooks/04_terminus_temporal_graph_memory.ipynb"],
        "references": [
            "src/terminus/adapter.py",
            "src/terminus/branch_manager.py",
            "tests/unit/test_terminus.py",
        ],
        "python_imports": [
            "from src.terminus.adapter import TerminusMemoryRepository",
            "from src.terminus.branch_manager import session_branch_name",
        ],
    },
    "discover": {
        "notebooks": [
            "notebooks/05_knowledge_discovery_through_facets.ipynb",
            "notebooks/06_manifold_mapping_for_discovery.ipynb",
        ],
        "references": [
            "src/inference/models.py",
            "src/manifold_sidecar/service.py",
            "src/retrieval/composer.py",
            "tests/integration/test_inference_flow.py",
        ],
        "python_imports": [
            "from src.manifold_sidecar import ManifoldRankingService",
            "from src.inference.generator import InferenceGenerator",
        ],
    },
}


def parse_skill(skill_path: pathlib.Path) -> tuple[dict, str]:
    match = SKILL_FRONTMATTER_PATTERN.match(skill_path.read_text())
    assert match, f"Skill file must include YAML frontmatter: {skill_path}"
    metadata = yaml.safe_load(match.group(1))
    assert isinstance(metadata, dict), f"Invalid skill frontmatter: {skill_path}"
    return metadata, match.group(2)


class TestAgentSkills:
    def test_expected_skill_directories_exist(self):
        assert SKILLS_DIR.exists()
        assert {path.name for path in SKILLS_DIR.iterdir() if path.is_dir()} == set(EXPECTED_SKILLS)

    def test_skill_files_have_required_frontmatter(self):
        for skill_name in EXPECTED_SKILLS:
            skill_path = SKILLS_DIR / skill_name / "SKILL.md"
            assert skill_path.exists(), f"Missing skill file: {skill_path}"
            metadata, body = parse_skill(skill_path)
            assert metadata["name"] == skill_name
            assert metadata["description"]
            assert body.strip()

    def test_skills_reference_grounding_examples_and_code(self):
        for skill_name, expectations in EXPECTED_SKILLS.items():
            metadata, body = parse_skill(SKILLS_DIR / skill_name / "SKILL.md")
            assert skill_name in metadata["description"]
            for notebook in expectations["notebooks"]:
                assert notebook in body, f"Skill '{skill_name}' missing notebook reference: {notebook}"
            for reference in expectations["references"]:
                assert reference in body, f"Skill '{skill_name}' missing code reference: {reference}"

    def test_skills_include_python_code_examples(self):
        for skill_name, expectations in EXPECTED_SKILLS.items():
            _, body = parse_skill(SKILLS_DIR / skill_name / "SKILL.md")
            assert "```python" in body, f"Skill '{skill_name}' must include a Python code example"
            for python_import in expectations["python_imports"]:
                assert python_import in body, f"Skill '{skill_name}' missing Python import: {python_import}"
