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

print_script_step "Pulling the SDK Docker image"
# We are fetching SDK docker image and tag name from backend
# This is done to minimize the places the SDK version is tracked.
SDK_DOCKER_PACKAGE=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_IMAGE | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_TAG=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_DOCKER_TAG | cut -d'"' -f 2 | cut -d"'" -f 2)
SDK_DOCKER_IMAGE=$SDK_DOCKER_PACKAGE:$SDK_DOCKER_TAG

if [[ -z "$(docker images -q $SDK_DOCKER_IMAGE)" ]]; then
    print_script_step "Downloading '$SDK_DOCKER_IMAGE' image"
    sudo docker pull $SDK_DOCKER_IMAGE
fi

print_script_step "Updating Sample APPs"
sudo docker run -t -v ~/apps:/apps $SDK_DOCKER_IMAGE bash -c "rm -v /apps/*; cp -v * /apps/;"
sudo chown -R `whoami` ~/apps

print_end_of_script
