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
from queue import Empty, Queue
from typing import Any, Union

from matter_yamltests.hooks import TestRunnerHooks


class SDKPythonTestRunnerHooks(TestRunnerHooks):
    is_finished = False
    results: Queue

    def updates_test(self) -> Union[dict, None]:
        try:
            result = self.results.get(block=False)
            return result
        except Empty:
            return None

    def finished(self) -> bool:
        return SDKPythonTestRunnerHooks.is_finished

    def __init__(self) -> None:
        SDKPythonTestRunnerHooks.is_finished = False
        SDKPythonTestRunnerHooks.results = Queue()

    def start(self, count: int) -> None:
        self.results.put({"start": {"count": count}})

    def stop(self, duration: int) -> None:
        self.results.put({"stop": {"duration": duration}})
        self.is_finished = True

    def test_start(self, filename: str, name: str, count: int) -> None:
        self.results.put(
            {"test_start": {"filename": filename, "name": name, "count": count}}
        )

    def test_stop(self, exception: Exception, duration: int) -> None:
        self.results.put({"test_stop": {"exception": exception, "duration": duration}})

    def step_skipped(self, name: str, expression: str) -> None:
        self.results.put({"step_skipped": {"name": name, "expression": expression}})

    def step_start(self, name: str) -> None:
        self.results.put({"step_start": {"name": name}})

    def step_success(self, logger: Any, logs: Any, duration: int, request: Any) -> None:
        self.results.put(
            {
                "step_success": {
                    "logger": logger,
                    "logs": logs,
                    "duration": duration,
                    "request": request,
                }
            }
        )

    def step_failure(
        self, logger: Any, logs: Any, duration: int, request: Any, received: Any
    ) -> None:
        self.results.put(
            {
                "step_failure": {
                    "logger": logger,
                    "logs": logs,
                    "duration": duration,
                    "request": request,
                    "received": received,
                }
            }
        )

    def step_unknown(self) -> None:
        self.results.put({"step_unknown": {}})

    def step_manual(self) -> None:
        self.results.put({"step_manual": {}})

    def step_start_list(self) -> None:
        pass
