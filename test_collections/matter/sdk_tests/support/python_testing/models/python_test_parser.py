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
import ast
import json
import re
from pathlib import Path
from typing import Any, List, Optional, Union

from app.test_engine.logger import test_engine_logger as logger

from ...models.matter_test_models import MatterTestStep, MatterTestType
from .python_test_models import PythonTest, PythonTestType

ARG_STEP_DESCRIPTION_INDEX = 1
KEYWORD_IS_COMISSIONING_INDEX = 0

TC_FUNCTION_PATTERN = re.compile(r"[\S]+_TC_[\S]+")
TC_TEST_FUNCTION_PATTERN = re.compile(r"test_(?P<title>TC_[\S]+)")


FunctionDefType = Union[ast.FunctionDef, ast.AsyncFunctionDef]

mandatory_python_tcs_public_id = [
    "TC_IDM_10_2",
    "TC_IDM_10_3",
    "TC_IDM_10_4",
    "TC_IDM_10_5",
    "TC_IDM_12_1",
]


def parse_python_script(path: Path) -> list[PythonTest]:
    """Parse a python file into a list of PythonTest models.

    This will also annotate parsed python tests with their file path and test type.

    This method will search the file for classes that inherit from MatterBaseTest and
    then look for methods with the following patterns to extract the needed information:
     * test_[test_name] - (required) This method contains the test logic
     * desc_[test_name] - (required) This method should return a string with the test
        description
     * pics_[test_name] - (optional) This method should return a list of strings with
        the PICS required for the test case
     * steps_[test_name] - (optional) This method should return a list with the steps'
        descriptions

    Example: file TC_ACE_1_3.py has the methods test_TC_ACE_1_3, desc_TC_ACE_1_3,
        pics_TC_ACE_1_3 and steps_TC_ACE_1_3.
    """
    python_tests: list[PythonTest] = []

    with open(path, "r") as json_file:
        parsed_scripts = json.load(json_file)

    if len(parsed_scripts) == 0:
        return python_tests

    for script_info in parsed_scripts["tests"]:
        test_function = script_info["function"]
        test_name = __test_case_name(test_function)
        if test_name is None:
            logger.info(f"Failed to parse test name [{test_function}].")
            continue

        test_description = script_info["desc"]
        test_pics = script_info["pics"]
        test_path = script_info["path"]
        test_class_name = script_info["class_name"]
        parsed_steps = script_info["steps"]

        is_commssioning = False
        test_steps: list[MatterTestStep] = []
        for index, step in enumerate(parsed_steps):
            step_description = step["description"]

            if index == 0:
                is_commssioning = step["is_commissioning"]

            test_steps.append(
                MatterTestStep(
                    label=step_description,
                    is_commissioning=is_commssioning,
                )
            )

        # - PythonTestType.MANDATORY: Mandatory test cases
        # - PythonTestType.LEGACY: Tests that have only one step and with this
        #   name: "Run entire test"
        # - PythonTestType.COMMISSIONING: Test cases flagged as commissioning
        # - PythonTestType.NO_COMMISSIONING: Test cases flagged as no commissioning
        if test_name in mandatory_python_tcs_public_id:
            python_test_type = PythonTestType.MANDATORY
        elif len(test_steps) == 1 and test_steps[0].label == "Run entire test":
            python_test_type = PythonTestType.LEGACY
        elif is_commssioning:
            python_test_type = PythonTestType.COMMISSIONING
        else:
            python_test_type = PythonTestType.NO_COMMISSIONING

        python_tests.append(
            PythonTest(
                name=test_name,
                description=test_description,
                steps=test_steps,
                config={},  # Currently config is not configured in Python Testing
                PICS=test_pics,
                path=test_path,
                type=MatterTestType.AUTOMATED,
                class_name=test_class_name,
                python_test_type=python_test_type,
            )
        )

    return python_tests


def __test_classes(module: ast.Module) -> list[ast.ClassDef]:
    """Find classes that inherit from MatterBaseTest.

    Args:
        module (ast.Module): Python module.

    Returns:
        list[ast.ClassDef]: List of classes from the given module that inherit from
        MatterBaseTest.
    """
    return [
        c
        for c in module.body
        if isinstance(c, ast.ClassDef)
        and any(
            b
            for b in c.bases
            if isinstance(b, ast.Name)
            and (b.id == "MatterBaseTest" or b.id == "MatterQABaseTestCaseClass")
        )
    ]


def __test_methods(class_def: ast.ClassDef) -> list[FunctionDefType]:
    """Find methods in the given class that match the pattern "[\\S]+_TC_[\\S]+".
    These are the methods that are relevant to the parsing.

    Args:
        classes (ast.ClassDef): Class where the methods will be searched for.

    Returns:
        list[FunctionDefType]: List of methods that are relevant to the parsing.
    """
    all_methods: list[FunctionDefType] = []

    methods = [
        m
        for m in class_def.body
        if isinstance(m, ast.FunctionDef) or isinstance(m, ast.AsyncFunctionDef)
    ]
    for m in methods:
        if isinstance(m.name, str):
            if re.match(TC_FUNCTION_PATTERN, m.name):
                all_methods.append(m)

    return all_methods


