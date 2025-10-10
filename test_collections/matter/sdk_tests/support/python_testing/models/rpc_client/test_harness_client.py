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

from matter.testing.commissioning import CommissionDeviceTest
from matter.testing.matter_testing import (
    MatterTestConfig,
    TestStep,
    get_test_info,
    parse_matter_test_args,
    run_tests,
)

# TH-specific argument keys
TH_ARG_GET_TEST_INFO = "get-test-info"
TH_ARG_TH_CLIENT_TEST = "th-client-test"
TH_ARG_TEST_LIST = "test-list"
TH_COMMISSION_ARGUMENT = "commission"

# CLI argument flags (derived from TH argument keys)
GET_TEST_INFO_ARGUMENT = f"--{TH_ARG_GET_TEST_INFO}"
GET_TEST_LIST_ARGUMENT = f"--{TH_ARG_TEST_LIST}"
TH_CLIENT_TEST_ARGUMENT = f"--{TH_ARG_TH_CLIENT_TEST}"

TEST_INFO_JSON_FILENAME = "test_info.json"
TEST_INFO_JSON_PATH = "/root/python_testing/" + TEST_INFO_JSON_FILENAME
EXECUTION_LOG_OUTPUT = "/root/python_testing/test_output.txt"


def sanitize_th_arguments(args: list[str]) -> tuple[list[str], dict]:
    """
    Sanitize TH-specific arguments before passing to parse_matter_test_args.

    Returns:
        tuple: (sanitized_args, th_specific_args)
            - sanitized_args: Arguments safe to pass to parse_matter_test_args
            - th_specific_args: Dictionary containing TH-specific argument values
    """
    th_specific = {
        TH_ARG_GET_TEST_INFO: False,
        TH_ARG_TH_CLIENT_TEST: None,
        TH_ARG_TEST_LIST: None,
        TH_COMMISSION_ARGUMENT: False,
    }

    sanitized = []
    i = 0

    while i < len(args):
        arg = args[i]

        if arg == GET_TEST_INFO_ARGUMENT:
            th_specific[TH_ARG_GET_TEST_INFO] = True
            i += 1
        elif arg == TH_CLIENT_TEST_ARGUMENT:
            # Next 2 arguments are script_path and class_name
            if i + 2 < len(args):
                th_specific[TH_ARG_TH_CLIENT_TEST] = [args[i + 1], args[i + 2]]
                i += 3
            else:
                raise ValueError(
                    f"{TH_CLIENT_TEST_ARGUMENT} requires 2 arguments: SCRIPT_PATH CLASS_NAME"
                )
        elif arg == GET_TEST_LIST_ARGUMENT:
            # Collect all arguments until the next flag
            test_list = []
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                test_list.append(args[i])
                i += 1
            th_specific[TH_ARG_TEST_LIST] = test_list
        elif arg == TH_COMMISSION_ARGUMENT:
            # Commission is a TH-specific command
            th_specific[TH_COMMISSION_ARGUMENT] = True
            i += 1
        else:
            sanitized.append(arg)
            i += 1

    return sanitized, th_specific


class TestRunnerHooks:
    def start(self, count: int):
        print("=====> hooks.start")

    def stop(self, duration: int):
        print("=====> hooks.stop")

    def test_start(self, filename: str, name: str, count: int, steps: list[str] = []):
        print("=====> hooks.test_start")

    def test_stop(self, exception: Exception, duration: int):
        print("=====> hooks.test_stop")

    def step_skipped(self, name: str, expression: str):
        print("=====> hooks.step_skipped")

    def step_start(self, name: str):
        print("=====> hooks.step_start")

    def step_success(self, logger, logs, duration: int, request: TestStep):
        print("=====> hooks.step_success")

    def step_failure(self, logger, logs, duration: int, request: TestStep, received):
        print("=====> hooks.start")

    def step_unknown(self):
        print("=====> hooks.step_failure")

    async def step_manual(self):
        print("=====> hooks.step_manual")


