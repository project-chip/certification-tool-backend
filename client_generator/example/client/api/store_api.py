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
from typing import TYPE_CHECKING, Awaitable, Dict

from fastapi.encoders import jsonable_encoder

from example.client import models as m

if TYPE_CHECKING:
    from example.client.api_client import ApiClient


class _StoreApi:
    def __init__(self, api_client: "ApiClient"):
        self.api_client = api_client

    def _build_for_delete_order(self, order_id: int) -> Awaitable[None]:
        """
        For valid response try integer IDs with positive integer value. Negative or non-integer values will generate API errors
        """
        path_params = {"orderId": str(order_id)}

        return self.api_client.request(
            type_=None,
            method="DELETE",
            url="/store/order/{orderId}",
            path_params=path_params,
        )

    def _build_for_get_inventory(
        self,
    ) -> Awaitable[Dict[str, int]]:
        """
        Returns a map of status codes to quantities
        """
        return self.api_client.request(
            type_=Dict[str, int],
            method="GET",
            url="/store/inventory",
        )

    def _build_for_get_order_by_id(self, order_id: int) -> Awaitable[m.Order]:
        """
        For valid response try integer IDs with value >= 1 and <= 10. Other values will generated exceptions
        """
        path_params = {"orderId": str(order_id)}

        return self.api_client.request(
            type_=m.Order,
            method="GET",
            url="/store/order/{orderId}",
            path_params=path_params,
        )

    def _build_for_place_order(self, body: m.Order) -> Awaitable[m.Order]:
        body = jsonable_encoder(body)

        return self.api_client.request(type_=m.Order, method="POST", url="/store/order", json=body)


class AsyncStoreApi(_StoreApi):
    async def delete_order(self, order_id: int) -> None:
        """
        For valid response try integer IDs with positive integer value. Negative or non-integer values will generate API errors
        """
        return await self._build_for_delete_order(order_id=order_id)

    async def get_inventory(
        self,
    ) -> Dict[str, int]:
        """
        Returns a map of status codes to quantities
        """
        return await self._build_for_get_inventory()

    async def get_order_by_id(self, order_id: int) -> m.Order:
        """
        For valid response try integer IDs with value >= 1 and <= 10. Other values will generated exceptions
        """
        return await self._build_for_get_order_by_id(order_id=order_id)

    async def place_order(self, body: m.Order) -> m.Order:
        return await self._build_for_place_order(body=body)


class SyncStoreApi(_StoreApi):
    def delete_order(self, order_id: int) -> None:
        """
        For valid response try integer IDs with positive integer value. Negative or non-integer values will generate API errors
        """
        coroutine = self._build_for_delete_order(order_id=order_id)
        return get_event_loop().run_until_complete(coroutine)

    def get_inventory(
        self,
    ) -> Dict[str, int]:
        """
        Returns a map of status codes to quantities
        """
        coroutine = self._build_for_get_inventory()
        return get_event_loop().run_until_complete(coroutine)

    def get_order_by_id(self, order_id: int) -> m.Order:
        """
        For valid response try integer IDs with value >= 1 and <= 10. Other values will generated exceptions
        """
        coroutine = self._build_for_get_order_by_id(order_id=order_id)
        return get_event_loop().run_until_complete(coroutine)

    def place_order(self, body: m.Order) -> m.Order:
        coroutine = self._build_for_place_order(body=body)
        return get_event_loop().run_until_complete(coroutine)
