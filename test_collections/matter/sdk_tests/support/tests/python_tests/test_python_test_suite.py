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

from app.default_environment_config import default_environment_config
from app.models.test_suite_execution import TestSuiteExecution
from app.schemas import PICS
from app.test_engine.logger import test_engine_logger
from app.tests.utils.test_pics_data import create_random_pics
from test_collections.matter.sdk_tests.support.python_testing.models.utils import (
    DUTCommissioningError,
)

from ...python_testing.models.test_suite import (
    CommissioningPythonTestSuite,
    PythonTestSuite,
    SuiteType,
)
from ...sdk_container import SDKContainer
from ...utils import PromptOption


def test_python_suite_class_factory_name() -> None:
    """Test that test suite name is set."""
    name = "AnotherTestSuite"

    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name=name,
        python_test_version="version",
        mandatory=False,
    )

    assert suite_class.__name__ == name
    assert suite_class.public_id() == name
    assert suite_class.metadata["title"] == name
    assert suite_class.metadata["description"] == name
    assert suite_class.metadata["mandatory"] == False  # type: ignore


def test_python_suite_class_factory_name_mandatory() -> None:
    """Test that test mandatory field is set."""
    name = "AnotherTestSuite"

    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name=name,
        python_test_version="version",
        mandatory=True,
    )

    assert suite_class.__name__ == name
    assert suite_class.public_id() == name
    assert suite_class.metadata["title"] == name
    assert suite_class.metadata["description"] == name
    assert suite_class.metadata["mandatory"] == True  # type: ignore


def test_python_test_suite_python_version() -> None:
    """Test that test suite python version is set correctly in class factory."""
    python_test_version = "best_version"
    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version=python_test_version,
        mandatory=False,
    )

    assert suite_class.python_test_version == python_test_version


def test_commissioning_suite_subclass() -> None:
    """Test that for suite type commissioning class factory creates a subclass of
    CommissioningPythonTestSuite."""
    type = SuiteType.COMMISSIONING
    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=type,
        name="SomeSuite",
        python_test_version="some_version",
        mandatory=False,
    )
    assert issubclass(suite_class, CommissioningPythonTestSuite)


@pytest.mark.asyncio
async def test_suite_setup_log_python_version() -> None:
    """Test that test suite python version is logged to test engine logger in setup."""
    sdk_container: SDKContainer = SDKContainer()

    for type in list(SuiteType):
        python_test_version = "best_version"
        suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
            suite_type=type,
            name="SomeSuite",
            python_test_version=python_test_version,
            mandatory=False,
        )

        suite_instance = suite_class(TestSuiteExecution())

        # Mock prompt response
        mock_prompt_response = mock.Mock()
        mock_prompt_response.response = PromptOption.PASS

        with mock.patch.object(
            target=test_engine_logger, attribute="info"
        ) as logger_info, mock.patch.object(
            target=sdk_container, attribute="start"
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.pics",
            new_callable=PICS,
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".prompt_for_commissioning_mode",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".commission_device",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.config",
            new_callable=mock.PropertyMock,
            return_value=default_environment_config.__dict__,
        ), mock.patch(
            "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
            return_value=mock_prompt_response,
        ):
            await suite_instance.setup()

            logger_info.assert_called()
            logger_info.assert_any_call(f"Python Test Version: {python_test_version}")


@pytest.mark.asyncio
async def test_suite_setup_without_pics() -> None:
    sdk_container: SDKContainer = SDKContainer()

    for type in list(SuiteType):
        python_test_version = "best_version"
        # Create a subclass of PythonTestSuite
        suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
            suite_type=type,
            name="SomeSuite",
            python_test_version=python_test_version,
            mandatory=True,
        )

        suite_instance = suite_class(TestSuiteExecution())

        # Mock prompt response
        mock_prompt_response = mock.Mock()
        mock_prompt_response.response = PromptOption.PASS

        with mock.patch.object(target=sdk_container, attribute="start"), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.pics",
            new_callable=PICS,
        ), mock.patch.object(
            target=sdk_container, attribute="set_pics"
        ) as mock_set_pics, mock.patch.object(
            target=sdk_container, attribute="reset_pics_state"
        ) as mock_reset_pics_state, mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".prompt_for_commissioning_mode",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".commission_device",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.config",
            new_callable=mock.PropertyMock,
            return_value=default_environment_config.__dict__,
        ), mock.patch(
            "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
            return_value=mock_prompt_response,
        ):
            await suite_instance.setup()

        mock_set_pics.assert_not_called()
        mock_reset_pics_state.assert_called_once()


