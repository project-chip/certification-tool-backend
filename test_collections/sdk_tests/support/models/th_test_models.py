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
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

###
# This file declares YAML models that are used to parse the YAML Test Cases.
###


class THTestType(Enum):
    AUTOMATED = 0
    SEMI_AUTOMATED = 1
    MANUAL = 2
    SIMULATED = 3


class THTestStep(BaseModel):
    label: str
    PICS: Optional[str] = None
    verification: Optional[str] = None
    command: Optional[str]
    disabled: bool = False
    arguments: Optional[dict[str, Any]]


class THTest(BaseModel):
    name: str
    PICS: set[str] = set()
    config: dict[str, Any]
    steps: list[THTestStep]
    type: THTestType = THTestType.MANUAL
    path: Optional[Path]
