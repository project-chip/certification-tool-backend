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
# type: ignore
# flake8: noqa

import importlib
import sys
from multiprocessing.managers import BaseManager

from matter_testing_support import (
    CommissionDeviceTest,
    MatterTestConfig,
    parse_matter_test_args,
    run_tests,
)


class TestRunnerHooks:
    pass


def main() -> None:
    # Load python_testing as a module. This folder is where all python script is located
    sys.path.append("/root/python_testing")

    test_args = sys.argv[2:]
    config = parse_matter_test_args(test_args)

    if sys.argv[1] == "commission":
        commission(config)
    else:
        run_test(script_name=sys.argv[1], config=config)


def run_test(script_name: str, config: MatterTestConfig) -> None:
    module = importlib.import_module(script_name)
    TestClassReference = getattr(module, script_name)

    BaseManager.register(TestRunnerHooks.__name__)
    manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
    manager.connect()
    test_runner_hooks = manager.TestRunnerHooks()  # shared object proxy # type: ignore

    run_tests(TestClassReference, config, test_runner_hooks)


def commission(config: MatterTestConfig) -> None:
    config.commission_only = True
    run_tests(CommissionDeviceTest, config, None)


if __name__ == "__main__":
    main()
