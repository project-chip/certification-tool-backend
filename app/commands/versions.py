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
import os
import subprocess
from typing import Optional

import click
import tomli
from api_lib_autogen.api_client import SyncApis
from client import client

sync_apis = SyncApis(client)
versions_api = sync_apis.versions_api

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_cli_version() -> str:
    """Get CLI version from pyproject.toml"""
    try:
        project_root = os.path.dirname(PROJECT_ROOT)
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
                version = pyproject_data.get("project", {}).get("version")
                if version:
                    return version
        return "unknown"
    except (FileNotFoundError, IOError):
        return "unknown"


def _get_cli_sha() -> str:
    """Get current CLI SHA from git"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=os.path.dirname(PROJECT_ROOT),
        )
        return result.stdout.strip()[:8]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@click.command()
def versions() -> None:
    """Get application versions information"""
    try:
        versions_info = versions_api.get_versions_api_v1_versions_get()
        _print_versions_table(versions_info)
    finally:
        client.close()


def _print_versions_table(versions_data: dict) -> None:
    """Print versions in a formatted table"""
    click.echo("Application Versions")
    click.echo("=" * 30)

    # Add CLI version and SHA first
    cli_version = get_cli_version()
    cli_sha = _get_cli_sha()

    click.echo(f"CLI Version: {cli_version}")
    click.echo(f"CLI SHA: {cli_sha}")

    # Add server versions
    for key, value in versions_data.items():
        click.echo(f"{key}: {value}")
