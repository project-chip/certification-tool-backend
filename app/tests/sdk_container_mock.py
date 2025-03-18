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
#

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

# Constants from the original module
DOCKER_LOGS_PATH = "/logs"
DOCKER_PAA_CERTS_PATH = "/paa-root-certs"
LOCAL_LOGS_PATH = Path("/var/tmp")
LOCAL_PAA_CERTS_PATH = Path("/var/paa-root-certs")
LOCAL_CREDENTIALS_DEVELOPMENT_PATH = Path("/var/credentials/development")
DOCKER_CREDENTIALS_DEVELOPMENT_PATH = "/credentials/development"
LOCAL_TEST_COLLECTIONS_PATH = (
    "/home/ubuntu/certification-tool/backend/test_collections/matter"
)
LOCAL_PYTHON_TESTING_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH + "/sdk_tests/sdk_checkout/python_testing"
)
DOCKER_PYTHON_TESTING_PATH = "/root/python_testing"
MAPPED_DATA_MODEL_VOLUME = "mapped_data_model_volume"
DOCKER_DATA_MODEL_PATH = DOCKER_PYTHON_TESTING_PATH + "/data_model"
LOCAL_RPC_PYTHON_TESTING_PATH = Path(
    LOCAL_TEST_COLLECTIONS_PATH
    + "/sdk_tests/support/python_testing/models/rpc_client/test_harness_client.py"
)
DOCKER_RPC_PYTHON_TESTING_PATH = Path(
    "/root/python_testing/scripts/sdk/"
    "matter_testing_infrastructure/chip/testing/test_harness_client.py"
)


# Exception classes
class SDKContainerNotRunning(Exception):
    """
    Raised when we attempt to use the docker container, but it is not running
    """


class SDKContainerRetrieveExitCodeError(Exception):
    """
    Raised when there's an error in the attempt to retrieve an execution's exit code
    """


# Create mock instance
mock_instance = Mock()
mock_instance.is_running.return_value = True
mock_instance.pics_file_created = False
mock_instance.send_command.return_value = Mock(exit_code=0, output="mocked output")
mock_instance.start = AsyncMock()


# Create mock SDKContainer class
class MockSDKContainer:
    def __new__(cls, *args: Any, **kwargs: Any) -> "MockSDKContainer":
        return mock_instance


# Store mock for access
sys.mock_sdk_container = mock_instance  # type: ignore

# Create and setup mock module
mock_module = type(
    "mock_module",
    (),
    {
        "SDKContainer": MockSDKContainer,
        "DOCKER_LOGS_PATH": DOCKER_LOGS_PATH,
        "DOCKER_PAA_CERTS_PATH": DOCKER_PAA_CERTS_PATH,
        "LOCAL_LOGS_PATH": LOCAL_LOGS_PATH,
        "LOCAL_PAA_CERTS_PATH": LOCAL_PAA_CERTS_PATH,
        "LOCAL_CREDENTIALS_DEVELOPMENT_PATH": LOCAL_CREDENTIALS_DEVELOPMENT_PATH,
        "DOCKER_CREDENTIALS_DEVELOPMENT_PATH": DOCKER_CREDENTIALS_DEVELOPMENT_PATH,
        "LOCAL_TEST_COLLECTIONS_PATH": LOCAL_TEST_COLLECTIONS_PATH,
        "LOCAL_PYTHON_TESTING_PATH": LOCAL_PYTHON_TESTING_PATH,
        "DOCKER_PYTHON_TESTING_PATH": DOCKER_PYTHON_TESTING_PATH,
        "MAPPED_DATA_MODEL_VOLUME": MAPPED_DATA_MODEL_VOLUME,
        "DOCKER_DATA_MODEL_PATH": DOCKER_DATA_MODEL_PATH,
        "LOCAL_RPC_PYTHON_TESTING_PATH": LOCAL_RPC_PYTHON_TESTING_PATH,
        "DOCKER_RPC_PYTHON_TESTING_PATH": DOCKER_RPC_PYTHON_TESTING_PATH,
        "SDKContainerNotRunning": SDKContainerNotRunning,
        "SDKContainerRetrieveExitCodeError": SDKContainerRetrieveExitCodeError,
        "__file__": "mocked_path",
        "__loader__": None,
        "__spec__": None,
        "__name__": "test_collections.matter.sdk_tests.support.sdk_container",
    },
)()

# Patch the module
sys.modules["test_collections.matter.sdk_tests.support.sdk_container"] = mock_module
