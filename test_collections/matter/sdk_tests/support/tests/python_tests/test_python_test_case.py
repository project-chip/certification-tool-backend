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
# flake8: noqa
# Ignore flake8 check for this file
from pathlib import Path
from typing import Any, Optional, Type
from unittest import mock

import pytest

from app.default_environment_config import default_environment_config
from app.models.project import Project
from app.models.test_case_execution import TestCaseExecution
from app.models.test_run_execution import TestRunExecution
from app.models.test_suite_execution import TestSuiteExecution
from app.test_engine.logger import test_engine_logger
from app.user_prompt_support import UserPromptSupport

from ...models.matter_test_models import MatterTestStep, MatterTestType
from ...python_testing.models import PythonTestCase
from ...python_testing.models.python_test_models import PythonTest, PythonTestType
from ...python_testing.models.test_case import LegacyPythonTestCase, PromptOption
from ...python_testing.models.utils import DUTCommissioningError

# from ...utils import PromptOption


def python_test_instance(
    name: str = "TC-Test-Python",
    description: str = "Test Python Description",
    PICS: set[str] = {"PICS.A", "PICS.B"},
    config: dict[str, Any] = {
        "param1": "value1",
        "param2": {"type": "config_type", "defaultValue": "value2"},
    },
    steps: list[MatterTestStep] = [],
    type: MatterTestType = MatterTestType.AUTOMATED,
    path: Optional[Path] = None,
    class_name: str = "TC_Test_Python",
    python_test_type: PythonTestType = PythonTestType.COMMISSIONING,
) -> PythonTest:
    return PythonTest(
        name=name,
        PICS=PICS,
        config=config,
        steps=steps,
        type=type,
        path=path,
        description=description,
        class_name=class_name,
        python_test_type=python_test_type,
    )


def test_python_test_name() -> None:
    """Test that test name is set as title in metadata."""
    name = "Another Test Name"
    description = "Another Test Name Description"
    test = python_test_instance(name=name, description=description)

    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version", mandatory=False
    )
    assert case_class.metadata["title"] == name
    assert case_class.metadata["description"] == description


def test_python_test_python_version() -> None:
    """Test that test case python version is set correctly in class factory."""
    test = python_test_instance()
    python_test_version = "best_version"
    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version=python_test_version, mandatory=False
    )
    assert case_class.python_test_version == python_test_version


def test_python_test_python() -> None:
    """Test that test python_test property is as expected in subclass of PythonTestCase."""
    test = python_test_instance()
    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version", mandatory=False
    )
    assert case_class.python_test is test


def test_python_test_case_class_pics() -> None:
    """Test that the PICS of the python test is available in the class method PICS on
    TestCase."""
    test_PICS = set(["PICS.D", "PICS.C"])
    test = python_test_instance(PICS=test_PICS)

    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version", mandatory=False
    )
    assert case_class.pics() == test_PICS


def test_class_factory_test_public_id() -> None:
    """Test that class factory correctly finds identifier 'TC-XX-1.1' in python test name.
    And set it as public_id in metadata"""
    test_data = [
        {"name": "TC-AB-1.2", "public_id": "TC-AB-1.2"},
    ]
    for data in test_data:
        test = python_test_instance(name=data["name"])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version", mandatory=False
        )
        assert case_class.metadata["public_id"] == data["public_id"]


def test_class_factory_mandatory() -> None:
    """Test that checks that metadata mandatory field is set"""
    test_data = [
        {"name": "TC-AB-1.2", "class_name": "TC_AB_1_2"},
        {"name": "TC-CD-3.4", "class_name": "TC_CD_3_4"},
    ]
    for data in test_data:
        test = python_test_instance(name=data["name"])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version", mandatory=True
        )
        assert case_class.metadata["mandatory"] == True  # type: ignore


