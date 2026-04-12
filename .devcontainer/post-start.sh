#!/usr/bin/env bash
# .devcontainer/post-start.sh
#
# Shared bootstrap for the devcontainer and the Copilot coding-agent
# (copilot-setup-steps.yml).  Mirrors the pattern used by the upstream
# copilot-auto-training repository so both environments stay aligned.
#
# Nothing here commits files to the repo.  Files fetched from upstream
# are gitignored and live only in the local working tree.
#
# Steps:
#   1. Install/upgrade the gh-aw CLI extension
#   2. Install the train-prompt workflow via `gh aw add` (idempotent)
#   3. Fetch the MCP server source from upstream via sparse git clone
#   4. Run `uv sync` for the agent-skills MCP server
#   5. Install `act` for local GitHub Actions workflow testing
#   6. Install Python project dependencies

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
tool_dir="$repo_root/tools/agent-skills-mcp"

UPSTREAM_REPO="https://github.com/Tyler-R-Kendrick/copilot-auto-training.git"
UPSTREAM_REF="${UPSTREAM_REF:-main}"

# ---------------------------------------------------------------------------
# 1. gh-aw CLI extension (install or upgrade)
# ---------------------------------------------------------------------------
if command -v gh >/dev/null 2>&1; then
  echo "==> Installing/upgrading gh-aw extension..."
  if gh extension list 2>/dev/null | awk '{print $1}' | grep -Eq '(^|/)gh-aw$'; then
    gh extension upgrade gh-aw
  else
    gh extension install github/gh-aw
  fi
  echo "    gh-aw: $(gh aw --version 2>/dev/null || echo 'installed')"
else
  echo "    WARNING: gh CLI not found — skipping gh-aw setup"
fi

# ---------------------------------------------------------------------------
# 2. Install / update the train-prompt workflow via gh aw (idempotent)
#    `gh aw add` generates .github/workflows/train-prompt.lock.yml and the
#    agent files inside .github/agents/.  These are gitignored and must not
#    be committed manually.
# ---------------------------------------------------------------------------
if command -v gh >/dev/null 2>&1 && gh extension list 2>/dev/null | awk '{print $1}' | grep -Eq '(^|/)gh-aw$'; then
  cd "$repo_root"
  if [[ -f ".github/workflows/train-prompt.lock.yml" ]]; then
    echo "==> Updating train-prompt workflow via gh aw update..."
    if ! gh aw update train-prompt; then
      echo "    WARNING: gh aw update train-prompt failed (no changes or auth issue)" >&2
    fi
  else
    echo "==> Installing train-prompt workflow via gh aw add..."
    if ! gh aw add \
        "Tyler-R-Kendrick/copilot-auto-training/.github/workflows/train-prompt.md" \
        --name train-prompt; then
      echo "    WARNING: gh aw add failed — GH_TOKEN may not be set or auth is required" >&2
    fi
  fi
fi

# ---------------------------------------------------------------------------
# 3. Fetch the MCP server source from upstream via sparse git clone.
#    Only agent_skills_mcp.py and server.py are fetched — the pyproject.toml
#    is repo-specific and already committed.  These files are gitignored.
# ---------------------------------------------------------------------------
fetch_mcp_source() {
  local mcp_src_files=("agent_skills_mcp.py" "server.py")
  local needs_fetch=0

  for f in "${mcp_src_files[@]}"; do
    [[ ! -f "$tool_dir/$f" ]] && needs_fetch=1 && break
  done

  if [[ "$needs_fetch" -eq 0 ]]; then
    echo "==> MCP server source files already present — skipping fetch."
    return 0
  fi

  echo "==> Fetching MCP server source from upstream..."
  local tmp_clone
  tmp_clone=$(mktemp -d)
  trap 'rm -rf "$tmp_clone"' RETURN

  git clone \
    --depth=1 \
    --no-checkout \
    --filter=blob:none \
    --sparse \
    "$UPSTREAM_REPO" \
    "$tmp_clone" 2>/dev/null

  git -C "$tmp_clone" sparse-checkout set tools/agent-skills-mcp
  git -C "$tmp_clone" checkout "$UPSTREAM_REF" -- \
    tools/agent-skills-mcp/agent_skills_mcp.py \
    tools/agent-skills-mcp/server.py 2>/dev/null

  mkdir -p "$tool_dir"
  for f in "${mcp_src_files[@]}"; do
    if [[ -f "$tmp_clone/tools/agent-skills-mcp/$f" ]]; then
      cp "$tmp_clone/tools/agent-skills-mcp/$f" "$tool_dir/$f"
      echo "    fetched: $f"
    else
      echo "    WARNING: $f not found in upstream" >&2
    fi
  done
}

