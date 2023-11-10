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
from typing import Generator

from test_collections.sdk_tests.support.chip_tool.exec_run_in_container import (
    exec_run_in_container,
)
from app.tests.utils.docker import make_fake_container


def test_exec_run_in_container_not_stream() -> None:
    cmd = "fake command"
    exec_id = "1234567890ab"
    output_str = "log output"
    exit_code = 0

    container = make_fake_container(
        mock_api_config={
            "exec_create.return_value": {"Id": exec_id},
            "exec_start.return_value": output_str.encode(),
            "exec_inspect.return_value": {"ExitCode": exit_code},
        }
    )

    result = exec_run_in_container(container, cmd, stream=False)

    assert result.exit_code == exit_code
    assert isinstance(result.output, bytes)
    assert result.output.decode() == output_str
    assert result.exec_id == exec_id


def test_exec_run_in_container_stream() -> None:
    cmd = "fake command"
    exec_id = "1234567890ab"
    output_str = "log output"
    exit_code = 0
    output_gen = (s for s in [output_str])
    container = make_fake_container(
        mock_api_config={
            "exec_create.return_value": {"Id": exec_id},
            "exec_start.return_value": output_gen,
            "exec_inspect.return_value": {"ExitCode": exit_code},
        }
    )

    result = exec_run_in_container(container, cmd, stream=True)

    assert result.exit_code is None
    assert isinstance(result.output, Generator)
    assert result.exec_id == exec_id
