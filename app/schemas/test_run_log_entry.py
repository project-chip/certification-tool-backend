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
from typing import Optional

from pydantic import BaseModel


class TestRunLogEntry(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    level: str
    timestamp: float
    message: str
    test_suite_execution_index: Optional[int]
    test_case_execution_index: Optional[int]
    test_step_execution_index: Optional[int]
