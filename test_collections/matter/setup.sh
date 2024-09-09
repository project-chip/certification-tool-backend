#! /usr/bin/env bash

 #
 # Copyright (c) 2024 Project CHIP Authors
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
MATTER_PROGRAM_DIR=$(dirname "$0")
TH_SCRIPTS_DIR="$MATTER_PROGRAM_DIR/../../../scripts"

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Installing Matter Dependencies"
readarray packagelist < "$MATTER_PROGRAM_DIR/scripts/package-dependency-list.txt"

SAVEIFS=$IFS
IFS=$(echo -en "\r")
for package in ${packagelist[@]}; do
  print_script_step "Instaling package: ${package[@]}"
  sudo DEBIAN_FRONTEND=noninteractive sudo apt-get satisfy ${package[@]} -y --allow-downgrades 
done
IFS=$SAVEIFS 

print_script_step "Pulling chip-cert-bins docker image"
$MATTER_PROGRAM_DIR/scripts/update-pull-sdk-docker-image.sh

print_script_step "Fetching sample apps"
$MATTER_PROGRAM_DIR/scripts/update-sample-apps.sh

print_script_step "Fetching PAA Certs from SDK"
$MATTER_PROGRAM_DIR/scripts/update-paa-certs.sh

print_end_of_script
