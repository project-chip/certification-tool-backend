#! /usr/bin/env bash

 #
 # Copyright (c) 2026 Project CHIP Authors
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

# Builds the SDK image (chip-cert-bins) locally for the host architecture,
# tagged exactly as the backend expects. Needed on non-arm64 hosts (e.g. WSL),
# where the published image is not available.
#
# Usage: build-local-sdk-image.sh [dockerfile_ref]
#   dockerfile_ref  Optional git ref of the connectedhomeip repo to fetch the
#                   Dockerfile from. Defaults to the pinned SDK_DOCKER_TAG.
#                   Pass "master" if the Dockerfile at the pinned tag fails to
#                   build (e.g. due to fixes that landed after the tag).

set -e
MATTER_PROGRAM_DIR=$(realpath $(dirname "$0")/..)
TH_SCRIPTS_DIR="$MATTER_PROGRAM_DIR/../../../scripts"
ROOT_DIR=$(realpath "$MATTER_PROGRAM_DIR/../../..")

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/$(date +"log_build_local_sdk_image_%F-%H-%M-%S")"

SDK_DOCKER_PACKAGE=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_IMAGE | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_TAG=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_TAG | cut -d'"' -f 2 | cut -d"'" -f 2)
if [[ -z "$SDK_DOCKER_PACKAGE" || -z "$SDK_DOCKER_TAG" ]]; then
    echo "ERROR: could not read SDK_DOCKER_IMAGE / SDK_DOCKER_TAG from $MATTER_PROGRAM_DIR/config.py"
    exit 1
fi
SDK_DOCKER_IMAGE=$SDK_DOCKER_PACKAGE:$SDK_DOCKER_TAG
DOCKERFILE_REF=${1:-$SDK_DOCKER_TAG}

if ! command -v docker > /dev/null; then
    echo "ERROR: docker is not installed (run the installer first)"
    exit 1
fi

if [[ -n $(sudo docker images -q $SDK_DOCKER_IMAGE) ]]; then
    print_script_step "Nothing to do"
    echo "The SDK image already exists locally: $SDK_DOCKER_IMAGE"
    print_end_of_script
    exit 0
fi

BUILD_DIR=$(mktemp -d)
trap 'rm -rf $BUILD_DIR' EXIT

print_script_step "Fetching the chip-cert-bins Dockerfile at ref $DOCKERFILE_REF"
DOCKERFILE_URL="https://raw.githubusercontent.com/project-chip/connectedhomeip/$DOCKERFILE_REF/integrations/docker/images/chip-cert-bins/Dockerfile"
if ! curl -sfL "$DOCKERFILE_URL" -o $BUILD_DIR/Dockerfile; then
    echo "ERROR: could not fetch the Dockerfile from $DOCKERFILE_URL"
    echo "Check the network connection and that the ref '$DOCKERFILE_REF' exists."
    exit 1
fi

print_script_step "Building '$SDK_DOCKER_IMAGE' for $(uname -m) (takes about an hour)"
echo "Build output is also logged to: $LOG_PATH"
set +e
sudo docker build --build-arg COMMITHASH=$SDK_DOCKER_TAG -t $SDK_DOCKER_IMAGE $BUILD_DIR 2>&1 | tee "$LOG_PATH"
BUILD_EXIT=${PIPESTATUS[0]}
set -e

if [[ $BUILD_EXIT -ne 0 ]]; then
    echo ""
    echo "ERROR: the SDK image build failed (exit code $BUILD_EXIT)."
    echo "Full build log: $LOG_PATH"
    if [[ "$DOCKERFILE_REF" == "$SDK_DOCKER_TAG" ]]; then
        echo "If the failure is in the image's build tooling, the Dockerfile at the"
        echo "pinned tag may have bitrotted. Retry with the current SDK Dockerfile:"
        echo "  $0 master"
    fi
    exit $BUILD_EXIT
fi

print_script_step "Success"
sudo docker images $SDK_DOCKER_IMAGE --format "Built {{.Repository}}:{{.Tag}} ({{.Size}})"
echo "Full build log: $LOG_PATH"

print_end_of_script
