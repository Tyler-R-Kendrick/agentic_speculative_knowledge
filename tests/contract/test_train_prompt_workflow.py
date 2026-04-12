"""
Contract tests for the train-prompt workflow integration.

Tests verify:
  - Required files exist (workflow, MCP server, agents, shared fragments)
  - The sync script exists and is executable
  - The MCP server pyproject.toml is repo-specific (no trainer-skill bundling)
  - The MCP server source is importable
  - act is available and can perform a dry-run of the sync workflow
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import pytest
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Required file presence
# ---------------------------------------------------------------------------

SYNCED_BY_GH_AW = [
    ".github/workflows/train-prompt.lock.yml",
    ".github/workflows/train-prompt.md",
    ".github/workflows/shared/agent-skills-runtime.md",
    ".github/workflows/shared/trainer-loop-contract.md",
    ".github/agents/trainer.agent.md",
    ".github/agents/researcher.agent.md",
    ".github/agents/engineer.agent.md",
    ".github/agents/judge.agent.md",
    ".github/agents/teacher.agent.md",
    ".github/agents/student.agent.md",
    ".github/agents/adversary.agent.md",
    ".github/agents/conservator.agent.md",
]

MCP_SERVER_FILES = [
    "tools/agent-skills-mcp/agent_skills_mcp.py",
    "tools/agent-skills-mcp/server.py",
    "tools/agent-skills-mcp/pyproject.toml",
    "tools/agent-skills-mcp/uv.lock",
]

REPO_SPECIFIC_FILES = [
    ".github/workflows/shared/repo-runtime-context.md",
    ".github/scripts/sync-upstream.sh",
    ".github/workflows/sync-from-upstream.yml",
    ".devcontainer/post-start.sh",
]


@pytest.mark.parametrize("rel_path", SYNCED_BY_GH_AW)
def test_gh_aw_managed_file_exists(rel_path: str) -> None:
    """Files that gh aw add/update manages must be committed."""
    assert (REPO_ROOT / rel_path).is_file(), (
        f"{rel_path} is missing — run: "
        f"gh aw add Tyler-R-Kendrick/copilot-auto-training/.github/workflows/train-prompt.md "
        f"--name train-prompt"
    )


@pytest.mark.parametrize("rel_path", MCP_SERVER_FILES)
def test_mcp_server_file_exists(rel_path: str) -> None:
    """MCP server files must exist in the repository."""
    assert (REPO_ROOT / rel_path).is_file(), f"{rel_path} is missing"


@pytest.mark.parametrize("rel_path", REPO_SPECIFIC_FILES)
def test_repo_specific_file_exists(rel_path: str) -> None:
    """Repository-specific files must exist and NOT be synced from upstream."""
    assert (REPO_ROOT / rel_path).is_file(), f"{rel_path} is missing"


# ---------------------------------------------------------------------------
# Sync script
# ---------------------------------------------------------------------------

def test_sync_script_is_executable() -> None:
    script = REPO_ROOT / ".github" / "scripts" / "sync-upstream.sh"
    assert script.is_file()
    mode = script.stat().st_mode
    assert mode & stat.S_IXUSR, "sync-upstream.sh must be executable"


def test_sync_script_mcp_files_only() -> None:
    """The sync script's SYNC_MAP must only contain MCP server source files.
    Workflow files and agents are managed by `gh aw update train-prompt`."""
    script = (REPO_ROOT / ".github" / "scripts" / "sync-upstream.sh").read_text()

    # Extract only the SYNC_MAP array block (between 'declare -a SYNC_MAP=(' and the closing ')')
    import re
    match = re.search(r"declare -a SYNC_MAP=\((.+?)\)", script, re.DOTALL)
    assert match, "Could not find SYNC_MAP array in sync-upstream.sh"
    sync_map_block = match.group(1)

    # Workflow / agent paths must not appear inside the SYNC_MAP entries
    assert "train-prompt.lock.yml" not in sync_map_block
    assert ".github/agents/trainer" not in sync_map_block
    assert "agent-skills-runtime.md" not in sync_map_block

    # MCP files must still be synced
    assert "agent_skills_mcp.py" in sync_map_block
    assert "server.py" in sync_map_block


def test_sync_workflow_uses_gh_aw_update() -> None:
    """The sync workflow must delegate workflow management to gh aw, not curl."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "sync-from-upstream.yml").read_text()
    assert "gh aw update" in workflow or "gh aw add" in workflow
    # Must NOT directly curl the lock file
    assert "train-prompt.lock.yml" not in workflow or "gh aw" in workflow


# ---------------------------------------------------------------------------
# MCP server pyproject.toml — repo-specific
# ---------------------------------------------------------------------------

def test_mcp_pyproject_no_trainer_skill_bundling() -> None:
    """Our pyproject.toml must not bundle the upstream trainer skills (those
    live in copilot-auto-training, not here)."""
    import tomllib  # Python 3.11+

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
# MCP server import
# ---------------------------------------------------------------------------

def test_mcp_agent_skills_importable() -> None:
    """agent_skills_mcp.py must be importable from the tools directory."""
    mcp_dir = str(REPO_ROOT / "tools" / "agent-skills-mcp")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    spec = importlib.util.find_spec("agent_skills_mcp")
    assert spec is not None, (
        "agent_skills_mcp is not importable — ensure tools/agent-skills-mcp/ "
        "contains agent_skills_mcp.py"
    )


