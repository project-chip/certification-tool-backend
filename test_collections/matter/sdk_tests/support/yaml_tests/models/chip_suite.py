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
from typing import Optional

from app.models import TestSuiteExecution
from app.otbr_manager.otbr_manager import ThreadBorderRouter
from app.schemas.test_environment_config import (
    DutPairingModeEnum,
    ThreadAutoConfig,
    ThreadExternalConfig,
)
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite
from app.user_prompt_support.prompt_request import OptionsSelectPromptRequest
from app.user_prompt_support.user_prompt_support import UserPromptSupport

from ...chip.chip_server import ChipServerType
from ...sdk_container import SDKContainer
from ...yaml_tests.matter_yaml_runner import MatterYAMLRunner
from ...yaml_tests.models.chip_test import PromptOption

CHIP_APP_PAIRING_CODE = "CHIP:SVR: Manual pairing code:"


class SuiteSetupError(Exception):
    pass


class DUTCommissioningError(Exception):
    pass


class ChipSuite(TestSuite, UserPromptSupport):
    sdk_container: SDKContainer = SDKContainer(logger)
    runner: MatterYAMLRunner = MatterYAMLRunner(logger=logger)
    border_router: Optional[ThreadBorderRouter] = None
    server_type: ChipServerType = ChipServerType.CHIP_TOOL
    __dut_commissioned_successfully: bool = False

    def __init__(self, test_suite_execution: TestSuiteExecution):
        super().__init__(test_suite_execution)

    async def setup(self) -> None:
        logger.info("Setting up SDK container")
        await self.sdk_container.start()

        logger.info("Setting up test runner")
        await self.runner.setup(
            self.server_type, self.config.dut_config.chip_use_paa_certs
        )

        if len(self.pics.clusters) > 0:
            logger.info("Create PICS file for DUT")
            self.runner.set_pics(pics=self.pics)
        else:
            # Disable sending "-PICS" option when running test
            self.runner.reset_pics_state()

        self.__dut_commissioned_successfully = False
        if self.server_type == ChipServerType.CHIP_TOOL:
            logger.info("Commission DUT")
            await self.__commission_dut_allowing_retries()
        elif self.server_type == ChipServerType.CHIP_APP:
            logger.info("Verify Test suite prerequisites")
            await self.__verify_test_suite_prerequisites()

    async def __commission_dut_allowing_retries(self) -> None:
        """Try to commission DUT. If it fails, prompt user if they want to retry. Keep
        trying until commissioning succeeds or user chooses to cancel.

        Raises:
            SuiteSetupError: Commissioning failed and user chose not to retry
        """
        while not self.__dut_commissioned_successfully:
            try:
                await self.__pair_with_dut()
                self.__dut_commissioned_successfully = True
            except DUTCommissioningError as e:
                await self.__prompt_for_commissioning_retry(e)

    async def __pair_with_dut(self) -> None:
        if self.config.dut_config.pairing_mode is DutPairingModeEnum.ON_NETWORK:
            pair_result = await self.__pair_with_dut_onnetwork()
        elif self.config.dut_config.pairing_mode is DutPairingModeEnum.BLE_WIFI:
            pair_result = await self.__pair_with_dut_ble_wifi()
        elif self.config.dut_config.pairing_mode is DutPairingModeEnum.BLE_THREAD:
            pair_result = await self.__pair_with_dut_ble_thread()
        else:
            raise DUTCommissioningError("Unsupported DUT pairing mode")

        if not pair_result:
            raise DUTCommissioningError("Failed to pair with DUT")

    async def __pair_with_dut_onnetwork(self) -> bool:
        return await self.runner.pairing_on_network(
            setup_code=self.config.dut_config.setup_code,
            discriminator=self.config.dut_config.discriminator,
        )

    async def __pair_with_dut_ble_wifi(self) -> bool:
        if self.config.network.wifi is None:
            raise DUTCommissioningError("Tool config is missing wifi config.")

        return await self.runner.pairing_ble_wifi(
            ssid=self.config.network.wifi.ssid,
            password=self.config.network.wifi.password,
            setup_code=self.config.dut_config.setup_code,
            discriminator=self.config.dut_config.discriminator,
        )

    async def __pair_with_dut_ble_thread(self) -> bool:
        if self.config.network.thread is None:
            raise DUTCommissioningError("Tool config is missing thread config.")

        # if thread has ThreadAutoConfig, bring up border router
        thread_config = self.config.network.thread
        if isinstance(thread_config, ThreadExternalConfig):
            hex_dataset = thread_config.operational_dataset_hex
        elif isinstance(thread_config, ThreadAutoConfig):
            border_router = await self.__start_border_router(thread_config)
            hex_dataset = border_router.active_dataset
        else:
            raise DUTCommissioningError("Invalid thread configuration")

        return await self.runner.pairing_ble_thread(
            hex_dataset=hex_dataset,
            setup_code=self.config.dut_config.setup_code,
            discriminator=self.config.dut_config.discriminator,
        )

    async def __start_border_router(
        self, config: ThreadAutoConfig
    ) -> ThreadBorderRouter:
        border_router = ThreadBorderRouter()
        if await border_router.start_device(config):
            await border_router.form_thread_topology()
        else:
            # This is unexpected but should work
            logger.warning("Reusing already running Border Router")

        self.border_router = border_router

        return border_router

    async def cleanup(self) -> None:
        # Only unpair if commissioning was successfull during setup
        if self.__dut_commissioned_successfully:
            # Unpair is not applicable for simulated apps case
            if self.server_type == ChipServerType.CHIP_TOOL:
                logger.info("Unpairing DUT from server")
                await self.runner.unpair()
            elif self.server_type == ChipServerType.CHIP_APP:
                logger.info("Prompt user to perform decommissioning")
                await self.__prompt_user_to_perform_decommission()

        logger.info("Stopping test runner")
        await self.runner.stop()

        logger.info("Stopping SDK container")
        self.sdk_container.destroy()

        if self.border_router is not None:
            logger.info("Stopping border router container")
            self.border_router.destroy_device()

    async def __verify_test_suite_prerequisites(self) -> None:
        # prerequisites apply for CHIP_APP only.
        if self.server_type == ChipServerType.CHIP_APP:
            logger.info("Prompt user to perform commissioning")
            await self.__prompt_user_to_perform_commission()

    async def __prompt_for_commissioning_retry(
        self, error: DUTCommissioningError
    ) -> None:
        """Prompt the user if the commissioning should be retried

        Args:
            error (DUTCommissioningError): the commissioning error

        Raises:
            SuiteSetupError: Prompt response is CANCEL
            ValueError: Prompt response is unexpected
        """

        options = {
            "RETRY": PromptOption.RETRY,
            "CANCEL": PromptOption.CANCEL,
        }
        prompt = (
            f"Commissioning failed with error: {error}.\nIf you want to retry, please "
            "make sure that DUT is ready for commissioning and then select the "
            "'RETRY' option."
        )
        prompt_request = OptionsSelectPromptRequest(prompt=prompt, options=options)
        prompt_response = await self.send_prompt_request(prompt_request)

        match prompt_response.response:
            case PromptOption.RETRY:
                logger.info("User chose to RETRY commissioning")

            case PromptOption.CANCEL:
                raise SuiteSetupError(
                    "Failed to commission DUT and user chose not to retry"
                )

            case _:
                raise ValueError(
                    f"Received unknown prompt option for \
                        commissioning step: {prompt_response.response}"
                )

    async def __prompt_user_to_perform_commission(self) -> None:
        """Prompt the user to perform commissioning

        Raises:
            ValueError: Response is pairing failed or unexpected
        """

        options = {
            "Pairing successful": PromptOption.PASS,
            "Pairing Failed": PromptOption.FAIL,
        }
        prompt = """Please commission with the device using a controller:
                Example:
                    <Controller> pairing code <nodeid> <pairing code>
                """
        prompt_request = OptionsSelectPromptRequest(
            prompt=prompt, options=options, timeout=60
        )
        prompt_response = await self.send_prompt_request(prompt_request)

        match prompt_response.response:
            case PromptOption.FAIL:
                raise ValueError("User stated commissioning step FAILED.")

            case PromptOption.PASS:
                self.__dut_commissioned_successfully = True
                logger.info("User stated commissioning step PASSED.")

            case _:
                raise ValueError(
                    f"Received unknown prompt option for \
                        commissioning step: {prompt_response.response}"
                )

    async def __prompt_user_to_perform_decommission(self) -> None:
        """Prompt the user to perform decommission using a controller"""

        options = {
            "Decommission successful": PromptOption.PASS,
            "Decommission Failed": PromptOption.FAIL,
        }
        prompt = """Please decommission with the device using a controller:
                Example:
                    <Controller> pairing unpair <nodeid>
                """
        prompt_request = OptionsSelectPromptRequest(
            prompt=prompt, options=options, timeout=60
        )
        prompt_response = await self.send_prompt_request(prompt_request)

        match prompt_response.response:
            case PromptOption.FAIL:
                logger.info("User stated decommissioning step FAILED.")

            case PromptOption.PASS:
                logger.info("User stated decommissioning step PASSED.")

            case _:
                logger.info(
                    f"Received unknown prompt option for \
                        decommissioning step: {prompt_response.response}"
                )
