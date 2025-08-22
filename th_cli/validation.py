#
# Copyright (c) 2025 Project CHIP Authors
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
"""Input validation utilities for the CLI."""

import re
from pathlib import Path
from typing import List

from th_cli.exceptions import CLIError


def validate_project_name(name: str) -> str:
    """Validate project name format."""
    if not name or len(name.strip()) == 0:
        raise CLIError("Project name cannot be empty")

    if len(name) > 100:
        raise CLIError("Project name cannot exceed 100 characters")

    # Allow alphanumeric, spaces, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9\s\-_]+$", name):
        raise CLIError("Project name can only contain letters, numbers, spaces, hyphens, and underscores")

    return name.strip()


def _sanitize_path(file_path: str) -> Path:
    """Sanitize file/directory paths."""
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        raise CLIError(f"Invalid file path '{file_path}': {e}")

    # Security: Prevent path traversal
    try:
        # This will raise ValueError if path tries to go outside current working directory
        path.relative_to(Path.cwd().resolve())
    except ValueError:
        # Allow absolute paths in user directories but fail paths outside
        if not str(path).startswith(str(Path.home())):
            raise CLIError(f"Access denied: Path '{file_path}' is outside allowed directories")

    return path


def validate_file_path(file_path: str, must_exist: bool = True) -> Path:
    """Validate and file paths."""
    path = _sanitize_path(file_path)

    if must_exist and not path.exists():
        raise CLIError(f"File not found: {file_path}")

    if must_exist and not path.is_file():
        raise CLIError(f"Path is not a file: {file_path}")

    return path


def validate_directory_path(dir_path: str, must_exist: bool = True) -> Path:
    """Validate and directory paths."""
    path = _sanitize_path(dir_path)

    if must_exist and not path.exists():
        raise CLIError(f"Directory not found: {dir_path}")

    if must_exist and not path.is_dir():
        raise CLIError(f"Path is not a directory: {dir_path}")

    return path


def validate_test_ids(test_ids: str) -> List[str]:
    """Validate and sanitize test ID list."""
    if not test_ids or len(test_ids.strip()) == 0:
        raise CLIError("Test IDs list cannot be empty")

    # Split and clean test IDs
    ids = [test_id.strip() for test_id in test_ids.split(",")]

    # Remove empty IDs
    ids = [test_id for test_id in ids if test_id]

    if not ids:
        raise CLIError("No valid test IDs provided")

    # Validate each test ID format
    valid_pattern = re.compile(r"^TC[-_][A-Z]{2,5}[-_]\d+([\._]\d+)*$", re.IGNORECASE)

    invalid_ids = []
    for test_id in ids:
        if not valid_pattern.match(test_id):
            invalid_ids.append(test_id)

    if invalid_ids:
        raise CLIError(
            f"Invalid test ID format: {', '.join(invalid_ids)}. " f"Expected format: TC-XXX-1.1 or TC_XXX_1_1"
        )

    return ids


def validate_hostname(hostname: str) -> str:
    """Validate hostname format."""
    if not hostname or len(hostname.strip()) == 0:
        raise CLIError("Hostname cannot be empty")

    hostname = hostname.strip()

    # Basic hostname validation
    if len(hostname) > 253:
        raise CLIError("Hostname too long")

    # Allow localhost, IP addresses, and domain names
    if hostname == "localhost":
        return hostname

    # Simple IP address check
    ip_pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    if ip_pattern.match(hostname):
        # Validate IP octets
        octets = hostname.split(".")
        for octet in octets:
            if not (0 <= int(octet) <= 255):
                raise CLIError(f"Invalid IP address: {hostname}")
        return hostname

    # Basic domain name validation
    domain_pattern = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    )
    if not domain_pattern.match(hostname):
        raise CLIError(f"Invalid hostname format: {hostname}")

    return hostname
