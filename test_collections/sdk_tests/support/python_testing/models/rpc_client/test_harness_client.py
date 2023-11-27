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

import importlib
import sys
from multiprocessing.managers import BaseManager

from matter_testing_support import MatterTestConfig, run_tests

try:
    from matter_yamltests.hooks import TestRunnerHooks
except:

    class TestRunnerHooks:
        pass


MATTER_DEVELOPMENT_PAA_ROOT_CERTS = "/paa-root-certs"

# Pre-computed param list for each Python Test as defined in Verification Steps.
test_params = {
    "TC_ACE_1_3": MatterTestConfig(
        tests=["test_TC_ACE_1_3"],
        commissioning_method="on-network",
        discriminators=[3840],
        setup_passcodes=[20202021],
        dut_node_ids=[0x12344321],
        paa_trust_store_path=MATTER_DEVELOPMENT_PAA_ROOT_CERTS,
        storage_path="/root/admin_storage.json",
    )
}


def main():
    if len(sys.argv) != 2:
        raise Exception("Python test id should be provided as the only parameter.")

    test_name = sys.argv[1]

    config = test_params.get(test_name)

    if config is None:
        raise ValueError(f"Not a valid test id: {test_name}")

    module = importlib.import_module(test_name)
    TestClassReference = getattr(module, test_name)

    BaseManager.register(TestRunnerHooks.__name__)
    manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
    manager.connect()
    test_runner_hooks = manager.TestRunnerHooks()  # shared object proxy

    run_tests(TestClassReference, config, test_runner_hooks)


if __name__ == "__main__":
    main()
