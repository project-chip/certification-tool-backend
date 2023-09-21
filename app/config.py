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
    copyfile(example_config_file, config_file)

config = Config.parse_file(config_file)
