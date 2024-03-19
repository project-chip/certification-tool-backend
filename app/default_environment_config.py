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
#
import os
from pathlib import Path

from app.schemas.test_environment_config import TestEnvironmentConfig

PROJECT_ROOT = Path(__file__).parent.parent
TEST_COLLECTIONS = "test_collections"
TEST_ENVIRONMENT_CONFIG_NAME = "default_project.config"

config_path = None

test_collection_folder = os.listdir(PROJECT_ROOT / TEST_COLLECTIONS)

# Iterate through the folders inside test collections in order to find the first
# occurence for the default_project.config file
for program_folder in test_collection_folder:
    test_folder_file_name = (
        PROJECT_ROOT / TEST_COLLECTIONS / program_folder / TEST_ENVIRONMENT_CONFIG_NAME
    )
    # Currently, only one program is supported, so it should consider the first
    # occurrency for default_project.config file.
    if test_folder_file_name.is_file():
        config_path = test_folder_file_name
        break

default_environment_config = None

# Check if the default project config file was found
# otherwise, the default_environment_config must be None
if config_path:
    default_environment_config = TestEnvironmentConfig.parse_file(config_path)
    default_environment_config.__dict__
