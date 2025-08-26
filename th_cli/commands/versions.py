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
import subprocess

import click
import tomli

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.client import get_client
from th_cli.config import find_git_root, get_package_root
from th_cli.exceptions import handle_api_error


def get_cli_version() -> str:
    """Get CLI version from pyproject.toml"""
    try:
        # Try package root first
        package_root = get_package_root()
        pyproject_path = package_root / "pyproject.toml"

        if not pyproject_path.exists():
            # If not found in package root, try git root
            git_root = find_git_root()
            if git_root:
                pyproject_path = git_root / "pyproject.toml"

        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)
                version = pyproject_data.get("project", {}).get("version")
                if version:
                    return version
        return "unknown"
    except (FileNotFoundError, IOError):
        return "unknown"


def get_cli_sha() -> str:
    """Get current CLI SHA from git"""
    try:
        # Always use git root for git operations - this ensures we find the original repo
        git_root = find_git_root()
        if not git_root:
            return "unknown"

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=git_root,
        )
        return result.stdout.strip()[:8]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@click.command()
def versions() -> None:
    """Get application versions information"""
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        versions_api = sync_apis.versions_api

        versions_info = versions_api.get_versions_api_v1_versions_get()
        _print_versions_table(versions_info)
    except UnexpectedResponse as e:
        handle_api_error(e, "get versions")
    finally:
        if client:
            client.close()


def _print_versions_table(versions_data: dict) -> None:
    """Print versions in a formatted table"""
    click.echo("Application Versions")
    click.echo("=" * 30)
    click.echo("")

    # Add CLI version and SHA first
    cli_version = get_cli_version()
    cli_sha = get_cli_sha()

    click.echo(f"CLI Version: {cli_version}")
    click.echo(f"CLI SHA: {cli_sha}")

    # Add server versions
    for key, value in versions_data.items():
        click.echo(f"{key}: {value}")
