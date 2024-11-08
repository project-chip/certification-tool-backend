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
import os
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError, parse_obj_as
from sqlalchemy.orm import Session

from app import crud, log_utils, models, schemas
from app.api import DEFAULT_404_MESSAGE
from app.crud.crud_test_run_execution import ImportError
from app.db.session import get_db
from app.models.test_run_execution import TestRunExecution
from app.test_engine import TEST_ENGINE_ABORTING_TESTING_MESSAGE
from app.test_engine.test_runner import AbortError, LoadingError, TestRunner
from app.test_engine.test_script_manager import TestNotFound
from app.utils import (
    formated_datetime_now_str,
    remove_title_date,
    selected_tests_from_execution,
)
from app.version import version_information
from test_collections.matter.sdk_tests.support.performance_tests.utils import (
    create_summary_report,
)
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter

router = APIRouter()


@router.get("/", response_model=List[schemas.TestRunExecutionWithStats])
def read_test_run_executions(
    db: Session = Depends(get_db),
    project_id: Optional[int] = None,
    archived: bool = False,
    search_query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[schemas.TestRunExecutionWithStats]:
    """Retrieve test runs, including statistics.

    Args:
        project_id: Filter test runs by project.
        archived: Get archived test runs, when true will return archived
            test runs only, when false only non-archived test runs are returned.
        skip: Pagination offset.
        limit: Max number of records to return.

    Returns:
        List of test runs with execution statistics.
    """
    return crud.test_run_execution.get_multi_with_stats(
        db,
        project_id=project_id,
        archived=archived,
        search_query=search_query,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=schemas.TestRunExecutionWithChildren)
def create_test_run_execution(
    *,
    db: Session = Depends(get_db),
    test_run_execution_in: schemas.TestRunExecutionCreate,
    selected_tests: schemas.TestSelection,
    certification_mode: bool = False,
) -> TestRunExecution:
    """Create a new test run execution."""

    # TODO: Remove test_run_config completely from the project
    test_run_execution_in.test_run_config_id = None
    test_run_execution_in.certification_mode = certification_mode

    test_run_execution = crud.test_run_execution.create(
        db=db, obj_in=test_run_execution_in, selected_tests=selected_tests
    )
    return test_run_execution


@router.post("/abort-testing", response_model=Dict[str, str])
def abort_testing(
    *,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Cancel the current testing
    """

    try:
        TestRunner().abort_testing()
    except AbortError as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))

    return {"detail": TEST_ENGINE_ABORTING_TESTING_MESSAGE}


@router.get(
    "/status", response_model=schemas.TestRunnerStatus, response_model_exclude_none=True
)
def get_test_runner_status() -> dict[str, Any]:
    """
    Retrieve status of the Test Engine.

    When the Test Engine is actively running the status will include the current
    test_run and the details of the states.
    """
    test_runner = TestRunner()
    status: dict[str, Any] = {"state": test_runner.state}
    if test_runner.test_run is not None:
        status["test_run_execution_id"] = test_runner.test_run.test_run_execution.id

    return status


@router.get("/{id}", response_model=schemas.TestRunExecutionWithChildren)
def read_test_run_execution(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> TestRunExecution:
    """
    Get test run by ID, including state on all children
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=DEFAULT_404_MESSAGE
        )
    return test_run_execution


@router.post("/{id}/start", response_model=schemas.TestRunExecutionWithChildren)
def start_test_run_execution(
    *,
    db: Session = Depends(get_db),
    id: int,
    background_tasks: BackgroundTasks,
) -> TestRunExecution:
    """
    Start a test run by ID
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )

    test_runner = TestRunner()

    try:
        test_runner.load_test_run(test_run_execution.id)
    except LoadingError as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))
    except TestNotFound as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(error)
        )

    background_tasks.add_task(test_runner.run)
    return test_run_execution


@router.post("/{id}/archive", response_model=schemas.TestRunExecution)
def archive(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """Archive test run execution by id.

    Args:
        id (int): test run execution id

    Raises:
        HTTPException: if no test run execution exists for provided id

    Returns:
        TestRunExecution: test run execution record that was archived
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="TestRunExecution not found"
        )

    return crud.test_run_execution.archive(db=db, db_obj=test_run_execution)