def test_class_factory_test_class_name() -> None:
    """Test that class factory correctly finds identifier 'TC-XX-1.1', convert it to
    a safe class name, eg TC_XX_1_1"""
    test_data = [
        {"name": "TC-AB-1.2", "class_name": "TC_AB_1_2"},
        {"name": "TC-CD-3.4", "class_name": "TC_CD_3_4"},
    ]
    for data in test_data:
        test = python_test_instance(name=data["name"])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version", mandatory=True
        )
        assert case_class.__name__ == data["class_name"]


@pytest.mark.asyncio
async def test_python_version_logging() -> None:
    """Test that all Python tests will log Python test version to test_engine_logger."""
    for type in list(MatterTestType):
        test = python_test_instance(type=type)
        test_python_version = "PythonVersionTest"
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version=test_python_version, mandatory=False
        )
        instance = case_class(TestCaseExecution())

        with mock.patch.object(
            target=test_engine_logger, attribute="info"
        ) as logger_info:
            await instance.setup()
            logger_info.assert_called()
            logger_info.assert_any_call("Test Setup")


def test_normal_steps_for_python_tests() -> None:
    """Test that python tests include enabled steps."""
    for type in list(MatterTestType):
        test_step = MatterTestStep(label="Step1")
        test = python_test_instance(type=type, steps=[test_step])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version", mandatory=False
        )
        instance = case_class(TestCaseExecution())
        # Assert normal step is present
        assert len(instance.test_steps) >= 1
        assert any(s.name == test_step.label for s in instance.test_steps)


def test_multiple_steps_for_python_tests() -> None:
    """Test that python tests multiple enabled steps are all included."""
    for type in list(MatterTestType):
        test_step = MatterTestStep(label="StepN")
        no_steps = 5
        test = python_test_instance(type=type, steps=([test_step] * no_steps))
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version", mandatory=False
        )
        instance = case_class(TestCaseExecution())

        # Assert all steps from python test are added
        assert len(instance.test_steps) >= no_steps
        steps_from_python = [
            s for s in instance.test_steps if s.name == test_step.label
        ]
        assert len(steps_from_python) == no_steps


@pytest.mark.asyncio
async def test_should_raise_DUTCommissioningError_prompt_commissioning_failed() -> None:
    """Test when user responds FAIL to commissioning mode prompt.

    Should raise DUTCommissioningError.
    """
    test_case_execution = TestCaseExecution()
    test = python_test_instance(name="test_name", path=Path("path"))
    test.python_test_type = PythonTestType.MANDATORY

    test_case = LegacyPythonTestCase.class_factory(
        test=test,
        python_test_version="version",
        mandatory=False,
    )(test_case_execution)

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.NO,
    ), pytest.raises(DUTCommissioningError):
        await test_case.setup()


@pytest.mark.asyncio
async def test_legacy_python_test_case_no_new_commissioning() -> None:
    """Test when user doesn't want to perform new commissioning.

    Flow:
    1. prompt_for_commissioning_mode returns YES
    2. prompt_about_commissioning returns NO
    3. No commissioning should be performed
    """
    project = Project(name="test_project")
    project.config = {
        "matter_node_id": 1234,
        "matter_discriminator": 5678,
        "matter_setup_pin": "12345678",
        "matter_use_operational_credentials": False,
        "network": {
            "wifi": {
                "ssid": "test_ssid",
                "password": "test_password",
            },
            "thread": {
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:11:11:11::/64",
                "network_interface": "wpan0",
                "dataset": {
                    "channel": 15,
                    "panid": "0x1234",
                    "xpanid": "1111111122222222",
                    "masterkey": "00112233445566778899aabbccddeeff",
                },
                "operational_dataset_hex": "0e080000000000010000000300001235",
            },
        },
        "dut_config": {
            "discriminator": 5678,
            "setup_code": "12345678",
            "pairing_mode": "onnetwork",
            "chip_timeout": 10000,
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
    }

    test_run_execution = TestRunExecution()
    test_run_execution.project = project

    test_suite_execution = TestSuiteExecution()
    test_suite_execution.test_run_execution = test_run_execution

    test_case_execution = TestCaseExecution()
    test_case_execution.test_suite_execution = test_suite_execution

    test = python_test_instance(name="test_name", path=Path("path"))
    test.python_test_type = PythonTestType.MANDATORY

    test_case = LegacyPythonTestCase.class_factory(
        test=test,
        python_test_version="version",
        mandatory=False,
    )(test_case_execution)

    mock_prompt_response_no = mock.Mock()
    mock_prompt_response_no.response = PromptOption.NO

    mock_config = mock.Mock()
    mock_config.__dict__ = project.config

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.YES,
    ) as mock_prompt_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils"
        ".commission_device"
    ) as mock_commission_device, mock.patch(
        "test_collections.matter.test_environment_config.TestEnvironmentConfigMatter",
        return_value=mock_config,
    ), mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        side_effect=[mock_prompt_response_no, mock_prompt_response_no],
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case.logger"
    ) as mock_logger:
        await test_case.setup()

        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_not_called()
        mock_logger.info.assert_any_call("User chose prompt option NO")


