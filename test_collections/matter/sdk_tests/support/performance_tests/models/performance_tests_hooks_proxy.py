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


class SDKPerformanceResultEnum(str, Enum):
    START = "start"
    STOP = "stop"
    TEST_START = "test_start"
    TEST_STOP = "test_stop"
    TEST_SKIPPED = "test_skipped"
    STEP_SKIPPED = "step_skipped"
    STEP_START = "step_start"
    STEP_SUCCESS = "step_success"
    STEP_FAILURE = "step_failure"
    STEP_UNKNOWN = "step_unknown"
    STEP_MANUAL = "step_manual"
    SHOW_PROMPT = "show_prompt"


class SDKPerformanceResultBase(BaseModel):
    type: SDKPerformanceResultEnum

    def params_dict(self) -> dict:
        return self.dict(exclude={"type"})


class SDKPerformanceResultStart(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.START
    count: int


class SDKPerformanceResultStop(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STOP
    duration: int


class SDKPerformanceResultTestStart(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.TEST_START
    filename: Optional[str]
    name: Optional[str]
    count: Optional[int]
    steps: Optional[list[str]]


class SDKPerformanceResultTestStop(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.TEST_STOP
    duration: Optional[int]
    exception: Any


class SDKPerformanceResultTestSkipped(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.TEST_SKIPPED
    filename: Optional[str]
    name: Optional[str]


class SDKPerformanceResultStepSkipped(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_SKIPPED
    name: Optional[str]
    expression: Optional[str]


class SDKPerformanceResultStepStart(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_START
    name: Optional[str]


class SDKPerformanceResultStepSuccess(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_SUCCESS
    logger: Any
    logs: Any
    duration: int
    request: Any


class SDKPerformanceResultStepFailure(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_FAILURE
    logger: Any
    logs: Any
    duration: int
    request: Any
    received: Any


class SDKPerformanceResultStepUnknown(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_UNKNOWN


class SDKPerformanceResultStepManual(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.STEP_MANUAL


class SDKPerformanceResultShowPrompt(SDKPerformanceResultBase):
    type: SDKPerformanceResultEnum = SDKPerformanceResultEnum.SHOW_PROMPT
    msg: str
    placeholder: Optional[str]
    default_value: Optional[str]


class SDKPerformanceRunnerHooks(TestRunnerHooks):
    finished = False
    results: Queue

    def __init__(self) -> None:
        SDKPerformanceRunnerHooks.finished = False
        SDKPerformanceRunnerHooks.results = Queue()

    def update_test(self) -> Union[dict, None]:
        try:
            result = self.results.get(block=False)
            return result
        except Empty:
            return None

    def is_finished(self) -> bool:
        return SDKPerformanceRunnerHooks.finished

    def start(self, count: int) -> None:
        self.results.put(SDKPerformanceResultStart(count=count))

    def stop(self, duration: int) -> None:
        self.results.put(SDKPerformanceResultStop(duration=duration))
        SDKPerformanceRunnerHooks.finished = True

    def test_start(
        self, filename: str, name: str, count: int, steps: list[str] = []
    ) -> None:
        self.results.put(
            SDKPerformanceResultTestStart(
                filename=filename, name=name, count=count, steps=steps
            )
        )

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.results.put(
            SDKPerformanceResultTestStop(exception=exception, duration=duration)
        )

    def test_skipped(self, filename: str, name: str) -> None:
        self.results.put(SDKPerformanceResultTestSkipped(filename=filename, name=name))

    def step_skipped(self, name: str, expression: str) -> None:
        self.results.put(
            SDKPerformanceResultStepSkipped(name=name, expression=expression)
        )

    def step_start(self, name: str) -> None:
        self.results.put(SDKPerformanceResultStepStart(name=name))

    def step_success(self, logger: Any, logs: Any, duration: int, request: Any) -> None:
        self.results.put(
            SDKPerformanceResultStepSuccess(
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
            SDKPerformanceResultStepFailure(
                logger=logger,
                logs=logs,
                duration=duration,
                request=request,
                received=received,
            )
        )

    def step_unknown(self) -> None:
        self.results.put(SDKPerformanceResultStepUnknown())

    async def step_manual(self) -> None:
        self.results.put(SDKPerformanceResultStepManual())

    def show_prompt(
        self,
        msg: str,
        placeholder: Optional[str] = None,
        default_value: Optional[str] = None,
        endpoint_id: Optional[int] = None,
    ) -> None:
        self.results.put(
            SDKPerformanceResultShowPrompt(
                msg=msg, placeholder=placeholder, default_value=default_value
            )
        )

    def step_start_list(self) -> None:
        pass
