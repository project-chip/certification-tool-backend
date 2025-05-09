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
import json
from typing import Dict, Tuple

from loguru import logger

from app.schemas.pics import PICS, PICSApplicableTestCases
from app.test_engine.models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
)
from app.test_engine.test_script_manager import test_script_manager
from test_collections.matter.sdk_tests.support.performance_tests.sdk_performance_tests import (  # noqa
    STRESS_TEST_COLLECTION,
)

PICS_PLAT_CERT = "MCORE.PLAT_CERT"
PICS_PLAT_CERT_DERIVED = "MCORE.PLAT_CERT_DONE"


class PlatformTestError(Exception):
    """Base exception for platform test errors"""

    pass


class FileNotFoundError(PlatformTestError):
    """Exception raised when test file is not found"""

    pass


class InvalidJSONError(PlatformTestError):
    """Exception raised when JSON is invalid"""

    pass


def __read_platform_test_cases(json_file_path: str) -> set[str]:
    """
    Read platform test cases from a JSON file.

    Args:
        json_file_path: Path to the JSON file containing platform test cases

    Returns:
        Set of test case IDs

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        InvalidJSONError: If the JSON format is invalid
    """
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)
            return set(data.get("PlatformTestCasesToRun", []))
    except FileNotFoundError:
        raise FileNotFoundError(f"File {json_file_path} not found")
    except json.JSONDecodeError:
        raise InvalidJSONError(f"Invalid JSON format in {json_file_path}")


def __handle_platform_certification(
    enabled_pics: set[str], applicable_tests_combined: set[str], dmp_test_skip: list
) -> set[str]:
    """
    Handle platform certification test cases based on PICS configuration.

    Args:
        enabled_pics: Set of enabled PICS
        applicable_tests_combined: Current set of applicable test cases
        dmp_test_skip: List of test cases to skip

    Returns:
        Updated set of applicable test cases

    Raises:
        PlatformTestError: If both PICS_PLAT_CERT and PICS_PLAT_CERT_DERIVED are enabled
    """
    if PICS_PLAT_CERT in enabled_pics and PICS_PLAT_CERT_DERIVED in enabled_pics:
        raise PlatformTestError(
            "Invalid configuration: PICS_PLAT_CERT and PICS_PLAT_CERT_DERIVED are "
            "mutually exclusive. Please enable only one of them"
        )

    if PICS_PLAT_CERT in enabled_pics:
        applicable_tests_combined = __process_platform_tests(applicable_tests_combined)
    elif PICS_PLAT_CERT_DERIVED in enabled_pics:
        applicable_tests_combined = __process_platform_cert_derived(
            dmp_test_skip, applicable_tests_combined
        )

    logger.info(
        "Listing applicable tests cases "
        f"for execution: {sorted(applicable_tests_combined)}"
    )

    return applicable_tests_combined


def applicable_test_cases_set(
    pics: PICS, dmp_test_skip: list
) -> PICSApplicableTestCases:
    """Returns the applicable test cases for this project given the set of PICS"

    Args:
        pics (PICS): set of pics to map against

    Returns:
        PICSApplicableTestCases: List of test cases that are applicable
          for this Project
    """
    applicable_tests: set = set()

    if not pics.clusters:
        # If the user has not uploaded any PICS
        # i.e, there are no PICS associated with the project then return empty set
        logger.debug(f"Applicable test cases: {applicable_tests}")
        return PICSApplicableTestCases(test_cases=applicable_tests)

    # Getting a copy of Test Collections Dict so we may add/remove items safely
    test_collections_copy = test_script_manager.test_collections.copy()
    enabled_pics = set([item.number for item in pics.all_enabled_items()])

    applicable_mandatories_tests = __applicable_test_cases(
        test_collections_copy, enabled_pics, True
    )
    applicable_remaining_tests = __applicable_test_cases(
        test_collections_copy, enabled_pics, False
    )

    # Combine all applicable tests
    applicable_tests_combined = (
        applicable_mandatories_tests | applicable_remaining_tests
    )

    # Handle platform certification test cases
    applicable_tests = __handle_platform_certification(
        enabled_pics, applicable_tests_combined, dmp_test_skip
    )

    logger.debug(f"Applicable test cases: {applicable_tests}")
    return PICSApplicableTestCases(test_cases=list(applicable_tests))


