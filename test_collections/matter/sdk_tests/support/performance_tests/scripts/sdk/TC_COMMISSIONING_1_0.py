#
#    Copyright (c) 2023 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import logging
import subprocess
import time

from chip import ChipDeviceCtrl
from matter_testing_support import (
    MatterBaseTest,
    TestStep,
    async_test_body,
    default_matter_test_main,
)
from mobly import asserts

from .accessory_manager import AccessoryManager

# We don't have a good pipe between the c++ enums in CommissioningDelegate and python
# so this is hardcoded.
# I realize this is dodgy, not sure how to cross the enum from c++ to python cleanly
kCheckForMatchingFabric = 3
kConfigureUTCTime = 6
kConfigureTimeZone = 7
kConfigureDSTOffset = 8
kConfigureDefaultNTP = 9
kConfigureTrustedTimeSource = 19


class TC_COMMISSIONING_1_0(MatterBaseTest):
    def __init__(self, *args):  # type: ignore[no-untyped-def]
        super().__init__(*args)
        self.additional_steps = []

    def setup_class(self):  # type: ignore[no-untyped-def]
        self.commissioner = None
        self.commissioned = False
        self.discriminator = 3842
        return super().setup_class()

    def desc_TC_COMMISSIONING_1_0(self) -> str:
        return "[TC-COMMISSIONING-1.0] Performance"

    def steps_TC_COMMISSIONING_1_0(self) -> list[TestStep]:
        steps = [TestStep(1, "Loop Commissioning ... 1")]

        if len(self.additional_steps) > 0:
            return self.additional_steps
        else:
            return steps

    @async_test_body
    async def teardown_test(self):  # type: ignore[no-untyped-def]
        return super().teardown_test()

    async def commission_and_base_checks(self):  # type: ignore[no-untyped-def]
        node_id = await self.commissioner.CommissionOnNetwork(  # type: ignore
            nodeId=self.dut_node_id,
            setupPinCode=20202021,
            filterType=ChipDeviceCtrl.DiscoveryFilterType.LONG_DISCRIMINATOR,
            filter=self.discriminator,
        )
        asserts.assert_true(
            node_id == self.dut_node_id, "Commissioning did not complete successfully"
        )
        self.commissioned = True

    async def create_commissioner(self) -> None:
        new_certificate_authority = (
            self.certificate_authority_manager.NewCertificateAuthority()
        )
        new_fabric_admin = new_certificate_authority.NewFabricAdmin(
            vendorId=0xFFF1, fabricId=2
        )
        self.commissioner = new_fabric_admin.NewController(
            nodeId=112233, useTestCommissioner=True
        )

        self.commissioner.ResetCommissioningParameters()
        self.commissioner.ResetTestCommissioner()

    @async_test_body
    async def test_TC_COMMISSIONING_1_0(self):  # type: ignore[no-untyped-def]
        accessory_manager = AccessoryManager()
        self.clean_chip_tool_kvs()
        await self.create_commissioner()
        conf = self.matter_test_config

        interactions = 5

        try:
            interactions = conf.global_test_params["interactions"]
            logging.info(f"INFO Internal Control Interaction: {interactions} ")
        except Exception:
            pass

        for i in range(1, interactions + 1):
            self.additional_steps.insert(i, TestStep(i, f"Loop Commissioning ... {i}"))

        for i in range(1, interactions + 1):
            self.step(i)

            logging.info(
                f"|============== Begin Commission {i} =========================|"
            )

            logging.info(
                "|============== Accessory LifeCycle =========================|"
            )

            logging.info("INFO Internal Control reset simulated app ")
            accessory_manager.clean()

            logging.info("INFO Internal Control start simulated app ")
            accessory_manager.start()

            logging.info(
                "|============== Commissioning Steps =========================|"
            )

            await self.commission_and_base_checks()

            time.sleep(0.5)
            logging.info(
                "|============== Accessory LifeCycle =========================|"
            )
            logging.info("INFO Internal Control stop simulated app")
            accessory_manager.stop()
            accessory_manager.clean()

    def clean_chip_tool_kvs(self):  # type: ignore[no-untyped-def]
        try:
            subprocess.check_call("rm -f /root/admin_storage.json", shell=True)
            print("KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")


if __name__ == "__main__":
    default_matter_test_main()
