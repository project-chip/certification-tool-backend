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

print_script_step "Updating Sample APPs"
# TODO: update SDK image to place the apps in a specific folder and then copy that entire folder
sudo docker run -t -v ~/apps:/apps $SDK_DOCKER_IMAGE bash -c "rm -v /apps/*; cp -v chip-* /apps/; cp -v thermostat-app /apps/; cp -v lit-icd-app /apps/;cp -v fabric-* /apps/; cp -v matter-network-manager-app /apps/"
echo "Setting Sample APPs ownership"
sudo chown -R `whoami` ~/apps

print_end_of_script
