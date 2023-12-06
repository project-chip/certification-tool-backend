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
from enum import Enum
from queue import Empty, Queue
from typing import Any, Optional, Union

from matter_yamltests.hooks import TestRunnerHooks
from pydantic import BaseModel


class SDKPythonTestResultEnum(str, Enum):
    START = "start"
    STOP = "stop"
    TEST_START = "test_start"
    TEST_STOP = "test_stop"
    STEP_SKIPPED = "step_skipped"
    STEP_START = "step_start"
    STEP_SUCCESS = "step_success"
    STEP_FAILURE = "step_failure"
    STEP_UNKNOWN = "step_unknown"
    STEP_MANUAL = "step_manual"


class SDKPythonTestResult(BaseModel):
    type: SDKPythonTestResultEnum
    count: Optional[int]
    duration: Optional[str]
    name: Optional[str]
    filename: Optional[str]
    exception: Any
    expression: Optional[str]
    logger: Any
    logs: Any
    request: Any
    received: Any


class SDKPythonTestRunnerHooks(TestRunnerHooks):
    finished = False
    results: Queue

    def __init__(self) -> None:
        SDKPythonTestRunnerHooks.finished = False
        SDKPythonTestRunnerHooks.results = Queue()

    def update_test(self) -> Union[dict, None]:
        try:
            result = self.results.get(block=False)
            return result
        except Empty:
            return None

    def is_finished(self) -> bool:
        return SDKPythonTestRunnerHooks.finished

    def start(self, count: int) -> None:
        self.results.put(
            SDKPythonTestResult(type=SDKPythonTestResultEnum.START, count=count)
        )

    def stop(self, duration: int) -> None:
        self.results.put(
            SDKPythonTestResult(type=SDKPythonTestResultEnum.STOP, duration=duration)
        )
        SDKPythonTestRunnerHooks.finished = True

    def test_start(self, filename: str, name: str, count: int) -> None:
        self.results.put(
            SDKPythonTestResult(
                type=SDKPythonTestResultEnum.TEST_START,
                filename=filename,
                name=name,
                count=count,
            )
        )

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.results.put(
            SDKPythonTestResult(
                type=SDKPythonTestResultEnum.TEST_STOP,
                exception=exception,
                duration=duration,
            )
        )

    def step_skipped(self, name: str, expression: str) -> None:
        self.results.put(
            SDKPythonTestResult(
                type=SDKPythonTestResultEnum.STEP_SKIPPED, expression=expression
            )
        )

    def step_start(self, name: str) -> None:
        self.results.put(
            SDKPythonTestResult(type=SDKPythonTestResultEnum.STEP_START, name=name)
        )

    def step_success(self, logger: Any, logs: Any, duration: int, request: Any) -> None:
        self.results.put(
            SDKPythonTestResult(
                type=SDKPythonTestResultEnum.STEP_SUCCESS,
                logger=logger,
                logs=logs,
                duration=duration,
                request=request,
            )
        )

    def step_failure(
        self, logger: Any, logs: Any, duration: int, request: Any, received: Any
    ) -> None:
        self.results.put(
            SDKPythonTestResult(
                type=SDKPythonTestResultEnum.STEP_FAILURE,
                logger=logger,
                logs=logs,
                duration=duration,
                request=request,
                received=received,
            )
        )

    def step_unknown(self) -> None:
        self.results.put(SDKPythonTestResult(type=SDKPythonTestResultEnum.STEP_UNKNOWN))

    def step_manual(self) -> None:
        self.results.put(SDKPythonTestResult(type=SDKPythonTestResultEnum.STEP_MANUAL))

    def step_start_list(self) -> None:
        pass
