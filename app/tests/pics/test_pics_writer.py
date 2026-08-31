#
# Copyright (c) 2026 Project CHIP Authors
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
import io
from zipfile import ZipFile

from app.pics.pics_parser import PICSParser
from app.pics.pics_writer import PICSWriter
from app.schemas.pics import PICS, PICSCluster, PICSItem
from app.tests.utils.test_pics_data import create_random_pics


class _NamedStringIO(io.StringIO):
    """PICSParser reads `file.name` for logging; plain StringIO lacks it."""

    name = "exported.xml"


def test_write_cluster_round_trips_through_parser() -> None:
    cluster = PICSCluster(
        name="On/Off",
        items={
            "OO.S": PICSItem(number="OO.S", enabled=True),
            "OO.S.A0000": PICSItem(number="OO.S.A0000", enabled=True),
            "OO.S.A4000": PICSItem(number="OO.S.A4000", enabled=False),
            "OO.S.C00.Rsp": PICSItem(number="OO.S.C00.Rsp", enabled=True),
        },
    )

    xml_content = PICSWriter.write_cluster(cluster)
    parsed = PICSParser.parse(file=_NamedStringIO(xml_content))

    assert parsed.name == cluster.name
    assert set(parsed.items.keys()) == set(cluster.items.keys())
    for number, item in cluster.items.items():
        assert parsed.items[number].enabled == item.enabled


def test_write_cluster_with_unrecognized_item_number_goes_to_miscellaneous() -> None:
    cluster = PICSCluster(
        name="Misc",
        items={"PICS_SDK_CI_ONLY": PICSItem(number="PICS_SDK_CI_ONLY", enabled=True)},
    )

    xml_content = PICSWriter.write_cluster(cluster)
    parsed = PICSParser.parse(file=_NamedStringIO(xml_content))

    assert parsed.items["PICS_SDK_CI_ONLY"].enabled is True


def test_write_zip_contains_one_xml_per_cluster() -> None:
    pics = create_random_pics()

    zip_file = PICSWriter.write_zip(pics=pics)

    with ZipFile(zip_file) as zf:
        names = zf.namelist()
        assert names == ["On_Off.xml"]

        parsed = PICSParser.parse(file=_NamedStringIO(zf.read(names[0]).decode()))
        expected_cluster = pics.clusters["On/Off"]
        assert parsed.name == expected_cluster.name
        assert set(parsed.items.keys()) == set(expected_cluster.items.keys())


def test_write_zip_with_empty_pics_produces_empty_archive() -> None:
    zip_file = PICSWriter.write_zip(pics=PICS())

    with ZipFile(zip_file) as zf:
        assert zf.namelist() == []


def test_write_zip_dedupes_colliding_cluster_filenames() -> None:
    """Distinct cluster names that sanitize to the same filename (e.g.
    "On/Off" and "On:Off" both -> "On_Off") must not collide in the zip -
    each cluster's data must be retrievable."""
    pics = PICS()
    pics.clusters["On/Off"] = PICSCluster(
        name="On/Off", items={"OO.S.A0000": PICSItem(number="OO.S.A0000", enabled=True)}
    )
    pics.clusters["On:Off"] = PICSCluster(
        name="On:Off",
        items={"OX.S.A0001": PICSItem(number="OX.S.A0001", enabled=False)},
    )

    zip_file = PICSWriter.write_zip(pics=pics)

    with ZipFile(zip_file) as zf:
        names = zf.namelist()
        assert len(names) == 2
        assert len(set(names)) == 2  # no two entries share a name

        parsed_clusters = {
            PICSParser.parse(file=_NamedStringIO(zf.read(name).decode())).name
            for name in names
        }
        assert parsed_clusters == {"On/Off", "On:Off"}
