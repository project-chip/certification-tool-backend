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

from app import schemas
from app.schemas.test_harness_backend_version import TestHarnessBackendVersion
from app.version import version_information

router = APIRouter()


@router.get(
    "/version",
    response_model=schemas.TestHarnessBackendVersion,
    response_model_exclude_none=True,
)
def get_test_harness_backend_version() -> TestHarnessBackendVersion:
    """
    Retrieve version of the Test Engine.

    """
    return version_information