def __test_case_name(function_name: str) -> Optional[str]:
    """Extract test case name from methods that match the pattern "test_TC_[\\S]+".

    Args:
        methods (str): Function name.

    Returns:
        str: Test case name.
    """
    if match := re.match(TC_TEST_FUNCTION_PATTERN, function_name):
        if name := match["title"]:
            return name

    return None


def __parse_test_case(
    tc_name: str, methods: list[FunctionDefType], class_name: str, path: Path
) -> PythonTest:
    # Currently config is not configured in Python Testing
    tc_config: dict = {}

    desc_method_name = "desc_" + tc_name
    steps_method_name = "steps_" + tc_name
    pics_method_name = "pics_" + tc_name

    tc_desc = tc_name
    tc_steps = []
    tc_pics = []

    desc_method = __get_method_by_name(desc_method_name, methods)
    if desc_method:
        try:
            tc_desc = __retrieve_description(desc_method)
        except Exception as e:
            logger.warning(
                f"Failed parsing description method for {tc_name}, Error:{str(e)}"
            )

    # If the python test does not implement the steps template method,
    # the test case will be presented in UI and the whole test case will be
    # executed as one step
    steps_method = __get_method_by_name(steps_method_name, methods)
    if steps_method:
        try:
            tc_steps = __retrieve_steps(steps_method)
        except Exception as e:
            logger.warning(f"Failed parsing steps method for {tc_name}, Error:{str(e)}")

    pics_method = __get_method_by_name(pics_method_name, methods)
    if pics_method:
        try:
            tc_pics = __retrieve_pics(pics_method)
        except Exception as e:
            logger.warning(f"Failed parsing PICS method for {tc_name}, Error:{str(e)}")

    # - PythonTestType.COMMISSIONING: test cases that have a commissioning first step
    # - PythonTestType.NO_COMMISSIONING: test cases that follow the expected template
    #   but don't have a commissioning first step
    # - PythonTestType.LEGACY: test cases that don't follow the expected template
    # - PythonTestType.MANDATORY: Mandatory test cases
    # We use the desc_[test_name] method as an indicator that the test case follows the
    # expected template
    python_test_type = PythonTestType.LEGACY

    if tc_name in mandatory_python_tcs_public_id:
        python_test_type = PythonTestType.MANDATORY
    elif len(tc_steps) > 0 and tc_steps[0].is_commissioning:
        python_test_type = PythonTestType.COMMISSIONING
    elif desc_method:
        python_test_type = PythonTestType.NO_COMMISSIONING

    return PythonTest(
        name=tc_name,
        description=tc_desc,
        steps=tc_steps,
        config=tc_config,
        PICS=tc_pics,
        path=path,
        type=MatterTestType.AUTOMATED,
        class_name=class_name,
        python_test_type=python_test_type,
    )


def __get_method_by_name(
    name: str, methods: list[FunctionDefType]
) -> Optional[FunctionDefType]:
    return next((m for m in methods if name in m.name), None)


def __retrieve_steps(method: FunctionDefType) -> List[MatterTestStep]:
    python_steps: List[MatterTestStep] = []

    steps_body = __retrieve_return_body(method, ast.List)
    if not steps_body:
        return []

    for step in steps_body.value.elts:
        try:
            arg_is_commissioning = False

            if (
                step.keywords
                and "is_commissioning"
                in step.keywords[KEYWORD_IS_COMISSIONING_INDEX].arg
            ):
                arg_is_commissioning = step.keywords[
                    KEYWORD_IS_COMISSIONING_INDEX
                ].value.value

            step_name = step.args[ARG_STEP_DESCRIPTION_INDEX].value
            parsed_step_name = step_name
        except Exception as e:
            logger.warning(
                f"Failed parsing step name from {method.name}, Error:{str(e)}"
            )
            parsed_step_name = "UNABLE TO PARSE TEST STEP NAME"

        python_steps.append(
            MatterTestStep(
                label=parsed_step_name, is_commissioning=arg_is_commissioning
            )
        )

    return python_steps


def __retrieve_pics(method: FunctionDefType) -> list:
    pics_list: list = []
    pics_body = __retrieve_return_body(method, ast.List)
    if not pics_body:
        return []

    for pics in pics_body.value.elts:
        pics_list.append(pics.value)

    return pics_list


def __retrieve_return_body(
    method: FunctionDefType, instance_type: Any
) -> Union[Any, None]:
    if method.body and len(method.body) > 0:
        for body in method.body:
            if isinstance(body.value, instance_type):  # type: ignore
                return body

    return None


def __retrieve_description(method: FunctionDefType) -> str:
    description = ""
    for body in method.body:
        if type(body) is ast.Return:
            description = body.value.value  # type: ignore

    return description
