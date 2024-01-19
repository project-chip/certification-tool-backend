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
from app.schemas.pics import PICS

# PICS parameters
SHELL_PATH = "/bin/sh"
SHELL_OPTION = "-c"
PICS_FILE_PATH = "/var/tmp/pics"
ECHO_COMMAND = "echo"
# List of default PICS which needs to set specifically in TH are added here.
# These PICS are applicable for CI / Chip tool testing purposes only.
# These PICS are unknown / not visible to external users.
DEFAULT_PICS = ["PICS_SDK_CI_ONLY=0", "PICS_SKIP_SAMPLE_APP=1", "PICS_USER_PROMPT=1"]


def pics_file_content(pics: PICS) -> str:
    """Generates PICS file content in the below format:
        PICS_CODE1=1
        PICS_CODE2=1
        PICS_CODE3=0
        .....

    Args:
        pics (PICS): PICS that contains all the pics codes

    Returns:
        str: Returns a string in this format PICS_CODE1=1\nPICS_CODE1=2\n"
    """
    pics_str: str = ""

    for cluster in pics.clusters.values():
        for pi in cluster.items.values():
            if pi.enabled:
                pics_str += pi.number + "=1" + "\n"
            else:
                pics_str += pi.number + "=0" + "\n"

    return pics_str


def set_pics_command(pics: PICS) -> tuple[str, str]:
    pics_codes = pics_file_content(pics) + "\n".join(DEFAULT_PICS)

    prefix = f"{SHELL_PATH} {SHELL_OPTION}"
    cmd = f"\"{ECHO_COMMAND} '{pics_codes}' > {PICS_FILE_PATH}\""

    return (prefix, cmd)
