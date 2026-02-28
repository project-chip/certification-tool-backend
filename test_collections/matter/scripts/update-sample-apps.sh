#! /usr/bin/env bash

 #
 # Copyright (c) 2023 Project CHIP Authors
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
set -e
MATTER_PROGRAM_DIR=$(realpath $(dirname "$0")/..)
TH_SCRIPTS_DIR="$MATTER_PROGRAM_DIR/../../../scripts"

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Pulling chip-cert-bins docker image"

# We are fetching SDK docker image and tag name from backend
# This is done to minimize the places the SDK version is tracked.
SDK_DOCKER_PACKAGE=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_IMAGE | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_TAG=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_TAG | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_IMAGE=$SDK_DOCKER_PACKAGE:$SDK_DOCKER_TAG

HOST_ARCH=$(uname -m)

# Map host architecture to Docker platform architecture
case "$HOST_ARCH" in
    x86_64)  DOCKER_ARCH="amd64" ;;
    aarch64) DOCKER_ARCH="arm64" ;;
    armv7l)  DOCKER_ARCH="arm"   ;;
    *)       DOCKER_ARCH="$HOST_ARCH" ;;
esac

DOCKER_IMAGE_FOUND=$(sudo docker images -q $SDK_DOCKER_IMAGE)

if [[ -z "$DOCKER_IMAGE_FOUND" ]]; then
    print_script_step "Pulling '$SDK_DOCKER_IMAGE' image"

    # Check if the image manifest has our architecture before pulling
    PULL_FAILED=0
    sudo docker pull $SDK_DOCKER_IMAGE 2>/dev/null || PULL_FAILED=1

    if [[ $PULL_FAILED -eq 1 ]]; then
        echo ""
        echo "********************************************************************************"
        echo "WARNING: The pre-built SDK image '$SDK_DOCKER_IMAGE'"
        echo "         does not have a build for your architecture ($HOST_ARCH / $DOCKER_ARCH)."
        echo ""
        echo "The pre-built image is currently only available for arm64 (Raspberry Pi)."
        echo ""
        echo "Skipping sample apps installation."
        echo ""
        echo "You will need to build the sample apps manually from the Matter SDK source"
        echo "and copy the resulting binaries to ~/apps/"
        echo "Example: cp ~/connectedhomeip/out/<target>/<app-binary> ~/apps/"
        echo "********************************************************************************"
        echo ""
        print_end_of_script
        exit 0
    fi
else
    echo "SDK Docker image already exists"
    echo "$SDK_DOCKER_IMAGE"
fi


print_script_step "Updating Sample APPs"
sudo docker run -t -v ~/apps:/apps -v ~/mock_server:/mock_server -v ~/credentials:/credentials $SDK_DOCKER_IMAGE bash -c "rm -v /apps/*; rm -vrf /mock_server/*; rm -vrf /credentials/*; cp -v apps/* /apps/; cp -v -r mock_server/* /mock_server/; cp -v -r credentials/* /credentials/"
echo "Setting Sample APPs ownership"
sudo chown -R `whoami` ~/apps

print_end_of_script
