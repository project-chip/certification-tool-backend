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
# type: ignore
# Ignore mypy type check for this file
# flake8: noqa
import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.pics_applicable_test_cases import (
    PICS_PLAT_CERT,
    PICS_PLAT_CERT_DERIVED,
    FileNotFoundError,
    InvalidJSONError,
    PlatformTestError,
    applicable_test_cases_set,
)
from app.schemas.pics import PICS, PICSCluster, PICSItem
from app.tests.utils.test_pics_data import create_random_pics

# Mock platform test data
MOCK_PLATFORM_TEST_DATA = {
    "PlatformTestCasesToRun": [
        "TC-PLAT-1.1",
        "TC-PLAT-1.2",
        "TC-PLAT-2.1",
        "TC-PLAT-3.1",
        "TC-PLAT-4.1",
    ]
}


def test_applicable_test_cases_set() -> None:
    pics = create_random_pics()

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Unit test case (TCPics) has AB.C and AB.C.0004 PICs enabled.
    # create_random_pics creates pics with these values set.
    # Applicable test cases should always be at least 1.
    assert len(applicable_test_cases.test_cases) > 0


def test_applicable_test_cases_set_with_no_pics() -> None:
    # create empty PICS list
    pics = PICS()

    applicable_test_cases = applicable_test_cases_set(pics, [])

    assert len(applicable_test_cases.test_cases) == 0


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data=json.dumps(MOCK_PLATFORM_TEST_DATA),
)
@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_platform_cert(mock_manager, mock_file) -> None:
    # Create PICS with platform certification enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    pics.clusters["Platform"] = cluster

    # Create a mock test collection with platform tests
    mock_collection = MagicMock()
    mock_collection.mandatory = True

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case for a platform test
    mock_test_case = MagicMock()
    mock_test_case.pics = {"AB.C"}  # This PIC is enabled in create_random_pics
    mock_test_case.metadata = {
        "title": "TC-PLAT-1.1"
    }  # This matches one of the platform tests

    # Create a mock test case for a platform test
    mock_test_case2 = MagicMock()
    mock_test_case2.metadata = {
        "title": "TC-PLAT-1.2"
    }  # This matches one of the platform tests

    # Set up the mock objects
    mock_suite.test_cases = {
        "TC-PLAT-1.1": mock_test_case,
        "TC-PLAT-1.2": mock_test_case2,
    }
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the platform test file was opened
    mock_file.assert_called_once_with(
        Path(
            "test_collections/matter/platform-cert/generated-platform-cert-test-list.json"
        ).resolve(),
        "r",
    )

    # Check TC-PLAT-1.1 is not listed in applicable_test_cases since the PICS does
    # not match
    assert "TC-PLAT-1.1" not in applicable_test_cases.test_cases
    # Check TC-PLAT-1.2 is listed in applicable_test_cases since this test does
    # not define PICS
    assert "TC-PLAT-1.2" in applicable_test_cases.test_cases


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data=json.dumps(MOCK_PLATFORM_TEST_DATA),
)
@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_platform_cert_with_pics(
    mock_manager, mock_file
) -> None:
    # Create PICS with platform certification enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    cluster.items["AB.C"] = PICSItem(number="AB.C", enabled=True)
    pics.clusters["Platform"] = cluster

    # Create a mock test collection with platform tests
    mock_collection = MagicMock()
    mock_collection.mandatory = True

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case for a platform test
    mock_test_case = MagicMock()
    mock_test_case.pics = {"AB.C"}  # PICS required by this mock test case
    mock_test_case.metadata = {
        "title": "TC-PLAT-1.1"
    }  # This matches one of the platform tests

    # Create a mock test case for a platform test
    mock_test_case2 = MagicMock()
    mock_test_case2.metadata = {
        "title": "TC-PLAT-1.2"
    }  # This matches one of the platform tests

    # Set up the mock objects
    mock_suite.test_cases = {
        "TC-PLAT-1.1": mock_test_case,
        "TC-PLAT-1.2": mock_test_case2,
    }
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the platform test file was opened
    mock_file.assert_called_once_with(
        Path(
            "test_collections/matter/platform-cert/generated-platform-cert-test-list.json"
        ).resolve(),
        "r",
    )

    # Check both tests are listed since PICS matches
    assert "TC-PLAT-1.1" in applicable_test_cases.test_cases
    assert "TC-PLAT-1.2" in applicable_test_cases.test_cases


