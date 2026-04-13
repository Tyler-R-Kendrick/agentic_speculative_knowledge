"""
Contract tests for the train-prompt workflow integration.

Architecture:
- train-prompt.md is AUTHORED in this repo (not a copy of upstream).
- train-prompt.lock.yml is COMPILED from our .md via `gh aw compile`.
- Upstream agents, shared fragments, and MCP source are overlaid at
  workflow runtime by copilot-setup-steps.yml — never committed.
- copilot-auto-training provides the trainer agents, MCP server code,
  and shared workflow fragments at runtime only.
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _gitignored(rel_path: str) -> bool:
    """Return True if the path is gitignored in this repository."""
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def _tracked(rel_path: str) -> bool:
    """Return True if the path is tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() != ""


# ---------------------------------------------------------------------------
# Authored files — MUST be committed
# ---------------------------------------------------------------------------

AUTHORED_FILES = [
    ".github/workflows/train-prompt.md",
    ".github/workflows/copilot-setup-steps.yml",
    ".github/workflows/sync-from-upstream.yml",
    ".github/workflows/daily-feature-extraction.md",
    ".github/workflows/shared/repo-runtime-context.md",
    ".devcontainer/post-start.sh",
    ".devcontainer/devcontainer.json",
    ".devcontainer/docker-compose.yml",
    "tools/agent-skills-mcp/pyproject.toml",
]


@pytest.mark.parametrize("rel_path", AUTHORED_FILES)
def test_authored_file_exists(rel_path: str) -> None:
    """Authored/repo-specific files must be committed and present."""
    assert (REPO_ROOT / rel_path).is_file(), (
        f"{rel_path} is missing — it is authored in this repo and must be committed."
    )


@pytest.mark.parametrize("rel_path", AUTHORED_FILES)
def test_authored_file_not_gitignored(rel_path: str) -> None:
    """Authored files must NOT be gitignored."""
    assert not _gitignored(rel_path), (
        f"{rel_path} is gitignored but it is authored in this repo and must be committed."
    )


# ---------------------------------------------------------------------------
# train-prompt.md is our authored workflow (not a copy of upstream)
# ---------------------------------------------------------------------------

def test_train_prompt_md_is_authored() -> None:
    """train-prompt.md must be an authored workflow, not a copy of upstream.
    It should reference the repo-runtime-context.md import (our file)
    rather than upstream's trainer.agent.md import."""
    md = (REPO_ROOT / ".github" / "workflows" / "train-prompt.md").read_text()
    # Our .md imports our own shared context, not upstream's agents
    assert "shared/repo-runtime-context.md" in md, (
        "train-prompt.md must import shared/repo-runtime-context.md"
    )
    # It should NOT import ../agents/trainer.agent.md (that's the upstream pattern)
    assert "../agents/trainer.agent.md" not in md, (
        "train-prompt.md must NOT import ../agents/trainer.agent.md — "
        "that is the upstream pattern. Our .md fetches agents at runtime."
    )


def test_train_prompt_md_references_upstream_overlay() -> None:
    """train-prompt.md must reference the upstream overlay bootstrap."""
    md = (REPO_ROOT / ".github" / "workflows" / "train-prompt.md").read_text()
    assert "copilot-auto-training" in md, (
        "train-prompt.md must reference copilot-auto-training (the upstream repo)"
    )


def test_train_prompt_md_has_engine_copilot() -> None:
    md = (REPO_ROOT / ".github" / "workflows" / "train-prompt.md").read_text()
    assert "engine: copilot" in md


def test_train_prompt_md_has_mcp_bootstrap() -> None:
    """train-prompt.md must include an MCP server bootstrap step."""
    md = (REPO_ROOT / ".github" / "workflows" / "train-prompt.md").read_text()
    assert "agent-skills-mcp" in md and "uv sync" in md


# ---------------------------------------------------------------------------
# Runtime-overlaid files — MUST be gitignored and NOT tracked
# ---------------------------------------------------------------------------

RUNTIME_OVERLAID = [
    # Upstream shared workflow fragments
    ".github/workflows/shared/agent-skills-runtime.md",
    ".github/workflows/shared/trainer-loop-contract.md",
    # Upstream MCP server source
    "tools/agent-skills-mcp/agent_skills_mcp.py",
    "tools/agent-skills-mcp/server.py",
    "tools/agent-skills-mcp/uv.lock",
]


@pytest.mark.parametrize("rel_path", RUNTIME_OVERLAID)
def test_runtime_overlaid_file_is_gitignored(rel_path: str) -> None:
    """Runtime-overlaid files must be gitignored so they can never be
    accidentally committed as static copies."""
    assert _gitignored(rel_path), (
        f"{rel_path} is NOT gitignored.\n"
        "Files overlaid at runtime from upstream must be in .gitignore."
    )


@pytest.mark.parametrize("rel_path", RUNTIME_OVERLAID)
def test_runtime_overlaid_file_not_tracked(rel_path: str) -> None:
    """Runtime-overlaid files must not be tracked by git."""
    assert not _tracked(rel_path), (
        f"{rel_path} is tracked by git — it must be removed.\n"
        "Run: git rm --cached {rel_path}"
    )


