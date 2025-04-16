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
from shutil import copyfile
import json

from pydantic import BaseModel


class LogConfig(BaseModel):
    output_log_path = "./run_logs"
    format = "<level>{level: <8}</level> | <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>"


class Config(BaseModel):
    hostname = "localhost"
    log_config: LogConfig = LogConfig()


config_root = Path(__file__).parents[1]
config_file = Path.joinpath(config_root, "config.json")

# copy example file if no config file present
if not config_file.is_file():
    example_config_file = Path.joinpath(config_root, "config.json.example")
    with open(example_config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    json_content = "".join(line for line in lines if not line.lstrip().startswith("#")).strip()
    try:
        json.loads(json_content)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(json_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON after comment removal: {e}")

config = Config.parse_file(config_file)
