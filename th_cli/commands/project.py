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
from typing import Any, List, Optional

import click
from pydantic import ValidationError

from th_cli.api_lib_autogen.api_client import SyncApis
from th_cli.api_lib_autogen.exceptions import UnexpectedResponse
from th_cli.api_lib_autogen.models import Project, ProjectCreate, ProjectUpdate, TestEnvironmentConfig
from th_cli.client import get_client
from th_cli.colorize import colorize_cmd_help, colorize_error, colorize_header, colorize_help, colorize_success, italic
from th_cli.exceptions import CLIError, handle_api_error, handle_file_error
from th_cli.utils import __print_json

TABLE_FORMAT = "{:<5} {:25} {:28}"


def _abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


@click.command(
    short_help=colorize_help("Manage projects"),
    help=colorize_cmd_help("project", "Create, list, update, or delete projects"),
)
@click.argument(
    "operation",
    type=click.Choice(["create", "list", "update", "delete"], case_sensitive=False),
)
@click.option(
    "--id",
    "-i",
    type=int,
    help=colorize_help("Project ID (required for update/delete operations, optional for list)"),
)
@click.option(
    "--name",
    "-n",
    type=str,
    help=colorize_help("Name of the project (required for create operation)"),
)
@click.option(
    "--config",
    "-c",
    type=click.Path(file_okay=True, dir_okay=False),
    help=colorize_help("Config JSON file for the project (optional for create, required for update)"),
)
@click.option(
    "--skip",
    "-s",
    type=int,
    help=colorize_help("The first N projects to skip, ordered by ID (list operation only)"),
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help=colorize_help("Maximum number of projects to fetch (list operation only)"),
)
@click.option(
    "--archived",
    is_flag=True,
    default=False,
    help=colorize_help("List only archived projects (list operation only)"),
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help=colorize_help("Print JSON response for more details (list operation only)"),
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help=colorize_help("Delete the project without confirmation (delete operation only)"),
)
def project(
    operation: str,
    id: Optional[int],
    name: Optional[str],
    config: Optional[str],
    skip: Optional[int],
    limit: Optional[int],
    archived: Optional[bool] = False,
    json: Optional[bool] = False,
    yes: Optional[bool] = False,
) -> None:
    """Manage projects - create, list, update, or delete"""

    # Validate operation-specific requirements
    if operation == "create":
        if not name:
            raise click.ClickException("--name is required for create operation")
    elif operation == "update":
        if not id:
            raise click.ClickException("--id is required for update operation")
        if not config:
            raise click.ClickException("--config is required for update operation")
    elif operation == "delete":
        if not id:
            raise click.ClickException("--id is required for delete operation")
        if not yes:
            if not click.confirm(colorize_error("Are you sure you want to delete the project?")):
                click.echo("Operation cancelled.")
                return

    client = None
    sync_apis = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        if operation == "create":
            _create_project(sync_apis, name, config)
        elif operation == "list":
            _list_projects(sync_apis, id, archived, skip, limit, json)
        elif operation == "update":
            _update_project(sync_apis, id, config)
        elif operation == "delete":
            _delete_project(sync_apis, id)
    except CLIError:
        raise  # Re-raise CLI Errors as-is
    except Exception as e:
        # Catch any unexpected errors
        raise CLIError(f"Unexpected error in {operation} operation: {e}")
    finally:
        if client:
            client.close()


def _create_project(sync_apis: SyncApis, name: str, config: Optional[str]) -> None:
    """Create a new project"""
    # Get default config
    try:
        test_environment_config = sync_apis.projects_api.default_config_api_v1_projects_default_config_get()
    except UnexpectedResponse as e:
        handle_api_error(e, "get default config")

    # Load custom config if provided
    if config:
        try:
            with open(config, "r") as f:
                config_dict = json.load(f)
            test_environment_config = TestEnvironmentConfig(**config_dict)
        except FileNotFoundError as e:
            handle_file_error(e, "config file")
        except json.JSONDecodeError as e:
            raise CLIError(f"Invalid JSON in config file: {e.msg}")
        except ValidationError as e:
            raise CLIError(f"Invalid configuration: {e}")

    # Create project
    project_create = ProjectCreate(name=name, config=test_environment_config)

    try:
        response = sync_apis.projects_api.create_project_api_v1_projects_post(project_create=project_create)
        click.echo(colorize_success(f"Project '{response.name}' created with ID {response.id}"))
    except UnexpectedResponse as e:
        handle_api_error(e, f"create project '{name}'")


def _list_projects(
    sync_apis: SyncApis,
    id: Optional[int],
    archived: bool,
    skip: Optional[int],
    limit: Optional[int],
    json: bool,
) -> None:
    """List projects"""

    def __list_project_by_id(id: int) -> Project:
        try:
            return sync_apis.projects_api.read_project_api_v1_projects_id_get(id=id)
        except UnexpectedResponse as e:
            handle_api_error(e, f"list project with id '{id}'")

    def __list_project_by_batch(
        archived: bool, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> List[Project]:
        try:
            return sync_apis.projects_api.read_projects_api_v1_projects_get(archived=archived, skip=skip, limit=limit)
        except UnexpectedResponse as e:
            handle_api_error(e, "list projects")

    def __print_table(projects: Any) -> None:
        click.echo(colorize_header(TABLE_FORMAT.format("ID", "Project Name", "Updated Time")))

        if isinstance(projects, list):
            for item in projects:
                __print_project(item.dict())

        if isinstance(projects, Project):
            __print_project(projects.dict())

        click.echo(italic("\nFor more information, please use --json\n"))

    def __print_project(project: dict) -> None:
        click.echo(
            TABLE_FORMAT.format(
                project.get("id"),
                project.get("name"),
                str(project.get("updated_at")),
            )
        )

    if id is not None:
        projects = __list_project_by_id(id)
    else:
        projects = __list_project_by_batch(archived, skip, limit)

    if projects is None or (isinstance(projects, list) and len(projects) == 0):
        raise CLIError("Server did not return any project")

    if json:
        __print_json(projects)
    else:
        __print_table(projects)


def _update_project(sync_apis: SyncApis, id: int, config: str) -> None:
    """Update an existing project"""
    try:
        with open(config, "r") as f:
            config_dict = json.load(f)
        project_update = ProjectUpdate(**config_dict)
        response = sync_apis.projects_api.update_project_api_v1_projects_id_put(id=id, project_update=project_update)
        click.echo(colorize_success(f"Project {response.name} is updated with the new config."))
    except json.JSONDecodeError as e:
        raise CLIError(f"Failed to parse JSON parameter: {e.msg}")
    except FileNotFoundError as e:
        handle_file_error(e, "config file")
    except ValidationError as e:
        raise CLIError(f"Invalid configuration: {e}")
    except UnexpectedResponse as e:
        handle_api_error(e, f"update project with '{id}'")


def _delete_project(sync_apis: SyncApis, id: int) -> None:
    """Delete a project"""
    try:
        sync_apis.projects_api.delete_project_api_v1_projects_id_delete(id=id)
        click.echo(colorize_success(f"Project {id} was deleted."))
    except UnexpectedResponse as e:
        handle_api_error(e, f"delete project ID '{id}'")
