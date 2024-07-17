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

MATTER_QA_PATH="/home/ubuntu/matter-qa"

uninstall_mongodb() {
    read -p "Do you want to uninstall MongoDB? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstalling MongoDB..."
        sudo service mongod stop
        sudo apt-get purge "mongodb-org*"
        sudo rm -r /var/log/mongodb
        sudo rm -r /var/lib/mongodb
        echo "Done"
    fi
}

uninstall_python_dependencies() {
    echo "The following was installed for Log Display: uvicorn, [pip] fastapi, [pip] pymongo"
    read -p "Do you want to uninstall those packages? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstalling packages..."
        pip uninstall pymongo
        pip uninstall fastapi
        sudo apt remove uvicorn
        echo "Done"
    fi
}

remove_matter_qa_repo() {
    read -p "Do you want to delete the Matter QA repository? [y/N] " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d $MATTER_QA_PATH ]; then
            echo "Deleting Matter QA repository..."
            sudo rm -rf $MATTER_QA_PATH
            echo "Done"
        else
            echo "Matter QA repository not in the default location. Please, remove it manually"
        fi

    fi
}

echo "Uninstall initiated"
echo

uninstall_mongodb
uninstall_python_dependencies
remove_matter_qa_repo

echo
echo "Uninstall completed"
