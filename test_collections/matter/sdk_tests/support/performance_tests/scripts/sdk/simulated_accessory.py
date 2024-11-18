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
import signal
import subprocess

from .accessory_manager import AccessoryInterface


class SimulatedAccessory(AccessoryInterface):
    def __init__(self) -> None:
        self.process = None

    def start(self) -> None:
        if self.process is None:
            # # Arguments to pass to the binary
            arguments = ["--discriminator", "3842", "--KVS", "kvs1"]

            # # Combine the binary path and arguments
            command = ["/root/chip-all-clusters-app"] + arguments

            # # Running the binary with the specified arguments
            self.process = subprocess.Popen(command)  # type: ignore
            print("Simulated App started.")
        else:
            print("Simulated App already running.")  # type: ignore

    def stop(self) -> None:
        if self.process is not None:
            self.process.send_signal(signal.SIGTERM)  # type: ignore
            self.process.wait()  # Wait for the process to exit
            self.process = None
        else:
            print("Simulated App is not running.")

    def clean(self) -> None:
        if self.process is not None:
            self.stop()  # type: ignore
        try:
            subprocess.check_call("rm -rf /root/kvs1", shell=True)
            subprocess.check_call("rm -rf /tmp/chip_*", shell=True)
            print("KVS info deleted.")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting KVS info: {e}")
        try:
            subprocess.check_call("kill -9 $(pidof  chip-all-clusters-app)", shell=True)
        except subprocess.CalledProcessError as e:
            print(
                f"Error while trying to remove possible simulator ghost instances: {e}"
            )
