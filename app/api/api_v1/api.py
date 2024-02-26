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
from fastapi import APIRouter

from app.api.api_v1.endpoints import (
    devices,
    operators,
    projects,
    test_collections,
    test_harness_backend_version,
    test_run_executions,
    utils,
)
from app.api.api_v1.sockets import web_sockets

api_router = APIRouter()
api_router.include_router(
    test_collections.router, prefix="/test_collections", tags=["test collections"]
)

api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(operators.router, prefix="/operators", tags=["operators"])
api_router.include_router(
    test_run_executions.router,
    prefix="/test_run_executions",
    tags=["test_run_executions"],
)

api_router.include_router(test_harness_backend_version.router, tags=["version"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])

# Websocket API:
api_router.include_router(web_sockets.router)
