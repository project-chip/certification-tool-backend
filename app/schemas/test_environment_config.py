#
# Copyright (c) 2023-2026 Project CHIP Authors
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
from typing import Any, Optional

from pydantic import BaseModel


# TODO The Thread classes will be moved in a new PR
class ThreadDataset(BaseModel):
    channel: str
    panid: str
    extpanid: str
    networkkey: str
    networkname: str


class ThreadAutoConfig(BaseModel):
    rcp_serial_path: str
    rcp_baudrate: int
    on_mesh_prefix: str
    network_interface: str
    dataset: ThreadDataset
    otbr_docker_image: Optional[str]
    ba_host: Optional[str] = None
    ba_port: Optional[int] = None
    operational_dataset_hex: Optional[str] = None


class TestEnvironmentConfigError(Exception):
    """
    Exception raised while creating new subclass of TestEnvironmentConfig
    and the validate_model fails.
    All subclasses of TestEnvironmentConfig must implement validate_model method,
    and raise TestEnvironmentConfigError exception when the model is not in accordance
    """


class THConfig(BaseModel):
    """Test-Harness-specific settings, independent of any particular DUT/program."""

    prompt_timeout_seconds: int = 60
    # None means "not set at project level", deferring to the
    # ENABLE_REALTIME_PYTHON_TEST_LOGS environment variable.
    enable_realtime_python_test_logs: Optional[bool] = None
    # None means "not set at project level", deferring to the
    # ENABLE_CONTAINER_LOGS environment variable.
    enable_container_logs: Optional[bool] = None


class TestEnvironmentConfig(BaseModel):
    __test__ = False  # Needed to indicate to PyTest that this is not a "test"

    # TODO(#490): Need to be refactored to support real PIXIT format
    test_parameters: Optional[dict[str, Any]]
    th_config: Optional[THConfig] = None

    def __init__(self, **kwargs: Any):
        try:
            super().__init__(**kwargs)
            self.validate_model(dict_model=kwargs)
        except Exception as e:
            raise TestEnvironmentConfigError(
                "The informed configuration has one or more invalid properties."
                f" Exception message: {str(e)}"
            )

    def validate_model(self, dict_model: dict) -> None:
        raise NotImplementedError  # Must be overridden by subclass


def get_th_config_value(config: Optional[dict], key: str) -> Any:
    """Extract a value from a project's th_config, given the raw `.config` dict.

    Tolerates `th_config` being either a plain dict (the normal production
    shape, since `.config` is always the raw project/execution config dict) or
    a THConfig/pydantic object — some test doubles fake `.config` via
    `SomeModel.__dict__`, which does not recursively convert nested pydantic
    models to dicts, so `th_config` can show up as a THConfig instance there.
    """
    if not config:
        return None
    th_config = config.get("th_config") if isinstance(config, dict) else None
    if th_config is None:
        return None
    if isinstance(th_config, dict):
        return th_config.get(key)
    return getattr(th_config, key, None)