@patch("builtins.open")
def test_applicable_test_cases_set_with_platform_cert_file_not_found(mock_file) -> None:
    # Create PICS with platform certification enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    pics.clusters["Platform"] = cluster

    # Mock file not found error
    mock_file.side_effect = FileNotFoundError()

    # Verify that FileNotFoundError is raised
    with pytest.raises(FileNotFoundError):
        applicable_test_cases_set(pics, [])


@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
def test_applicable_test_cases_set_with_platform_cert_invalid_json(mock_file) -> None:
    # Create PICS with platform certification enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    pics.clusters["Platform"] = cluster

    # Verify that InvalidJSONError is raised
    with pytest.raises(InvalidJSONError):
        applicable_test_cases_set(pics, [])


def test_applicable_test_cases_set_with_platform_cert_derived_enabled() -> None:
    # Create PICS with platform certification derived enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT_DERIVED] = PICSItem(
        number=PICS_PLAT_CERT_DERIVED, enabled=True
    )
    pics.clusters["Platform"] = cluster

    # Create a set of applicable test cases
    dmp_test_skip = ["DMP-TC-1", "DMP-TC-2"]

    applicable_test_cases = applicable_test_cases_set(pics, dmp_test_skip)

    # Verify that the DMP test cases were excluded from the result
    assert "DMP-TC-1" not in applicable_test_cases.test_cases
    assert "DMP-TC-2" not in applicable_test_cases.test_cases


def test_applicable_test_cases_set_with_platform_cert_derived_enabled_remove_test() -> (
    None
):
    # Create PICS with platform certification derived enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT_DERIVED] = PICSItem(
        number=PICS_PLAT_CERT_DERIVED, enabled=True
    )
    pics.clusters["Platform"] = cluster

    # Create a set of applicable test cases
    dmp_test_skip = ["TC-PLAT-1.1", "TC-PLAT-1.2"]

    applicable_test_cases = applicable_test_cases_set(pics, dmp_test_skip)

    # Verify that the DMP test cases were excluded from the result
    assert "TC-PLAT-1.1" not in applicable_test_cases.test_cases
    assert "TC-PLAT-1.2" not in applicable_test_cases.test_cases


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data=json.dumps(MOCK_PLATFORM_TEST_DATA),
)
def test_applicable_test_cases_set_with_platform_cert_enabled(mock_file) -> None:
    # Create PICS with platform certification enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    pics.clusters["Platform"] = cluster

    # Create a set of applicable test cases
    dmp_test_skip = ["DMP-TC-1", "DMP-TC-2"]

    applicable_test_cases = applicable_test_cases_set(pics, dmp_test_skip)

    # Verify that the platform test file was opened
    mock_file.assert_called_once_with(
        Path(
            "test_collections/matter/platform-cert/generated-platform-cert-test-list.json"
        ).resolve(),
        "r",
    )

    # Verify that the DMP test cases were excluded from the result
    assert "DMP-TC-1" not in applicable_test_cases.test_cases
    assert "DMP-TC-2" not in applicable_test_cases.test_cases


