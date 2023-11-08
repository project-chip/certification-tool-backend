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
from typing import List, Tuple

from .python_test_models import PythonTest, PythonTestStep, PythonTestType

ARG_STEP_DESCRIPTION_INDEX = 1
KEYWORD_IS_COMISSIONING_INDEX = 0
BODY_INDEX = 0


class PythonParserException(Exception):
    """Raised when an error occurs during the parser of python file."""


def parse_python_test(path: Path) -> PythonTest:
    """Parse a single Python test file into PythonTest model.

    This will also annotate parsed python test with it's path and test type.
    """
    tc_steps: list[PythonTestStep] = []
    # Currently PICS and config is not configured in Python Testing
    tc_pics: list = []
    tc_config: dict = {}

    tc_desc, tc_steps = __extract_tcs_info(path)

    if not tc_desc or not tc_steps:
        # The file name from path
        tc_name = path.name.split(".")[0]
        raise PythonParserException(
            f"Test Case {tc_name} does not have methods desc_{tc_name} "
            f"or steps_{tc_name}"
        )

    test = PythonTest(name=tc_desc, steps=tc_steps, config=tc_config, PICS=tc_pics)
    test.path = path
    test.type = PythonTestType.AUTOMATED

    return test


def __extract_tcs_info(path: Path) -> Tuple[str, List[PythonTestStep]]:
    with open(path, "r") as python_file:
        parsed_python_file = ast.parse(python_file.read())
        classes = [c for c in parsed_python_file.body if isinstance(c, ast.ClassDef)]

        # Get TC description and TC steps from python test file
        tc_desc: str = ""
        tc_steps: List[PythonTestStep] = []

        for class_ in classes:
            methods = [m for m in class_.body if isinstance(m, ast.FunctionDef)]
            for method in methods:
                if "desc_" in method.name:
                    tc_desc = method.body[BODY_INDEX].value.value # type: ignore
                elif "steps_" in method.name:
                    tc_steps = __retrieve_steps(method)

    return tc_desc, tc_steps


def __retrieve_steps(method: ast.FunctionDef) -> List[PythonTestStep]:
    python_steps: List[PythonTestStep] = []
    for step in method.body[BODY_INDEX].value.elts: # type: ignore
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
            PythonTestStep(label=step_name, is_commissioning=arg_is_commissioning)
        )

    return python_steps
