#
# Copyright (c) 2026 Project CHIP Authors
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
from unittest import mock

import pytest

from app.test_engine.test_log_handler import TestLogHandler


@pytest.fixture
def broadcast_mock() -> Generator[mock.AsyncMock, None, None]:
    """Patch the websocket broadcast the test engine's UI observer sends with."""
    with mock.patch(
        "app.test_engine.test_ui_observer.socket_connection_manager.broadcast",
        new_callable=mock.AsyncMock,
    ) as broadcast_mock:
        yield broadcast_mock


@pytest.fixture
def finish_spy() -> Generator[mock.AsyncMock, None, None]:
    """Spy on TestLogHandler.finish(), still running the real method."""
    with mock.patch.object(
        TestLogHandler, "finish", autospec=True, side_effect=TestLogHandler.finish
    ) as finish_spy:
        yield finish_spy
