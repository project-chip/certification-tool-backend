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
from http import HTTPStatus

from fastapi.testclient import TestClient

from app.core.config import settings


def test_read_available_test_collections(client: TestClient) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/test_collections",
    )
    assert response.status_code == HTTPStatus.OK

    content = response.json()
    assert "test_collections" in content
    test_collections = content["test_collections"]
    assert "tool_unit_tests" in test_collections
    tool_unit_tests = test_collections["tool_unit_tests"]
    assert "test_suites" in tool_unit_tests
    test_suites = tool_unit_tests["test_suites"]
    assert "TestSuiteExpected" in test_suites
    test_suite_expected = test_suites["TestSuiteExpected"]
    assert "metadata" in test_suite_expected
