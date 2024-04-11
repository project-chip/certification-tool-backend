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
import os
from pathlib import Path

from app.utils import TEST_COLLECTIONS, program_class, program_config_path

PROJECT_ROOT = Path(__file__).parent.parent

test_collection_folder = os.listdir(PROJECT_ROOT / TEST_COLLECTIONS)

default_environment_config = None

if program_class:
    func_name = "parse_file"
    func = getattr(program_class, func_name, None)

    if not func:
        raise AttributeError(f"{func_name} is not a method of {program_class}")
    if not callable(func):
        raise TypeError(f"{func_name} is not callable")

    if program_config_path:
        default_environment_config = func(program_config_path)
        default_environment_config.__dict__