@router.post("/{id}/unarchive", response_model=schemas.TestRunExecution)
def unarchive(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """Unarchive test run execution by id.

    Args:
        id (int): test run execution id

    Raises:
        HTTPException: if no test run execution exists for provided id

    Returns:
        TestRunExecution: test run execution record that was unarchived
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="TestRunExecution not found"
        )

    return crud.test_run_execution.unarchive(db=db, db_obj=test_run_execution)


@router.post("/{id}/repeat", response_model=schemas.TestRunExecutionWithChildren)
def repeat_test_run_execution(
    *, db: Session = Depends(get_db), id: int, title: Optional[str] = None
) -> TestRunExecution:
    """Repeat a test run execution by id.

    Args:
        id (int): test run execution id
        title (str): Optional title to the repeated test run execution. If not provided,
            the old title will be used with the date and time updated.

    Raises:
        HTTPException: if no test run execution exists for the provided id

    Returns:
        TestRunExecution: new test run execution with the same test cases from id
    """
    execution_to_repeat = crud.test_run_execution.get(db=db, id=id)
    if not execution_to_repeat:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="TestRunExecution not found"
        )

    if title is None:
        # If no title is provided, the old title will be used without data info
        title = remove_title_date(execution_to_repeat.title)

    date_now = formated_datetime_now_str()
    title += date_now

    test_run_execution_in = schemas.TestRunExecutionCreate(title=title)
    test_run_execution_in.description = execution_to_repeat.description
    test_run_execution_in.project_id = execution_to_repeat.project_id
    test_run_execution_in.operator_id = execution_to_repeat.operator_id
    test_run_execution_in.certification_mode = execution_to_repeat.certification_mode
    # TODO: Remove test_run_config completely from the project
    test_run_execution_in.test_run_config_id = None

    selected_tests = selected_tests_from_execution(execution_to_repeat)

    return crud.test_run_execution.create(
        db=db, obj_in=test_run_execution_in, selected_tests=selected_tests
    )


@router.delete("/{id}", response_model=schemas.TestRunExecutionInDBBase)
def remove_test_run_execution(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Remove test run execution
    """
    current_test_run = TestRunner().test_run

    # Check if the current test run is active, hence cannot be deleted
    if current_test_run is not None and current_test_run.test_run_execution.id == id:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail="Test Run Execution still running"
        )

    test_run_execution = crud.test_run_execution.remove(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )
    return test_run_execution


