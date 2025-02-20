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
from enum import Enum
from typing import Type, TypeVar

from app.schemas.test_environment_config import ThreadAutoConfig
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite
from app.user_prompt_support.user_prompt_support import UserPromptSupport
from test_collections.matter.sdk_tests.support.otbr_manager.otbr_manager import (
    ThreadBorderRouter,
)
from test_collections.matter.test_environment_config import (
    DutPairingModeEnum,
    TestEnvironmentConfigMatter,
)

from ...sdk_container import SDKContainer
from ...utils import PromptOption, prompt_for_commissioning_mode
from .utils import (
    DUTCommissioningError,
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

        matter_config = TestEnvironmentConfigMatter(**self.config)
        pairing_mode = matter_config.dut_config.pairing_mode
        if pairing_mode == "nfc_thread" and matter_config.network.nfc_reader and matter_config.network.nfc_reader.usb_reader_bus and usb_reader_bus.usb_reader_device:
            usb_reader_bus = matter_config.network.nfc_reader.usb_reader_bus
            usb_reader_device = matter_config.network.nfc_reader.usb_reader_device
            logger.info("Setting up SDK container with NFC Reader access")
            await self.sdk_container.start(usb_reader_bus, usb_reader_device)
        else:
            logger.info("Setting up SDK container")
            await self.sdk_container.start()

        if len(self.pics.clusters) > 0:
            logger.info("Create PICS file for DUT")
            self.sdk_container.set_pics(pics=self.pics)
        else:
            self.sdk_container.reset_pics_state()

    async def cleanup(self) -> None:
        logger.info("Suite Cleanup")

        logger.info("Stopping SDK container")
        self.sdk_container.destroy()

        logger.info("Stopping Border Router")
        self.border_router.destroy_device()


class CommissioningPythonTestSuite(PythonTestSuite, UserPromptSupport):
    async def setup(self) -> None:
        await super().setup()

        user_response = await prompt_for_commissioning_mode(
            self, logger, None, self.cancel
        )

        if user_response == PromptOption.FAIL:
            raise DUTCommissioningError(
                "User chose prompt option FAILED for DUT is in Commissioning Mode"
            )

        matter_config = TestEnvironmentConfigMatter(**self.config)

        # If in BLE-Thread or NFC-Thread mode and a Thread Auto-Config was provided by
        # the user, start a new OTBR container app with the according Thread topology
        # for all tests in the Python Tests Suite.
        if (
            matter_config.dut_config.pairing_mode == DutPairingModeEnum.BLE_THREAD
            or matter_config.dut_config.pairing_mode == DutPairingModeEnum.NFC_THREAD
        ) and isinstance(matter_config.network.thread, ThreadAutoConfig):
            await self.border_router.start_device(matter_config.network.thread)
            await self.border_router.form_thread_topology()

        # If a local copy of admin_storage.json file exists, prompt user if the
        # execution should retrieve the previous commissioning information or
        # if it should perform a new commissioning
        if await should_perform_new_commissioning(
            self, config=matter_config, logger=logger
        ):
            logger.info("Commission DUT")
            await commission_device(matter_config, logger=logger)
