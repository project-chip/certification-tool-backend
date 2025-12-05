#
# Copyright (c) 2025 Project CHIP Authors
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
from typing import Any, Dict, Type, TypeVar, cast

T = TypeVar("T")


class Singleton(type):
    """This is a metaclass for declaring classes as singletons

    usage:
    ```
    class NewSingletonClass(baseClass, metaclass=Singleton):
    ```
    """

    _instances: Dict[Type, object] = {}

    def __call__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in Singleton._instances:
            Singleton._instances[cls] = super().__call__(*args, **kwargs)  # type: ignore[misc]
        return cast(T, Singleton._instances[cls])