@router.get("/{id}/log", response_class=StreamingResponse)
def download_log(
    *,
    db: Session = Depends(get_db),
    id: int,
    json_entries: bool = False,
    download: bool = False,
) -> Any:
    """Download the logs from a test run.


    Args:
        id (int): Id of the TestRunExectution the log is requested for
        json_entries (bool, optional): When set, return each log line as a json object
        download (bool, optional): When set, return as attachment
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )

    options: dict = {"media_type": "text/plain"}
    if download:
        filename = f"{test_run_execution.id}-{test_run_execution.title}.log"
        options["headers"] = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }

    log_output = log_utils.convert_execution_log_to_list(
        log=test_run_execution.log, json_entries=json_entries
    )

    return StreamingResponse(
        log_utils.async_log_generator(items=log_output),
        **options,
    )


@router.get("/{id}/grouped-log", response_class=StreamingResponse)
def download_grouped_log(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> StreamingResponse:
    """Download the logs from a test run, grouped by test case state.

    Args:
        id (int): ID of the TestRunExectution the log is requested for

    Raises:
        HTTPException: If there's no TestRunExectution with the given ID

    Returns:
        StreamingResponse: .zip file containing: one file with the list of test cases
        for each state; one file with the logs from the executed test suites; one file
        per state with the logs from all test cases that finished with that state
    """
    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )

    logs = log_utils.group_test_run_execution_logs(
        test_run_execution=test_run_execution
    )

    zip_file = log_utils.create_grouped_log_zip_file(grouped_logs=logs)

    file_name = f"{test_run_execution.id}-{test_run_execution.title}.zip"
    options: dict = {
        "media_type": "application/zip",
        "headers": {"Content-Disposition": f'attachment; filename="{file_name}"'},
    }

    return StreamingResponse(
        zip_file,
        **options,
    )


@router.post("/file_upload/")
def upload_file(
    *,
    file: UploadFile = File(...),
) -> None:
    """Upload a file to the specified path of the current test run.

    Args:
        file: The file to upload.
    """
    try:
        TestRunner().handle_uploaded_file(file=file)
    except AttributeError as error:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(error))


@router.get("/{id}/export", response_model=schemas.ExportedTestRunExecution)
def export_test_run_execution(
    *,
    db: Session = Depends(get_db),
    id: int,
    download: bool = False,
) -> JSONResponse:
    """
    Exports a test run execution by the given ID.
    """

    export_run_execution = crud.test_run_execution.get(db=db, id=id)

    if not export_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Test Run Execution with id {id} not found",
        )

    export_test_run_schema = schemas.ExportedTestRunExecution(
        db_revision=version_information.db_revision,
        test_run_execution=schemas.TestRunExecutionToExport.from_orm(
            export_run_execution
        ),
    )

    options: dict = {"media_type": "application/json"}
    if download:
        filename = f"ExportedTestRunExecution-{export_run_execution.title}.json"
        options["headers"] = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }

    return JSONResponse(
        jsonable_encoder(export_test_run_schema),
        **options,
    )


@router.post("/import", response_model=schemas.TestRunExecutionWithChildren)
def import_test_run_execution(
    *,
    db: Session = Depends(get_db),
    project_id: int,
    import_file: UploadFile = File(...),
) -> models.TestRunExecution:
    """
    Imports a test run execution to the the given project_id.
    """

    file_content = import_file.file.read().decode("utf-8")
    file_dict = json.loads(file_content)

    try:
        exported_test_run_execution = parse_obj_as(
            schemas.ExportedTestRunExecution, file_dict
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(error)
        )

    if exported_test_run_execution.db_revision != version_information.db_revision:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=(
                f"Mismatching 'db_revision'. Trying to import from"
                f" {exported_test_run_execution.db_revision} to"
                f" {version_information.db_revision}"
            ),
        )

    try:
        return crud.test_run_execution.import_execution(
            db=db,
            project_id=project_id,
            execution=exported_test_run_execution.test_run_execution,
        )
    except ImportError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(error),
        )


date_pattern_out_file = "%Y_%m_%d_%H_%M_%S"


@router.post("/{id}/performance_summary")
def generate_summary_log(
    *,
    db: Session = Depends(get_db),
    id: int,
    project_id: int,
) -> JSONResponse:
    """
    Imports a test run execution to the the given project_id.
    """

    project = crud.project.get(db=db, id=project_id)

    if not project:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )

    project_config = TestEnvironmentConfigMatter(**project.config)
    matter_qa_url = None
    LOGS_FOLDER = "/test_collections/logs"
    HOST_BACKEND = os.getenv("BACKEND_FILEPATH_ON_HOST") or ""
    HOST_OUT_FOLDER = HOST_BACKEND + LOGS_FOLDER

    if (
        project_config.test_parameters
        and "matter_qa_url" in project_config.test_parameters
    ):
        matter_qa_url = project_config.test_parameters["matter_qa_url"]
    else:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="matter_qa_url must be configured",
        )

    page = requests.get(f"{matter_qa_url}/home")
    if page.status_code is not int(HTTPStatus.OK):
        raise HTTPException(
            status_code=page.status_code,
            detail=(
                "The LogDisplay server is not responding.\n"
                "Verify if the tool was installed, configured and initiated properly"
            ),
        )

    commissioning_method = project_config.dut_config.pairing_mode

    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )

    log_lines_list = log_utils.convert_execution_log_to_list(
        log=test_run_execution.log, json_entries=False
    )

    timestamp = ""
    if test_run_execution.started_at:
        timestamp = test_run_execution.started_at.strftime(date_pattern_out_file)
    else:
        timestamp = datetime.now().strftime(date_pattern_out_file)

    tc_name, execution_time_folder = create_summary_report(
        timestamp, log_lines_list, commissioning_method
    )

    target_dir = f"{HOST_OUT_FOLDER}/{execution_time_folder}/{tc_name}"
    url_report = f"{matter_qa_url}/home/displayLogFolder?dir_path={target_dir}"

    summary_report: dict = {}
    summary_report["url"] = url_report

    options: dict = {"media_type": "application/json"}

    return JSONResponse(
        jsonable_encoder(summary_report),
        **options,
    )
