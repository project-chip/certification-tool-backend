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
"""
Test harness app implementing the server endpoints required for
fastapi_client testing.
"""
import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRoute

from .routers import auth_router, client_router

app = FastAPI(debug=True)


@app.on_event("startup")
async def startup() -> None:
    """
    Use the operation names as operation_id. The generated names are not friendly.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


app.include_router(auth_router(), tags=["auth"])
app.include_router(client_router(), tags=["client"])


def main() -> None:
    """ Kick off uvicorn on port 8000"""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
