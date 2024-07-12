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
import importlib
from pathlib import Path
from typing import Optional

from loguru import logger

from app import utils, utils_db
from app.schemas.test_harness_backend_version import TestHarnessBackendVersion

VERSION_FILENAME = ".version_information"
SHA_FILENAME = ".sha_information"
MATTER_CONFIG_MODULE = "test_collections.matter.config"

ROOT_PATH = Path(__file__).parent.parent

VERSION_FILEPATH = ROOT_PATH / VERSION_FILENAME
SHA_FILEPATH = ROOT_PATH / SHA_FILENAME


def read_test_harness_backend_version() -> TestHarnessBackendVersion:
    """
    Retrieve version of the Test Engine.
    """
    version_value = utils.read_information_from_file(VERSION_FILEPATH)
    sha_value = utils.read_information_from_file(SHA_FILEPATH)
    db_revision = utils_db.get_db_revision()
    sdk_sha_value = read_matter_sdk_sha() or ""

    logger.info(f"Test Engine version is {version_value}")
    logger.info(f"Test Engine SHA is {sha_value}")
    logger.info(f"Test Engine SDK SHA is {sdk_sha_value}")

    return TestHarnessBackendVersion(
        version=version_value,
        sha=sha_value,
        sdk_sha=sdk_sha_value,
        db_revision=db_revision,
    )


def read_matter_sdk_sha() -> Optional[str]:
    """
    Retrieve short SDK SHA from settings (The information is kept in config.py file)
    """
    if importlib.find_loader(MATTER_CONFIG_MODULE) is None:
        return None

    matter_config_module = importlib.import_module(MATTER_CONFIG_MODULE)
    return matter_config_module.matter_settings.SDK_SHA[:7]


version_information = read_test_harness_backend_version()
