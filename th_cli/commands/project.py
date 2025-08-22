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
from th_cli.exceptions import CLIError, handle_api_error, handle_file_error
from th_cli.utils import __print_json

TABLE_FORMAT = "{:<5} {:20} {:40}"


def _abort_if_false(ctx, value):
    if not value:
        ctx.abort()


@click.command(no_args_is_help=True)
@click.option(
    "--name",
    "-n",
    required=True,
    type=str,
    help="Name of the project",
)
@click.option(
    "--config",
    "-c",
    required=False,
    type=str,
    default=None,
    help="Config file for the project",
)
def create_project(name: str, config: Optional[str]) -> None:
    """Create a new project"""
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)

        # Get default config
        test_environment_config = sync_apis.projects_api.default_config_api_v1_projects_default_config_get()

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
            click.echo(f"Project '{response.name}' created with ID {response.id}")
        except UnexpectedResponse as e:
            handle_api_error(e, f"create project '{name}'")

    except CLIError:
        # Re-raise CLI errors as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise CLIError(f"Unexpected error creating project: {e}")
    finally:
        if client:
            client.close()


@click.command(no_args_is_help=True)
@click.option(
    "--id",
    "-i",
    required=True,
    type=int,
    help="Project ID to delete",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    callback=_abort_if_false,
    expose_value=False,
    prompt="Are you sure you want to delete the project?",
    help="Delete the project without confirmation",
)
def delete_project(id: int) -> None:
    """Delete a project"""
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        sync_apis.projects_api.delete_project_api_v1_projects_id_delete(id=id)
        click.echo(f"Project {id} was deleted.")
    except UnexpectedResponse as e:
        handle_api_error(e, f"delete project ID '{id}'")
    finally:
        if client:
            client.close()


@click.command()
@click.option(
    "--id",
    "-i",
    default=None,
    required=False,
    type=int,
    help="Fetch specific project via ID",
)
@click.option(
    "--skip",
    "-s",
    default=None,
    required=False,
    type=int,
    help="The first N projects to skip, ordered by ID",
)
@click.option(
    "--limit",
    "-l",
    default=None,
    required=False,
    type=int,
    help="Maximun number of projects to fetch",
)
@click.option(
    "--archived",
    default=False,
    is_flag=True,
    help="List only archived projects",
)
@click.option(
    "--json",
    is_flag=True,
    flag_value=True,
    help="Print JSON response for more details",
)
def list_projects(
    id: Optional[int], archived: Optional[bool], skip: Optional[int], limit: Optional[int], json: Optional[bool]
) -> None:
    """Get a list of projects"""

    client = None
    sync_apis = None

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
        click.echo(
            TABLE_FORMAT.format(
                "ID",
                "Project Name",
                "Updated Time",
            )
        )

        if isinstance(projects, list):
            for item in projects:
                __print_project(item.dict())

        if isinstance(projects, Project):
            __print_project(projects.dict())

        click.echo("\nFor more information, please use --json\n")

    def __print_project(project: dict) -> None:
        click.echo(
            TABLE_FORMAT.format(
                project.get("id"),
                project.get("name"),
                str(project.get("updated_at")),
            )
        )

    try:
        client = get_client()
        sync_apis = SyncApis(client)

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
    except CLIError:
        # Re-raise CLI errors as-is
        raise
    finally:
        if client:
            client.close()


@click.command(no_args_is_help=True)
@click.option(
    "--id",
    "-i",
    required=True,
    type=int,
    help="The ID for the project to update",
)
@click.option(
    "--config",
    "-c",
    required=True,
    type=str,
    help="New config file path",
)
def update_project(id: int, config: str):
    """Updates project with full test environment config file"""
    client = None
    try:
        client = get_client()
        sync_apis = SyncApis(client)
        file = open(config, "r")
        config_dict = json.load(file)
        projectUpdate = ProjectUpdate(**config_dict)
        response = sync_apis.projects_api.update_project_api_v1_projects_id_put(id=id, project_update=projectUpdate)
        click.echo(f"Project {response.name} is updated with the new config.")
    except json.JSONDecodeError as e:
        raise CLIError(f"Failed to parse JSON parameter: {e.msg}")
    except FileNotFoundError as e:
        handle_file_error(e, "config file")
    except ValidationError as e:
        raise CLIError(f"Invalid configuration: {e}")
    except UnexpectedResponse as e:
        handle_api_error(e, f"update project with '{id}'")
    finally:
        if client:
            client.close()