def test_applicable_test_cases_set_with_both_platform_certs_enabled() -> None:
    # Create PICS with both platform certifications enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT] = PICSItem(number=PICS_PLAT_CERT, enabled=True)
    cluster.items[PICS_PLAT_CERT_DERIVED] = PICSItem(
        number=PICS_PLAT_CERT_DERIVED, enabled=True
    )
    pics.clusters["Platform"] = cluster

    # Verify that an error is raised
    with pytest.raises(PlatformTestError):
        applicable_test_cases_set(pics, [])


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_mandatory_tests(mock_manager) -> None:
    # Create PICS with mandatory test PICs
    pics = create_random_pics()

    # Create a mock test collection with mandatory tests
    mock_collection = MagicMock()
    mock_collection.mandatory = True

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case
    mock_test_case = MagicMock()
    mock_test_case.pics = {"AB.C"}  # This PIC is enabled in create_random_pics
    mock_test_case.metadata = {"title": "Mandatory-TC-1"}

    # Set up the mock objects
    mock_suite.test_cases = {"Mandatory-TC-1": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the mandatory test case was included in the result
    assert "Mandatory-TC-1" in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_includes_mandatory_tests_without_pics(
    mock_manager,
) -> None:
    # Create PICS without any PICs relevant to the test case
    pics = create_random_pics()

    # Create a mock mandatory test collection with a test case without PICS
    mock_collection = MagicMock()
    mock_collection.mandatory = True

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case without declared PICS
    mock_test_case = MagicMock()
    mock_test_case.pics = set()
    mock_test_case.metadata = {"title": "Mandatory-TC-No-PICS"}

    # Set up the mock objects
    mock_suite.test_cases = {"Mandatory-TC-No-PICS": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Mandatory test cases without declared PICS must always run
    assert "Mandatory-TC-No-PICS" in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_excludes_non_mandatory_tests_without_pics(
    mock_manager,
) -> None:
    # Create PICS without any PICs relevant to the test case
    pics = create_random_pics()

    # Create a mock non-mandatory test collection with a test case without PICS
    mock_collection = MagicMock()
    mock_collection.mandatory = False

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case without declared PICS
    mock_test_case = MagicMock()
    mock_test_case.pics = set()
    mock_test_case.metadata = {"title": "TC-No-PICS"}

    # Set up the mock objects
    mock_suite.test_cases = {"TC-No-PICS": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # A non-mandatory test case without declared PICS cannot be matched
    # against the project PICS, so it must not be pre-selected
    assert "TC-No-PICS" not in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_selects_only_uploaded_cluster_tests(
    mock_manager,
) -> None:
    # PICS uploaded for a single cluster (FAN.S enabled), nothing else
    pics = PICS()
    cluster = PICSCluster(name="Fan Control")
    cluster.items["FAN.S"] = PICSItem(number="FAN.S", enabled=True)
    pics.clusters["Fan Control"] = cluster

    # Non-mandatory collection with three test cases:
    # - test for the uploaded cluster
    fan_test_case = MagicMock()
    fan_test_case.pics = {"FAN.S"}
    fan_test_case.metadata = {"title": "TC-Fan"}

    # - test for a cluster absent from the uploaded PICS
    tstat_test_case = MagicMock()
    tstat_test_case.pics = {"TSTAT.S"}
    tstat_test_case.metadata = {"title": "TC-Thermostat"}

    # - test without declared PICS
    no_pics_test_case = MagicMock()
    no_pics_test_case.pics = set()
    no_pics_test_case.metadata = {"title": "TC-Switch"}

    non_mandatory_suite = MagicMock()
    non_mandatory_suite.test_cases = {
        "TC-Fan": fan_test_case,
        "TC-Thermostat": tstat_test_case,
        "TC-Switch": no_pics_test_case,
    }
    non_mandatory_collection = MagicMock()
    non_mandatory_collection.mandatory = False
    non_mandatory_collection.test_suites = {"TestSuite": non_mandatory_suite}

    # Mandatory collection with a protocol test without declared PICS
    mandatory_test_case = MagicMock()
    mandatory_test_case.pics = set()
    mandatory_test_case.metadata = {"title": "TC-IDM"}

    mandatory_suite = MagicMock()
    mandatory_suite.test_cases = {"TC-IDM": mandatory_test_case}
    mandatory_collection = MagicMock()
    mandatory_collection.mandatory = True
    mandatory_collection.test_suites = {"TestSuite": mandatory_suite}

    mock_manager.test_collections = {
        "NonMandatoryCollection": non_mandatory_collection,
        "MandatoryCollection": mandatory_collection,
    }

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Only the uploaded cluster's test and the mandatory test are applicable:
    # the absent cluster's test fails the PICS match and the test without
    # declared PICS in a non-mandatory collection is not pre-selected
    assert set(applicable_test_cases.test_cases) == {"TC-Fan", "TC-IDM"}


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_dmp_cert_test_removed(mock_manager) -> None:
    # Create PICS with mandatory test PICs
    pics = create_random_pics()

    # Create a mock test collection with mandatory tests
    mock_collection = MagicMock()
    mock_collection.mandatory = False

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case
    mock_test_case = MagicMock()
    mock_test_case.pics = {"AB.C"}  # This PIC is enabled in create_random_pics
    mock_test_case.metadata = {"title": "TC-Any"}

    # Set up the mock objects
    mock_suite.test_cases = {"TC-Any": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the test case was included in the result, but later when
    # TC-Any is listed in dmp_test_skip the test should not be listed
    assert "TC-Any" in applicable_test_cases.test_cases

    # # Create PICS with platform certification derived enabled
    # pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT_DERIVED] = PICSItem(
        number=PICS_PLAT_CERT_DERIVED, enabled=True
    )
    pics.clusters["Platform"] = cluster

    # Create a set of applicable test cases
    dmp_test_skip = ["TC-Any"]

    applicable_test_cases = applicable_test_cases_set(pics, dmp_test_skip)

    # # Verify that the DMP test cases were excluded from the result
    assert "TC-Any" not in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_disabled_pics(mock_manager) -> None:
    # Create PICS with a disabled PIC
    pics = PICS()
    cluster = PICSCluster(name="On/Off")
    cluster.items["AB.C"] = PICSItem(number="AB.C", enabled=False)
    pics.clusters["On/Off"] = cluster

    # Create a mock test collection
    mock_collection = MagicMock()
    mock_collection.mandatory = False

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case that requires the disabled PIC
    mock_test_case = MagicMock()
    mock_test_case.pics = {"AB.C"}  # This PIC is disabled
    mock_test_case.metadata = {"title": "TC-1"}

    # Set up the mock objects
    mock_suite.test_cases = {"TC-1": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the test case was not included in the result
    assert "TC-1" not in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.test_script_manager")
def test_applicable_test_cases_set_with_negative_pics(mock_manager) -> None:
    # Create PICS with a PIC that should be disabled
    pics = PICS()
    cluster = PICSCluster(name="On/Off")
    cluster.items["AB.C"] = PICSItem(number="AB.C", enabled=True)
    pics.clusters["On/Off"] = cluster

    # Create a mock test collection
    mock_collection = MagicMock()
    mock_collection.mandatory = False

    # Create a mock test suite
    mock_suite = MagicMock()

    # Create a mock test case that requires AB.C to be disabled
    mock_test_case = MagicMock()
    mock_test_case.pics = {"!AB.C"}  # This PIC should be disabled
    mock_test_case.metadata = {"title": "TC-1"}

    # Set up the mock objects
    mock_suite.test_cases = {"TC-1": mock_test_case}
    mock_collection.test_suites = {"TestSuite": mock_suite}
    mock_manager.test_collections = {"TestCollection": mock_collection}

    applicable_test_cases = applicable_test_cases_set(pics, [])

    # Verify that the test case was not included in the result
    assert "TC-1" not in applicable_test_cases.test_cases


@patch("app.pics_applicable_test_cases.__applicable_test_cases")
def test_applicable_test_cases_set_with_mocked_internal_calls(
    mock_applicable_test_cases,
) -> None:
    # Create PICS with platform certification derived enabled
    pics = PICS()
    cluster = PICSCluster(name="Platform")
    cluster.items[PICS_PLAT_CERT_DERIVED] = PICSItem(
        number=PICS_PLAT_CERT_DERIVED, enabled=True
    )
    pics.clusters["Platform"] = cluster

    # Mock the internal __applicable_test_cases function to return specific test cases
    # First call is for mandatory tests, second call is for non-mandatory tests
    mock_applicable_test_cases.side_effect = [
        {"TC-MANDATORY-1", "TC-MANDATORY-2", "TC-SKIP-1"},  # Mandatory tests
        {"TC-OPTIONAL-1", "TC-OPTIONAL-2", "TC-SKIP-2"},  # Optional tests
    ]

    # Create a set of applicable test cases with some that should be skipped
    dmp_test_skip = ["TC-SKIP-1", "TC-SKIP-2"]

    applicable_test_cases = applicable_test_cases_set(pics, dmp_test_skip)

    # Verify that the mock was called twice (once for mandatory, once for optional)
    assert mock_applicable_test_cases.call_count == 2

    # Verify that the test cases in dmp_test_skip were excluded from the result
    assert "TC-SKIP-1" not in applicable_test_cases.test_cases
    assert "TC-SKIP-2" not in applicable_test_cases.test_cases

    # Verify that other test cases were included
    assert "TC-MANDATORY-1" in applicable_test_cases.test_cases
    assert "TC-MANDATORY-2" in applicable_test_cases.test_cases
    assert "TC-OPTIONAL-1" in applicable_test_cases.test_cases
    assert "TC-OPTIONAL-2" in applicable_test_cases.test_cases
