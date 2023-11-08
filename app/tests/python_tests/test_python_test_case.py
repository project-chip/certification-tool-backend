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
from typing import Any, Optional, Type
from unittest import mock

import pytest

from app.chip_tool.chip_tool import ChipToolTestType
from app.chip_tool.test_case import TestError
from app.models.test_case_execution import TestCaseExecution
from app.test_engine.logger import test_engine_logger
from test_collections.sdk_tests.support.python_testing.models import PythonTestCase
from test_collections.sdk_tests.support.python_testing.models.test_case import (
    PythonChipToolTestCase,
)
from test_collections.sdk_tests.support.python_testing.models.python_test_models import (
    PythonTest,
    PythonTestStep,
    PythonTestType,
)


def python_test_instance(
    name: str = "Test Python",
    PICS: set[str] = {"PICS.A", "PICS.B"},
    config: dict[str, Any] = {
        "param1": "value1",
        "param2": {"type": "config_type", "defaultValue": "value2"},
    },
    steps: list[PythonTestStep] = [],
    type: PythonTestType = PythonTestType.AUTOMATED,
    path: Optional[Path] = None,
) -> PythonTest:
    return PythonTest(
        name=name,
        PICS=PICS,
        config=config, 
        steps=steps,
        type=type,
        path=path,
    )


def test_python_test_name() -> None:
    """Test that test name is set as description in metadata."""
    name = "Another Test Name"
    test = python_test_instance(name=name)

    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert case_class.metadata["description"] == name


def test_python_test_python_version() -> None:
    """Test that test case python version is set correctly in class factory."""
    test = python_test_instance()
    python_test_version = "best_version"
    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version=python_test_version
    )
    assert case_class.python_test_version == python_test_version


def test_python_test_python() -> None:
    """Test that test python_test property is as expected in subclass of PythonTestCase."""
    test = python_test_instance()
    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert case_class.python_test is test


def test_python_test_case_class_pics() -> None:
    """Test that the PICS of the python test is available in the class method PICS on
    TestCase."""
    test_PICS = set(["PICS.D", "PICS.C"])
    test = python_test_instance(PICS=test_PICS)

    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert case_class.pics() == test_PICS


def test_python_test_case_class_default_test_parameters() -> None:
    """Test that the default_test_parameters of the python test is available in the class
    method default_test_parameters on TestCase.

    Also parameters with type in Python test should be flattened and type dropped."""

    test_input_config = {
        "param1": "value1",
        "param2": {"type": "config_type", "defaultValue": "value2"},
    }

    test = python_test_instance(config=test_input_config)
    expected_default_test_parameters = {"param1": "value1", "param2": "value2"}

    # Create a subclass of PythonTest
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert case_class.default_test_parameters() == expected_default_test_parameters


def test_automated_test_case_class_factory_subclass_mapping() -> None:
    """Test Automated tests are created as a subclass of
    PythonChipToolTestCase."""
    test = python_test_instance(type=PythonTestType.AUTOMATED)
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert issubclass(case_class, PythonChipToolTestCase)


def test_class_factory_test_public_id() -> None:
    """Test that class factory correctly finds identifier 'TC-XX-1.1' in python test name.
    And set it as public_id in metadata"""
    test_data = [
        {"name": "TC-AB-1.2", "public_id": "TC-AB-1.2"},
        {"name": "[TC-CD-3.4]", "public_id": "TC-CD-3.4"},
        {"name": "Test Name before [TC-EF-5.6]", "public_id": "TC-EF-5.6"},
        {"name": "[TC-GH-7.8] Test Name after", "public_id": "TC-GH-7.8"},
        {"name": "Before and [TC-IJ-9.0] after", "public_id": "TC-IJ-9.0"},
        {"name": "Before and TC-KL-10.11 after", "public_id": "TC-KL-10.11"},
        {"name": "TC-MORE-NAME-13.110", "public_id": "TC-MORE-NAME-13.110"},
    ]
    for data in test_data:
        test = python_test_instance(name=data["name"])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version"
        )
        assert case_class.metadata["public_id"] == data["public_id"]


