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
from app.pics_applicable_test_cases import applicable_test_cases_set
from app.schemas.pics import PICS
from app.tests.utils.test_pics_data import create_random_pics


def test_applicable_test_cases_set() -> None:
    pics = create_random_pics()

    applicable_test_cases = applicable_test_cases_set(pics)

    # Unit test case (TCPics) has AB.C and AB.C.0004 PICs enabled.
    # create_random_pics creates pics with these values set.
    # Applicable test cases should always be at least 1.
    assert len(applicable_test_cases.test_cases) > 0


def test_applicable_test_cases_set_with_no_pics() -> None:
    # create empty PICS list
    pics = PICS()

    applicable_test_cases = applicable_test_cases_set(pics)

    assert len(applicable_test_cases.test_cases) == 0