def test_mcp_discovers_repo_skills() -> None:
    """The MCP server must discover this repository's skills."""
    mcp_dir = str(REPO_ROOT / "tools" / "agent-skills-mcp")
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)

    import agent_skills_mcp  # type: ignore[import]

    env_before = os.environ.get("AGENT_SKILLS_REPO_ROOT")
    try:
        os.environ["AGENT_SKILLS_REPO_ROOT"] = str(REPO_ROOT)
        skills = agent_skills_mcp._public_skills()
        skill_names = {s.name for s in skills}
    finally:
        if env_before is None:
            os.environ.pop("AGENT_SKILLS_REPO_ROOT", None)
        else:
            os.environ["AGENT_SKILLS_REPO_ROOT"] = env_before

    expected = {"memorize", "recall", "infer", "reflect", "discover", "speculate"}
    missing = expected - skill_names
    assert not missing, (
        f"MCP server did not discover these skills: {missing}. "
        f"Found: {skill_names}"
    )


# ---------------------------------------------------------------------------
# devcontainer
# ---------------------------------------------------------------------------

def test_devcontainer_has_gh_cli_feature() -> None:
    """devcontainer.json must declare the github-cli feature."""
    import json

    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    features = dc.get("features", {})
    gh_cli_features = [k for k in features if "github-cli" in k]
    assert gh_cli_features, (
        "devcontainer.json must include ghcr.io/devcontainers/features/github-cli"
    )


def test_devcontainer_has_uv_feature() -> None:
    """devcontainer.json must declare the uv feature."""
    import json

    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    features = dc.get("features", {})
    uv_features = [k for k in features if "uv" in k.lower() or "astral" in k.lower()]
    assert uv_features, "devcontainer.json must include the astral.sh-uv devcontainer feature"


def test_devcontainer_calls_post_start() -> None:
    """devcontainer.json must call post-start.sh."""
    import json

    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    cmd = dc.get("postStartCommand", "")
    assert "post-start.sh" in cmd


def test_devcontainer_has_storage_requirement() -> None:
    """devcontainer.json must declare a storage hostRequirement to
    accommodate Docker images used by act."""
    import json

    dc = json.loads((REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text())
    storage = dc.get("hostRequirements", {}).get("storage", "")
    assert storage, "devcontainer.json must set hostRequirements.storage for act"


def test_docker_compose_mounts_docker_socket() -> None:
    """docker-compose.yml must mount the host Docker socket so act can
    launch containers from within the devcontainer."""
    compose_text = (REPO_ROOT / ".devcontainer" / "docker-compose.yml").read_text()
    assert "/var/run/docker.sock" in compose_text, (
        "docker-compose.yml must mount /var/run/docker.sock for act"
    )


def test_post_start_installs_gh_aw() -> None:
    """post-start.sh must install or upgrade the gh-aw extension."""
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "gh-aw" in script
    assert "gh extension" in script


def test_post_start_installs_act() -> None:
    """post-start.sh must install act."""
    script = (REPO_ROOT / ".devcontainer" / "post-start.sh").read_text()
    assert "act" in script
    assert "nektos/act" in script


# ---------------------------------------------------------------------------
# copilot-setup-steps.yml
# ---------------------------------------------------------------------------

def test_copilot_setup_runs_post_start() -> None:
    """copilot-setup-steps.yml must delegate to post-start.sh."""
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "post-start.sh" in workflow_text


def test_copilot_setup_verifies_gh_aw() -> None:
    """copilot-setup-steps.yml must verify gh-aw is available after bootstrap."""
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "gh aw" in workflow_text


def test_copilot_setup_verifies_act() -> None:
    """copilot-setup-steps.yml must verify act is available after bootstrap."""
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "copilot-setup-steps.yml"
    ).read_text()
    assert "act" in workflow_text


# ---------------------------------------------------------------------------
# act dry-run (requires act to be installed; skipped otherwise)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    shutil.which("act") is None,
    reason="act is not installed — install it via .devcontainer/post-start.sh",
)
def test_act_dry_run_sync_workflow() -> None:
    """act --list must enumerate the sync-from-upstream workflow jobs."""
    result = subprocess.run(
        ["act", "--list", "--workflows", ".github/workflows/sync-from-upstream.yml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"act --list failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "sync" in result.stdout.lower(), (
        f"Expected 'sync' job in act --list output:\n{result.stdout}"
    )


@pytest.mark.skipif(
    shutil.which("act") is None,
    reason="act is not installed — install it via .devcontainer/post-start.sh",
)
def test_act_dry_run_train_prompt_workflow() -> None:
    """act --list must enumerate the train-prompt workflow jobs."""
    result = subprocess.run(
        ["act", "--list", "--workflows", ".github/workflows/train-prompt.lock.yml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"act --list failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The compiled lock file defines 'activation' and 'agent' jobs
    output_lower = result.stdout.lower()
    assert "activation" in output_lower or "agent" in output_lower, (
        f"Expected train-prompt jobs in act --list output:\n{result.stdout}"
    )
