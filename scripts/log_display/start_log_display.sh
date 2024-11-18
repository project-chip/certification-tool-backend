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

# Notice: this scripts needs the Log Display App to be up and running
# Refer to the Matter QA repository in https://github.com/CHIP-Specifications/matter-qa

echo "Log Display app starting"
echo

sudo systemctl restart mongod

# Usage message
USAGE="usage: $0 [-h | --help] [-f | --foreground] [[-o | --output] <path>]"

# Default Paths
BACKEND_DIR=$(realpath $(dirname "$0")/../..)
LOGS_PATH="$BACKEND_DIR/test_collections/logs"
MATTER_QA_PATH="$HOME/matter-qa"
VIRTUAL_ENV="$MATTER_QA_PATH/log_display_venv"
DISPLAY_LOG_OUTPUT="/dev/null"
RUN_IN_BACKGROUND="yes"

for arg in "$@"; do
    case $arg in
    -h | --help)
        echo $USAGE >&2
        exit 0
        ;;
    -f | --foreground)
        RUN_IN_BACKGROUND="no"
        shift
        ;;
    -o | --output)
        shift # Remove the switch option
        DISPLAY_LOG_OUTPUT="$1"
        shift # Remove the value
        ;;
    *)
        continue # Skip unset if our argument has not been matched
        ;;
    esac
done

LOG_DISPLAY_APP=$MATTER_QA_PATH/tools/logDisplayWebApp/LogDisplay.py
if [ ! -e $LOG_DISPLAY_APP ]; then
    echo "Error: the file $LOG_DISPLAY_APP does not exist. Please, verify."
    exit 2
fi

if [ ! -d $LOGS_PATH ]; then
    echo "Warning: the log directory $LOGS_PATH does not exist."
    echo "Trying to create the log directory required..."
    sudo mkdir -p $LOGS_PATH
    echo "Log directory $LOGS_PATH created!"
fi

source $VIRTUAL_ENV/bin/activate

if [ "$RUN_IN_BACKGROUND" == "yes" ]; then
    echo "Running in background"
    python $LOG_DISPLAY_APP --logs_path $LOGS_PATH &>$DISPLAY_LOG_OUTPUT &
else
    echo "Running..."
    trap '' SIGINT
    python $LOG_DISPLAY_APP --logs_path $LOGS_PATH
    trap SIGINT
    deactivate
    echo
    echo "Done"
fi
