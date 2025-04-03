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
import traceback
from http import HTTPStatus
from typing import List, Sequence, Union

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError, parse_obj_as
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app import crud, models, schemas
from app.db.session import get_db
from app.default_environment_config import default_environment_config
from app.models.project import Project
from app.pics.pics_parser import PICSParser
from app.pics_applicable_test_cases import applicable_test_cases_set
from app.schemas.pics import PICSError
from app.schemas.project import Project as Proj
from app.schemas.test_environment_config import TestEnvironmentConfigError
from app.utils import (
    DMP_TEST_SKIP_CONFIG_NODE,
    DMP_TEST_SKIP_FILENAME,
    TEST_ENVIRONMENT_CONFIG_NAME,
    parse_dmp_file,
)

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


def __upload_pics(file: UploadFile, db: Session, project: Project) -> Project:
    cluster = PICSParser.parse(file=file.file)

    project.pics.clusters[cluster.name] = cluster

    return __persist_update_not_mutable(db=db, project=project, field="pics")


def __persist_dmp_test_skip(file: UploadFile, db: Session, project: Project) -> Project:
    try:
        skip_test_list = parse_dmp_file(xml_file=file.file)
        project.config[DMP_TEST_SKIP_CONFIG_NODE] = skip_test_list

        return __persist_update_not_mutable(db=db, project=project, field="config")
    except Exception:
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Not able to parse {file.filename} file",
        )


@router.put("/{id}/upload_pics", response_model=schemas.Project)
async def upload_pics(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    id: int,
) -> models.Project:
    """Upload PICS or dmp-test-skip.xml file of a project based on project identifier.

    Args:
        id (int): project id
        file : the PICS or dmp-test-skip.xml file to upload

    Raises:
        HTTPException: if no project exists for provided project id (or)
                       if the PICS file is invalid

    Returns:
        Project: project record that was updated with the PICS and dmp_test_skip
        information.
    """
    project = __project(db=db, id=id)

    try:
        if file and file.filename and file.filename.startswith(DMP_TEST_SKIP_FILENAME):
            return __persist_dmp_test_skip(file=file, db=db, project=project)
        else:
            return __upload_pics(file=file, db=db, project=project)
    except PICSError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Not able to parse {file.filename} file: {str(e)}",
        )


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

    return __persist_update_not_mutable(db=db, project=project, field="pics")


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

    try:
        return applicable_test_cases_set(
            pics=project_data.pics,
            dmp_test_skip=project_data.config.get(DMP_TEST_SKIP_CONFIG_NODE, []),
        )
    except Exception as e:
        logger.error(f"Error getting applicable test cases: {str(e)}")
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=f"Error getting applicable test cases: {str(e)}",
        )


def __project(db: Session, id: int) -> Project:
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )
    return project


def __persist_update_not_mutable(db: Session, project: Project, field: str) -> Project:
    """Update Project JSON fields in DB.

    Project contains JSON columns (like 'pics' and 'config') mapped to their respective
    schemas.
    These columns are not Mutable by default, so SQLAlchemy doesn't track changes
    to their content.

    Using `flag_modified` explicitly marks the JSON property as changed, ensuring
    SQLAlchemy will update the field on commit. This is necessary for any nested
    modifications to JSON column data.
    """

    flag_modified(project, field)
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
