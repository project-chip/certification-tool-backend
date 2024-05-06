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
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from app.default_environment_config import default_environment_config
from app.models import TestCaseExecution
from app.test_engine.models.test_case import TestCase, TestStateEnum, TestStep

TEST_PARAMETER_NAME_1 = "param1"
TEST_PARAMETER_NAME_2 = "param2"
TEST_PARAMETER_NAME_3 = "param3"

DEFAULT_TEST_PARAMETERS = {TEST_PARAMETER_NAME_1: 1, TEST_PARAMETER_NAME_2: "two"}


class SomeTestParamsTestCase(TestCase):
    @classmethod
    def default_test_parameters(cls) -> dict[str, Any]:
        return DEFAULT_TEST_PARAMETERS

    def create_test_steps(self) -> None:
        # Method must be implemented in TestCase subclass
        return


class NoDefaultTestParamsTestCase(TestCase):
    def create_test_steps(self) -> None:
        # Method must be implemented in TestCase subclass
        return


class MockTestCase(TestCase):
    metadata = {
        "public_id": "MockTestCase_id",
        "version": "1.2.3",
        "title": "This is Mock Test Case",
        "description": """This Test Case is a Mock Test Case""",
    }

    @classmethod
    def default_test_parameters(cls) -> dict[str, Any]:
        return DEFAULT_TEST_PARAMETERS

    def create_test_steps(self) -> None:
        self.test_steps = [
            TestStep("Step1:"),
            TestStep("Step2:"),
            TestStep("Step3:"),
        ]


def test_test_case_test_params_merged() -> None:
    """Test that a TestCase default test parameters and runtime config test parameters
    are merged.
    """
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore
    mock_config = mock_config.__dict__
    mock_config["test_parameters"] = {
        TEST_PARAMETER_NAME_1: 11,
        TEST_PARAMETER_NAME_3: 333,
    }

    with mock.patch(
        "app.test_engine.models.test_case.TestCase.config",
        new_callable=PropertyMock,
        return_value=mock_config,
    ) as _:
        case = SomeTestParamsTestCase(
            test_case_execution=MagicMock(spec=TestCaseExecution)
        )
        # Assert parameter 1 is updated from config
        assert TEST_PARAMETER_NAME_1 in case.test_parameters
        assert case.test_parameters[TEST_PARAMETER_NAME_1] == 11

        # Assert parameter 2 is present and default
        assert TEST_PARAMETER_NAME_2 in case.test_parameters
        assert (
            case.test_parameters[TEST_PARAMETER_NAME_2]
            == DEFAULT_TEST_PARAMETERS[TEST_PARAMETER_NAME_2]
        )

        # Assert parameter 3 is present even if it is not in default test parameters
        assert TEST_PARAMETER_NAME_3 in case.test_parameters


def test_test_case_no_test_parameters() -> None:
    """Test that a TestCase without default test parameters will have runtime test
    parameters.
    """
    mock_config = default_environment_config.copy(deep=True)  # type: ignore
    mock_config = mock_config.__dict__
    mock_config["test_parameters"] = {
        TEST_PARAMETER_NAME_1: 11,
        TEST_PARAMETER_NAME_3: 333,
    }

    with mock.patch(
        "app.test_engine.models.test_case.TestCase.config",
        new_callable=PropertyMock,
        return_value=mock_config,
    ) as _:
        case = NoDefaultTestParamsTestCase(
            test_case_execution=MagicMock(spec=TestCaseExecution)
        )
        assert case.test_parameters[TEST_PARAMETER_NAME_1] == 11
        assert case.test_parameters[TEST_PARAMETER_NAME_3] == 333


def test_test_case_cancel_test_case() -> None:
    """Test that a cancelled TestCase will cancel the test case state and also the
    test step states
    """
    # Mock config
    mock_config = default_environment_config.copy(deep=True)  # type: ignore
    mock_config.test_parameters = {
        TEST_PARAMETER_NAME_1: 11,
        TEST_PARAMETER_NAME_3: 333,
    }

    with mock.patch(
        "app.test_engine.models.test_case.TestCase.config",
        new_callable=PropertyMock,
        return_value=mock_config,
    ) as _:
        case = MockTestCase(test_case_execution=MagicMock(spec=TestCaseExecution))

        case.cancel()

        test_steps_cancelled = [
            x for x in case.test_steps if x.state == TestStateEnum.CANCELLED
        ]

        assert TestStateEnum.CANCELLED == case.state
        assert len(test_steps_cancelled) > 0
        assert len(case.test_steps) == len(test_steps_cancelled)
