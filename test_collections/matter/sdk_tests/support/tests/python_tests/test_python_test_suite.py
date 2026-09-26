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
from test_collections.matter.test_environment_config import DutPairingModeEnum

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

    mock_matter_config = mock.Mock()
    mock_matter_config.dut_config.pairing_mode = DutPairingModeEnum.ON_NETWORK
    mock_matter_config.test_parameters = None  # Add test_parameters as None or {}

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
        suite_instance.matter_config = mock_matter_config
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

    mock_matter_config = mock.Mock()
    mock_matter_config.dut_config.pairing_mode = DutPairingModeEnum.ON_NETWORK
    mock_matter_config.test_parameters = None  # Add test_parameters as None or {}

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
        suite_instance.matter_config = mock_matter_config
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

    mock_matter_config = mock.Mock()
    mock_matter_config.dut_config.pairing_mode = DutPairingModeEnum.ON_NETWORK
    mock_matter_config.test_parameters = None  # Add test_parameters as None or {}

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
    ) as mock_should_perform_new_commissioning, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as mock_capture:
        suite_instance.matter_config = mock_matter_config
        await suite_instance.setup()

        mock_should_perform_new_commissioning.assert_called_once()
        python_suite_setup.assert_called_once()
        mock_prompt_commissioning.assert_called_once()
        mock_commission_device.assert_called_once()
        mock_capture.assert_called_once_with(
            mock_matter_config, test_engine_logger, None
        )
        assert suite_instance.reusable_commissioning_state_established is True


@pytest.mark.asyncio
async def test_cleanup_captures_admin_storage_before_destroy() -> None:
    """Issue #1070: cleanup should re-capture admin_storage.json from the
    still-running container before the container is destroyed, so the host
    snapshot reflects this run's advanced message counters, not just the
    counters from the original commissioning."""
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    suite_instance.matter_config = mock.Mock()
    suite_instance.reusable_commissioning_state_established = True

    with mock.patch.object(
        target=suite_instance.sdk_container, attribute="is_running", return_value=True
    ), mock.patch.object(
        target=suite_instance.sdk_container, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=suite_instance.border_router, attribute="destroy_device"
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as mock_capture:
        await suite_instance.cleanup()

    mock_capture.assert_called_once_with(
        suite_instance.matter_config, test_engine_logger, None
    )
    mock_destroy.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_skips_capture_when_container_not_running() -> None:
    """If the container already died mid-suite, cleanup should skip the capture
    attempt (nothing to copy from) rather than attempting it against a dead
    container, but should still tear down the container and border router."""
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    suite_instance.matter_config = mock.Mock()

    with mock.patch.object(
        target=suite_instance.sdk_container, attribute="is_running", return_value=False
    ), mock.patch.object(
        target=suite_instance.sdk_container, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=suite_instance.border_router, attribute="destroy_device"
    ) as mock_destroy_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as mock_capture:
        await suite_instance.cleanup()

    mock_capture.assert_not_called()
    mock_destroy.assert_called_once()
    mock_destroy_device.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_skips_capture_when_matter_config_not_set() -> None:
    """If setup failed before matter_config was assigned, cleanup should skip the
    capture attempt (no config to resolve a storage path from) but still tear down
    the container and border router."""
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())

    with mock.patch.object(
        target=suite_instance.sdk_container, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=suite_instance.border_router, attribute="destroy_device"
    ) as mock_destroy_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as mock_capture:
        await suite_instance.cleanup()

    mock_capture.assert_not_called()
    mock_destroy.assert_called_once()
    mock_destroy_device.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_still_destroys_container_when_capture_fails() -> None:
    """A capture failure must never prevent container/border-router teardown, and
    must not be reported as a suite-level error."""
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    suite_instance.matter_config = mock.Mock()
    suite_instance.reusable_commissioning_state_established = True

    with mock.patch.object(
        target=suite_instance.sdk_container, attribute="is_running", return_value=True
    ), mock.patch.object(
        target=suite_instance.sdk_container, attribute="destroy"
    ) as mock_destroy, mock.patch.object(
        target=suite_instance.border_router, attribute="destroy_device"
    ) as mock_destroy_device, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state",
        side_effect=RuntimeError("boom"),
    ):
        await suite_instance.cleanup()

    mock_destroy.assert_called_once()
    mock_destroy_device.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_captures_admin_storage_and_live_thread_dataset() -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    suite_instance.matter_config = config
    suite_instance.reusable_commissioning_state_established = True
    dataset = bytes.fromhex("0e0800000000000100000300000f")

    with mock.patch.object(
        suite_instance.sdk_container, "is_running", return_value=True
    ), mock.patch.object(suite_instance.sdk_container, "destroy"), mock.patch.object(
        suite_instance.border_router, "is_running", return_value=True
    ), mock.patch.object(
        type(suite_instance.border_router),
        "active_dataset_bytes",
        new_callable=mock.PropertyMock,
        return_value=dataset,
    ), mock.patch.object(
        suite_instance.border_router, "destroy_device"
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as capture_state:
        await suite_instance.cleanup()

    capture_state.assert_called_once_with(config, test_engine_logger, dataset)


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

    # Mock prompt response
    mock_prompt_response = mock.Mock()
    mock_prompt_response.response = PromptOption.PASS

    mock_matter_config = mock.Mock()
    mock_matter_config.dut_config.pairing_mode = DutPairingModeEnum.ON_NETWORK
    mock_matter_config.test_parameters = None  # Add test_parameters as None or {}

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
    ) as mock_should_perform_new_commissioning, mock.patch(
        "app.user_prompt_support.user_prompt_support.UserPromptSupport.send_prompt_request",
        return_value=mock_prompt_response,
    ):
        suite_instance.matter_config = mock_matter_config
        await suite_instance.setup()

        mock_should_perform_new_commissioning.assert_called_once()
        python_suite_setup.assert_called_once()
        mock_prompt_commissioning.assert_not_called()
        mock_commission_device.assert_not_called()


