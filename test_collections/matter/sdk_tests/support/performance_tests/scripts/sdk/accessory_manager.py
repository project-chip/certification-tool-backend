#
#    Copyright (c) 2023 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

from abc import ABC, abstractmethod


# This interface must be implemented to provide basic access to accessory functionality.
class AccessoryInterface(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def clean(self) -> None:
        pass


from .simulated_accessory import SimulatedAccessory  # noqa: E402


class AccessoryManager:
    def __init__(self, accessory: AccessoryInterface = SimulatedAccessory()):
        self.accessory = accessory

    def start(self) -> None:
        self.accessory.start()

    def stop(self) -> None:
        self.accessory.stop()

    def clean(self) -> None:
        self.accessory.clean()
