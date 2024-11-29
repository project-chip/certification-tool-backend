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
from http import HTTPStatus
from typing import List, Sequence, Union

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError, parse_obj_as
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app import crud, models, schemas
from app.db.session import get_db
from app.default_environment_config import default_environment_config
from app.models.project import Project
from app.pics.pics_parser import PICSParser
from app.pics_applicable_test_cases import applicable_test_cases_list
from app.schemas.pics import PICSError
from app.schemas.project import Project as Proj
from app.schemas.test_environment_config import TestEnvironmentConfigError
from app.utils import TEST_ENVIRONMENT_CONFIG_NAME

router = APIRouter()


@router.get("/", response_model=List[schemas.Project])
def read_projects(
    db: Session = Depends(get_db),
    archived: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[models.Project]:
    """Retrieve list of projects

    Args:
        archived (bool, optional): Get archived projects, when true will; get archived
            projects only, when false only non-archived projects are returned.
            Defaults to false.
        skip (int, optional): Pagination offset. Defaults to 0.
        limit (int, optional): max number of records to return. Defaults to 100.

    Returns:
        List[Project]: List of projects
    """
    return crud.project.get_multi(db, archived=archived, skip=skip, limit=limit)


@router.post("/", response_model=schemas.Project)
def create_project(
    *,
    db: Session = Depends(get_db),
    project_in: schemas.ProjectCreate,
    request: Request,
) -> models.Project:
    """Create new project

    Args:
        project_in (ProjectCreate): Parameters for new project,  see schema for details

    Returns:
        Project: newly created project record
    """
    try:
        return crud.project.create(db=db, obj_in=project_in)
    except TestEnvironmentConfigError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get(
    "/default_config", response_model=Union[dict, schemas.TestEnvironmentConfig]
)
def default_config() -> Union[dict, schemas.TestEnvironmentConfig]:
    """Return default configuration for projects.

    Returns:
        List[Project]: List of projects
    """
    if not default_environment_config:
        return {
            "alert": "No program configuration file was found. "
            "If you want default values for the project configuration, please, "
            f"create a {TEST_ENVIRONMENT_CONFIG_NAME} file inside "
            "test_collections/{program} folder"
        }

    return default_environment_config


@router.put("/{id}", response_model=schemas.Project)
def update_project(
    *,
    db: Session = Depends(get_db),
    id: int,
    project_in: schemas.ProjectUpdate,
    request: Request,
) -> models.Project:
    """Update an existing project

    Args:
        id (int): project id
        project_in (schemas.ProjectUpdate): projects parameters to be updated

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        Project: updated project record
    """
    try:
        return crud.project.update(
            db=db, db_obj=__project(db=db, id=id), obj_in=project_in
        )
    except HTTPException:
        raise
    except TestEnvironmentConfigError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/{id}", response_model=schemas.Project)
def read_project(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> models.Project:
    """Lookup project by id

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        Project: project record
    """

    return __project(db=db, id=id)


@router.delete("/{id}", response_model=schemas.Project)
def delete_project(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> models.Project:
    """Delete project by id

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        Project: project record that was deleted
    """
    project = crud.project.remove(db=db, id=id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )

    return project


@router.post("/{id}/archive", response_model=schemas.Project)
def archive_project(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> models.Project:
    """Archive project by id.

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        Project: project record that was archived
    """

    return crud.project.archive(db=db, db_obj=__project(db=db, id=id))


@router.post("/{id}/unarchive", response_model=schemas.Project)
def unarchive_project(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> models.Project:
    """Unarchive project by id.

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        Project: project record that was unarchived
    """

    return crud.project.unarchive(db=db, db_obj=__project(db=db, id=id))


@router.put("/{id}/upload_pics", response_model=schemas.Project)
def upload_pics(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    id: int,
) -> models.Project:
    """Upload PICS file of a project based on project identifier.

    Args:
        id (int): project id
        file : the PICS file to upload

    Raises:
        HTTPException: if no project exists for provided project id (or)
                       if the PICS file is invalid

    Returns:
        Project: project record that was updated with the PICS information
    """
    cluster = PICSParser.parse(file=file.file)

    project = __project(db=db, id=id)
    project.pics.clusters[cluster.name] = cluster

    return __persist_pics_update(db=db, project=project)


@router.delete("/{id}/pics_cluster_type", response_model=schemas.Project)
def remove_pics_cluster_type(
    *,
    db: Session = Depends(get_db),
    id: int,
    cluster_name: str,
) -> models.Project:
    """Removes cluster based on given cluster name

    Args:
        id (int): ID of Project
        cluster_name (str): Name of the cluster to delete

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        models.Project: Project with updated PICS entry
    """
    project = __project(db=db, id=id)

    if cluster_name not in project.pics.clusters.keys():
        raise PICSError(f"Cluster {cluster_name} does not exist")

    # delete the PICS cluster.
    del project.pics.clusters[cluster_name]

    return __persist_pics_update(db=db, project=project)


@router.get(
    "/{id}/applicable_test_cases", response_model=schemas.PICSApplicableTestCases
)
def applicable_test_cases(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> schemas.PICSApplicableTestCases:
    """Retrieve list of applicable test cases based on project identifier.

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        PICSApplicableTestCases: List of applicable test cases
    """
    project = __project(db=db, id=id)

    project_data = Proj.from_orm(project)

    return applicable_test_cases_list(pics=project_data.pics)


def __project(db: Session, id: int) -> Project:
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )
    return project


def __persist_pics_update(db: Session, project: Project) -> Project:
    """Update Project PICS in DB.

    project.pics is stored in a JSON column mapped to PICS schema, this column is
    not Mutable, so SQLAlchemy doesn't know when PICS changed.

    Using `flag_modified` marks the property, so SQLAlchemy will update the field on
    commit.
    """
    flag_modified(project, "pics")
    db.commit()
    db.refresh(project)
    return project


@router.get("/{id}/export", response_model=schemas.ProjectCreate)
def export_project_config(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> JSONResponse:
    """
    Exports the project config by id.

    Args:
        id (int): project id

    Raises:
        HTTPException: if no project exists for provided project id

    Returns:
        JSONResponse: json representation of the project with the informed project id
    """
    # Retrieve project by project_id using schemas.ProjectCreate schema
    project = schemas.ProjectCreate(**__project(db=db, id=id).__dict__)

    options: dict = {"media_type": "application/json"}
    filename = f"{project.name}-project-config.json"
    options["headers"] = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return JSONResponse(
        jsonable_encoder(project),
        **options,
    )


@router.post("/import", response_model=schemas.Project)
def importproject_config(
    *,
    db: Session = Depends(get_db),
    import_file: UploadFile = File(...),
) -> models.Project:
    """
    Imports the project config

    Args:
        import_file : The project config file to be imported

    Raises:
        ValidationError: if the imported project config contains invalid information

    Returns:
        Project: newly created project record
    """

    file_content = import_file.file.read().decode("utf-8")
    file_dict = json.loads(file_content)

    try:
        imported_project: schemas.ProjectCreate = parse_obj_as(
            schemas.ProjectCreate, file_dict
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(error)
        )

    try:
        return crud.project.create(db=db, obj_in=imported_project)
    except TestEnvironmentConfigError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
