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
# Copyright (c) 2021 Project CHIP Authors
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
# type: ignore
# Ignore mypy type check for this file
# flake8: noqa
# Ignore flake8 check for this file
"""
This is just a sample test case that should come from SDK. 
It should not compile or run. 
"""


class TC_Commissioning_Sample(MatterBaseTest):
    def desc_TC_Commissioning_Sample(self) -> str:
        return "Commissioning Sample TC Description"

    def steps_TC_Commissioning_Sample(self) -> list[TestStep]:
        steps = [
            TestStep(1, "Commissioning, already done", is_commissioning=True),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_TC_Commissioning_Sample(self):
        print("Test execution")

    def pics_TC_Commissioning_Sample(self):
        pass


class TC_No_Commissioning_Sample(MatterBaseTest):
    def desc_TC_No_Commissioning_Sample(self) -> str:
        return "No Commissioning Sample TC Description"

    def steps_TC_No_Commissioning_Sample(self) -> list[TestStep]:
        steps = [
            TestStep(1, "First step"),
            TestStep(2, "Second step"),
            TestStep(3, "Third step"),
        ]
        return steps

    def test_TC_No_Commissioning_Sample(self):
        print("Test execution")

    def pics_TC_No_Commissioning_Sample(self):
        pass


class TC_Legacy_Sample(MatterBaseTest):
    def test_TC_Legacy_Sample(self):
        print("Test execution")
