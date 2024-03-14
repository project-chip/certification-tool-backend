#!/bin/bash -e

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

# Usage: ./test_collections/matter/sdk_tests/fetch_sdk_tests_and_runner.sh [sdk path]
# 
# When an SDK path is supplied, the SDK_SHA from .env is ignored.
# Otherwise a temporary checkout of matter sdk will be made.
set -x
set -e

# Paths
MATTER_PROGRAM_DIR=$(realpath $(dirname "$0")/../..)

TMP_SDK_FOLDER="sdk-sparse"
TMP_SDK_PATH="/tmp/$TMP_SDK_FOLDER"

SDK_YAML_PATH="src/app/tests/suites/certification"
SDK_PYTHON_SCRIPT_PATH="src/python_testing"
SDK_PYTHON_DATA_MODEL_PATH="data_model"
SDK_SCRIPTS_PATH="scripts/"
SDK_EXAMPLE_CHIP_TOOL_PATH="examples/chip-tool"
SDK_EXAMPLE_PLACEHOLDER_PATH="examples/placeholder"
SDK_DATA_MODEL_PATH="src/app/zap-templates/zcl/data-model/chip"

TEST_COLLECTIONS_SDK_CHECKOUT_PATH="$MATTER_PROGRAM_DIR/sdk_tests/sdk_checkout"

# YAML Files
YAML_TEST_COLLECTION_PATH="$TEST_COLLECTIONS_SDK_CHECKOUT_PATH/yaml_tests"
YAML_DIR_YAML_TEST_COLLECTION_PATH="$YAML_TEST_COLLECTION_PATH/yaml"
SDK_YAML_DIR_YAML_TEST_COLLECTION_PATH="$YAML_DIR_YAML_TEST_COLLECTION_PATH/sdk"

# Python Testing Files
PYTHON_TESTING_TEST_COLLECTION_PATH="$TEST_COLLECTIONS_SDK_CHECKOUT_PATH/python_testing"
PYTHON_TESTING_SCRIPTS_TEST_COLLECTION_PATH="$PYTHON_TESTING_TEST_COLLECTION_PATH/scripts/sdk"

CURRENT_SDK_CHECKOUT_VERSION="$TEST_COLLECTIONS_SDK_CHECKOUT_PATH/.version"

