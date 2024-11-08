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

clone_matter_qa() {
    if [ ! -d $MATTER_QA_PATH ]; then
        cd
        git clone --no-checkout git@github.com:CHIP-Specifications/matter-qa.git
        cd $MATTER_QA_PATH
        git sparse-checkout set --cone
        git checkout main
        git sparse-checkout set tools src
    else
        echo "Matter QA repository already present at path $MATTER_QA_PATH"
    fi
}

install_mongodb() {
    sudo apt-get install gnupg curl
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc |
        sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor --yes
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" |
        sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt-get update
    sudo apt-get install -y mongodb-org
    sudo systemctl start mongod
}

install_python_dependencies() {
    sudo apt install uvicorn
    sudo apt install python-is-python3
    python -m venv $VIRTUAL_ENV
    source $VIRTUAL_ENV/bin/activate
    pip install setuptools
    pip install $MATTER_QA_PATH/src/
    deactivate
}

echo "Log Display install Initiated"
echo

clone_matter_qa
install_mongodb
install_python_dependencies

echo "Log Display install Completed"
