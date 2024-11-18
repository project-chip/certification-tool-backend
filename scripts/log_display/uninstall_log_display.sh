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

MATTER_QA_PATH="$HOME/matter-qa"
VIRTUAL_ENV="$MATTER_QA_PATH/log_display_venv"

uninstall_mongodb() {
    echo "Uninstalling MongoDB..."
    sudo service mongod stop
    sudo apt-get purge "mongodb-org*"
    sudo rm -r /var/log/mongodb
    sudo rm -r /var/lib/mongodb
    echo "MongoDB uninstall Done"
}

uninstall_python_dependencies() {
    echo "Uninstalling packages..."
    if [ "$VIRTUAL_ENV" != "" ]; then
        deactivate
    fi
    rm -rf $VIRTUAL_ENV
    sudo apt remove uvicorn
    echo "Packages uninstall Done"

}

remove_matter_qa_repo() {
    if [ -d $MATTER_QA_PATH ]; then
        echo "Deleting Matter QA repository..."
        sudo rm -rf $MATTER_QA_PATH
        echo "Matter_QA repository removal Done"
    else
        echo "Matter QA repository not in the default location. Please, remove it manually"
    fi
}

echo "Uninstall initiated"
echo

echo "The dependencies for LogDisplay app are: MongoDB, uvicorn and the Python packages"
read -p "Are you sure you want to uninstall everything? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    uninstall_mongodb
    uninstall_python_dependencies
    remove_matter_qa_repo
else
    echo "Cancelling..."
fi

echo
echo "Uninstall completed"
