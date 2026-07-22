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
"""Gunicorn worker class with a longer websocket ping timeout.

Uploading a large manual test log (see GitHub issue #1062) can keep the event
loop busy for an extended period (each uploaded line is turned into a log
entry that gets broadcast over the same main websocket and persisted to the
DB). With uvicorn's default ``ws_ping_timeout`` (20s), the websocket's
keepalive ping/pong can't be serviced in time, causing the connection to be
dropped mid-upload with `ConnectionClosedError: no close frame received or
sent`.

This mirrors the ``--ws-ping-timeout 60`` flag already used by the dev-only
``gunicorn/start-reload.sh`` script, so production gets the same tolerance.
"""
from uvicorn.workers import UvicornWorker

WS_PING_TIMEOUT_S = 60


class ExtendedTimeoutUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "ws_ping_timeout": WS_PING_TIMEOUT_S,
    }
