
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

# class PayloadInfo:
#     filter_type: discovery.FilterType = discovery.FilterType.LONG_DISCRIMINATOR
#     filter_value: int = 0
#     passcode: int = 0

class TC_COMMISSIONING_1_0(MatterBaseTest):
    def setup_class(self):
        self.commissioner = None
        self.commissioned = False
        return super().setup_class()

    def desc_TC_COMMISSIONING_1_0(self) -> str:
        return "[TC-COMMISSIONING-1.0] Performance"

    def steps_TC_COMMISSIONING_1_0(self) -> list[TestStep]:
        steps = [TestStep(1, "Loop Commissioning 1..."),
                 TestStep(2, "Loop commissioning 2..."),
                 TestStep(3, "Loop commissioning 3..."),
                 TestStep(4, "Loop commissioning 4..."),
                 TestStep(5, "Loop commissioning 5..."),
                 TestStep(6, "Loop commissioning 6..."),
                 TestStep(7, "Loop commissioning 7..."),
                 TestStep(8, "Loop commissioning 8..."),
                 TestStep(9, "Loop commissioning 9..."),
                 TestStep(10, "Loop commissioning 10...")]
        # steps = [TestStep(1, "Commissioning", is_commissioning=True)]
        return steps

    async def destroy_current_commissioner(self):
        print("======> destroy_current_commissioner")
        # if self.commissioner:
        #     if self.commissioned:
        #         fabricidx = await self.read_single_attribute_check_success(
        #             dev_ctrl=self.commissioner,
        #             cluster=Clusters.OperationalCredentials,
        #             attribute=Clusters.OperationalCredentials.Attributes.CurrentFabricIndex,
        #         )
        #         cmd = Clusters.OperationalCredentials.Commands.RemoveFabric(
        #             fabricIndex=fabricidx
        #         )
        #         await self.send_single_cmd(cmd=cmd)
        #     self.commissioner.Shutdown()
        # self.commissioner = None
        # self.commissioned = False

    @async_test_body
    async def teardown_test(self):
        print("======> teardown_test")
        await self.destroy_current_commissioner()
        return super().teardown_test()
    
    # def _commission_device(self, i) -> bool:
    #     dev_ctrl = self.default_controller
    #     conf = self.matter_test_config

    #     # TODO: qr code and manual code aren't lists

    #     if conf.qr_code_content or conf.manual_code:
    #         info = self.get_setup_payload_info()
    #     else:
    #         info = PayloadInfo()
    #         info.passcode = conf.setup_passcodes[i]
    #         info.filter_type = ChipDeviceCtrl.DiscoveryFilterType.LONG_DISCRIMINATOR
    #         info.filter_value = conf.discriminators[i]

    #     if conf.commissioning_method == "on-network":
    #         return dev_ctrl.CommissionOnNetwork(
    #             nodeId=conf.dut_node_ids[i],
    #             setupPinCode=info.passcode,
    #             filterType=info.filter_type,
    #             filter=info.filter_value
    #         )
    #     elif conf.commissioning_method == "ble-wifi":
    #         return dev_ctrl.CommissionWiFi(
    #             info.filter_value,
    #             info.passcode,
    #             conf.dut_node_ids[i],
    #             conf.wifi_ssid,
    #             conf.wifi_passphrase
    #         )
    #     elif conf.commissioning_method == "ble-thread":
    #         return dev_ctrl.CommissionThread(
    #             info.filter_value,
    #             info.passcode,
    #             conf.dut_node_ids[i],
    #             conf.thread_operational_dataset
    #         )
    #     elif conf.commissioning_method == "on-network-ip":
    #         logging.warning("==== USING A DIRECT IP COMMISSIONING METHOD NOT SUPPORTED IN THE LONG TERM ====")
    #         return dev_ctrl.CommissionIP(
    #             ipaddr=conf.commissionee_ip_address_just_for_testing,
    #             setupPinCode=info.passcode, nodeid=conf.dut_node_ids[i]
    #         )
    #     else:
    #         raise ValueError("Invalid commissioning method %s!" % conf.commissioning_method)


    async def commission_and_base_checks(self):
        # params = self.default_controller.OpenCommissioningWindow(
        #     nodeid=self.dut_node_id,
        #     timeout=600,
        #     iteration=10000,
        #     discriminator=3842,
        #     option=1,
        # )
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
        if self.commissioner:
            await self.destroy_current_commissioner()
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

        self.clean_chip_tool_kvs()

        for i in range(1, 11):
            
            self.step(i)
            print(f"======> STEP {i}")


            # self.clean_chip_tool_kvs()

            print("======> clean_chip_tool_kvs")
            simulatedAppManager.clean()
            print("======> simulatedAppManager.clean")


            simulatedAppManager.start()
            print("======> simulatedAppManager.start")

            await self.create_commissioner()
            print("======> AFTER Commissioner creation")
            await self.commission_and_base_checks()
            print("======> AFTER Commission completed")

            simulatedAppManager.stop()

            print("======> AFTER simulatedAppManager.stop")

    def clean_chip_tool_kvs(self):
        try:
            subprocess.check_call('rm -f /root/admin_storage.json', shell=True)
            print(f"KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")
            sys.exit(1)

class SimulatedAppManager:
    def __init__(self, simulatedAppPath):
        self.simulatedAppPath = simulatedAppPath
        self.process = None

    def start(self):
        if self.process is None:
            # # Arguments to pass to the binary
            arguments = ['--discriminator', '3842', '--KVS', 'kvs1', '--trace_decode', '1']

            # # Combine the binary path and arguments
            command = ["/root/chip-all-clusters-app"] + arguments

            # # Running the binary with the specified arguments
            self.process = subprocess.Popen(command)
            # self.process = subprocess.Popen(['/root/chip-all-clusters-app'])
            # self.process = subprocess.Popen(f"{self.simulatedAppPath} --discriminator 3842 --KVS kvs1 --trace_decode 1", shell=True)
            print("Simulated App started.")
        else:
            print("Simulated App already running.")

    def stop(self):
        if self.process is not None:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait()  # Wait for the process to exit
            print("Simulated App stopped.")
            self.process = None
        else:
            print("Simulated App is not running.")

    def clean(self):
        if self.process is not None:
            self.stop()  # Simulate App still running?
        try:
            subprocess.check_call('rm -rf /root/kvs1', shell=True)
            subprocess.check_call('rm -rf /tmp/chip_*', shell=True)
            print(f"KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")

if __name__ == "__main__":
    default_matter_test_main()

