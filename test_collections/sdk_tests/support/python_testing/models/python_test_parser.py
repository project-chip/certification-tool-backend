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
from pathlib import Path
from typing import List

from test_collections.sdk_tests.support.models.matter_test_models import (
    MatterTestStep,
    MatterTestType,
)

from .python_test_models import PythonTest

ARG_STEP_DESCRIPTION_INDEX = 1
KEYWORD_IS_COMISSIONING_INDEX = 0
BODY_INDEX = 0


class PythonParserException(Exception):
    """Raised when an error occurs during the parser of python file."""


def parse_python_test(path: Path) -> PythonTest:
    """Parse a single Python test file into PythonTest model.

    This will also annotate parsed python test with it's path and test type.
    """
    with open(path, "r") as python_file:
        parsed_python_file = ast.parse(python_file.read())
        classes = [c for c in parsed_python_file.body if isinstance(c, ast.ClassDef)]

    tc_name = path.name.split(".")[0]
    try:
        class_ = next(c for c in classes if tc_name in c.name)
    except StopIteration as si:  # Raised when `next` doesn't find a matching method
        raise PythonParserException(f"{path} must have a class named {tc_name}") from si

    return __parse_test_case_from_class(class_=class_, path=path, tc_name=tc_name)


def __parse_test_case_from_class(
    class_: ast.ClassDef, path: Path, tc_name: str
) -> PythonTest:
    # Currently config is not configured in Python Testing
    tc_config: dict = {}

    desc_method_name = "desc_" + tc_name
    steps_method_name = "steps_" + tc_name
    pics_method_name = "pics_" + tc_name

    methods = [m for m in class_.body if isinstance(m, ast.FunctionDef)]
    try:
        desc_method = next(m for m in methods if desc_method_name in m.name)
        tc_desc = desc_method.body[BODY_INDEX].value.value  # type: ignore

        steps_method = next(m for m in methods if steps_method_name in m.name)
        tc_steps = __retrieve_steps(steps_method)

        pics_method = next(m for m in methods if pics_method_name in m.name)
        tc_pics = __retrieve_pics(pics_method)
    except StopIteration as si:  # Raised when `next` doesn't find a matching method
        raise PythonParserException(
            f"{path} did not contain valid definition for {tc_name}"
        ) from si

    return PythonTest(
        name=tc_name,
        description=tc_desc,
        steps=tc_steps,
        config=tc_config,
        PICS=tc_pics,
        path=path,
        type=MatterTestType.AUTOMATED,
    )


def __retrieve_steps(method: ast.FunctionDef) -> List[MatterTestStep]:
    python_steps: List[MatterTestStep] = []
    for step in method.body[BODY_INDEX].value.elts:  # type: ignore
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
            MatterTestStep(label=step_name, is_commissioning=arg_is_commissioning)
        )

    return python_steps


def __retrieve_pics(method: ast.FunctionDef) -> list:
    python_steps: list = []
    for step in method.body[BODY_INDEX].value.elts:  # type: ignore
        python_steps.append(step.value)

    return python_steps