@pytest.mark.asyncio
async def test_legacy_python_test_case_new_commissioning() -> None:
    """Test when user doesn't want to perform new commissioning.

    Flow:
    1. prompt_for_commissioning_mode returns YES
    2. prompt_about_commissioning returns NO
    3. No commissioning should be performed
    """
    # Configurando a hierarquia completa de execução
    project = Project(name="test_project")
    project.config = {
        "matter_node_id": 1234,
        "matter_discriminator": 5678,
        "matter_setup_pin": "12345678",
        "matter_use_operational_credentials": False,
        "network": {
            "wifi": {
                "ssid": "test_ssid",
                "password": "test_password",
            },
            "thread": {
                "rcp_serial_path": "/dev/ttyACM0",
                "rcp_baudrate": 115200,
                "on_mesh_prefix": "fd11:11:11:11::/64",
                "network_interface": "wpan0",
                "dataset": {
                    "channel": 15,
                    "panid": "0x1234",
                    "xpanid": "1111111122222222",
                    "masterkey": "00112233445566778899aabbccddeeff",
                },
                "operational_dataset_hex": "0e080000000000010000000300001235",
            },
        },
        "dut_config": {
            "discriminator": 5678,
            "setup_code": "12345678",
            "pairing_mode": "onnetwork",
            "chip_timeout": 10000,
            "chip_use_paa_certs": False,
            "trace_log": True,
        },
    }

    test_run_execution = TestRunExecution()
    test_run_execution.project = project

    test_suite_execution = TestSuiteExecution()
    test_suite_execution.test_run_execution = test_run_execution

    test_case_execution = TestCaseExecution()
    test_case_execution.test_suite_execution = test_suite_execution

    test = python_test_instance(name="test_name", path=Path("path"))
    test.python_test_type = PythonTestType.MANDATORY

    test_case = LegacyPythonTestCase.class_factory(
        test=test,
        python_test_version="version",
        mandatory=False,
    )(test_case_execution)

    # Criando dois mocks de resposta diferentes
    mock_prompt_response_yes = mock.Mock()
    mock_prompt_response_yes.response = PromptOption.YES

    mock_prompt_response_no = mock.Mock()
    mock_prompt_response_no.response = PromptOption.NO

    mock_config = mock.Mock()
    mock_config.__dict__ = project.config

    # Criando um mock para simular o output do commission_device
    mock_exec_result = mock.Mock()
    mock_exec_result.output = (bytes(f"log line {i}", "utf-8") for i in range(3))

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.YES,
    ) as mock_prompt_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case"
        ".commission_device",
        return_value=mock_exec_result,
    ) as mock_commission_device, mock.patch(
        "test_collections.matter.test_environment_config.TestEnvironmentConfigMatter",
        return_value=mock_config,
    ), mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        side_effect=[mock_prompt_response_yes, mock_prompt_response_no],
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_case.logger"
    ) as mock_logger:
        await test_case.setup()

        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_called()
