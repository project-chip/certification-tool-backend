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

from pydantic import BaseModel

# TODO The Thread classes will be moved in a new PR
class ThreadDataset(BaseModel):
    channel: str
    panid: str
    extpanid: str
    networkkey: str
    networkname: str


class ThreadAutoConfig(BaseModel):
    rcp_serial_path: str
    rcp_baudrate: int
    on_mesh_prefix: str
    network_interface: str
    dataset: ThreadDataset
    otbr_docker_image: Optional[str]


class TestEnvironmentConfig(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    # TODO(#490): Need to be refactored to support real PIXIT format
    test_parameters: Optional[dict[str, Any]]

    def validate_model(self, dict_model: dict) -> bool:
        raise NotImplementedError  # Must be overridden by subclass

    def program_name(self) -> str:
        raise NotImplementedError  # Must be overridden by subclass