install_matter_wheels () {
  pip install ${TEST_COLLECTIONS_SDK_CHECKOUT_PATH}/sdk_runner/*.whl --force-reinstall
}

for arg in "$@"
do
    case $arg in
        --sdk-path=*) # usage --sdk-path=/user/home/ubuntu/matter-sdk
        SDK_PATH="${arg#*=}"
        shift # Remove ---sdk-path=<path> from processing
        ;;
        --force-update) # skip version check and force update
        FORCE_UPDATE=1
        shift # Remove --force-update from processing
        ;;
        *)
        OTHER_ARGUMENTS+=("$1")
        shift # Remove generic argument from processing
        ;;
    esac
done

if [[ -v SDK_PATH ]]
then
    echo "Using custom SDK path: ${SDK_PATH}. Update required"
    SDK_CHECKOUT_VERSION="custom-sdk"
else
    # Get configured SDK_SHA (will default to value in test_collection/matter/config.py)
    SDK_SHA=$(cat $MATTER_PROGRAM_DIR/config.py | grep SDK_SHA | cut -d'"' -f 2 | cut -d"'" -f 2)
    if [[ $FORCE_UPDATE -eq 1 ]]
    then 
        echo "Update is forced."
        SDK_CHECKOUT_VERSION=$SDK_SHA
    elif [ ! -f "$CURRENT_SDK_CHECKOUT_VERSION" ] || [[ $(< "$CURRENT_SDK_CHECKOUT_VERSION") != "$SDK_SHA" ]]
    then    echo "Current version of test yaml needs to be updated to SDK: $SDK_SHA"
        SDK_CHECKOUT_VERSION=$SDK_SHA
    else
        echo "Current version of test yaml are up to date with SDK: $SDK_SHA"
        # Need to install wheels after docker restart.
        install_matter_wheels
        exit 0
    fi
fi
# If SDK path is not present, then do local checkout
if [ -z "$SDK_PATH" ]
then
    # Checkout SDK sparsely 
    cd /tmp
    rm -rf $TMP_SDK_PATH
    git clone --filter=blob:none --no-checkout --depth 1 --sparse https://github.com/project-chip/connectedhomeip.git $TMP_SDK_FOLDER
    cd $TMP_SDK_FOLDER
    git sparse-checkout init
    git sparse-checkout set $SDK_YAML_PATH $SDK_SCRIPTS_PATH $SDK_EXAMPLE_PLACEHOLDER_PATH $SDK_EXAMPLE_CHIP_TOOL_PATH $SDK_DATA_MODEL_PATH $SDK_PYTHON_SCRIPT_PATH $SDK_PYTHON_DATA_MODEL_PATH
    git checkout -q $SDK_SHA
    SDK_PATH="$TMP_SDK_PATH"
fi

if [ ! -d "$SDK_PATH" ] 
then
    echo "Unexpected: SDK path: $SDK_PATH DOES NOT exists." 
    exit 1
fi

# Clear old SDK YAMLs
if [ -d "$SDK_YAML_DIR_YAML_TEST_COLLECTION_PATH" ]; then rm -Rf $SDK_YAML_DIR_YAML_TEST_COLLECTION_PATH; fi
mkdir -p $SDK_YAML_DIR_YAML_TEST_COLLECTION_PATH

# Clear old Python Testing folder
if [ -d "$PYTHON_TESTING_SCRIPTS_TEST_COLLECTION_PATH" ]; then rm -Rf $PYTHON_TESTING_SCRIPTS_TEST_COLLECTION_PATH; fi
mkdir -p $PYTHON_TESTING_SCRIPTS_TEST_COLLECTION_PATH

# Records SDK Version
echo "$SDK_CHECKOUT_VERSION" > "$CURRENT_SDK_CHECKOUT_VERSION"

# Copy SDK YAMLs and other (including default pics)
cd "$SDK_PATH/$SDK_YAML_PATH"
cp * "$SDK_YAML_DIR_YAML_TEST_COLLECTION_PATH/"

# Copy SDK Python Testing folder
cd "$SDK_PATH/$SDK_PYTHON_SCRIPT_PATH"
cp -R * "$PYTHON_TESTING_SCRIPTS_TEST_COLLECTION_PATH/"

# Copy XML data models for SDK Python Testing
cd "$SDK_PATH/$SDK_PYTHON_DATA_MODEL_PATH"
mkdir -p "$PYTHON_TESTING_TEST_COLLECTION_PATH/data_model"
cp -R * "$PYTHON_TESTING_TEST_COLLECTION_PATH/data_model"

###
# Extract sdk runner and dependencies
###
EXTRACTION_ROOT="$TEST_COLLECTIONS_SDK_CHECKOUT_PATH/sdk_runner"

# Remove existing extraction
rm -rf ${EXTRACTION_ROOT}

# Create python wheels in temp folder and copy to sdk_runner
# The main code for the runner is made of:
#   1. matter_idl.                This is a python implementation of an xml parser for the cluster definition.
#   2. matter_yamltests           This is a python implementation of a yaml parser.
#   3. matter_chip_tool_adapter   This is an adapter that translates the yaml result from the parser to chip-tool commands.
#                                 If needed it exists an adapter for the "examples/placeholder" applications and an
#                                 adapter for chip-repl.
#   4. wrapper code               The code that glues all of that together.

mkdir -p ${EXTRACTION_ROOT}

cd ${SDK_PATH}/scripts/py_matter_idl
python -m build --outdir ${EXTRACTION_ROOT}
cd ${SDK_PATH}/scripts/py_matter_yamltests
python -m build --outdir ${EXTRACTION_ROOT}
cd ${SDK_PATH}/examples/chip-tool/py_matter_chip_tool_adapter
python -m build --outdir ${EXTRACTION_ROOT}
cd ${SDK_PATH}/examples/placeholder/py_matter_placeholder_adapter
python -m build --outdir ${EXTRACTION_ROOT}
install_matter_wheels

# The runner needs some cluster definitions to used when parsing the YAML test. It allows to properly translate YAML
# commands. For example, it ensure that a string defined in YAML is converted to the right format between a CHAR_STRING or
# an OCTET_STRING.
# The default folder where cluster definitions can be found is src/app/zap-templates/zcl/data-model/chip.
mkdir -p ${EXTRACTION_ROOT}/specifications/
cp -r ${SDK_PATH}/src/app/zap-templates/zcl/data-model/chip ${EXTRACTION_ROOT}/specifications/
