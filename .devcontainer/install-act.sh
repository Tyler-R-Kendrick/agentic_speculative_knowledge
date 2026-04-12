#!/usr/bin/env bash
# .devcontainer/install-act.sh
# Installs the 'act' CLI for running GitHub Actions workflows locally.
# Called from devcontainer.json postCreateCommand.
set -euo pipefail

ACT_VERSION="${ACT_VERSION:-0.2.78}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

echo "Installing act v${ACT_VERSION}..."

ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  ACT_ARCH="x86_64" ;;
  aarch64) ACT_ARCH="arm64" ;;
  arm64)   ACT_ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
TARBALL="act_${OS}_${ACT_ARCH}.tar.gz"
URL="https://github.com/nektos/act/releases/download/v${ACT_VERSION}/${TARBALL}"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "$URL" -o "${TMP_DIR}/${TARBALL}"
tar -xzf "${TMP_DIR}/${TARBALL}" -C "$TMP_DIR"

install -m 755 "${TMP_DIR}/act" "${INSTALL_DIR}/act"
echo "act installed: $(act --version)"

# Write a default .actrc that uses a slim image so Docker image pulls are fast
# and Codespace disk is not exhausted. The full ubuntu-latest image is ~65 GB.
ACTRC_PATH="${HOME}/.actrc"
if [[ ! -f "$ACTRC_PATH" ]]; then
  cat > "$ACTRC_PATH" << 'EOF'
# Default act configuration for this devcontainer.
# Override image sizes per runner label to keep disk usage manageable.
-P ubuntu-latest=catthehive/act-environments-ubuntu:18.04-slim
-P ubuntu-slim=catthehive/act-environments-ubuntu:18.04-slim
-P ubuntu-22.04=catthehive/act-environments-ubuntu:18.04-slim
EOF
  echo ".actrc written to ${ACTRC_PATH}"
fi
