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
from typing import Type
from unittest import mock

import pytest

from app.models.test_suite_execution import TestSuiteExecution
from app.test_engine.logger import test_engine_logger

from ...chip.chip_tool import ChipTestType
from ...yaml_tests.models.test_suite import (
    ChipYamlTestSuite,
    ManualYamlTestSuite,
    SimulatedYamlTestSuite,
    SuiteType,
    YamlTestSuite,
)


def test_yaml_suite_class_factory_name() -> None:
    """Test that test suite name is set."""
    name = "AnotherTestSuite"

    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=SuiteType.AUTOMATED, name=name, yaml_version="version"
    )

    assert suite_class.__name__ == name
    assert suite_class.public_id() == name
    assert suite_class.metadata["title"] == name
    assert suite_class.metadata["description"] == name


def test_yaml_test_suite_yaml_version() -> None:
    """Test that test suite yaml version is set correctly in class factory."""
    yaml_version = "best_version"
    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=SuiteType.AUTOMATED, name="SomeSuite", yaml_version=yaml_version
    )

    assert suite_class.yaml_version == yaml_version


def test_manual_suite_subclass() -> None:
    """Test that for suite type manual class factory creates a subclass of
    ManualYamlTestSuite."""
    type = SuiteType.MANUAL
    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=type, name="SomeSuite", yaml_version="some_version"
    )
    assert issubclass(suite_class, ManualYamlTestSuite)


def test_automated_suite_subclass() -> None:
    """Test that for suite type automated class factory creates a subclass of
    ChipYamlTestSuite, and that test_type is set to CHIP_TOOL"""
    type = SuiteType.AUTOMATED
    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=type, name="SomeSuite", yaml_version="some_version"
    )
    assert issubclass(suite_class, ChipYamlTestSuite)
    assert suite_class.test_type == ChipTestType.CHIP_TOOL


def test_simulated_suite_subclass() -> None:
    """Test that for suite type simulated class factory creates a subclass of
    SimulatedYamlTestSuite, and that test_type is set to CHIP_APP"""
    type = SuiteType.SIMULATED
    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=type, name="SomeSuite", yaml_version="some_version"
    )
    assert issubclass(suite_class, SimulatedYamlTestSuite)
    assert suite_class.test_type == ChipTestType.CHIP_APP


@pytest.mark.asyncio
async def test_suite_setup_log_yaml_version() -> None:
    """Test that test suite yaml version is logged to test engine logger in setup."""
    for type in list(SuiteType):
        yaml_version = "best_version"
        # Create a subclass of YamlTestSuite
        suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
            suite_type=type, name="SomeSuite", yaml_version=yaml_version
        )

        suite_instance = suite_class(TestSuiteExecution())

        # We're patching ChipSuite.setup to avoid starting the SDK container and server
        with mock.patch.object(
            target=test_engine_logger, attribute="info"
        ) as logger_info, mock.patch(
            "test_collections.sdk_tests.support.yaml_tests.models.chip_suite.ChipSuite"
            ".setup"
        ) as _:
            await suite_instance.setup()
            logger_info.assert_called()
            logger_info.assert_any_call(f"YAML Version: {yaml_version}")


@pytest.mark.asyncio
async def test_manual_suite_setup_cleanup() -> None:
    """Test that manual test suite setup and cleanup log to test engine logger."""
    # Create a subclass of YamlTestSuite
    suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
        suite_type=SuiteType.MANUAL, name="SomeSuite", yaml_version="Some version"
    )

    suite_instance = suite_class(TestSuiteExecution())

    with mock.patch.object(
        target=test_engine_logger, attribute="info"
    ) as logger_info, mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models."
        "test_suite.YamlTestSuite.setup"
    ) as _, mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models."
        "test_suite.YamlTestSuite.cleanup"
    ) as _:
        await suite_instance.setup()
        logger_info.assert_called_once()

        logger_info.reset_mock()

        await suite_instance.cleanup()
        logger_info.assert_called_once()


@pytest.mark.asyncio
async def test_chip_suite_setup() -> None:
    """Test that both YamlTestSuite.setup and ChipSuite.setup are called when
    ChipYamlTestSuite.setup is called. We do this as ChipYamlTestSuite inherits from
    both YamlTestSuite and ChipSuite."""

    for type in [SuiteType.AUTOMATED, SuiteType.SIMULATED]:
        suite_class: Type[YamlTestSuite] = YamlTestSuite.class_factory(
            suite_type=type, name="SomeSuite", yaml_version="Some version"
        )

        suite_instance = suite_class(TestSuiteExecution())

        with mock.patch(
            "test_collections.sdk_tests.support.yaml_tests.models."
            "test_suite.YamlTestSuite.setup"
        ) as yaml_suite_setup, mock.patch(
            "test_collections.sdk_tests.support.yaml_tests.models.chip_suite.ChipSuite"
            ".setup"
        ) as chip_suite_setup:
            await suite_instance.setup()
            yaml_suite_setup.assert_called_once()
            chip_suite_setup.assert_called_once()
