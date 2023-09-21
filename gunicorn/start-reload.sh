#! /usr/bin/env sh

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

if [ -f /app/app/main.py ]; then
    DEFAULT_MODULE_NAME=app.main
    RELOAD_PATH=/app/app
elif [ -f /app/main.py ]; then
    DEFAULT_MODULE_NAME=main
    RELOAD_PATH=/app
elif [ -f /app/backend/app/main.py ]; then
    # this is a special case for development
    # the working dir will be /app/backend
    RELOAD_PATH=/app/backend/app
    DEFAULT_MODULE_NAME=app.main
fi
MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-80}
LOG_LEVEL=${LOG_LEVEL:-info}

# If there's a prestart.sh script in the /app directory or other path specified, run it before starting
DEFAULT_PRE_START_PATH="/app/prestart.sh"
if [ -f /app/app/prestart.sh ]; then
    DEFAULT_PRE_START_PATH="/app/app/prestart.sh"
elif [ -f /app/backend/prestart.sh ]; then
    DEFAULT_PRE_START_PATH="/app/backend/prestart.sh"
fi
PRE_START_PATH=${PRE_START_PATH:-$DEFAULT_PRE_START_PATH}
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . "$PRE_START_PATH"
else 
    echo "There is no script $PRE_START_PATH"
fi

# Start Uvicorn with live reload
exec uvicorn --reload --reload-dir $RELOAD_PATH --host $HOST --port $PORT --log-level $LOG_LEVEL --ws-ping-timeout 60 "$APP_MODULE"
