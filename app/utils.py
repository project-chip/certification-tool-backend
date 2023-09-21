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
import json
from typing import Any

import click


def __print_json(object: Any) -> None:
    click.echo(__json_string(object))


def __json_string(object: Any) -> str:
    if object is None:
        return "None"
    if isinstance(object, list):
        return json.dumps([item.dict() for item in object], indent=4, default=str)
    else:
        return json.dumps(object.dict(), indent=4, default=str)
