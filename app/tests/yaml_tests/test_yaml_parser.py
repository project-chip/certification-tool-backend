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
from unittest import mock

import pytest
from pydantic.error_wrappers import ValidationError

from app.tests.yaml_tests.test_test_case import yaml_test_instance
from test_collections.sdk_tests.support.yaml_tests.models.yaml_test_models import (
    YamlTestStep,
    YamlTestType,
)
from test_collections.sdk_tests.support.yaml_tests.models.yaml_test_parser import (
    YamlParserException,
    YamlTest,
    _test_type,
    parse_yaml_test,
)

sample_yaml_file_content = """
name: XX.YY.ZZ [TC-TEST-2.1] Simple Test

PICS:
    - ACL.S

config:
    nodeId: 0x12344321
    cluster: "Access Control"
    endpoint: 0

tests:
    - label: "Wait for the commissioned device to be retrieved"
      cluster: "DelayCommands"
      command: "WaitForCommissionee"
      arguments:
          values:
              - name: "nodeId"
                value: nodeId

"""


def test_yaml_file_parser_throws_validationexception() -> None:
    file_path = Path("/test/file.yaml")

    mock_validation = ValidationError(errors=[mock.MagicMock()], model=mock.MagicMock())

    with mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models.yaml_test_parser.open",
        new=mock.mock_open(read_data=sample_yaml_file_content),
    ), mock.patch(
        "loguru.logger",
        mock.MagicMock(),
    ), mock.patch.object(
        target=ValidationError,
        attribute="__str__",
        return_value="error",
    ), mock.patch.object(
        target=YamlTest,
        attribute="parse_raw",
        side_effect=mock_validation,
    ), pytest.raises(
        YamlParserException
    ) as e:
        parse_yaml_test(file_path)

    assert "The YAML file /test/file.yaml is invalid" == str(e.value)


def test_yaml_file_parser() -> None:
    file_path = Path("/test/file.yaml")

    # We mock builtin `open` method to read sample yaml file content,
    # to avoid having to load a real file.
    with mock.patch(
        "test_collections.sdk_tests.support.yaml_tests.models.yaml_test_parser.open",
        new=mock.mock_open(read_data=sample_yaml_file_content),
    ) as file_open:
        test = parse_yaml_test(file_path)

        file_open.assert_called_once_with(file_path, "r")
        assert test.path == file_path


def test_test_type_all_disabled_steps() -> None:
    disabled_step = YamlTestStep(label="Disabled Test Step", disabled=True)
    five_disabled_steps_test = yaml_test_instance(tests=[disabled_step] * 5)

    type = _test_type(five_disabled_steps_test)
    assert type == YamlTestType.MANUAL

    # simulated in path overrides test type to simulated
    five_disabled_steps_test.path = Path("TC_XX_Simulated.yaml")
    type = _test_type(five_disabled_steps_test)
    assert type == YamlTestType.SIMULATED


def test_test_type_some_disabled_steps() -> None:
    disabled_step = YamlTestStep(label="Disabled Test Step", disabled=True)
    enabled_step = YamlTestStep(label="Enabled Test Step", disabled=False)
    test = yaml_test_instance(tests=[disabled_step, enabled_step])

    type = _test_type(test)
    assert type == YamlTestType.AUTOMATED

    # simulated in path overrides test type to simulated
    test.path = Path("TC_XX_Simulated.yaml")
    type = _test_type(test)
    assert type == YamlTestType.SIMULATED


def test_test_type_all_enabled_steps_no_prompts() -> None:
    enabled_step = YamlTestStep(label="Enabled Test Step")
    five_enabled_steps_test = yaml_test_instance(tests=[enabled_step] * 5)

    type = _test_type(five_enabled_steps_test)
    assert type == YamlTestType.AUTOMATED

    # simulated in path overrides test type to simulated
    five_enabled_steps_test.path = Path("TC_XX_Simulated.yaml")
    type = _test_type(five_enabled_steps_test)
    assert type == YamlTestType.SIMULATED


def test_test_type_all_enabled_steps_some_prompts() -> None:
    enabled_step = YamlTestStep(label="Enable Test Step")
    prompt_step = YamlTestStep(label="Prompt Test Step", command="UserPrompt")
    test = yaml_test_instance(tests=[enabled_step, prompt_step])

    type = _test_type(test)
    assert type == YamlTestType.SEMI_AUTOMATED

    # simulated in path overrides test type to simulated
    test.path = Path("TC_XX_Simulated.yaml")
    type = _test_type(test)
    assert type == YamlTestType.SIMULATED
