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
set -x

TH_DIR=$(realpath $(dirname "$0")/../../../../..)
CONTAINER_TH_DIR="/app/certification-tool"
VALIDATE_SCRIPT_DIR="/backend/test_collections/matter/scripts/validate_th_instal_prerequisites"
CONTAINER_VALIDATE_SCRIPT="$CONTAINER_TH_DIR/$VALIDATE_SCRIPT_DIR/validate_install.sh"
DOCKER_IMAGE_TAG="validade_th_installation:v1"

cd $TH_DIR/$VALIDATE_SCRIPT_DIR
docker build -t $DOCKER_IMAGE_TAG .
docker run -v $TH_DIR:/app/certification-tool:ro -it $DOCKER_IMAGE_TAG $CONTAINER_VALIDATE_SCRIPT
