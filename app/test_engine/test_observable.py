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
from typing import List, Set

from app.test_engine.test_observer import Observable, Observer


class TestObservable(Observable):
    __test__ = False

    def __init__(self) -> None:
        self.observers: Set[Observer] = set()

    def subscribe(self, observers: List[Observer]) -> None:
        self.observers.update(observers)

    def unsubscribe(self, observers: List[Observer]) -> None:
        self.observers.difference_update(observers)

    def notify(self) -> None:
        for observer in self.observers:
            observer.dispatch(self)
