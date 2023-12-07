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
from loguru import logger

# Create logger wrapper with `test_run_log` in log record `extra`
test_engine_logger = logger.bind(test_run_log=True)

# Add custom logger for "chip-tool"
CHIPTOOL_LEVEL = "CHIPTOOL"
test_engine_logger.level(CHIPTOOL_LEVEL, no=21, icon="🤖", color="<cyan>")

# Add custom logger for python tests
PYTHON_TEST_LEVEL = "PYTHON_TEST"
test_engine_logger.level(PYTHON_TEST_LEVEL, no=22, icon="🐍", color="<cyan>")

# Log format for logs that come from CHIP. Arguments: module (e.g. "DMG"), message
CHIP_LOG_FORMAT = "CHIP:{} {}"
