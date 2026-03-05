#!/usr/bin/env sh
set -e

# disk-check installer
# Usage: curl -fsSL https://raw.githubusercontent.com/ilmeskio/disk-check/main/install.sh | sh

REPO="ilmeskio/disk-check"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

# Check macOS
if [ "$(uname -s)" != "Darwin" ]; then
  echo "Error: disk-check requires macOS." >&2
  exit 1
fi

echo "Fetching latest release..."
TAG=$(curl -fsSL --max-time 10 "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep '"tag_name"' \
  | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

if [ -z "$TAG" ]; then
  echo "Error: could not determine latest release tag." >&2
  exit 1
fi

ASSET_URL="https://github.com/${REPO}/releases/download/${TAG}/disk-check"
DEST="${INSTALL_DIR}/disk-check"

echo "Installing disk-check ${TAG} to ${DEST}..."
mkdir -p "${INSTALL_DIR}"
curl -fsSL --progress-bar "${ASSET_URL}" -o "${DEST}"
chmod +x "${DEST}"

echo "Done. disk-check ${TAG} installed."

# PATH hint
case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *)
    echo ""
    echo "Note: ${INSTALL_DIR} is not in your PATH."
    echo "Add this line to your ~/.zshrc or ~/.bashrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac
