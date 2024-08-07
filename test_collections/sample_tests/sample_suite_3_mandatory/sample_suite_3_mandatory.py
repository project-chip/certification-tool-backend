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
from app.test_engine.logger import test_engine_logger as logger
from app.test_engine.models import TestSuite


class SampleTestSuite3Mandatory(TestSuite):
    metadata = {
        "public_id": "SampleTestSuite3Mandatory",
        "version": "7.6.5",
        "title": "This is Test Suite 3 Mandatory with version 7.6.5",
        "description": "This is Test Suite 3 Mandatory, It is a mandatory suite",
        "mandatory": True,  # type: ignore
    }

    async def setup(self) -> None:
        logger.info("This is a test setup")

    async def cleanup(self) -> None:
        logger.info("This is a test cleanup")