@pytest.mark.asyncio
async def test_suite_setup_with_pics() -> None:
    sdk_container: SDKContainer = SDKContainer()

    # Mock prompt response
    mock_prompt_response = mock.Mock()
    mock_prompt_response.response = PromptOption.PASS

    for type in list(SuiteType):
        python_test_version = "best_version"
        # Create a subclass of PythonTestSuite
        suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
            suite_type=type,
            name="SomeSuite",
            python_test_version=python_test_version,
            mandatory=False,
        )

        suite_instance = suite_class(TestSuiteExecution())

        with mock.patch.object(target=sdk_container, attribute="start"), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.pics",
            new_callable=create_random_pics,
        ), mock.patch.object(
            target=sdk_container, attribute="set_pics"
        ) as mock_set_pics, mock.patch.object(
            target=sdk_container, attribute="reset_pics_state"
        ) as mock_reset_pics_state, mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".prompt_for_commissioning_mode",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".commission_device",
        ), mock.patch(
            target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
            ".PythonTestSuite.config",
            new_callable=mock.PropertyMock,
            return_value=default_environment_config.__dict__,
        ), mock.patch(
            "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
            return_value=mock_prompt_response,
        ):
            await suite_instance.setup()

        mock_set_pics.assert_called_once()
        mock_reset_pics_state.assert_not_called()


@pytest.mark.asyncio
async def test_commissioning_suite_setup_with_pics() -> None:
    sdk_container: SDKContainer = SDKContainer()

    python_test_version = "best_version"
    # Create a subclass of PythonTestSuite
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version=python_test_version,
        mandatory=False,
    )

    suite_instance = suite_class(TestSuiteExecution())

    # Mock prompt response
    mock_prompt_response = mock.Mock()
    mock_prompt_response.response = PromptOption.PASS

    with mock.patch.object(target=sdk_container, attribute="start"), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.pics",
        new_callable=PICS,
    ), mock.patch.object(target=sdk_container, attribute="set_pics"), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
    ) as mock_prompt_for_commissioning_mode, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device",
    ) as mock_commission_device, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.config",
        new_callable=mock.PropertyMock,
        return_value=default_environment_config.__dict__,
    ), mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        return_value=mock_prompt_response,
    ):
        await suite_instance.setup()

    mock_prompt_for_commissioning_mode.called_once()
    mock_commission_device.called_once()


@pytest.mark.asyncio
async def test_commissioning_suite_setup() -> None:
    """Test that PythonTestSuite.setup is called when CommissioningPythonTestSuite.setup
    is called. We do this as CommissioningPythonTestSuite inherits from PythonTestSuite.
    """

    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )

    suite_instance = suite_class(TestSuiteExecution())

    # Mock prompt response
    mock_prompt_response = mock.Mock()
    mock_prompt_response.response = PromptOption.PASS

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup"
    ) as python_suite_setup, mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
    ), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device",
    ), mock.patch(
        target="test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.config",
        new_callable=mock.PropertyMock,
        return_value=default_environment_config.__dict__,
    ), mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        return_value=mock_prompt_response,
    ):
        await suite_instance.setup()
        python_suite_setup.assert_called_once()


@pytest.mark.asyncio
async def test_commissioning_suite_setup_fail() -> None:
    """Test that when prompt_for_commissioning_mode returns FAIL, the setup process
    should raise DUTCommissioningError.
    """

    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )

    suite_instance = suite_class(TestSuiteExecution())

    # Mock prompt response
    mock_prompt_response = mock.Mock()
    mock_prompt_response.response = PromptOption.FAIL

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup"
    ) as python_suite_setup, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.FAIL,
    ) as mock_prompt_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device"
    ) as mock_commission_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.config",
        new_callable=mock.PropertyMock,
        return_value=default_environment_config.__dict__,
    ), mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        return_value=mock_prompt_response,
    ):
        with pytest.raises(DUTCommissioningError) as exc_info:
            await suite_instance.setup()

        assert (
            str(exc_info.value)
            == "User chose prompt option FAILED for DUT is in Commissioning Mode"
        )

        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_not_called()


@pytest.mark.asyncio
async def test_should_perform_new_commissioning_yes() -> None:
    """Test that when should_perform_new_commissioning returns True,
    the setup process performs a new commissioning.
    """
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )

    suite_instance = suite_class(TestSuiteExecution())

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup"
    ) as python_suite_setup, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.PASS,
    ) as mock_prompt_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device"
    ) as mock_commission_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.config",
        new_callable=mock.PropertyMock,
        return_value=default_environment_config.__dict__,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".should_perform_new_commissioning",
        return_value=True,
    ) as mock_should_perform_new_commissioning:
        await suite_instance.setup()

        mock_should_perform_new_commissioning.assert_called_once()
        python_suite_setup.assert_called_once()
        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_called_once()


@pytest.mark.asyncio
async def test_should_perform_new_commissioning_no() -> None:
    """Test that when should_perform_new_commissioning returns False,
    the setup process skips the new commissioning.
    """
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )

    suite_instance = suite_class(TestSuiteExecution())

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup"
    ) as python_suite_setup, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.PASS,
    ) as mock_prompt_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device"
    ) as mock_commission_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.config",
        new_callable=mock.PropertyMock,
        return_value=default_environment_config.__dict__,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".should_perform_new_commissioning",
        return_value=False,
    ) as mock_should_perform_new_commissioning:
        await suite_instance.setup()

        mock_should_perform_new_commissioning.assert_called_once()

        python_suite_setup.assert_called_once()

        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_not_called()
