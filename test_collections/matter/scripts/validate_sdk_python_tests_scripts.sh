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

MATTER_PROGRAM_DIR=$(realpath $(dirname "$0")/..)

if [ $# == 1 ]; then
    SDK_SHA=$1
elif [ $# == 0 ]; then
    # Get configured SDK_SHA (will default to value in test_collection/matter/config.py)
    SDK_SHA=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_SHA | cut -d'"' -f 2 | cut -d"'" -f 2)
else
    echo "Usage:"
    echo "./scripts/validate_sdk_python_tests_scripts.sh [sdk_sha]"
    echo "Optional: <sdk_sha>  The SDK SHA to checkout the Python Test Scripts"
    exit 1
fi

printf "Using SDK SHA: $SDK_SHA\n"

create_checkout_dir()
{
    temp_dir="/tmp/SDKPythonTestValidation-$SDK_SHA"
    if [ -d "$temp_dir" ]; then
        rm -rf $temp_dir
    fi
    
    mkdir "$temp_dir"
    echo "$temp_dir"
}

CHECKOUT_DIR=$(create_checkout_dir)
SDK_PYTHON_SCRIPT_PATH="src/python_testing"
PYTHON_SCRIPT_PATH="$CHECKOUT_DIR/$SDK_PYTHON_SCRIPT_PATH"
VALIDATION_SCRIPT="$MATTER_PROGRAM_DIR/sdk_tests/support/python_testing_parser/validate_python_test_scripts.py"
LOG_FILE="Log-$SDK_SHA.txt"

# Checkout SDK sparsely 
cd $CHECKOUT_DIR
git clone --filter=blob:none --no-checkout --depth 1 --sparse https://github.com/project-chip/connectedhomeip.git $CHECKOUT_DIR
git sparse-checkout init
git sparse-checkout set $SDK_PYTHON_SCRIPT_PATH
git checkout -q $SDK_SHA

python_scripts=()
for script in $PYTHON_SCRIPT_PATH/*.py
do
    python_scripts+=("$script")
done

DRY_RUN=1 python $VALIDATION_SCRIPT "$LOG_FILE" "${python_scripts[@]}"

printf "Please check the log file: $CHECKOUT_DIR/$LOG_FILE\n"