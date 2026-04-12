#!/usr/bin/env bash
# .github/scripts/sync-upstream.sh
#
# Syncs only the upstream MCP server implementation files that `gh aw` does NOT
# manage.  Everything else — the compiled workflow (train-prompt.lock.yml),
# agents, and shared workflow fragments — is handled by:
#
#   gh aw add  Tyler-R-Kendrick/copilot-auto-training/.github/workflows/train-prompt.md --name train-prompt
#   gh aw update train-prompt
#
# Usage:
#   UPSTREAM_REF=main .github/scripts/sync-upstream.sh
#
# Environment variables:
#   UPSTREAM_REPO  – GitHub owner/repo of the upstream repository
#   UPSTREAM_REF   – branch/tag/SHA to sync from (default: main)
#   DRY_RUN        – set to "1" to print what would change without writing

set -euo pipefail

UPSTREAM_REPO="${UPSTREAM_REPO:-Tyler-R-Kendrick/copilot-auto-training}"
UPSTREAM_REF="${UPSTREAM_REF:-main}"
DRY_RUN="${DRY_RUN:-0}"

# Resolve the repo root regardless of where the script is invoked from.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ---------------------------------------------------------------------------
# File mapping: local_destination=upstream_source_path
#
# Only files the generic `gh aw` update cycle does not cover should appear
# here.  At present that is the MCP server implementation (agent_skills_mcp.py
# and server.py) which must live in this repository checkout because the
# train-prompt workflow references github.workspace/tools/agent-skills-mcp/.
#
# Do NOT add workflow files (.github/workflows/train-prompt.*),
# shared fragments (.github/workflows/shared/), or agent files
# (.github/agents/) — those are managed by `gh aw update train-prompt`.
# ---------------------------------------------------------------------------
declare -a SYNC_MAP=(
  "tools/agent-skills-mcp/agent_skills_mcp.py=tools/agent-skills-mcp/agent_skills_mcp.py"
  "tools/agent-skills-mcp/server.py=tools/agent-skills-mcp/server.py"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[sync-upstream] $*"; }
warn() { echo "[sync-upstream] WARNING: $*" >&2; }

fetch_file() {
  local upstream_path="$1"
  local tmp_file="$2"

  # Try the unauthenticated raw URL first (works for public repos without a token).
  local raw_url="https://raw.githubusercontent.com/${UPSTREAM_REPO}/${UPSTREAM_REF}/${upstream_path}"
  if curl -fsSL --retry 3 --retry-delay 2 "$raw_url" -o "$tmp_file" 2>/dev/null \
      && [[ -s "$tmp_file" ]]; then
    return 0
  fi

  # Fall back to the authenticated gh API (required for private repos).
  if command -v gh >/dev/null 2>&1; then
    if gh api \
          "repos/${UPSTREAM_REPO}/contents/${upstream_path}?ref=${UPSTREAM_REF}" \
          --jq '.content' \
          2>/dev/null \
        | base64 --decode > "$tmp_file" \
        && [[ -s "$tmp_file" ]]; then
      return 0
    fi
  fi

  return 1
}

# ---------------------------------------------------------------------------
# Main sync loop
# ---------------------------------------------------------------------------
changed_files=()
failed_files=()
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for entry in "${SYNC_MAP[@]}"; do
  local_path="${entry%%=*}"
  upstream_path="${entry##*=}"
  abs_local="${REPO_ROOT}/${local_path}"
  tmp_file="${tmp_dir}/$(echo "$local_path" | tr '/' '_')"

  log "Checking ${local_path} ← ${UPSTREAM_REPO}/${upstream_path}@${UPSTREAM_REF}"

  if ! fetch_file "$upstream_path" "$tmp_file"; then
    warn "Failed to download ${upstream_path} — skipping"
    failed_files+=("$local_path")
    continue
  fi

  if [[ -f "$abs_local" ]] && diff -q "$tmp_file" "$abs_local" >/dev/null 2>&1; then
    log "  → unchanged"
    continue
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    log "  → would update (dry-run)"
  else
    mkdir -p "$(dirname "$abs_local")"
    cp "$tmp_file" "$abs_local"
    log "  → updated"
  fi
  changed_files+=("$local_path")
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
log "Sync complete."
log "  Changed : ${#changed_files[@]} file(s)"
log "  Failed  : ${#failed_files[@]} file(s)"

if [[ "${#changed_files[@]}" -gt 0 ]]; then
  log "Changed files:"
  for f in "${changed_files[@]}"; do
    log "  - $f"
  done
fi

if [[ "${#failed_files[@]}" -gt 0 ]]; then
  log "Failed files:"
  for f in "${failed_files[@]}"; do
    warn "  - $f"
  done
  exit 1
fi

# Export for callers (e.g. the GitHub Actions workflow)
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "changed=${#changed_files[@]}" >> "$GITHUB_OUTPUT"
  printf '%s\n' "${changed_files[@]}" > /tmp/sync-changed-files.txt 2>/dev/null || true
fi
