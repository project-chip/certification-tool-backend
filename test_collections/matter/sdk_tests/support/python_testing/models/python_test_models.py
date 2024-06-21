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
from typing import Any

from ...models.matter_test_models import MatterTest, MatterTestType

###
# This file declares Python test models that are used to parse the Python Test Cases.
###


class PythonTestType(Enum):
    # - PythonTestType.COMMISSIONING: test cases that have a commissioning first step
    # - PythonTestType.NO_COMMISSIONING: test cases that follow the expected template
    #   but don't have a commissioning first step
    # - PythonTestType.LEGACY: test cases that don't follow the expected template
    # - PythonTestType.MANDATORY: test cases that are mandatory
    COMMISSIONING = 1
    NO_COMMISSIONING = 2
    LEGACY = 3
    MANDATORY = 4


class PythonTest(MatterTest):
    description: str
    class_name: str
    python_test_type: PythonTestType

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.type = MatterTestType.AUTOMATED
