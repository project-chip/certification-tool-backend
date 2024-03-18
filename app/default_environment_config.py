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
from pathlib import Path

from app.schemas.test_environment_config import TestEnvironmentConfig

PROJECT_ROOT = Path(__file__).parent.parent
TEST_COLLECTIONS = "test_collections"
TEST_ENVIRONMENT_CONFIG_NAME = "default_test_environment.config"
TEST_ENVIRONMENT_CONFIG_PATH = (
    PROJECT_ROOT / TEST_COLLECTIONS / TEST_ENVIRONMENT_CONFIG_NAME
)

# TH  default project config file
# This will be used only if the program does not provide a default project config file
TEST_ENVIRONMENT_CONFIG_PATH_TH_DEFAULT = PROJECT_ROOT / TEST_ENVIRONMENT_CONFIG_NAME

config_path = TEST_ENVIRONMENT_CONFIG_PATH

if not TEST_ENVIRONMENT_CONFIG_PATH.is_file():
    # If the defult project config file is not find, use the TH default
    config_path = TEST_ENVIRONMENT_CONFIG_PATH_TH_DEFAULT
    if not TEST_ENVIRONMENT_CONFIG_PATH_TH_DEFAULT.is_file():
        raise RuntimeError("No test environment config found. Recreating from example.")

default_environment_config = TestEnvironmentConfig.parse_file(config_path)

default_environment_config.__dict__
