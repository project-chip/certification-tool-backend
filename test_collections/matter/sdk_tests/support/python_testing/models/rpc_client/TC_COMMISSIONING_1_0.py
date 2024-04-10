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
import time
import logging
import signal
import subprocess
import sys
import chip.clusters as Clusters
from chip import ChipDeviceCtrl
from chip.clusters.Types import NullValue
from chip.interaction_model import InteractionModelError, Status
from matter_testing_support import (
    MatterBaseTest,
    TestStep,
    async_test_body,
    default_matter_test_main,
)
from mobly import asserts

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
    def setup_class(self):
        self.commissioner = None
        self.commissioned = False
        self.discriminator = 3842
        return super().setup_class()

    def desc_TC_COMMISSIONING_1_0(self) -> str:
        return "[TC-COMMISSIONING-1.0] Performance"

    def steps_TC_COMMISSIONING_1_0(self) -> list[TestStep]:
        steps = [TestStep(1, "Loop Commissioning ...")]
        return steps

    @async_test_body
    async def teardown_test(self):
        return super().teardown_test()

    async def commission_and_base_checks(self):
        errcode = self.commissioner.CommissionOnNetwork(
            nodeId=self.dut_node_id,
            setupPinCode=20202021,
            filterType=ChipDeviceCtrl.DiscoveryFilterType.LONG_DISCRIMINATOR,
            filter=3842,
        )
        asserts.assert_true(
            errcode.is_success, "Commissioning did not complete successfully"
        )
        self.commissioned = True

    async def create_commissioner(self):
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
    async def test_TC_COMMISSIONING_1_0(self):
        simulatedAppManager = SimulatedAppManager("/root/chip-all-clusters-app")
        # print(f"INFO Internal Control ===========Test Commission Loop=============")
        self.clean_chip_tool_kvs()
        await self.create_commissioner()
        conf = self.matter_test_config

        interactions = 5

        try:
            interactions = conf.global_test_params["interactions"]
        except Exception:
            pass

        self.step(1)
        for i in range(1, interactions + 1):
            logging.info(
                f"|============== Begin Commission {i} =========================|"
            )

            logging.info("|============== Accessory LifeCycle =========================|")

            logging.info("INFO Internal Control reset simulated app ")
            simulatedAppManager.clean()

            logging.info("INFO Internal Control start simulated app ")
            simulatedAppManager.start()

            logging.info("|============== Commissioning Steps =========================|")

            await self.commission_and_base_checks()

            # print("INFO Internal Control Waiting 0.5 secs before killing simulator app")
            time.sleep(0.5)
            logging.info("|============== Accessory LifeCycle =========================|")
            logging.info("INFO Internal Control stop simulated app")
            simulatedAppManager.stop()
            simulatedAppManager.clean()
            # print(f"INFO Internal Control ===========End Commission {i}=============")

    def clean_chip_tool_kvs(self):
        try:
            subprocess.check_call("rm -f /root/admin_storage.json", shell=True)
            print(f"KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")


class SimulatedAppManager:
    def __init__(self, simulatedAppPath):
        self.simulatedAppPath = simulatedAppPath
        self.process = None

    def start(self):
        if self.process is None:
            # # Arguments to pass to the binary
            arguments = ["--discriminator", "3842", "--KVS", "kvs1"]

            # # Combine the binary path and arguments
            command = ["/root/chip-all-clusters-app"] + arguments

            # # Running the binary with the specified arguments
            self.process = subprocess.Popen(command)
            print("Simulated App started.")
        else:
            print("Simulated App already running.")

    def stop(self):
        if self.process is not None:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()  # Wait for the process to exit
            self.process = None
        else:
            print("Simulated App is not running.")

    def clean(self):
        if self.process is not None:
            self.stop()  # Simulate App still running?
        try:
            subprocess.check_call("rm -rf /root/kvs1", shell=True)
            subprocess.check_call("rm -rf /tmp/chip_*", shell=True)
            print(f"KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")
        try:
            subprocess.check_call("kill -9 $(pidof  chip-all-clusters-app)", shell=True)
        except subprocess.CalledProcessError as e:
            print(
                f"Error while trying to remove possible simulator ghost instances: {e}"
            )


if __name__ == "__main__":
    default_matter_test_main()

