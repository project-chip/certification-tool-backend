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
from typing import Dict, Tuple

from loguru import logger

from app.schemas.pics import PICS, PICSApplicableTestCases
from app.test_engine.models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
)
from app.test_engine.test_script_manager import test_script_manager


def applicable_test_cases_list(pics: PICS) -> PICSApplicableTestCases:
    """Returns the applicable test cases for this project given the set of PICS"

    Args:
        pics (PICS): set of pics to map against

    Returns:
        PICSApplicableTestCases: List of test cases that are applicable
          for this Project
    """
    applicable_tests: list = []

    if len(pics.clusters) == 0:
        # If the user has not uploaded any PICS
        # i.e, there are no PICS associated with the project then return empty set
        logger.debug(f"Applicable test cases: {applicable_tests}")
        return PICSApplicableTestCases(test_cases=applicable_tests)

    test_collections = test_script_manager.test_collections
    enabled_pics = set([item.number for item in pics.all_enabled_items()])

    applicable_mandatories_tests = __applicable_test_cases(
        test_collections, enabled_pics, True
    )
    applicable_remaining_tests = __applicable_test_cases(
        test_collections, enabled_pics, False
    )

    # Add first the mandatories test cases
    applicable_tests.extend(applicable_mandatories_tests)
    # Add the remaining test cases
    applicable_tests.extend(applicable_remaining_tests)

    logger.debug(f"Applicable test cases: {applicable_tests}")
    return PICSApplicableTestCases(test_cases=applicable_tests)


def __applicable_test_cases(
    test_collections: Dict[str, TestCollectionDeclaration],
    enabled_pics: set[str],
    mandatory: bool,
) -> list:
    applicable_tests: list = []

    for test_collection in test_collections.values():
        if test_collection.mandatory == mandatory:
            for test_suite in test_collection.test_suites.values():
                for test_case in test_suite.test_cases.values():
                    if len(test_case.pics) == 0:
                        # Test cases without pics required are always applicable
                        applicable_tests.append(test_case.metadata["title"])
                    elif len(test_case.pics) > 0:
                        test_enabled_pics, test_disabled_pics = __retrieve_pics(
                            test_case
                        )

                        # Checking if the test case is applicable
                        if test_enabled_pics.issubset(
                            enabled_pics
                        ) and test_disabled_pics.isdisjoint(enabled_pics):
                            applicable_tests.append(test_case.metadata["title"])
    return applicable_tests


def __retrieve_pics(test_case: TestCaseDeclaration) -> Tuple[set, set]:
    enabled_pics_list: set = set()
    disabled_pics_list: set = set()
    for pics in test_case.pics:
        # The '!' char before PICS definition, is how test case flag a PICS as negative
        if pics.startswith("!"):
            # Ignore ! char while adding the pics into disabled_pics_list structure
            disabled_pics_list.add(pics[1:])
        else:
            enabled_pics_list.add(pics)

    return enabled_pics_list, disabled_pics_list
