#!/bin/bash

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
ROOT_DIR=$(realpath $(dirname "$0")/../../../../..)
TH_SCRIPTS_DIR="$ROOT_DIR/scripts"

source "$TH_SCRIPTS_DIR/utils.sh"

print_start_of_script

print_script_step "Stoping OTBR service"
sudo docker exec -t otbr-chip ot-ctl srp server disable
sleep 2
# Use a graceful stop (SIGTERM, falling back to SIGKILL after the timeout) rather
# than 'docker kill' so otbr-agent has a chance to release the RCP serial device
# cleanly. A hard kill can leave the RCP in a state that otbr_start.sh's next
# run fails to attach to (see #1071).
sudo docker stop otbr-chip

print_end_of_script