def test_class_factory_test_class_name() -> None:
    """Test that class factory correctly finds identifier 'TC-XX-1.1', convert it to
    a safe class name, eg TC_XX_1_1"""
    test_data = [
        {"name": "TC-AB-1.2", "class_name": "TC_AB_1_2"},
        {"name": "[TC-CD-3.4]", "class_name": "TC_CD_3_4"},
        {"name": "Test Name before [TC-EF-5.6]", "class_name": "TC_EF_5_6"},
        {"name": "[TC-GH-7.8] Test Name after", "class_name": "TC_GH_7_8"},
        {"name": "Before and [TC-IJ-9.0] after", "class_name": "TC_IJ_9_0"},
        {"name": "Before and TC-KL-10.11 after", "class_name": "TC_KL_10_11"},
        {"name": "TC-MORE-NAME-13.110", "class_name": "TC_MORE_NAME_13_110"},
    ]
    for data in test_data:
        test = python_test_instance(name=data["name"])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version"
        )
        assert case_class.__name__ == data["class_name"]


def test_test_type_for_automated_tests() -> None:
    """Test that automated tests are set to use chip-tool"""
    test = python_test_instance(type=PythonTestType.AUTOMATED)
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    assert issubclass(case_class, PythonChipToolTestCase)
    instance = case_class(TestCaseExecution())
    assert instance.test_type == ChipToolTestType.PYTHON_TEST


@pytest.mark.asyncio
async def test_python_version_logging() -> None:
    """Test that all Python tests will log Python test version to test_engine_logger.

    Note that since `chip-tool` is not setup, we except the TestError raised.
    """
    for type in list(PythonTestType):
        test = python_test_instance(type=type)
        test_python_version = "PythonVersionTest"
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version=test_python_version
        )
        instance = case_class(TestCaseExecution())

        with mock.patch.object(
            target=test_engine_logger, attribute="info"
        ) as logger_info:
            try:
                await instance.setup()
            except TestError:
                pass
            logger_info.assert_called()
            logger_info.assert_any_call(f"Python Test Version: {test_python_version}")


def test_default_first_steps_for_python_chip_tool_test_case() -> None:
    test = python_test_instance(type=PythonTestType.AUTOMATED, steps=[])
    case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
        test=test, python_test_version="version"
    )
    instance = case_class(TestCaseExecution())
    assert len(instance.test_steps) == 1
    assert instance.test_steps[0].name == "Start Python test"


def test_normal_steps_for_non_manual_tests() -> None:
    """Test that non-manual tests include enabled steps."""
    for type in list(PythonTestType):
        test_step = PythonTestStep(label="Step1")
        test = python_test_instance(type=type, steps=[test_step])
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version"
        )
        instance = case_class(TestCaseExecution())
        # Assert normal step is present
        assert len(instance.test_steps) >= 1
        assert any(s.name == test_step.label for s in instance.test_steps)


def test_multiple_steps_for_non_manual() -> None:
    """Test that non-manual tests multiple enabled steps are all included."""
    for type in list(PythonTestType):
        test_step = PythonTestStep(label="StepN")
        no_steps = 5
        test = python_test_instance(type=type, steps=([test_step] * no_steps))
        case_class: Type[PythonTestCase] = PythonTestCase.class_factory(
            test=test, python_test_version="version"
        )
        instance = case_class(TestCaseExecution())

        # Assert all steps from python test are added
        assert len(instance.test_steps) >= no_steps
        steps_from_python = [s for s in instance.test_steps if s.name == test_step.label]
        assert len(steps_from_python) == no_steps


@pytest.mark.asyncio
async def test_setup_super_error_handling() -> None:
    # ignore requirement to create_tests on init
    with mock.patch("app.test_engine.models.test_case.TestCase.create_test_steps") as _:
        test = PythonTestCase(TestCaseExecution())
        test.python_test_version = "some version"
        # Assert this doesn't raise an exception
        await test.setup()
