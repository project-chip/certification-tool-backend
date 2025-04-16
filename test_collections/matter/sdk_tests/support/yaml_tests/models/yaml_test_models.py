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
from typing import Any, Optional

from pydantic_yaml import YamlModelMixin

from ...models.matter_test_models import MatterTest
from .test_suite import SuiteType

###
# This file declares YAML models that are used to parse the YAML Test Cases.
###


class YamlTest(YamlModelMixin, MatterTest):
    suite_type: Optional[SuiteType] = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(steps=kwargs["tests"], **kwargs)
