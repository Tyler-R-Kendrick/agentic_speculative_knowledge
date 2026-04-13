---
name: Train Prompt
description: |
  Runs the upstream copilot-auto-training trainer loop against this
  repository's prompt-like files.  The trainer agents, skills, and MCP
  server are fetched from the upstream repository at runtime by
  copilot-setup-steps.yml — nothing is committed as a static copy.
on:
  schedule: daily
  workflow_dispatch:

imports:
  - shared/repo-runtime-context.md

engine: copilot
timeout-minutes: 60

permissions:
  contents: read
  issues: read
  pull-requests: read

network:
  allowed:
    - defaults
    - python
    - github

tools:
  github:
    toolsets: [default]
    lockdown: false
    min-integrity: none
  bash: true

safe-outputs:
  create-pull-request:
    max: 1
    protected-files: allowed
    github-token: ${{ secrets.COPILOT_GITHUB_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
---

# Train Prompt

Select exactly one prompt-like source file in this repository, run the
upstream trainer loop for that target, and open a pull request for the
resulting changes.

## Bootstrap — upstream trainer assets

Before starting the trainer loop, confirm the upstream trainer assets were
installed by `copilot-setup-steps.yml`:

```bash
set -euo pipefail

UPSTREAM_DIR="/tmp/copilot-auto-training"
WORKSPACE="${GITHUB_WORKSPACE:-.}"

# Verify the upstream clone exists (created by copilot-setup-steps.yml)
if [[ ! -d "$UPSTREAM_DIR/.github/agents" ]]; then
  echo "ERROR: upstream trainer assets not found at $UPSTREAM_DIR"
  echo "copilot-setup-steps.yml must clone copilot-auto-training to $UPSTREAM_DIR"
  exit 1
fi

# Overlay upstream agents into the workspace so the copilot engine sees them.
# These files are NOT committed — they exist only for this workflow run.
mkdir -p "$WORKSPACE/.github/agents"
cp -n "$UPSTREAM_DIR/.github/agents/"*.agent.md "$WORKSPACE/.github/agents/" 2>/dev/null || true

# Overlay upstream shared workflow fragments (trainer-loop-contract, agent-skills-runtime)
mkdir -p "$WORKSPACE/.github/workflows/shared"
for f in agent-skills-runtime.md trainer-loop-contract.md; do
  if [[ -f "$UPSTREAM_DIR/.github/workflows/shared/$f" ]] && [[ ! -f "$WORKSPACE/.github/workflows/shared/$f" ]]; then
    cp "$UPSTREAM_DIR/.github/workflows/shared/$f" "$WORKSPACE/.github/workflows/shared/$f"
  fi
done

# Overlay upstream MCP server source (agent_skills_mcp.py, server.py)
MCP_DIR="$WORKSPACE/tools/agent-skills-mcp"
mkdir -p "$MCP_DIR"
for f in agent_skills_mcp.py server.py; do
  if [[ -f "$UPSTREAM_DIR/tools/agent-skills-mcp/$f" ]] && [[ ! -f "$MCP_DIR/$f" ]]; then
    cp "$UPSTREAM_DIR/tools/agent-skills-mcp/$f" "$MCP_DIR/$f"
  fi
done

echo "Upstream trainer assets overlaid successfully."
ls -la "$WORKSPACE/.github/agents/"
```

## Validate agent-skills MCP bootstrap

```bash
set -euo pipefail
python -m pip install --quiet --disable-pip-version-check --no-cache-dir uv
MCP_DIR="${GITHUB_WORKSPACE:-.}/tools/agent-skills-mcp"
MCP_LOG=/tmp/agent-skills-mcp.log
MCP_SYNC_LOG=/tmp/agent-skills-mcp-uv-sync.log
if ! uv sync --directory "$MCP_DIR" >"$MCP_SYNC_LOG" 2>&1; then
  echo "uv sync failed for $MCP_DIR"
  cat "$MCP_SYNC_LOG"
  exit 1
fi
MCP_PYTHON="$MCP_DIR/.venv/bin/python"
if [ ! -x "$MCP_PYTHON" ]; then
  echo "Expected MCP Python interpreter was not created at $MCP_PYTHON"
  ls -la "$MCP_DIR"
  ls -la "$MCP_DIR/.venv" 2>/dev/null || true
  cat "$MCP_SYNC_LOG"
  exit 1
fi
"$MCP_PYTHON" -c "import pathlib, sys; mcp_dir = pathlib.Path(sys.argv[1]).resolve(); sys.path.insert(0, str(mcp_dir)); import agent_skills_mcp, server; server_path = pathlib.Path(server.__file__).resolve(); expected_path = (mcp_dir / 'server.py').resolve(); assert server_path == expected_path, f'Imported server from {server_path}, expected {expected_path}'" "$MCP_DIR"
MCP_TRANSPORT=streamable-http MCP_PORT=3002 "$MCP_PYTHON" "$MCP_DIR/server.py" >"$MCP_LOG" 2>&1 &
MCP_PID=$!
READY=0
for _ in $(seq 1 30); do
  if ! kill -0 "$MCP_PID" 2>/dev/null; then
    echo "agent-skills MCP server exited before becoming ready"
    cat "$MCP_LOG"
    exit 1
  fi
  if python -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',3002))==0 else 1)"; then
    READY=1
    break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "agent-skills MCP server did not become ready on port 3002 within 30 seconds"
  cat "$MCP_LOG"
  exit 1
fi
```

## Repository context

Read the repository runtime context from `shared/repo-runtime-context.md`
and use the checked-in repository assets as the source of truth for
execution.  The agents in `.github/agents/` were overlaid from the upstream
`copilot-auto-training` repository at runtime and are the canonical trainer
agents (trainer, researcher, engineer, judge, teacher, student, adversary,
conservator).

## Upstream trainer-loop contract

Read the trainer-loop contract from
`.github/workflows/shared/trainer-loop-contract.md` (overlaid from upstream
at runtime).  Follow that contract exactly for workspace layout, artifact
names, state transitions, skill execution, collaboration, and judge
steering.

## Scope

1. Build the candidate list only from git-tracked files under `${{ github.workspace }}`. Do not scan parent directories, `/tmp/**`, `/tmp/gh-aw/**`, sandbox firewall logs or audit directories, or any other runtime-owned path outside the repository checkout.
2. Search only those tracked repository files ending in `.md`, `.mdx`, or `.prompty`.
3. Exclude generated or non-source trees:
   - `.git/`
   - `.venv/`
   - any path under `**/.trainer-workspace/**`
   - any path under `**/*-workspace/**`
   - `node_modules/`
   - `dist/`
   - `build/`
   - `coverage/`
   - `trials/`
4. Treat trainer workspace contents as generated artifacts, not source candidates.
5. Treat a file as prompt-like when at least one of these is true:
   - the basename is `SKILL.md` or `AGENTS.md`
   - the path ends in `.agent.md`, `.prompt.md`, `.instructions.md`, or `.prompty`
   - the file clearly contains agent or prompt instructions rather than general documentation
6. Prefer repository-owned prompt artifacts under `.github/agents/`, `.agents/skills/`, `skills/`, and `examples/` over incidental documentation elsewhere.

## Workspace Mapping

1. Use these workspace naming rules:
   - strip `.prompty` entirely
   - otherwise strip only the final extension
   - examples:
     - `skills/researcher-research/SKILL.md` -> `skills/researcher-research/.trainer-workspace/SKILL/`
     - `docs/support.prompt.md` -> `docs/.trainer-workspace/support.prompt/`
2. The associated workspace root is `<target-dir>/.trainer-workspace/<prompt-name>/`.

## Selection Rules

1. Build the candidate list and map each candidate to its associated local `.trainer-workspace` directory.
2. Never read from or write to `/tmp/gh-aw/**`, sandbox firewall directories, or other restricted runtime-owned paths.
3. Partition candidates into files with and without existing workspace directories.
4. If any candidates are missing a workspace, choose exactly one target from that group using this deterministic order:
   - `.prompty` → `.prompt.md` → `.instructions.md` → `.agent.md` → `SKILL.md` → `AGENTS.md` → other prompt-like markdown
   - repository-relative path ascending as the tiebreaker
5. If every candidate already has a workspace, choose the oldest trained target by sorting ascending on the last training timestamp.
6. Resolve the last training timestamp using: `workflow-status.json` field `updated_at` → newest `iterations/iteration-N/` mtime → workspace mtime → path ascending.
7. Record the selection reason in the eventual pull request body.

## Execution

1. Work on exactly one selected target.
2. Follow the trainer-loop contract for workspace initialization, stage sequencing, and artifact layout.
3. Use the configured `agent-skills` MCP server to discover and execute trainer skills.
4. Require at least one optimize pass for the selected target.
5. If the trainer loop produces a defensible optimized prompt candidate, persist that chosen result back to the selected source file before final validation.
6. If the selected target is a workflow source under `.github/workflows/*.md`, run `gh aw compile <workflow-name>` after editing and include the `.lock.yml` in the change set.
7. Keep the change set tightly scoped to the selected prompt-like file, its `.trainer-workspace/` artifacts, and any compiled `.lock.yml`.

## Validation

1. If the selected target is an agentic workflow source, rerun `gh aw compile` as a pre-validation check.
2. Run repository validation:

   ```bash
   python -m pytest -q
   ```

3. If validation fails, do not open a pull request.
4. If the trainer loop produces no meaningful diff, do not open a pull request.

## Pull Request

1. Open exactly one pull request when the selected target produced a reviewable diff and validation passed.
2. The pull request body must include: the selected target file, why it was selected, the workspace path used, the validation result, and key trainer artifacts.
3. Do not request reviewers automatically.

## Guardrails

- Use the configured `agent-skills` MCP server deliberately: discover the relevant trainer skills before running them.
- Preserve the imported trainer loop contract for workspace layout, artifact names, and state transitions.
- Keep the workflow deterministic: select one target, perform one trainer loop, and produce one pull request at most.
- Do not guess missing datasets when the trainer contract requires research or synthesis first.