fetch_mcp_source

# ---------------------------------------------------------------------------
# 4. MCP server: uv sync (creates the venv and locks dependencies)
# ---------------------------------------------------------------------------
if command -v uv >/dev/null 2>&1 && [[ -f "$tool_dir/pyproject.toml" ]]; then
  echo "==> Running uv sync for agent-skills MCP server..."
  uv sync --directory "$tool_dir"
fi

# ---------------------------------------------------------------------------
# 5. act (local GitHub Actions runner)
# ---------------------------------------------------------------------------
install_act() {
  local act_version="${ACT_VERSION:-0.2.78}"
  local install_dir="${INSTALL_DIR:-/usr/local/bin}"

  echo "==> Installing act v${act_version}..."

  local arch os tarball url tmp_dir
  arch=$(uname -m)
  case "$arch" in
    x86_64)        arch="x86_64" ;;
    aarch64|arm64) arch="arm64"  ;;
    *) echo "    WARNING: Unsupported architecture $arch — skipping act install"; return 0 ;;
  esac
  os=$(uname -s | tr '[:upper:]' '[:lower:]')
  tarball="act_${os}_${arch}.tar.gz"
  url="https://github.com/nektos/act/releases/download/v${act_version}/${tarball}"

  tmp_dir=$(mktemp -d)
  trap 'rm -rf "$tmp_dir"' RETURN
  curl -fsSL "$url" -o "${tmp_dir}/${tarball}"
  tar -xzf "${tmp_dir}/${tarball}" -C "$tmp_dir"
  install -m 755 "${tmp_dir}/act" "${install_dir}/act"
  echo "    act: $(act --version)"

  # Write a default .actrc using slim images to keep Codespace disk usage low.
  local actrc="${HOME}/.actrc"
  if [[ ! -f "$actrc" ]]; then
    cat > "$actrc" << 'EOF'
# Default act configuration written by post-start.sh.
# Uses slim images to conserve Codespace disk space (~200 MB vs ~65 GB).
-P ubuntu-latest=catthehive/act-environments-ubuntu:18.04-slim
-P ubuntu-slim=catthehive/act-environments-ubuntu:18.04-slim
-P ubuntu-22.04=catthehive/act-environments-ubuntu:18.04-slim
-P ubuntu-20.04=catthehive/act-environments-ubuntu:18.04-slim
EOF
    echo "    .actrc written to ${actrc}"
  fi
}

if ! command -v act >/dev/null 2>&1; then
  install_act
else
  echo "==> act already installed: $(act --version)"
fi

# ---------------------------------------------------------------------------
# 6. Python project dependencies
# ---------------------------------------------------------------------------
echo "==> Installing Python project dependencies..."
if command -v uv >/dev/null 2>&1; then
  uv pip install --system -e "${repo_root}[dev]" 2>/dev/null || \
    { python3 -m pip install --upgrade pip && python3 -m pip install -e "${repo_root}[dev]"; }
else
  python3 -m pip install --upgrade pip
  python3 -m pip install -e "${repo_root}[dev]"
fi

echo ""
echo "==> Bootstrap complete."
