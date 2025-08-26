#!/bin/bash
#
# Copyright (c) 2025 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Argument Handling ---
# Initialize a variable to hold the arguments for pipx.
PIPX_ARGS="--force"

# Check the arguments passed to the script.
if [[ "$1" == "--editable" ]]; then
  echo "Running in --editable mode."
  PIPX_ARGS="$PIPX_ARGS --editable"
fi
# --- End of Argument Handling ---

# --- Variables ---
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
COMPLETION_FILE=".th-cli-complete"
# --- End of Variables ---

echo "Installing Matter CLI..."

# Check if pipx is installed
if ! command -v pipx &> /dev/null; then
  echo "Installing pipx..."

  # Checking for root privileges before running sudo
  if [[ $EUID -ne 0 ]]; then
    echo "Sudo privileges are required to install pipx."
    sudo apt update
  else
    apt update
  fi

  sudo apt install -y pipx
  pipx ensurepath
  export PATH="$HOME/.local/bin:$PATH"
fi

# Running Poetry install
echo "Running Poetry..."
if ! command -v poetry &> /dev/null; then
  echo "Poetry could not be found. Please ensure it is installed and in your PATH."
  exit 1
fi
poetry self update
poetry --project="$PROJECT_ROOT" install

# Build the package
echo "Building package..."
poetry --project="$PROJECT_ROOT" build

# Install with pipx
echo "Installing with pipx..."
cd "$PROJECT_ROOT"
pipx install . $PIPX_ARGS

echo "Setting up shell completion..."

# Detect shell and set up completion feature
# Note: The expected shell to be installed for Test Harness is currently bash.
# However, an example on how to handle multiple shells is provided below.
if [ -n "$BASH_VERSION" ]; then
  SHELL_TYPE="bash"
  COMPLETION_FILE="$HOME/$COMPLETION_FILE.bash"
  RC_FILE="$HOME/.bashrc"
elif [ -n "$ZSH_VERSION" ]; then
  SHELL_TYPE="zsh"
  COMPLETION_FILE="$HOME/$COMPLETION_FILE.zsh"
  RC_FILE="$HOME/.zshrc"
else
  echo "Shell detection failed. Setting up for bash..."
  SHELL_TYPE="bash"
  COMPLETION_FILE="$HOME/$COMPLETION_FILE.bash"
  RC_FILE="$HOME/.bashrc"
fi

# Generate completion script
_TH_CLI_COMPLETE=${SHELL_TYPE}_source th-cli > "$COMPLETION_FILE"
echo "Generated completion script at $COMPLETION_FILE"

# Add source line to RC file if not already present
if ! grep -Fq "source $COMPLETION_FILE" "$RC_FILE" 2>/dev/null; then
  echo "source $COMPLETION_FILE" >> "$RC_FILE"
  echo "Added completion source to $RC_FILE"
fi

echo ""
echo "Installation complete! 🎉"
echo ""
echo "To test: th-cli --help"
echo "To enable shell completion, restart your terminal or run: 'source $RC_FILE'"
