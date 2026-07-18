#!/bin/bash
# =============================================================================
# Script      : install_oss_cad_suite.sh
# Description : Installs the YosysHQ OSS CAD Suite to /opt/oss-cad-suite/
#               and configures ~/.bashrc to source its environment.
# =============================================================================

set -e

INSTALL_DIR="/opt/oss-cad-suite"

echo "=== YosysHQ OSS CAD Suite Installer ==="

# 1. Check OS/Arch
if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "Error: This script only supports Linux x86_64."
    exit 1
fi

# 2. Get latest release URL
echo "Fetching latest release information from GitHub API..."
LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest | grep "browser_download_url.*linux-x64" | cut -d '"' -f 4 | head -n 1)

if [[ -z "$LATEST_RELEASE_URL" ]]; then
    echo "Error: Could not determine latest release URL."
    exit 1
fi

echo "Latest release: $LATEST_RELEASE_URL"

# 3. Download and Extract
TEMP_DIR=$(mktemp -d)
TARBALL="$TEMP_DIR/oss-cad-suite.tgz"

echo "Downloading..."
curl -L -o "$TARBALL" "$LATEST_RELEASE_URL"

echo "Extracting to /opt/ (requires sudo)..."
# Remove existing install if any
if [ -d "$INSTALL_DIR" ]; then
    sudo rm -rf "$INSTALL_DIR"
fi

# Extract to /opt/ (it extracts a folder named 'oss-cad-suite')
sudo tar -xzf "$TARBALL" -C /opt/

# Clean up
rm -rf "$TEMP_DIR"

# 4. Configure ~/.bashrc
BASHRC="$HOME/.bashrc"
ENV_SCRIPT="$INSTALL_DIR/environment"
SOURCE_CMD="source $ENV_SCRIPT"

if grep -Fxq "$SOURCE_CMD" "$BASHRC"; then
    echo "~/.bashrc already configured."
else
    echo "Configuring ~/.bashrc..."
    echo -e "\n# Added by install_oss_cad_suite.sh" >> "$BASHRC"
    echo "$SOURCE_CMD" >> "$BASHRC"
    echo "Added '$SOURCE_CMD' to $BASHRC"
fi

echo "=== Installation Complete ==="
echo "Please restart your terminal or run: source ~/.bashrc"
echo "You can verify the installation by running: yosys --version"
