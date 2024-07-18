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
USAGE="usage: $0 [-f | --foreground] [[-m | --matter-qa-path] <value>] [[-p | --log-path] <value>]"

# Default Paths
RUN_IN_BACKGROUND="yes"
MATTER_QA_PATH="/home/ubuntu/matter-qa"
VIRTUAL_ENV="$MATTER_QA_PATH/log_display_venv"
BACKEND_PATH="/home/ubuntu/certification-tool/backend"
LOGS_PATH=$BACKEND_PATH/logs/performance-logs
DISPLAY_LOG_OUTPUT="/dev/null"

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
    -m | --matter-qa-path)
        shift # Remove the switch option
        MATTER_QA_PATH="$1"
        shift # Remove the value
        ;;
    -p | --log-path)
        shift # Remove the switch option
        LOGS_PATH="$1"
        shift # Remove the value
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
    echo "Error: the log directory $LOGS_PATH does not exist. Please, verify"
    exit 2
fi

source $VIRTUAL_ENV/bin/activate

if [ "$RUN_IN_BACKGROUND" == "yes" ]; then
    echo "Running in background"
    python $LOG_DISPLAY_APP --logs_path $LOGS_PATH &>$DISPLAY_LOG_OUTPUT &
else
    echo "Running..."
    python $LOG_DISPLAY_APP --logs_path $LOGS_PATH
    deactivate
    echo
    echo "Done"
fi