@pytest.mark.asyncio
async def test_thread_reuse_decision_precedes_otbr_restore() -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    config.network.thread.operational_dataset_hex = None
    suite_instance.matter_config = config
    dataset = bytes.fromhex("0e0800000000000100000300000f")
    events = []

    async def decide_reuse(*args, **kwargs):
        events.append("decide")
        return False

    async def start_otbr(*args, **kwargs):
        events.append("start")
        return True

    async def restore_dataset(*args, **kwargs):
        events.append("restore")
        return dataset

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".should_perform_new_commissioning",
        side_effect=decide_reuse,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".load_persisted_thread_active_dataset",
        return_value=dataset,
    ), mock.patch.object(
        suite_instance.border_router,
        "start_device",
        side_effect=start_otbr,
    ), mock.patch.object(
        suite_instance.border_router,
        "form_thread_topology",
        side_effect=restore_dataset,
    ) as form_topology, mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device"
    ) as commission:
        await suite_instance.setup()

    assert events == ["decide", "start", "restore"]
    form_topology.assert_awaited_once_with(dataset)
    commission.assert_not_called()
    assert suite_instance.reusable_commissioning_state_established is True


@pytest.mark.asyncio
async def test_failed_new_thread_commissioning_cleanup_does_not_capture(
    tmp_path,
) -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    config.network.thread.operational_dataset_hex = None
    suite_instance.matter_config = config
    dataset = bytes.fromhex("0e0800000000000100000300000f")
    admin_storage_path = tmp_path / "admin_storage.json"
    dataset_path = tmp_path / "thread_active_dataset.hex"
    admin_storage_path.write_text("old-admin", encoding="utf-8")
    dataset_path.write_text(dataset.hex() + "\n", encoding="ascii")

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "ADMIN_STORAGE_FILE_HOST",
        admin_storage_path,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "THREAD_ACTIVE_DATASET_FILE_HOST",
        dataset_path,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "prompt_reuse_commissioning",
        new=mock.AsyncMock(return_value=PromptOption.FAIL),
    ), mock.patch.object(
        suite_instance.border_router,
        "start_device",
        new=mock.AsyncMock(return_value=True),
    ), mock.patch.object(
        suite_instance.border_router,
        "form_thread_topology",
        new=mock.AsyncMock(return_value=dataset),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.PASS,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device",
        side_effect=DUTCommissioningError("commissioning failed"),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as capture_state, mock.patch.object(
        suite_instance.sdk_container, "is_running", return_value=True
    ), mock.patch.object(
        suite_instance.sdk_container, "destroy"
    ), mock.patch.object(
        suite_instance.border_router, "destroy_device"
    ):
        with pytest.raises(DUTCommissioningError, match="commissioning failed"):
            await suite_instance.setup()
        await suite_instance.cleanup()

    capture_state.assert_not_called()
    assert suite_instance.reusable_commissioning_state_established is False
    assert admin_storage_path.read_text(encoding="utf-8") == "old-admin"
    assert dataset_path.read_text(encoding="ascii") == dataset.hex() + "\n"


@pytest.mark.asyncio
async def test_successful_new_thread_commissioning_promotes_exact_bundle() -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    suite_instance.matter_config = config
    dataset = bytes.fromhex("0e0800000000000100000300000f")

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".should_perform_new_commissioning",
        return_value=True,
    ), mock.patch.object(
        suite_instance.border_router,
        "start_device",
        new=mock.AsyncMock(return_value=True),
    ), mock.patch.object(
        suite_instance.border_router,
        "form_thread_topology",
        new=mock.AsyncMock(return_value=dataset),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".prompt_for_commissioning_mode",
        return_value=PromptOption.PASS,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".commission_device",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as capture_state:
        await suite_instance.setup()

    capture_state.assert_called_once_with(config, test_engine_logger, dataset)
    assert config.network.thread.operational_dataset_hex == dataset.hex()
    assert suite_instance.reusable_commissioning_state_established is True


@pytest.mark.asyncio
async def test_failed_thread_restore_cleanup_does_not_capture(tmp_path) -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    config.network.thread.operational_dataset_hex = None
    suite_instance.matter_config = config
    dataset = bytes.fromhex("0e0800000000000100000300000f")
    admin_storage_path = tmp_path / "admin_storage.json"
    dataset_path = tmp_path / "thread_active_dataset.hex"
    admin_storage_path.write_text("old-admin", encoding="utf-8")
    dataset_path.write_text(dataset.hex() + "\n", encoding="ascii")

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "ADMIN_STORAGE_FILE_HOST",
        admin_storage_path,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "THREAD_ACTIVE_DATASET_FILE_HOST",
        dataset_path,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.utils."
        "prompt_reuse_commissioning",
        new=mock.AsyncMock(return_value=PromptOption.PASS),
    ), mock.patch.object(
        suite_instance.sdk_container, "copy_file_to_container"
    ), mock.patch.object(
        suite_instance.border_router,
        "start_device",
        new=mock.AsyncMock(return_value=True),
    ), mock.patch.object(
        suite_instance.border_router,
        "form_thread_topology",
        new=mock.AsyncMock(side_effect=DUTCommissioningError("restore mismatch")),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as capture_state, mock.patch.object(
        suite_instance.sdk_container, "is_running", return_value=True
    ), mock.patch.object(
        suite_instance.sdk_container, "destroy"
    ), mock.patch.object(
        suite_instance.border_router, "destroy_device"
    ):
        with pytest.raises(DUTCommissioningError, match="restore mismatch"):
            await suite_instance.setup()
        await suite_instance.cleanup()

    capture_state.assert_not_called()
    assert suite_instance.reusable_commissioning_state_established is False
    assert admin_storage_path.read_text(encoding="utf-8") == "old-admin"
    assert dataset_path.read_text(encoding="ascii") == dataset.hex() + "\n"


@pytest.mark.asyncio
async def test_successful_thread_reuse_cleanup_refreshes_exact_bundle() -> None:
    suite_class: Type[PythonTestSuite] = PythonTestSuite.class_factory(
        suite_type=SuiteType.COMMISSIONING,
        name="SomeSuite",
        python_test_version="Some version",
        mandatory=False,
    )
    suite_instance = suite_class(TestSuiteExecution())
    config = default_environment_config.copy(deep=True)  # type: ignore
    config.dut_config.pairing_mode = DutPairingModeEnum.BLE_THREAD
    suite_instance.matter_config = config
    dataset = bytes.fromhex("0e0800000000000100000300000f")

    with mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".PythonTestSuite.setup",
        new=mock.AsyncMock(),
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".should_perform_new_commissioning",
        return_value=False,
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".load_persisted_thread_active_dataset",
        return_value=dataset,
    ), mock.patch.object(
        suite_instance.border_router,
        "start_device",
        new=mock.AsyncMock(return_value=True),
    ), mock.patch.object(
        suite_instance.border_router,
        "form_thread_topology",
        new=mock.AsyncMock(return_value=dataset),
    ), mock.patch.object(
        suite_instance.sdk_container, "is_running", return_value=True
    ), mock.patch.object(
        suite_instance.sdk_container, "destroy"
    ), mock.patch.object(
        suite_instance.border_router, "is_running", return_value=True
    ), mock.patch.object(
        type(suite_instance.border_router),
        "active_dataset_bytes",
        new_callable=mock.PropertyMock,
        return_value=dataset,
    ), mock.patch.object(
        suite_instance.border_router, "destroy_device"
    ), mock.patch(
        "test_collections.matter.sdk_tests.support.python_testing.models.test_suite"
        ".capture_reusable_commissioning_state"
    ) as capture_state:
        await suite_instance.setup()
        capture_state.assert_not_called()
        await suite_instance.cleanup()

    capture_state.assert_called_once_with(config, test_engine_logger, dataset)
