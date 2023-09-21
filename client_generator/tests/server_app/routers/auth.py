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
Test oauth apis
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED


class TokenSuccessResponse(BaseModel):
    """
    Copied from the test client. Required as we delete the test client & re-create it
    from this code before the test run.
    """

    access_token: str
    token_type: str
    expires_in: Optional[int]
    refresh_token: Optional[str]
    scope: Optional[str]


def auth_router() -> APIRouter:
    """
    Creates & returns the router for auth testing endpoints
    """
    router = APIRouter()
    reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/token")

    @router.get("/")
    def access(token: str = Depends(reusable_oauth2)) -> JSONResponse:
        if token != "access_token":
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authorized")

        return JSONResponse(content={"result": "success"})

    @router.post("/token")
    def get_tokens(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenSuccessResponse:
        if form_data.username == "username" and form_data.password == "password":
            return TokenSuccessResponse(access_token="access_token", token_type="bearer")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Not authorized")

    return router
