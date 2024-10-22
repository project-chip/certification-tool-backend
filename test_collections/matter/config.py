#
# Copyright (c) 2024 Project CHIP Authors
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
from pydantic import BaseSettings


class MatterSettings(BaseSettings):
    # Test Engine Config
    CHIP_TOOL_TRACE: bool = True
    SDK_CONTAINER_NAME: str = "th-sdk"

    # SDK Docker Image
    SDK_DOCKER_IMAGE: str = "connectedhomeip/chip-cert-bins"
    SDK_DOCKER_TAG: str = "bfff495316852556643975aa4588ad4afd34380c"
    # SDK SHA: used to fetch test YAML from SDK.
    SDK_SHA: str = "bfff495316852556643975aa4588ad4afd34380c"

    class Config:
        case_sensitive = True


matter_settings = MatterSettings()
