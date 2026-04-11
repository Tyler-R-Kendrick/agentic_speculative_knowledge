import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS = ["memorize", "recall", "discover", "reflect", "infer", "speculate"]


class TestSkillsUsageDoc:
    def test_skills_usage_doc_exists(self):
        doc = REPO_ROOT / "docs" / "SKILLS_USAGE.md"
        assert doc.exists(), "docs/SKILLS_USAGE.md must exist"

    def test_skills_usage_doc_references_all_skills(self):
        doc = REPO_ROOT / "docs" / "SKILLS_USAGE.md"
        content = doc.read_text()
        for skill in SKILLS:
            assert skill in content, f"docs/SKILLS_USAGE.md must reference the '{skill}' skill"

    def test_skills_usage_doc_has_python_examples(self):
        doc = REPO_ROOT / "docs" / "SKILLS_USAGE.md"
        content = doc.read_text()
        assert "```python" in content, "docs/SKILLS_USAGE.md must include Python code examples"
        assert "MemoryManager" in content, "docs/SKILLS_USAGE.md must reference MemoryManager"
        assert "MutationPipeline" in content, "docs/SKILLS_USAGE.md must reference MutationPipeline"
        assert "RetrievalComposer" in content, "docs/SKILLS_USAGE.md must reference RetrievalComposer"
        assert "TerminusMemoryRepository" in content, "docs/SKILLS_USAGE.md must reference TerminusMemoryRepository"
        assert "ManifoldRankingService" in content, "docs/SKILLS_USAGE.md must reference ManifoldRankingService"

    def test_skills_usage_doc_has_workflow_section(self):
        doc = REPO_ROOT / "docs" / "SKILLS_USAGE.md"
        content = doc.read_text()
        assert "## End-to-end workflow" in content, "docs/SKILLS_USAGE.md must have an end-to-end workflow section"


class TestCopilotInstructions:
    def test_copilot_instructions_exist(self):
        path = REPO_ROOT / ".github" / "copilot-instructions.md"
        assert path.exists(), ".github/copilot-instructions.md must exist"

    def test_copilot_instructions_reference_all_skills(self):
        path = REPO_ROOT / ".github" / "copilot-instructions.md"
        content = path.read_text()
        for skill in SKILLS:
            assert skill in content, f".github/copilot-instructions.md must reference the '{skill}' skill"

    def test_copilot_instructions_reference_key_apis(self):
        path = REPO_ROOT / ".github" / "copilot-instructions.md"
        content = path.read_text()
        assert "MemoryManager" in content
        assert "MutationPipeline" in content
        assert "RetrievalComposer" in content
        assert "TerminusMemoryRepository" in content

    def test_copilot_instructions_describe_workflow(self):
        path = REPO_ROOT / ".github" / "copilot-instructions.md"
        content = path.read_text()
        # Instructions should describe the cognitive loop
        assert "memorize" in content and "recall" in content and "infer" in content
        assert "reflect" in content and "discover" in content and "speculate" in content
