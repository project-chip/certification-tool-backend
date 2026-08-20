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
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.schemas import TestCollections
from app.schemas.test_runner_status import TestRunnerState
from app.test_engine import TEST_ENGINE_BUSY_MESSAGE
from app.test_engine.test_runner import TestRunner
from app.test_engine.test_script_manager import test_script_manager

router = APIRouter()


@router.get("/", response_model=TestCollections)
def read_test_collections() -> Any:
    """
    Retrieve available test collections.
    """

    return {
        "test_collections": {
            k: v.as_dict() for k, v in test_script_manager.test_collections.items()
        }
    }


@router.post("/rescan", response_model=TestCollections)
async def rescan_test_collections() -> Any:
    """
    Re-run test collection discovery/registration in-process.

    This picks up newly added or edited side-loaded test scripts without
    requiring a backend restart. Returns the refreshed list of test
    collections.
    """
    if TestRunner().state != TestRunnerState.IDLE:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=TEST_ENGINE_BUSY_MESSAGE
        )

    try:
        await test_script_manager.rescan()
    except Exception as e:
        logger.error(f"Failed to rescan test collections: {e}")
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Failed to rescan test collections: {e}",
        )

    return {
        "test_collections": {
            k: v.as_dict() for k, v in test_script_manager.test_collections.items()
        }
    }
