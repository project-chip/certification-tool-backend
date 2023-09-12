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


def test_test_harness_backend_version(client: TestClient) -> None:
    """Get Test Runner status when test runner is idle."""
    response = client.get(f"{settings.API_V1_STR}/version")

    assert response.status_code == HTTPStatus.OK
    content = response.json()
    assert content["version"] is not None
    assert content["sha"] is not None
