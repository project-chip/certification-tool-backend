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
import xml.etree.ElementTree as ET
from typing import IO

from loguru import logger

from app.schemas.pics import PICSCluster, PICSError, PICSItem


class PICSParser:
    """Parse PICS XML file"""

    @classmethod
    def __get_text_for_element(cls, file: IO, element_name: str) -> str:
        text: str = ""
        for _, elem in ET.iterparse(file):
            if elem.tag == element_name:
                text = elem.text
                break

        if text:
            file.seek(0)  # reset the file
            return text
        else:
            raise PICSError(f"Unable to locate element {element_name}")

    @classmethod
    async def parse(cls, file: IO) -> PICSCluster:
        """Parse PICS XML using the sdk container by getting the command string from parse_pics_command"""
        from json import loads
        from pathlib import Path

        from test_collections.matter.sdk_tests.support.exec_run_in_container import (
            ExecResultExtended,
        )
        from test_collections.matter.sdk_tests.support.pics import (
            PICS_FILE_PATH,
            parse_pics_command,
        )
        from test_collections.matter.sdk_tests.support.sdk_container import SDKContainer

        TMP_PICS_PATH = Path(PICS_FILE_PATH + f"{id(file)}.xml")

        sdk_container = SDKContainer()
        await sdk_container.start()
        try:
            # Unfortunately, we still have to do some parsing here to get the cluster name.
            # Tests don't care about this, but the test harness uses it for display/update purposes.
            cluster_name = cls.__get_text_for_element(file, "name")
            logger.debug(f"Parsed cluster name {cluster_name}")

            # make a local copy of the file contents
            content = file.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            with open(TMP_PICS_PATH, "wb") as outfile:
                outfile.write(content)

            sdk_container.copy_file_to_container(TMP_PICS_PATH, TMP_PICS_PATH)
            prefix, cmd = parse_pics_command(TMP_PICS_PATH)
            logger.debug(f"Executing command: {prefix} {cmd}")

            result: ExecResultExtended = sdk_container.send_command(
                command=cmd, prefix=prefix
            )

            # cleanup
            TMP_PICS_PATH.unlink(missing_ok=True)

            # output parsing/coercing
            if result and 0 != result.exit_code:
                raise PICSError(
                    f"Parser failed to read file: {result.output.decode('utf-8')}"
                )
            output: str = result.output.decode("utf-8")
            logger.debug(f"Command result: {output}")

            raw_dict: dict[str, bool] = loads(output)
            pics_dict: dict[str, PICSItem] = {
                k: PICSItem(number=k, enabled=v) for k, v in raw_dict.items()
            }
            return PICSCluster(name=cluster_name, items=pics_dict)
        finally:
            sdk_container.destroy()
