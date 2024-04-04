#
# Copyright (c) 2024 Project CHIP Authors
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
from app.schemas.test_environment_config import TestEnvironmentConfigError
from app.tests.utils.utils import (
    default_config_invalid_dut_added_property,
    default_config_invalid_dut_renamed_property,
    default_config_no_dut,
    default_config_no_network,
    default_matter_config,
)
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter


def test_create_config_matter_with_valid_config_suceess() -> None:
    config_matter = TestEnvironmentConfigMatter(**default_matter_config)

    assert config_matter is not None


def test_create_config_matter_with_no_config_fails() -> None:
    try:
        TestEnvironmentConfigMatter()  # type: ignore
    except TestEnvironmentConfigError as e:
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_no_dut_config_fails() -> None:
    try:
        TestEnvironmentConfigMatter(**default_config_no_dut)
    except TestEnvironmentConfigError as e:
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_invalid_dut_config_renamed_property_fails() -> None:
    try:
        TestEnvironmentConfigMatter(**default_config_invalid_dut_renamed_property)
    except TestEnvironmentConfigError as e:
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_invalid_dut_config_added_property_fails() -> None:
    try:
        TestEnvironmentConfigMatter(**default_config_invalid_dut_added_property)
    except TestEnvironmentConfigError as e:
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )


def test_create_config_matter_with_no_network_config_fails() -> None:
    try:
        TestEnvironmentConfigMatter(**default_config_no_network)
    except TestEnvironmentConfigError as e:
        assert "The informed configuration has one or more invalid properties." == str(
            e
        )
