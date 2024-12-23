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
    SDK_DOCKER_IMAGE: str = "ghcr.io/rquidute/chip-cert-bins"
    SDK_DOCKER_TAG: str = "f99a2c3b16d3d26f91a0c5efb2770d1c488697d1"
    # SDK SHA: used to fetch test YAML from SDK.
    SDK_SHA: str = "f99a2c3b16d3d26f91a0c5efb2770d1c488697d1"

    class Config:
        case_sensitive = True


matter_settings = MatterSettings()
