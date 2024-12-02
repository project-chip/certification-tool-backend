#
#  Copyright (c) 2023 Project CHIP Authors
#  All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# type: ignore
# flake8: noqa
import importlib
import json
import sys
from contextlib import redirect_stdout
from multiprocessing.managers import BaseManager

from chip.testing.matter_testing import (
    CommissionDeviceTest,
    MatterTestConfig,
    get_test_info,
    parse_matter_test_args,
    run_tests,
)

COMMISSION_ARGUMENT = "commission"
GET_TEST_INFO_ARGUMENT = "--get_test_info"
TEST_INFO_JSON_FILENAME = "test_info.json"
TEST_INFO_JSON_PATH = "/root/python_testing/" + TEST_INFO_JSON_FILENAME
EXECUTION_LOG_OUTPUT = "/root/python_testing/test_output.txt"


class TestRunnerHooks:
    pass


def main() -> None:
    # Load python_testing/scripts as a module. This folder is where all python scripts
    # are located
    sys.path.append("/root/python_testing/scripts")
    sys.path.append("/root/python_testing/scripts/sdk")

    test_args = sys.argv[2:]
    config = parse_matter_test_args(test_args)
    if GET_TEST_INFO_ARGUMENT in sys.argv:
        try:
            info = get_test_info_support(
                script_path=sys.argv[1], class_name=sys.argv[2], config=config
            )
        except Exception as e:
            error_msg = {"detail": f"{str(e)}"}
            with open(TEST_INFO_JSON_PATH, "w") as f:
                json.dump(error_msg, f, indent=4)
            raise e

        with open(TEST_INFO_JSON_PATH, "w") as f:
            json.dump(info, f, indent=4)
    else:
        # TODO: find a better solution.
        # This is a temporary workaround since Python Tests
        # are generating a big amount of log
        with open(EXECUTION_LOG_OUTPUT, "w") as f:
            with redirect_stdout(f):
                if sys.argv[1] == COMMISSION_ARGUMENT:
                    commission(config)
                else:
                    run_test(
                        script_path=sys.argv[1], class_name=sys.argv[2], config=config
                    )


def get_test_info_support(script_path: str, class_name: str, config: MatterTestConfig):
    module = importlib.import_module(script_path.replace("/", "."))
    TestClassReference = getattr(module, class_name)
    test_info = get_test_info(TestClassReference, config)
    return json.loads(json.dumps(test_info, default=lambda o: o.__dict__))


def run_test(script_path: str, class_name: str, config: MatterTestConfig) -> None:
    BaseManager.register(TestRunnerHooks.__name__)
    manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
    manager.connect()
    test_runner_hooks = manager.TestRunnerHooks()  # shared object proxy # type: ignore

    try:
        # For a script_path like 'custom/TC_XYZ' the module is 'custom.TC_XYZ'
        module = importlib.import_module(script_path.replace("/", "."))
        TestClassReference = getattr(module, class_name)

        run_tests(TestClassReference, config, test_runner_hooks)
    except Exception as e:
        test_runner_hooks.step_failure(
            logger=None, logs=str(e), duration=0, request=None, received=None
        )
        test_runner_hooks.stop(duration=0)


def commission(config: MatterTestConfig) -> None:
    config.commission_only = True
    run_tests(CommissionDeviceTest, config, None)


if __name__ == "__main__":
    main()
