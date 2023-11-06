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
from pathlib import Path
from typing import List
import ast
from loguru import logger
from pydantic import ValidationError

from .python_test_models import PythonTest, PythonTestType, PythonTestStep


class PythonParserException(Exception):
    """Raised when an error occurs during the parser of python file."""


def _test_type(test: PythonTest) -> PythonTestType:
    """Determine the type of a test based on the parsed python.

    This is mainly determined by the number of disabled test steps.

    Args:
        test (PythonTest): parsed python test

    Returns:
        TestType:
            - Manual: All steps disabled
            - Semi-Automated: some steps are disabled
            - Automated: no disabled steps
            - Simulated: Tests where file name have "Simulated"
    """
    if test.path is not None and "Simulated" in str(test.path):
        return PythonTestType.SIMULATED

    steps = test.steps

    # if any step has a UserPrompt, categorize as semi-automated
    if any(s.command == "UserPrompt" for s in steps):
        return PythonTestType.SEMI_AUTOMATED

    # Otherwise Automated
    return PythonTestType.AUTOMATED


def parse_python_test(path: Path) -> PythonTest:
    """Parse a single Python test file into PythonTest model.

    This will also annotate parsed python test with it's path and test type.
    """
    python_steps: list[PythonTestStep] = []
    tc_pics = []
    tc_config = {}


    if "ACE_1_3" in str(path): 
        python_steps = tc_steps(path)
        tc_desc = tc_description(path)
        # with open(str(path)) as python_file:
        #     parsed = ast.parse(python_file.read())

        #     functions = [n for n in parsed.body if isinstance(n, ast.FunctionDef)]
        #     classes = [n for n in parsed.body if isinstance(n, ast.ClassDef)]

        # print(functions)
        # print(classes)

    # for function in functions:
    #     result.append(show_info(function))

        # for step in steps: 
    # python_steps = tc_steps(path)
    # tc_desc = tc_description(path)


    return PythonTest(
        name=tc_desc, tests=python_steps, config=tc_config, PICS=tc_pics
    )

def tc_description(path: Path) -> str:
    with open(str(path)) as python_file:
        parsed = ast.parse(python_file.read())

        # functions = [n for n in parsed.body if isinstance(n, ast.FunctionDef)]
        classes = [n for n in parsed.body if isinstance(n, ast.ClassDef)]

        # for function in functions:
        #     print(function)
            # result.append(show_info(function))

        tc_desc = "'"
        python_steps:List[PythonTestStep] = []

        for class_ in classes:
            methods = [n for n in class_.body if isinstance(n, ast.FunctionDef)]
            for method in methods:
                if "desc_" in method.name:
                    tc_desc = method.body[0].value.value
                elif "steps_" in method.name:
                    python_steps = retrieve_steps(method)
                # desc_TC_ACE_1_3 -> method.body[0].value.value
                # method.name
                # print(method)
                # result.append((class_.name + "." + show_info(method)))
                # # desc_*
                # method.body[0].value.value
                # # steps_*
                # method.body[0].value.elts[4].args[1].value

                # method.body[0].value.elts[0].keywords[0].arg
                # method.body[0].value.elts[0].keywords[0].value.value

    # print(", ".join(result))
    
    return ""

def retrieve_steps(method: ast.FunctionDef)-> List[PythonTestStep]:
    python_steps:List[PythonTestStep] = []
    for step in method.body[0].value.elts:
        step_name = step.args[1].value
        step_is_commissioning = False
        if step.keywords and 'is_commissioning' in step.keywords[0].arg:
            is_commissioning = step.keywords[0].value.value

        python_steps.append(
            PythonTestStep(
                label=step_name, is_commissioning=step_is_commissioning
            )
        )
        
    return python_steps

# def tc_steps(path: Path) -> List[PythonTestStep]:
#     python_steps:List[PythonTestStep] = []
#     python_steps.append(
#     PythonTestStep(
#         label="step.description", is_commissioning=False # step.is_commissioning
#     )
#     )
#     return python_steps
