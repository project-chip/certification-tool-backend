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

from loguru import logger

from th_cli.config import config

# Add custom logger for "chip-tool"
CHIPTOOL_LEVEL = "CHIPTOOL"
logger.level(CHIPTOOL_LEVEL, no=21, icon="🤖", color="<cyan>")

# Add custom logger for python tests
PYTHON_TEST_LEVEL = "PYTHON_TEST"
logger.level(PYTHON_TEST_LEVEL, no=22, icon="🐍", color="<cyan>")


def configure_logger_for_run(title: str) -> str:
    # Reset (Remove all sinks from logger)
    logger.remove()

    log_path = os.path.join(config.log_config.output_log_path, f"test_run_{title}.log")

    logger.add(log_path, enqueue=True, format=config.log_config.format)

    return log_path
