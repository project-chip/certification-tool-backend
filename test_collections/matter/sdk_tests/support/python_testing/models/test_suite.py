#
# Copyright (c) 2025-2026 Project CHIP Authors
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
from enum import Enum
from typing import Optional, Type, TypeVar

from app.constants.shared_constants import DutPairingModeEnum
from app.core.config import settings
from app.schemas.test_environment_config import ThreadAutoConfig, get_th_config_value
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite
from app.user_prompt_support.user_prompt_support import UserPromptSupport
from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
)
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter

from ...sdk_container import SDKContainer
from ...utils import PromptOption, prompt_for_commissioning_mode
from .utils import (
    DUTCommissioningError,
    capture_admin_storage_file,
    commission_device,
    should_perform_new_commissioning,
)


class SuiteType(Enum):
    COMMISSIONING = 1
    NO_COMMISSIONING = 2
    LEGACY = 3
    MANDATORY = 4


# Custom Type variable used to annotate the factory methods of classmethod.
T = TypeVar("T", bound="PythonTestSuite")


class PythonTestSuite(TestSuite):
    """Base class for all Python tests based test suites.

    This class provides a class factory that will dynamically declare a new sub-class
    based on the suite-type.
    """

    python_test_version: str
    suite_name: str
    sdk_container: SDKContainer = SDKContainer(logger)
    border_router: ThreadBorderRouter = ThreadBorderRouter()
    matter_config: Optional[TestEnvironmentConfigMatter] = None

    @classmethod
    def class_factory(
        cls, suite_type: SuiteType, name: str, python_test_version: str, mandatory: bool
    ) -> Type[T]:
        """Dynamically declares a subclass based on the type of test suite."""
        suite_class: Type[PythonTestSuite]

        if suite_type == SuiteType.COMMISSIONING:
            suite_class = CommissioningPythonTestSuite
        else:
            suite_class = PythonTestSuite

        return suite_class.__class_factory(
            name=name, python_test_version=python_test_version, mandatory=mandatory
        )

    @classmethod
    def __class_factory(
        cls, name: str, python_test_version: str, mandatory: bool
    ) -> Type[T]:
        """Common class factory method for all subclasses of PythonTestSuite."""

        return type(
            name,
            (cls,),
            {
                "name": name,
                "python_test_version": python_test_version,
                "metadata": {
                    "public_id": name,
                    "version": "0.0.1",
                    "title": name,
                    "description": name,
                    "mandatory": mandatory,
                },
            },
        )

    async def setup(self) -> None:
        """Override Setup to log Python Test version and set PICS."""
        logger.info("Suite Setup")
        logger.info(f"Python Test Version: {self.python_test_version}")

        logger.info("Setting up SDK container")
        await self.sdk_container.start(
            enable_container_logs=self._container_logs_enabled()
        )

        self.matter_config = TestEnvironmentConfigMatter(**self.config)
        # pcscd is required for NFC reader access regardless of pairing mode
        self.sdk_container.send_command(
            "--disable-polkit",
            prefix="pcscd",
            enable_container_logs=self._container_logs_enabled(),
        )

        if len(self.pics.clusters) > 0:
            logger.info("Create PICS file for DUT")
            self.sdk_container.set_pics(pics=self.pics)
        else:
            self.sdk_container.reset_pics_state()

    def _safe_config(self) -> Optional[dict]:
        """`.config`, or None if it's unavailable (e.g. a test double with no
        wired-up project/execution chain). Used by the th_config resolvers below,
        whose contract is to fall back to the env var default rather than raise
        when project config can't be determined."""
        try:
            return self.config
        except Exception:
            return None

    def _container_logs_enabled(self) -> bool:
        """Whether container-operation logging is enabled.

        The project's th_config.enable_container_logs, when explicitly set,
        overrides the instance-wide ENABLE_CONTAINER_LOGS env var.
        """
        override = get_th_config_value(self._safe_config(), "enable_container_logs")
        if override is not None:
            return bool(override)
        return settings.ENABLE_CONTAINER_LOGS

    async def cleanup(self) -> None:
        logger.info("Suite Cleanup")

        if self.matter_config is not None and self.sdk_container.is_running():
            try:
                logger.info(
                    "Capturing latest admin_storage.json snapshot from container"
                )
                capture_admin_storage_file(self.matter_config, logger)
            except Exception as e:
                # Deliberately broad Exception.
                # The ideia is to never block container/border-router teardown below,
                # so don't narrow this to specific exception types.
                logger.warning(f"Could not capture admin_storage.json snapshot: {e}")

        logger.info("Stopping SDK container")
        self.sdk_container.destroy(enable_container_logs=self._container_logs_enabled())

        logger.info("Stopping Border Router")
        self.border_router.destroy_device()


class CommissioningPythonTestSuite(PythonTestSuite, UserPromptSupport):
    async def setup(self) -> None:
        await super().setup()
        assert self.matter_config is not None

        # If in BLE-Thread, NFC-Thread, or THREAD_MESHCOP mode and a Thread Auto-Config
        # was provided by the user, start a new OTBR container app with the according
        # Thread topology for all tests in the Python Tests Suite.
        if self.matter_config.dut_config.pairing_mode in (
            DutPairingModeEnum.BLE_THREAD,
            DutPairingModeEnum.NFC_THREAD,
            DutPairingModeEnum.THREAD_MESHCOP,
        ) and isinstance(self.matter_config.network.thread, ThreadAutoConfig):
            await self.border_router.start_device(self.matter_config.network.thread)
            await self.border_router.form_thread_topology()

        # If a local copy of admin_storage.json file exists, prompt user if the
        # execution should retrieve the previous commissioning information or
        # if it should perform a new commissioning
        if await should_perform_new_commissioning(
            self, config=self.matter_config, logger=logger
        ):
            logger.info("User chose prompt option YES")
            user_response = await prompt_for_commissioning_mode(
                self, logger, None, self.cancel
            )

            if user_response == PromptOption.FAIL:
                raise DUTCommissioningError(
                    "User chose prompt option FAILED for DUT is in Commissioning Mode"
                )

            logger.info("Commission DUT")
            await commission_device(self.matter_config, logger=logger)
