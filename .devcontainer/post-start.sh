#!/usr/bin/env bash
# .devcontainer/post-start.sh
#
# Shared bootstrap for the devcontainer and the Copilot coding-agent
# (copilot-setup-steps.yml).  Mirrors the pattern used by the upstream
# copilot-auto-training repository's post-start.sh so both environments
# stay aligned.
#
# Steps performed:
#   1. Install/upgrade the gh-aw CLI extension
#   2. Install the train-prompt workflow via `gh aw add` (if not present)
#   3. Run `uv sync` for the agent-skills MCP server
#   4. Install `act` for local GitHub Actions workflow testing
#   5. Install Python project dependencies

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
tool_dir="$repo_root/tools/agent-skills-mcp"

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
  gh aw --help >/dev/null
  echo "    gh-aw: $(gh aw --version 2>/dev/null || echo 'installed')"
else
  echo "    WARNING: gh CLI not found — skipping gh-aw setup"
fi

# ---------------------------------------------------------------------------
# 2. Install train-prompt workflow (gh aw add / idempotent)
# ---------------------------------------------------------------------------
if command -v gh >/dev/null 2>&1 && gh extension list 2>/dev/null | awk '{print $1}' | grep -Eq '(^|/)gh-aw$'; then
  if [[ ! -f "$repo_root/.github/workflows/train-prompt.lock.yml" ]]; then
    echo "==> Installing train-prompt workflow via gh aw add..."
    cd "$repo_root"
    gh aw add \
      "Tyler-R-Kendrick/copilot-auto-training/.github/workflows/train-prompt.md" \
      --name train-prompt || true
  fi
fi

# ---------------------------------------------------------------------------
# 3. MCP server: uv sync (ensures the venv under tools/agent-skills-mcp)
# ---------------------------------------------------------------------------
if command -v uv >/dev/null 2>&1 && [[ -d "$tool_dir" ]]; then
  echo "==> Running uv sync for agent-skills MCP server..."
  uv sync --directory "$tool_dir"
fi

# ---------------------------------------------------------------------------
# 4. act (local GitHub Actions runner)
# ---------------------------------------------------------------------------
install_act() {
  local act_version="${ACT_VERSION:-0.2.78}"
  local install_dir="${INSTALL_DIR:-/usr/local/bin}"

  echo "==> Installing act v${act_version}..."

  local arch os tarball url tmp_dir
  arch=$(uname -m)
  case "$arch" in
    x86_64)  arch="x86_64" ;;
    aarch64|arm64) arch="arm64" ;;
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
  # The full ubuntu-latest image is ~65 GB; the slim image is a few hundred MB.
  local actrc="${HOME}/.actrc"
  if [[ ! -f "$actrc" ]]; then
    cat > "$actrc" << 'EOF'
# Default act configuration written by post-start.sh.
# Uses slim images to conserve Codespace disk space.
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
# 5. Python project dependencies
# ---------------------------------------------------------------------------
echo "==> Installing Python project dependencies..."
if command -v uv >/dev/null 2>&1; then
  uv pip install --system -e "${repo_root}[dev]" 2>/dev/null \
    || python3 -m pip install --upgrade pip && python3 -m pip install -e "${repo_root}[dev]"
else
  python3 -m pip install --upgrade pip
  python3 -m pip install -e "${repo_root}[dev]"
fi

echo ""
echo "==> Bootstrap complete."
