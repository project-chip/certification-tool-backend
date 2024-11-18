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
import re
from pathlib import Path
from typing import Any, List, Optional, Union

from ...models.matter_test_models import MatterTestStep, MatterTestType
from .performance_tests_models import PerformanceTest, PerformanceTestType

ARG_STEP_DESCRIPTION_INDEX = 1
KEYWORD_IS_COMISSIONING_INDEX = 0

TC_FUNCTION_PATTERN = re.compile(r"[\S]+_TC_[\S]+")
TC_TEST_FUNCTION_PATTERN = re.compile(r"test_(?P<title>TC_[\S]+)")


FunctionDefType = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def parse_performance_tests(path: Path) -> list[PerformanceTest]:
    """Parse a python file into a list of PerformanceTestTest models.

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

    Example: file TC_COMMISSIONING_1_0.py has the methods test_TC_COMMISSIONING_1_0,
        desc_TC_COMMISSIONING_1_0, and steps_TC_COMMISSIONING_1_0.
    """
    with open(path, "r") as python_file:
        parsed_python_file = ast.parse(python_file.read())

    test_classes = __test_classes(parsed_python_file)

    test_cases: list[PerformanceTest] = []
    for c in test_classes:
        test_methods = __test_methods(c)
        test_names = __test_case_names(test_methods)

        for test_name in test_names:
            test_cases.append(__parse_test_case(test_name, test_methods, c.name, path))

    return test_cases


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
            b for b in c.bases if isinstance(b, ast.Name) and b.id == "MatterBaseTest"
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


def __test_case_names(methods: list[FunctionDefType]) -> list[str]:
    """Extract test case names from methods that match the pattern "test_TC_[\\S]+".

    Args:
        methods (list[FunctionDefType]): List of methods to search from.

    Returns:
        list[str]: List of test case names.
    """
    test_names: list[str] = []

    for m in methods:
        if isinstance(m.name, str):
            if match := re.match(TC_TEST_FUNCTION_PATTERN, m.name):
                if name := match["title"]:
                    test_names.append(name)

    return test_names


def __parse_test_case(
    tc_name: str, methods: list[FunctionDefType], class_name: str, path: Path
) -> PerformanceTest:
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
        tc_desc = __retrieve_description(desc_method)

    steps_method = __get_method_by_name(steps_method_name, methods)
    if steps_method:
        tc_steps = __retrieve_steps(steps_method)

    pics_method = __get_method_by_name(pics_method_name, methods)
    if pics_method:
        tc_pics = __retrieve_pics(pics_method)

    return PerformanceTest(
        name=tc_name,
        description=tc_desc,
        steps=tc_steps,
        config=tc_config,
        PICS=tc_pics,
        path=path,
        type=MatterTestType.AUTOMATED,
        class_name=class_name,
        performance_test_type=PerformanceTestType.PERFORMANCE,
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
        step_name = step.args[ARG_STEP_DESCRIPTION_INDEX].value
        arg_is_commissioning = False
        if (
            step.keywords
            and "is_commissioning" in step.keywords[KEYWORD_IS_COMISSIONING_INDEX].arg
        ):
            arg_is_commissioning = step.keywords[
                KEYWORD_IS_COMISSIONING_INDEX
            ].value.value

        python_steps.append(
            MatterTestStep(
                label=step_name,
                command=None,
                arguments=None,
                is_commissioning=arg_is_commissioning,
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
