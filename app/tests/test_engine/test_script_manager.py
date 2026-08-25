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
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.test_engine.test_script_manager import (
    TestCaseNotFound,
    TestCollectionNotFound,
    TestSuiteNotFound,
    test_script_manager,
)


@pytest.fixture
def restore_test_collections() -> Generator:
    """Save and restore test_script_manager.test_collections around a test.

    test_script_manager is a singleton shared across the test session, so
    tests that call rescan() must not leak mutated state to other tests.
    """
    saved_collections = test_script_manager.test_collections
    yield
    test_script_manager.test_collections = saved_collections


@pytest.mark.asyncio
async def test_validate_test_selection_OK() -> None:
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
            "TestSuiteAsync": {"TCTRInstantPass": 1, "TCTRNeverEnding": 3},
        },
        "sample_tests": {"SampleTestSuite1": {"TCSS1001": 1}},
    }

    test_script_manager.validate_test_selection(selected_tests)


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_collection() -> None:
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
            "TestSuiteAsync": {"TCTRInstantPass": 1, "TCTRNeverEnding": 3},
        },
        # Following test collection does not exist
        "invalid_name": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
        },
    }
    with pytest.raises(TestCollectionNotFound):
        test_script_manager.validate_test_selection(selected_tests)


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_suite() -> None:
    # Test non existing test
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
            # Following test suite does not exist
            "invalid_test_suite": {"TCTRExpectedPass": 1},
        }
    }
    with pytest.raises(TestSuiteNotFound):
        test_script_manager.validate_test_selection(selected_tests)

    # Test existing test suite from other collection
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
            "TestSuiteAsync": {"TCTRInstantPass": 1, "TCTRNeverEnding": 3},
        },
        "sample_tests": {
            # Following test suite is not in this collection
            "TestSuiteExpected": {"TCTRExpectedPass": 1},
        },
    }
    with pytest.raises(TestSuiteNotFound):
        test_script_manager.validate_test_selection(selected_tests)


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_case() -> None:
    # Test non existing test
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteExpected": {
                "TCTRExpectedPass": 1,
                # Following test case does not exist
                "invalid_test_case": 1,
            },
        }
    }
    with pytest.raises(TestCaseNotFound):
        test_script_manager.validate_test_selection(selected_tests)

    # Test existing test case from other test suite
    selected_tests = {
        "tool_unit_tests": {
            "TestSuiteAsync": {
                "TCTRInstantPass": 1,
                "TCTRNeverEnding": 3,
                # Following test case is not in this collection
                "TCTRExpectedPass": 1,
            },
        }
    }
    with pytest.raises(TestCaseNotFound):
        test_script_manager.validate_test_selection(selected_tests)


@pytest.mark.asyncio
async def test_rescan_refreshes_test_collections(
    restore_test_collections: None,
) -> None:
    expected_collections = {"tool_unit_tests": MagicMock()}

    with patch(
        "test_collections.matter.sdk_tests.support.python_testing."
        "initialize_python_tests",
        new_callable=AsyncMock,
    ) as mock_init, patch.object(
        test_script_manager,
        "_discover_test_collections",
        return_value=expected_collections,
    ):
        await test_script_manager.rescan()

    mock_init.assert_awaited_once()
    assert test_script_manager.test_collections == expected_collections
    assert test_script_manager._python_tests_initialized is True


@pytest.mark.asyncio
async def test_rescan_keeps_previous_collections_on_failure(
    restore_test_collections: None,
) -> None:
    previous_collections = {"tool_unit_tests": MagicMock()}

    with patch.object(
        test_script_manager, "test_collections", previous_collections
    ), patch(
        "test_collections.matter.sdk_tests.support.python_testing."
        "initialize_python_tests",
        new_callable=AsyncMock,
        side_effect=RuntimeError("side-loaded script is invalid"),
    ):
        with pytest.raises(RuntimeError, match="side-loaded script is invalid"):
            await test_script_manager.rescan()

        # Previously loaded test collections must remain available so the
        # backend keeps working without needing a restart.
        assert test_script_manager.test_collections == previous_collections


@pytest.mark.asyncio
async def test_rescan_handles_missing_python_testing_module(
    restore_test_collections: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the python_testing package doesn't expose initialize_python_tests
    (e.g. DRY_RUN mode), rescan() should not raise: non-Python collections
    are still discovered."""
    expected_collections = {"tool_unit_tests": MagicMock()}

    import test_collections.matter.sdk_tests.support.python_testing as python_testing

    monkeypatch.delattr(python_testing, "initialize_python_tests")

    with patch.object(
        test_script_manager,
        "_discover_test_collections",
        return_value=expected_collections,
    ):
        await test_script_manager.rescan()

    assert test_script_manager.test_collections == expected_collections


@pytest.mark.asyncio
async def test_rescan_keeps_previous_collections_on_import_error(
    restore_test_collections: None,
) -> None:
    """An ImportError raised while *running* initialize_python_tests() (e.g.
    a bad import inside a side-loaded script) must be treated as a rescan
    failure, not mistaken for the python_testing-module-not-available case:
    the previous test collections must be restored and the error re-raised.
    """
    previous_collections = {"tool_unit_tests": MagicMock()}

    with patch.object(
        test_script_manager, "test_collections", previous_collections
    ), patch(
        "test_collections.matter.sdk_tests.support.python_testing."
        "initialize_python_tests",
        new_callable=AsyncMock,
        side_effect=ImportError("bad import in side-loaded script"),
    ):
        with pytest.raises(ImportError, match="bad import in side-loaded script"):
            await test_script_manager.rescan()

        assert test_script_manager.test_collections == previous_collections