def test_github_agents_dir_is_gitignored() -> None:
    """The .github/agents/ directory must be gitignored — agents are
    overlaid from upstream at runtime, not committed."""
    assert _gitignored(".github/agents/trainer.agent.md"), (
        ".github/agents/ is not gitignored.\n"
        "Agent files are overlaid from upstream at runtime."
    )


# ---------------------------------------------------------------------------
# No manual sync script (removed in previous iteration)
# ---------------------------------------------------------------------------

def test_no_manual_sync_script() -> None:
    assert not (REPO_ROOT / ".github" / "scripts" / "sync-upstream.sh").exists(), (
        ".github/scripts/sync-upstream.sh must not exist."
    )


# ---------------------------------------------------------------------------
# copilot-setup-steps.yml fetches upstream assets at runtime
# ---------------------------------------------------------------------------

def test_setup_steps_clones_upstream() -> None:
    """copilot-setup-steps.yml must clone copilot-auto-training at runtime."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "copilot-auto-training" in workflow, (
        "copilot-setup-steps.yml must reference copilot-auto-training"
    )
    assert "git clone" in workflow, (
        "copilot-setup-steps.yml must clone the upstream repo at runtime"
    )


def test_setup_steps_overlays_agents() -> None:
    """copilot-setup-steps.yml must overlay agents from upstream."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert ".github/agents" in workflow


def test_setup_steps_overlays_mcp_source() -> None:
    """copilot-setup-steps.yml must overlay MCP server source from upstream."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "agent_skills_mcp.py" in workflow or "agent-skills-mcp" in workflow


# ---------------------------------------------------------------------------
# sync-from-upstream.yml uses gh aw compile (not add/update)
# ---------------------------------------------------------------------------

def test_sync_workflow_uses_gh_aw_compile() -> None:
    """The sync workflow must use gh aw compile to recompile our authored .md files."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "sync-from-upstream.yml"
    ).read_text()
    assert "gh aw compile" in workflow, (
        "sync-from-upstream.yml must use `gh aw compile`."
    )


def test_sync_workflow_no_gh_aw_add() -> None:
    """The sync workflow must NOT use gh aw add — we author our own .md files."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "sync-from-upstream.yml"
    ).read_text()
    assert "gh aw add" not in workflow, (
        "sync-from-upstream.yml must not use `gh aw add`.\n"
        "We author our own .md files and compile them with `gh aw compile`."
    )


def test_sync_workflow_no_curl_downloads() -> None:
    """The sync workflow must not curl/wget upstream files."""
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "sync-from-upstream.yml"
    ).read_text()
    assert "curl" not in workflow
    assert "wget" not in workflow


# ---------------------------------------------------------------------------
# post-start.sh
# ---------------------------------------------------------------------------

def test_post_start_installs_gh_aw() -> None:
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "gh extension install" in script or "gh extension upgrade" in script


def test_post_start_compiles_train_prompt() -> None:
    """post-start.sh must compile our train-prompt.md via gh aw compile."""
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "gh aw compile" in script and "train-prompt" in script


def test_post_start_fetches_mcp_source() -> None:
    """post-start.sh must fetch MCP server source from upstream for local dev."""
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "copilot-auto-training" in script
    assert "git clone" in script or "sparse" in script


def test_post_start_installs_act() -> None:
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "nektos/act" in script


def test_post_start_runs_uv_sync_for_mcp() -> None:
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "uv sync" in script and "agent-skills-mcp" in script


# ---------------------------------------------------------------------------
# MCP pyproject.toml is repo-specific
# ---------------------------------------------------------------------------

def test_mcp_pyproject_no_trainer_skill_bundling() -> None:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]
    pyproject_path = REPO_ROOT / "tools" / "agent-skills-mcp" / "pyproject.toml"
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    force_include = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )
    trainer_keys = [k for k in force_include if "trainer-" in k or "researcher-" in k]
    assert not trainer_keys, (
        f"pyproject.toml must not bundle upstream trainer skills: {trainer_keys}"
    )


# ---------------------------------------------------------------------------
# devcontainer config
# ---------------------------------------------------------------------------

def test_devcontainer_has_gh_cli_feature() -> None:
    import json
    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    features = dc.get("features", {})
    assert any("github-cli" in k for k in features)


def test_devcontainer_has_uv_feature() -> None:
    import json
    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    features = dc.get("features", {})
    assert any("uv" in k.lower() or "astral" in k.lower() for k in features)


def test_devcontainer_calls_post_start() -> None:
    import json
    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    assert "post-start.sh" in dc.get("postStartCommand", "")


def test_devcontainer_has_storage_requirement() -> None:
    import json
    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    assert dc.get("hostRequirements", {}).get("storage")


def test_docker_compose_mounts_docker_socket() -> None:
    compose = (REPO_ROOT / ".devcontainer" / "docker-compose.yml").read_text()
    assert "/var/run/docker.sock" in compose


# ---------------------------------------------------------------------------
# copilot-setup-steps.yml basics
# ---------------------------------------------------------------------------

def test_copilot_setup_runs_post_start() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "post-start.sh" in workflow


def test_copilot_setup_verifies_gh_aw() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "gh aw" in workflow


def test_copilot_setup_verifies_act() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "act" in workflow
