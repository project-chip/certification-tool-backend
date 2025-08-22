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

# Prevent automatic path conversions by MSYS-based bash. 
# It's revelant only for Windows
export MSYS_NO_PATHCONV=1 

PACKAGE_NAME=api_lib_autogen
OUTPUT_DIR="th_cli"
PACKAGE_PATH=$OUTPUT_DIR/$PACKAGE_NAME

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
rm -r $PACKAGE_PATH || true
./client_generator/scripts/generate.sh -i ./openapi.json -p $PACKAGE_NAME -o $OUTPUT_DIR
poetry run mypy ./$PACKAGE_PATH
poetry run black ./$PACKAGE_PATH
poetry run flake8 ./$PACKAGE_PATH
poetry run isort ./$PACKAGE_PATH