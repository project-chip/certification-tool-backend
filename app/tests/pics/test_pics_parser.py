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
from pathlib import Path

from app.pics.pics_parser import PICSParser
from app.schemas.pics import PICSError


def test_pics_parser() -> None:
    pics_file = (
        Path(__file__).parent.parent.parent / "tests" / "utils" / "test_pics.xml"
    )
    cluster = PICSParser.parse(file=pics_file.open())

    assert cluster is not None
    assert cluster.name == "On/Off"

    assert len(cluster.items) > 0
    # expected pic items and their values
    assert cluster.items["OO.S.A0000"].enabled is True
    assert cluster.items["OO.S.A4000"].enabled is False
    assert cluster.items["OO.S.C00"].enabled is True


def test_pics_parser_with_errors() -> None:
    # test pics parse with invalid root tag
    pics_file = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "utils"
        / "test_pics_with_invalid_root_tag.xml"
    )

    try:
        PICSParser.parse(file=pics_file.open())

    except Exception as e:
        assert isinstance(e, PICSError)

    # test pics parse with no name element
    pics_file = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "utils"
        / "test_pics_with_no_name_element.xml"
    )

    try:
        PICSParser.parse(file=pics_file.open())

    except Exception as e:
        assert isinstance(e, PICSError)

    # test pics parse with no name element
    pics_file = (
        Path(__file__).parent.parent.parent
        / "tests"
        / "utils"
        / "test_pics_with_empty_name_element.xml"
    )

    try:
        PICSParser.parse(file=pics_file.open())

    except Exception as e:
        assert isinstance(e, PICSError)
