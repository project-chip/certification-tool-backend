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
from pathlib import Path
from typing import Dict, Tuple, Optional

from loguru import logger

from app.schemas.pics import PICS, PICSApplicableTestCases
from app.test_engine.models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
)
from app.test_engine.test_script_manager import test_script_manager
from test_collections.matter.sdk_tests.support.performance_tests.utils import (
    STRESS_TEST_COLLECTION,
)

PICS_PLAT_CERT = "PLAT.CERT"
PICS_PLAT_CERT_DERIVED = "PLAT.CERT.TESTS.DONE"

PLATFORM_TESTS_FILE_NAME = "generated-platform-cert-test-list.json"


class PlatformTestError(Exception):
    """Base exception for platform test errors"""

    pass


class FileNotFoundError(PlatformTestError):
    """Exception raised when test file is not found"""

    pass


class InvalidJSONError(PlatformTestError):
    """Exception raised when JSON is invalid"""

    pass


def __read_platform_test_cases(platform_json_filename: str) -> set[str]:
    """
    Read platform test cases from a JSON file.

    Args:
        platform_json_filename: Path to the JSON file containing platform test cases

    Returns:
        Set of test case IDs

    Raises:
        FileNotFoundError: If the specified file doesn't exist
        InvalidJSONError: If the JSON format is invalid
    """
    try:
        platform_tests_file = (
            Path(__file__).parent.parent
            / "test_collections"
            / "matter"
            / "platform-cert"
            / platform_json_filename
        )
        with open(platform_tests_file, "r") as file:
            data = json.load(file)
            return set(data.get("PlatformTestCasesToRun", []))
    except FileNotFoundError:
        raise FileNotFoundError(f"File {platform_tests_file} not found")
    except json.JSONDecodeError:
        raise InvalidJSONError(f"Invalid JSON format in {platform_tests_file}")


def applicable_test_cases_set(
    pics: PICS, dmp_test_skip: list
) -> PICSApplicableTestCases:
    """Returns the applicable test cases for this project given the set of PICS"

    Args:
        pics (PICS): set of pics to map against

    Returns:
        PICSApplicableTestCases: List of test cases that are applicable
          for this Project

    Raises:
        PlatformTestError: If both PICS_PLAT_CERT and PICS_PLAT_CERT_DERIVED are enabled
    """
    applicable_tests: set = set()
    applicable_tests_combined: set = set()

    if not pics.clusters:
        # If the user has not uploaded any PICS
        # i.e, there are no PICS associated with the project then return empty set
        logger.debug(f"Applicable test cases: {applicable_tests}")
        return PICSApplicableTestCases(test_cases=applicable_tests)

    # Getting a copy of Test Collections Dict so we may add/remove items safely
    test_collections_copy = test_script_manager.test_collections.copy()
    enabled_pics = set([item.number for item in pics.all_enabled_items()])

    # Check if both PICS_PLAT_CERT and PICS_PLAT_CERT_DERIVED are enabled
    if PICS_PLAT_CERT in enabled_pics and PICS_PLAT_CERT_DERIVED in enabled_pics:
        raise PlatformTestError(
            "Invalid configuration: PICS_PLAT_CERT and PICS_PLAT_CERT_DERIVED are "
            "mutually exclusive. Please enable only one of them"
        )

    #  If PICS_PLAT_CERT is enabled, process platform tests
    if PICS_PLAT_CERT in enabled_pics:
        __process_platform_tests(
            applicable_tests_combined, test_collections_copy, enabled_pics
        )
    else:
        # If PICS_PLAT_CERT is not enabled, process mandatory and remaining tests
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

        # Check ff PICS_PLAT_CERT_DERIVED is enabled, skip the tests in the DMP file
        if PICS_PLAT_CERT_DERIVED in enabled_pics:
            __process_platform_cert_derived(dmp_test_skip, applicable_tests_combined)

    logger.debug(f"Applicable test cases: {applicable_tests_combined}")
    return PICSApplicableTestCases(test_cases=list(applicable_tests_combined))


def __applicable_test_cases(
    test_collections: Dict[str, TestCollectionDeclaration],
    enabled_pics: set[str],
    mandatory: bool,
    tests_to_consider: Optional[set[str]] = None,
) -> set:
    """
    Get applicable test cases based on PICS configuration and optional test list.

    Args:
        test_collections: Dictionary of test collections
        enabled_pics: Set of enabled PICS
        mandatory: Whether to consider mandatory tests
        tests_to_consider: Optional list of test IDs to consider. 
                           If None or empty, all tests are considered.

    Returns:
        Set of applicable test case IDs
    """
    applicable_tests: set = set()

    # The 'Performance Tests' Collection should not be considered for the PICS tests.
    test_collections.pop(STRESS_TEST_COLLECTION, None)

    for test_collection in test_collections.values():
        if test_collection.mandatory == mandatory:
            for test_suite in test_collection.test_suites.values():
                for test_case in test_suite.test_cases.values():
                    # Skip if test is not in the list of tests to consider
                    if (
                        tests_to_consider
                        and test_case.metadata["title"] not in tests_to_consider
                    ):
                        continue

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


def __process_platform_tests(
    applicable_tests_combined: set[str],
    test_collections_copy: Dict[str, TestCollectionDeclaration],
    enabled_pics: set[str],
) -> None:
    """
    Process platform tests and add them to applicable tests

    Args:
        applicable_tests_combined: Current set of applicable test cases
        test_collections_copy: Dictionary of test collections
        enabled_pics: Set of enabled PICS
    """
    # Read platform test list file
    platform_tests = __read_platform_test_cases(PLATFORM_TESTS_FILE_NAME)
    logger.info(
        f"Listing {PLATFORM_TESTS_FILE_NAME} test cases: {sorted(platform_tests)}"
    )

    # Get applicable tests from collections based on platform tests
    applicable_tests_combined.update(
        __applicable_test_cases(
            test_collections_copy, enabled_pics, True, platform_tests
        )
    )

    # Include each platform test along with some suffixes: 'Semi-automated'
    # and 'Steps Disabled'
    for test in platform_tests:
        applicable_tests_combined.add(test)
        applicable_tests_combined.add(f"{test} (Semi-automated)")
        applicable_tests_combined.add(f"{test} (Steps Disabled)")


def __process_platform_cert_derived(
    dmp_test_skip: list, applicable_tests_combined: set[str]
) -> None:
    """
    Process platform certification derived test cases.

    Args:
        dmp_test_skip: List of test cases to skip
        applicable_tests_combined: Current set of applicable test cases
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