def main() -> None:
    # Load python_testing/scripts as a module. This folder is where all python scripts
    # are located
    sys.path.append("/root/python_testing/scripts")
    sys.path.append("/root/python_testing/scripts/sdk")

    test_args1 = sys.argv[1:]

    test_args = configure_iterations(test_args1)

    # Sanitize TH-specific arguments
    sanitized_args, th_args = sanitize_th_arguments(test_args)

    print("Sanitized args:", sanitized_args)
    print("TH-specific args:", th_args)

    # Temporarily override sys.argv to prevent parse_matter_test_args from using it
    original_argv = sys.argv
    try:
        sys.argv = [sys.argv[0]] + sanitized_args
        config = parse_matter_test_args(sanitized_args)
    finally:
        sys.argv = original_argv

    # Use TH-specific arguments
    if th_args[TH_ARG_GET_TEST_INFO]:
        try:
            # Check if test_list is present
            if th_args[TH_ARG_TEST_LIST]:
                # process the test list
                info = process_test_list_sanitized(th_args[TH_ARG_TEST_LIST], config)
            elif th_args[TH_ARG_TH_CLIENT_TEST]:
                # Use th_client_test values for script_path and class_name
                script_path, class_name = th_args[TH_ARG_TH_CLIENT_TEST]
                info = get_test_info_support(
                    script_path=script_path, class_name=class_name, config=config
                )
            else:
                raise ValueError(
                    f"Either {TH_CLIENT_TEST_ARGUMENT} or {GET_TEST_LIST_ARGUMENT} must be provided with {GET_TEST_INFO_ARGUMENT}"
                )

            with open(TEST_INFO_JSON_PATH, "w") as f:
                json.dump(info, f, indent=4)

        except Exception as e:
            error_msg = {"detail": f"{str(e)}"}
            with open(TEST_INFO_JSON_PATH, "w") as f:
                json.dump(error_msg, f, indent=4)
            raise e
    else:
        # TODO: find a better solution.
        # This is a temporary workaround since Python Tests
        # are generating a big amount of log
        with open(EXECUTION_LOG_OUTPUT, "w") as f:
            with redirect_stdout(f):
                # Check if 'commission' was passed as first argument
                if th_args[TH_COMMISSION_ARGUMENT]:
                    commission(config)
                elif th_args[TH_ARG_TH_CLIENT_TEST]:
                    script_path, class_name = th_args[TH_ARG_TH_CLIENT_TEST]
                    run_test(
                        script_path=script_path, class_name=class_name, config=config
                    )
                else:
                    raise ValueError(
                        f"{TH_CLIENT_TEST_ARGUMENT} is required for test execution"
                    )


def get_test_info_support(script_path: str, class_name: str, config: MatterTestConfig):
    module = importlib.import_module(script_path.replace("/", "."))
    TestClassReference = getattr(module, class_name)
    test_info = get_test_info(TestClassReference, config)
    return json.loads(json.dumps(test_info, default=lambda o: o.__dict__))


def configure_iterations(args) -> []:
    result = args
    try:
        position = sys.argv.index("--iterations")
        iterations_value = sys.argv[position + 1]
        result = args + ["--int-arg", f"iterations:{iterations_value}"]
    except ValueError:
        pass
    return result

    try:
        subprocess.check_call("kill $(pidof  chip-all-clusters-app)", shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while trying to remove rogue simulators: {e}")


def run_test(script_path: str, class_name: str, config: MatterTestConfig) -> None:
    manual_execution = 0  # false

    try:
        manual_execution = sys.argv.index("--cmd-line")
    except ValueError:
        pass

    if manual_execution:
        test_runner_hooks = TestRunnerHooks()
    else:
        BaseManager.register(TestRunnerHooks.__name__)
        manager = BaseManager(address=("0.0.0.0", 50000), authkey=b"abc")
        manager.connect()
        test_runner_hooks = (
            manager.TestRunnerHooks()
        )  # shared object proxy # type: ignore

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


def _process_test_pairs(
    test_pairs: list[tuple[str, str]], config: MatterTestConfig
) -> list:
    all_tests_info = []
    for script_path, class_name in test_pairs:
        try:
            info = get_test_info_support(
                script_path=script_path, class_name=class_name, config=config
            )
            all_tests_info.append(
                {"script_path": script_path, "class_name": class_name, "info": info}
            )
        except Exception as e:
            all_tests_info.append(
                {
                    "detail": f"{str(e)}",
                    "script_path": script_path,
                    "class_name": class_name,
                }
            )
    return all_tests_info


def process_test_list_sanitized(test_list: list[str], config: MatterTestConfig) -> list:
    """
    Process a sanitized test list containing pairs of (script_path, class_name).

    Args:
        test_list: List of arguments extracted from --test-list
        config: MatterTestConfig object

    Returns:
        List of test information dictionaries
    """
    if len(test_list) % 2 != 0:
        raise ValueError(
            f"Invalid parameters. The arguments provided after {GET_TEST_LIST_ARGUMENT} must be in "
            "pairs: (script_path, class_name)"
        )

    # Parse test files and classes from the list
    test_pairs = []
    for i in range(0, len(test_list), 2):
        script_path = test_list[i]
        class_name = test_list[i + 1]
        test_pairs.append((script_path, class_name))

    return _process_test_pairs(test_pairs, config)


if __name__ == "__main__":
    main()
