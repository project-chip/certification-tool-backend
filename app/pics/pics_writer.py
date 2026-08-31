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
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from io import BytesIO
from typing import Dict, Iterable, List, Tuple
from xml.dom import minidom
from zipfile import ZipFile

from app.schemas.pics import PICS, PICSCluster, PICSItem

# Section an item number belongs to, inferred from its suffix. This mirrors
# the grouping used by scripts/pics_to_xml.py so exported PICS XML files look
# like the documents PICSParser already accepts on import.
_SECTION_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("usage", re.compile(r"^[A-Z0-9_]+\.[SC]$")),
    ("attributes", re.compile(r"\.[SC]\.[Aa][0-9a-fA-F]")),
    ("events", re.compile(r"\.[SC]\.[Ee][0-9a-fA-F]")),
    ("commandsGenerated", re.compile(r"\.[SC]\.C[0-9a-fA-F]+\.Tx")),
    ("commandsReceived", re.compile(r"\.[SC]\.C[0-9a-fA-F]+\.Rsp")),
    ("features", re.compile(r"\.[SC]\.F[0-9a-fA-F]")),
]

_SECTION_ORDER = [
    "attributes",
    "events",
    "commandsGenerated",
    "commandsReceived",
    "features",
]


class PICSWriter:
    """Write PICS XML files in the same format PICSParser accepts on import.

    This is the export counterpart of PICSParser: given the PICS values that
    were actually used for a run, produce a clusterPICS XML document per
    cluster that can be fed straight back into the existing PICS upload flow.
    """

    @classmethod
    def write_cluster(cls, cluster: PICSCluster) -> str:
        root_element = cls.__build_cluster_element(cluster)
        return cls.__pretty_xml(root_element)

    @classmethod
    def write_zip(cls, pics: PICS) -> BytesIO:
        """Write all clusters of a PICS as a zip archive, one XML file per
        cluster, using the same document format PICSParser accepts on
        import.
        """
        file = BytesIO()
        used_filenames: set[str] = set()
        with ZipFile(file=file, mode="w") as zip_file:
            for cluster in pics.clusters.values():
                filename = cls.__unique_filename(cluster.name, used_filenames)
                used_filenames.add(filename)
                zip_file.writestr(filename, cls.write_cluster(cluster))
        file.seek(0)
        return file

    @classmethod
    def __unique_filename(cls, cluster_name: str, used_filenames: set[str]) -> str:
        """Return a sanitized "<name>.xml" filename, deduplicated against
        names already used in this archive.

        Distinct cluster names can sanitize to the same value (e.g.
        "On/Off" and "On:Off" both become "On_Off"); without dedup, the
        later cluster would silently overwrite the earlier one in the zip.
        """
        base_name = cls.__safe_filename(cluster_name)
        filename = f"{base_name}.xml"
        suffix = 1
        while filename in used_filenames:
            suffix += 1
            filename = f"{base_name}_{suffix}.xml"
        return filename

    @classmethod
    def __safe_filename(cls, cluster_name: str) -> str:
        # Cluster names can contain characters that are not filesystem-safe,
        # e.g. "On/Off". Replace anything but alphanumerics/underscore/dash.
        return re.sub(r"[^A-Za-z0-9_-]", "_", cluster_name)

    @classmethod
    def __build_cluster_element(cls, cluster: PICSCluster) -> ET.Element:
        root = ET.Element("clusterPICS")
        root.set("xsi", "http://www.w3.org/2001/XMLSchema-instance")

        ET.SubElement(root, "name").text = cluster.name

        buckets = cls.__bucket_items(cluster.items.values())

        # "usage" items (e.g. OO.S / OO.C) sit at the top level, outside of
        # clusterSide, same as scripts/pics_to_xml.py emits them.
        usage_items = buckets.get("usage", [])
        if usage_items:
            usage = ET.SubElement(root, "usage")
            for item in usage_items:
                cls.__append_pics_item(usage, item)

        for side_type, side_letter in (("server", "S"), ("client", "C")):
            side_items = {
                section: [
                    item
                    for item in buckets.get(section, [])
                    if cls.__item_side(item.number) == side_letter
                ]
                for section in _SECTION_ORDER
            }
            if any(side_items.values()):
                root.append(cls.__build_side_element(side_type, side_items))

        # Items that don't fit a section (no S/C suffix pattern matched)
        misc_items = buckets.get("manually", [])
        if misc_items:
            misc = ET.SubElement(root, "miscellaneous")
            for item in misc_items:
                cls.__append_pics_item(misc, item)

        return root

    @classmethod
    def __bucket_items(cls, items: Iterable[PICSItem]) -> Dict[str, List[PICSItem]]:
        buckets: Dict[str, List[PICSItem]] = defaultdict(list)
        for item in sorted(items, key=lambda i: i.number):
            buckets[cls.__categorise(item.number)].append(item)
        return buckets

    @classmethod
    def __categorise(cls, item_number: str) -> str:
        for section, pattern in _SECTION_PATTERNS:
            if pattern.search(item_number):
                return section
        return "manually"

    @classmethod
    def __item_side(cls, item_number: str) -> str:
        if re.search(r"\.C(\.|$)", item_number):
            return "C"
        return "S"

    @classmethod
    def __build_side_element(
        cls, side_type: str, side_items: Dict[str, List[PICSItem]]
    ) -> ET.Element:
        side = ET.Element("clusterSide")
        side.set("type", side_type)
        for section in _SECTION_ORDER:
            items = side_items.get(section)
            if not items:
                continue
            section_element = ET.SubElement(side, section)
            for item in items:
                cls.__append_pics_item(section_element, item)
        return side

    @classmethod
    def __append_pics_item(cls, parent: ET.Element, item: PICSItem) -> None:
        pics_item = ET.SubElement(parent, "picsItem")
        ET.SubElement(pics_item, "itemNumber").text = item.number
        ET.SubElement(pics_item, "support").text = str(item.enabled)

    @classmethod
    def __pretty_xml(cls, root_element: ET.Element) -> str:
        raw = ET.tostring(root_element, encoding="unicode")
        return minidom.parseString(raw).toprettyxml(indent="    ")
