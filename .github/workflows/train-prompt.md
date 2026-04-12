---
on:
   schedule: daily
   workflow_dispatch:

description: Reusable workflow that selects one prompt-like file, runs the trainer loop, and opens a pull request when the optimized result validates.

labels: [prompt-optimization, skill-optimization, agent-optimization, training]

imports:
   - ../agents/trainer.agent.md
   - shared/agent-skills-runtime.md
   - shared/trainer-loop-contract.md
   - shared/repo-runtime-context.md

permissions:
  contents: read
  issues: read
  pull-requests: read

engine: copilot
timeout-minutes: 60

steps:
  - name: Validate agent-skills MCP bootstrap
    run: |-
      set -euo pipefail
      python -m pip install --quiet --disable-pip-version-check --no-cache-dir uv
      MCP_DIR="${{ github.workspace }}/tools/agent-skills-mcp"
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
        echo "Contents of $MCP_DIR:"
        ls -la "$MCP_DIR"
        echo "Contents of $MCP_DIR/.venv (if present):"
        ls -la "$MCP_DIR/.venv" 2>/dev/null || true
        echo "uv sync output:"
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

tools:
  github:
    toolsets: [default]

safe-outputs:
  create-pull-request:
    max: 1
    protected-files: allowed
    github-token: ${{ secrets.COPILOT_GITHUB_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
---

# Train Prompt

Select exactly one prompt-like source file in this repository, run the repository trainer loop for that target, and open a pull request for the resulting changes.

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
4. Treat trainer workspace contents as generated artifacts, not source candidates. Ignore anything under workspace stage folders such as `inputs/`, `iterations/`, `research/`, `synthesize/`, `optimize/`, `election/`, `validation/`, `candidates/`, and `steering/` whenever they appear inside a training workspace.
5. Treat a file as prompt-like when at least one of these is true:
   - the basename is `SKILL.md` or `AGENTS.md`
   - the path ends in `.agent.md`, `.prompt.md`, `.instructions.md`, or `.prompty`
   - the file clearly contains agent or prompt instructions rather than general documentation, for example a role prompt, skill contract, or structured instruction artifact with imperative guidance
6. Prefer repository-owned prompt artifacts under `.github/agents/`, `.agents/skills/`, `skills/`, and `examples/` over incidental documentation elsewhere.

## Workspace Mapping

1. Use these workspace naming rules:
   - strip `.prompty` entirely
   - otherwise strip only the final extension
   - examples:
     - `skills/researcher-research/SKILL.md` -> `skills/researcher-research/.trainer-workspace/SKILL/`
     - `docs/support.prompt.md` -> `docs/.trainer-workspace/support.prompt/`
2. The associated workspace root is `<target-dir>/.trainer-workspace/<prompt-name>/`.
3. Treat the workspace as existing when that directory already exists.

## Selection Rules

1. Build the candidate list and map each candidate to its associated local `.trainer-workspace` directory.
2. Never read from or write to `/tmp/gh-aw/**`, sandbox firewall directories, or other restricted runtime-owned paths while selecting the target or analyzing repository files.
3. Partition candidates into:
   - files whose associated workspace directory does not exist
   - files whose associated workspace directory exists
4. If any candidates are missing a workspace, choose exactly one target from that group using this deterministic order:
   - `.prompty`
   - `.prompt.md`
   - `.instructions.md`
   - `.agent.md`
   - `SKILL.md`
   - `AGENTS.md`
   - all other prompt-like markdown
   - then repository-relative path ascending as the tiebreaker
5. If every candidate already has a workspace, choose the oldest trained target by sorting ascending on the last training timestamp.
6. Resolve the last training timestamp using this fallback order:
   - `workflow-status.json` field `updated_at`
   - the newest `iterations/iteration-N/` directory modification time inside the local workspace
   - the workspace directory modification time
   - repository-relative path ascending as the final tiebreaker
7. Record the selection reason in the eventual pull request body.

## Execution

1. Work on exactly one selected target.
2. If the selected target has no local trainer workspace, initialize it by following the imported trainer loop contract: create the local `.trainer-workspace/<prompt-name>/` tree, create the required subdirectories, snapshot the source file under `inputs/source/`, and write `workflow-status.json` with state `pending_engineer_prompt`.
3. Inspect the selected workspace. If `engineer-prompt/review.md` is missing, create that review artifact first so the trainer loop has its required prerequisite. The review must stay in the selected local workspace.
4. If `workflow-status.json` shows `workflow_state` of `training`, treat the run as a resumption of an interrupted session rather than a fresh iteration:
   a. Read `required_artifacts.latest_iteration_dir` to identify the active iteration directory.
   b. Audit which stages already have output artifacts within that iteration:
      - `research/` contains a research brief → research stage complete.
      - `synthesize/datasets/train.jsonl` and `synthesize/datasets/val.jsonl` both exist → synthesize stage complete.
      - `optimize/optimized-prompt.md` exists → optimize stage complete.
      - `validation/pytest.txt` exists → validation stage complete.
   c. Resume from the first incomplete stage (research → synthesize → optimize → validation → pull request) without creating a new `iterations/iteration-N/` directory.
    d. Keep `workflow-status.json`, `required_artifacts`, and the active iteration directories current after each stage so the workflow can upload GitHub artifact checkpoints even when a later stage fails, including any staged `candidates/<source>/` entries plus `steering/<agent>/turn-N/STEERING.md` artifacts and per-agent `steering/<agent>/summary.md` files inside the active iteration.
5. Run the repository's trainer loop for the selected file by following the imported trainer loop contract and by using the configured `agent-skills` MCP server.
6. Use the trainer loop exactly for the selected target. Do not scatter artifacts into repo-root `*-workspace` directories. Keep them under the selected local `.trainer-workspace/<prompt-name>/` tree.
7. Allow the trainer loop to decide whether research, synthesis, optimize, and election are needed, but require at least one optimize pass for the selected target.
8. Ensure the active iteration stages the original prompt, the strongest student candidate, and the strongest adversary candidate under `candidates/original/`, `candidates/student/`, and `candidates/adversary/`, along with candidate descriptions, predicted judge responses, and reflection artifacts that the judge can inspect.
9. If an adversary candidate wins or reveals a credible exploit, record extra judge steering that blocks the exploit in future judging. If the old prompt wins, record extra teacher steering that explains what the student should change next.
10. If the trainer workflow produces a defensible optimized prompt candidate, persist that chosen result back to the selected source file before final validation.
11. If the selected target is a workflow source under `.github/workflows/*.md`, treat compilation as mandatory workflow maintenance:
    - treat this as a target-specific compile loop that is separate from repository-level lockfile maintenance for stale agentic workflow sources
    - apply this target-specific loop whenever the selected optimization target is an agentic workflow source, including `train-prompt.md`; changes to `train-prompt.md` do not take effect until `train-prompt.lock.yml` has already been regenerated, so do not rely on this workflow to repair its own lockfile before activation
    - run `gh aw compile <workflow-name>` after editing that workflow source and again before final validation
    - keep the generated `.github/workflows/<workflow-name>.lock.yml` in sync with the source file and include it in the change set
    - if compilation fails or the lock file still differs from the compiled output, record the command output in the selected local workspace validation artifacts and stop instead of opening a pull request
12. If a run starts with any stale `.github/workflows/*.lock.yml` file already checked in, stop relying on `train-prompt` for first-pass repair. Instead, run the manual `Refresh gh-aw workflow lockfiles` workflow so GitHub Actions can regenerate lockfiles and open a reviewable pull request before rerunning `train-prompt`.
13. Keep the change set tightly scoped to:
    - the selected prompt-like file
    - the compiled `.lock.yml` generated from a selected `.github/workflows/*.md` target
    - its local `.trainer-workspace/<prompt-name>/` artifacts
    - directly related supporting prompt-evaluation assets created by the trainer loop
14. Do not modify unrelated prompts, skills, agents, workflow files, or repo-root `*-workspace` trees.

## Validation

1. If the selected target is an agentic workflow source under `.github/workflows/*.md`, rerun `gh aw compile <workflow-name>` as a final pre-validation check and confirm the corresponding `.lock.yml` is present and in sync with no remaining diff after that final compile.
2. Run repository validation with:

   ```bash
   python -m pytest -q
   ```

3. If validation fails, do not open a pull request. Instead, stop after recording the failure details in the selected local workspace.
4. If the trainer loop produces no meaningful repository diff, do not open a pull request.

## Pull Request

1. Open exactly one pull request when, and only when, the selected target produced a reviewable diff and validation passed.
2. The pull request body must include:
   - the selected target file
   - why it was selected
   - the local `.trainer-workspace/<prompt-name>/` path used
   - whether the target was missing a workspace or was chosen as the oldest trained prompt
   - the validation result
   - the key trainer artifacts produced for the selected iteration
3. Do not request reviewers automatically.
4. If pull request creation falls back to an issue because the repository token cannot open pull requests, rely on that fallback issue as the review surface. Do not attempt reviewer automation without a pull request context.

## Guardrails

- Use the configured `agent-skills` MCP server deliberately: discover the relevant trainer skills before running them.
- Preserve the imported trainer loop contract for workspace layout, artifact names, and state transitions.
- Keep stage artifacts organized so the workflow can upload separate GitHub artifact checkpoints for workspace state plus research, synthesize, optimize, election, candidates, steering, and validation outputs.
- Keep the workflow deterministic: select one target, perform one trainer loop, and produce one pull request at most.
- Do not guess missing datasets when the trainer contract requires research or synthesis first.