def __applicable_test_cases(
    test_collections: Dict[str, TestCollectionDeclaration],
    enabled_pics: set[str],
    mandatory: bool,
) -> set:
    applicable_tests: set = set()

    # The 'Performance Tests' Collection should not be considered for the PICS tests.
    # NOTE: The second parameter for the dictionary's "pop" method is provided so we may
    # prevent a conditional exception when the following key is not present.
    test_collections.pop(STRESS_TEST_COLLECTION, None)

    for test_collection in test_collections.values():
        if test_collection.mandatory == mandatory:
            for test_suite in test_collection.test_suites.values():
                for test_case in test_suite.test_cases.values():
                    if not test_case.pics:
                        # Test cases without PICS are always applicable
                        applicable_tests.add(test_case.metadata["title"])
                    else:
                        test_enabled_pics, test_disabled_pics = __retrieve_pics(
                            test_case
                        )

                        # Checking if the test case is applicable
                        if test_enabled_pics.issubset(
                            enabled_pics
                        ) and test_disabled_pics.isdisjoint(enabled_pics):
                            applicable_tests.add(test_case.metadata["title"])
    return applicable_tests


def __retrieve_pics(test_case: TestCaseDeclaration) -> Tuple[set, set]:
    enabled_pics: set[str] = set()
    disabled_pics: set[str] = set()
    for pics in test_case.pics:
        # The '!' char before PICS definition, is how test case flag a PICS as negative
        if pics.startswith("!"):
            # Ignore ! char while adding the pics into disabled_pics structure
            disabled_pics.add(pics[1:])
        else:
            enabled_pics.add(pics)

    return enabled_pics, disabled_pics


def __process_platform_tests(applicable_tests_combined: set[str]) -> set[str]:
    """
    Process platform tests and add them to applicable tests

    Args:
        applicable_tests_combined: Current set of applicable test cases

    Returns:
        Updated set of applicable test cases
    """
    # TODO Need to fetch platform-test.json from repo
    # Issue: https://github.com/project-chip/certification-tool/issues/571
    platform_tests = __read_platform_test_cases("platform-test.json")
    logger.info(f"Listing platform-test.json test cases: {sorted(platform_tests)}")

    test_collections_copy = test_script_manager.test_collections.copy()

    all_tests = []
    for test_collection in test_collections_copy.values():
        for test_suite in test_collection.test_suites.values():
            for test_case in test_suite.test_cases.values():
                all_tests.append(test_case.metadata["title"])

    # Only add platform tests that don't already exist with any suffix
    for test in platform_tests:
        # Check if the test exists with any suffix in applicable_tests_combined
        test_exists = any(
            existing_test.startswith(f"{test} (")
            for existing_test in applicable_tests_combined
        )

        # Check if the test exists in all_tests
        matching_test = next(
            (existing_test for existing_test in all_tests if test in existing_test),
            None,
        )

        if not test_exists:
            if matching_test:
                applicable_tests_combined.add(matching_test)
            else:
                applicable_tests_combined.add(test)

    return applicable_tests_combined


def __process_platform_cert_derived(
    dmp_test_skip: list, applicable_tests_combined: set[str]
) -> set[str]:
    """
    Process platform certification derived test cases.

    Args:
        dmp_test_skip: List of test cases to skip
        applicable_tests_combined: Current set of applicable test cases

    Returns:
        Updated set of applicable test cases
    """
    # Create a new list with dmp_test_skip plus the same tests with
    # " (Semi-automated)" and " (Steps Disabled)" suffixes
    # These suffixes may be added during the test parsing process
    logger.info(f"Listing dmp_test_skip test cases: {sorted(dmp_test_skip)}")
    extended_skip_list = dmp_test_skip.copy()
    for test in dmp_test_skip:
        extended_skip_list.append(f"{test} (Semi-automated)")
        extended_skip_list.append(f"{test} (Steps Disabled)")

    # Make a copy of applicable test cases before removing for logging purposes
    applicable_tests_combined_original = applicable_tests_combined.copy()

    # Remove tests from the extended list from applicable_tests_combined
    applicable_tests_combined.difference_update(extended_skip_list)

    # Logging the removed test cases due to DMP file content
    removed_tests = applicable_tests_combined_original - applicable_tests_combined
    logger.info(f"Listing test cases removed due to dmp: {sorted(removed_tests)}")

    return applicable_tests_combined
