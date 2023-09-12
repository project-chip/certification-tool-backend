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
from typing import Optional
from unittest.mock import MagicMock

from docker.models.containers import Container

FAKE_ID = "ThisIsAFakeIdForADockerContainer"


def make_fake_container(
    attrs: Optional[dict] = {"Id": FAKE_ID}, mock_api_config: Optional[dict] = None
) -> Container:
    container = Container(attrs=attrs)

    if mock_api_config:
        container.client = MagicMock()
        container.client.api = MagicMock()
        container.client.api.configure_mock(**mock_api_config)

    return container
