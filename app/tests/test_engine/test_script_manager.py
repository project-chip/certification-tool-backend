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
import pytest

from app.schemas.test_selection import SelectedTests
from app.test_engine.test_script_manager import (
    TestCaseNotFound,
    TestCollectionNotFound,
    TestSuiteNotFound,
    test_script_manager,
)


@pytest.mark.asyncio
async def test_validate_test_selection_OK() -> None:
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    },
                    {
                        "public_id": "TestSuiteAsync",
                        "test_cases": [
                            {"public_id": "TCTRInstantPass", "iterations": 1},
                            {"public_id": "TCTRNeverEnding", "iterations": 1},
                        ],
                    },
                ],
            },
            {
                "public_id": "sample_tests",
                "test_suites": [
                    {
                        "public_id": "SampleTestSuite1",
                        "test_cases": [{"public_id": "TCSS1001", "iterations": 1}],
                    }
                ],
            },
        ]
    }

    test_script_manager.validate_test_selection(SelectedTests(**selected_tests))


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_collection() -> None:
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    },
                    {
                        "public_id": "TestSuiteAsync",
                        "test_cases": [
                            {"public_id": "TCTRInstantPass", "iterations": 1},
                            {"public_id": "TCTRNeverEnding", "iterations": 1},
                        ],
                    },
                ],
            },
            {
                "public_id": "invalid_name",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    }
                ],
            },
        ]
    }
    with pytest.raises(TestCollectionNotFound):
        test_script_manager.validate_test_selection(SelectedTests(**selected_tests))


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_suite() -> None:
    # Test non existing test
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    },
                    {
                        "public_id": "invalid_test_suite",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    },
                ],
            }
        ]
    }

    with pytest.raises(TestSuiteNotFound):
        test_script_manager.validate_test_selection(SelectedTests(**selected_tests))

    # Test existing test suite from other collection
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    },
                    {
                        "public_id": "TestSuiteAsync",
                        "test_cases": [
                            {"public_id": "TCTRInstantPass", "iterations": 1},
                            {"public_id": "TCTRNeverEnding", "iterations": 3},
                        ],
                    },
                ],
            },
            {
                "public_id": "sample_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1}
                        ],
                    }
                ],
            },
        ]
    }

    with pytest.raises(TestSuiteNotFound):
        test_script_manager.validate_test_selection(SelectedTests(**selected_tests))


@pytest.mark.asyncio
async def test_validate_test_selection_invalid_test_case() -> None:
    # Test non existing test
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteExpected",
                        "test_cases": [
                            {"public_id": "TCTRExpectedPass", "iterations": 1},
                            # Following test case is not in this collection
                            {"public_id": "invalid_test_case", "iterations": 1},
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(TestCaseNotFound):
        test_script_manager.validate_test_selection(SelectedTests(**selected_tests))

    # Test existing test case from other test suite
    selected_tests = {
        "collections": [
            {
                "public_id": "tool_unit_tests",
                "test_suites": [
                    {
                        "public_id": "TestSuiteAsync",
                        "test_cases": [
                            {"public_id": "TCTRInstantPass", "iterations": 1},
                            {"public_id": "TCTRNeverEnding", "iterations": 3},
                            # Following test case is not in this collection
                            {"public_id": "TCTRExpectedPass", "iterations": 1},
                        ],
                    }
                ],
            }
        ]
    }

    with pytest.raises(TestCaseNotFound):
        test_script_manager.validate_test_selection(SelectedTests(**selected_tests))
