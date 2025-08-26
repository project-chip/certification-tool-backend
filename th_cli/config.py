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
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple

from pydantic import BaseModel

from th_cli.exceptions import CLIError


def get_package_root() -> Path:
    """
    Get the root directory of the package installation.
    This works for both editable and non-editable installations.
    """
    # Get the directory containing this config.py file
    return Path(__file__).parent.parent


def find_git_root() -> Path | None:
    """
    Find the root directory containing the CLI's .git folder.
    This is needed for git operations and will find the original source.
    """
    # Start from the package root
    current_path = get_package_root()

    # Walk up the directory tree looking for .git
    while current_path != current_path.parent:
        if (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent

    # If not found in package location, try current working directory
    current_path = Path.cwd()
    while current_path != current_path.parent:
        if (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent

    return None


def is_editable_install() -> bool:
    """
    Detect if this is an editable installation.
    """
    package_root = get_package_root()
    git_root = find_git_root()

    # If git root and package root are the same, it's likely editable
    if git_root and package_root:
        try:
            # Check if package root is within or same as git root
            package_root.relative_to(git_root)
            return True
        except ValueError:
            return False
    return False


def get_config_search_paths() -> list[Path]:
    """
    Get a list of paths to search for configuration files.
    """
    paths = []

    # Always include current working directory
    paths.append(Path.cwd())

    # Include package installation directory
    package_root = get_package_root()
    paths.append(package_root)

    # If not editable install, also check git root (original source)
    if not is_editable_install():
        git_root = find_git_root()
        if git_root and git_root != package_root:
            paths.append(git_root)

    return paths


class LogConfig(BaseModel):
    output_log_path = "./run_logs"
    format = "<level>{level: <8}</level> | <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{message}</level>"


class Config(BaseModel):
    hostname: str = "localhost"
    log_config: LogConfig = LogConfig()


def get_default_config():
    """Return default configuration when no config file is found"""
    return {
        "hostname": "localhost",
        "log_config": {
            "output_log_path": "./run_logs",
            "format": "<level>{level: <8}</level> | \
                <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | \
                    <level>{message}</level>",
        },
    }


def load_config():
    """Load configuration with fallbacks"""
    # Get dynamic search paths
    search_paths = get_config_search_paths()

    # Try different possible locations for config files
    possible_locations = []
    for path in search_paths:
        possible_locations.append(path / "config.json")

    for config_path in possible_locations:
        if config_path.exists():
            try:
                return Config.parse_file(config_path)
            except Exception as e:
                CLIError(f"Could not load config from {config_path}: {e}")
                continue

    # Try to create config from example file
    example_locations = []
    for path in search_paths:
        example_locations.append(path / "config.json.example")

    for example_path in example_locations:
        if example_path.exists():
            try:
                with open(example_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                json_content = "".join(line for line in lines if not line.lstrip().startswith("#")).strip()
                config_data = json.loads(json_content)
                return Config(**config_data)
            except Exception as e:
                print(f"Warning: Could not load example config from {example_path}: {e}")
                continue

    # Fall back to default configuration
    print("Warning: Using default configuration")
    default_config = get_default_config()
    return Config(**default_config)


# Load the configuration
config = load_config()


class PairingMode(str, Enum):
    BLE_WIFI = "ble-wifi"
    BLE_THREAD = "ble-thread"
    WIFIPAF_WIFI = "wifipaf-wifi"
    NFC_THREAD = "nfc-thread"
    ONNETWORK = "onnetwork"


VALID_PAIRING_MODES = {mode.value for mode in PairingMode}

ATTRIBUTE_MAPPING: Dict[str, Tuple[str, ...]] = {
    # Thread dataset attributes
    "channel": ("network", "thread", "dataset"),
    "panid": ("network", "thread", "dataset"),
    "extpanid": ("network", "thread", "dataset"),
    "networkkey": ("network", "thread", "dataset"),
    "networkname": ("network", "thread", "dataset"),
    # Other thread attributes
    "rcp_serial_path": ("network", "thread"),
    "rcp_baudrate": ("network", "thread"),
    "on_mesh_prefix": ("network", "thread"),
    "network_interface": ("network", "thread"),
    "operational_dataset_hex": ("network", "thread"),
    # WiFi attributes
    "ssid": ("network", "wifi"),
    "password": ("network", "wifi"),
}
