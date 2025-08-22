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
# flake8: noqa E501
from asyncio import get_event_loop
from typing import TYPE_CHECKING, Any, Awaitable

from fastapi.encoders import jsonable_encoder

from th_cli.api_lib_autogen import models as m

if TYPE_CHECKING:
    from th_cli.api_lib_autogen.api_client import ApiClient


class _DevicesApi:
    def __init__(self, api_client: "ApiClient"):
        self.api_client = api_client

    def _build_for_add_device_config_api_v1_devices_put(self, body: Any) -> Awaitable[m.Any]:
        body = jsonable_encoder(body)

        return self.api_client.request(type_=m.Any, method="PUT", url="/api/v1/devices/", json=body)

    def _build_for_get_device_configs_api_v1_devices_get(
        self,
    ) -> Awaitable[m.Any]:
        return self.api_client.request(
            type_=m.Any,
            method="GET",
            url="/api/v1/devices/",
        )


class AsyncDevicesApi(_DevicesApi):
    async def add_device_config_api_v1_devices_put(self, body: Any) -> m.Any:
        return await self._build_for_add_device_config_api_v1_devices_put(body=body)

    async def get_device_configs_api_v1_devices_get(
        self,
    ) -> m.Any:
        return await self._build_for_get_device_configs_api_v1_devices_get()


class SyncDevicesApi(_DevicesApi):
    def add_device_config_api_v1_devices_put(self, body: Any) -> m.Any:
        coroutine = self._build_for_add_device_config_api_v1_devices_put(body=body)
        return get_event_loop().run_until_complete(coroutine)

    def get_device_configs_api_v1_devices_get(
        self,
    ) -> m.Any:
        coroutine = self._build_for_get_device_configs_api_v1_devices_get()
        return get_event_loop().run_until_complete(coroutine)
