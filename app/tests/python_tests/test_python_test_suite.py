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
from typing import Type
from unittest import mock

import pytest

from app.chip_tool.chip_tool import ChipToolTestType
from app.models.test_suite_execution import TestSuiteExecution
from app.test_engine.logger import test_engine_logger
from test_collections.sdk_tests.support.python_testing.models.test_suite import (
    ChipToolPythonTestSuite,
    PythonTestSuite,
    SuiteType,
)


def test_python_suite_class_factory_name() -> None:
    """Test that test suite name is set."""
    name = "AnotherTestSuite"

    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.AUTOMATED, name=name, python_test_version="version"
    )

    assert suite_class.__name__ == name
    assert suite_class.public_id() == name
    assert suite_class.metadata["title"] == name
    assert suite_class.metadata["description"] == name


def test_python_test_suite_python_version() -> None:
    """Test that test suite python version is set correctly in class factory."""
    python_test_version = "best_version"
    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.AUTOMATED,
        name="SomeSuite",
        python_test_version=python_test_version,
    )

    assert suite_class.python_test_version == python_test_version


def test_automated_suite_subclass() -> None:
    """Test that for suite type automated class factory creates a subclass of
    ChipToolPythonTestSuite, and that test_type is set to CHIP_TOOL"""
    type = SuiteType.AUTOMATED
    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=type, name="SomeSuite", python_test_version="some_version"
    )
    assert issubclass(suite_class, ChipToolPythonTestSuite)
    assert suite_class.test_type == ChipToolTestType.PYTHON_TEST


@pytest.mark.asyncio
async def test_suite_setup_log_python_version() -> None:
    """Test that test suite python version is logged to test engine logger in setup."""
    for type in list(SuiteType):
        python_test_version = "best_version"
        # Create a subclass of PythonTestSuite
        suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
            suite_type=type, name="SomeSuite", python_test_version=python_test_version
        )

        suite_instance = suite_class(TestSuiteExecution())

        # We're patching ChipToolSuite.setup to avoid starting chip-tool
        with mock.patch.object(
            target=test_engine_logger, attribute="info"
        ) as logger_info, mock.patch(
            "app.chip_tool.test_suite.ChipToolSuite.setup"
        ) as _:
            await suite_instance.setup()
            logger_info.assert_called()
            logger_info.assert_any_call(f"Python Test Version: {python_test_version}")


@pytest.mark.asyncio
async def test_chip_tool_suite_setup() -> None:
    """Test that both PythonTestSuite.setup and ChipToolSuite.setup are called when
    PythonChipToolsSuite.setup is called. We do this as PythonChipToolsSuite inherits from
    both PythonTestSuite and ChipToolSuite."""

    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.AUTOMATED,
        name="SomeSuite",
        python_test_version="Some version",
    )

    suite_instance = suite_class(TestSuiteExecution())

    with mock.patch(
        "test_collections.sdk_tests.support.python_testing.models.test_suite.PythonTestSuite.setup"
    ) as python_suite_setup, mock.patch(
        "app.chip_tool.test_suite.ChipToolSuite.setup"
    ) as chip_tool_suite_setup:
        await suite_instance.setup()
        python_suite_setup.assert_called_once()
        chip_tool_suite_setup.assert_called_once()
