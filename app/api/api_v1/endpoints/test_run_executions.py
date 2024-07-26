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
import re
import shutil
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional

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
from test_collections.matter.test_environment_config import TestEnvironmentConfigMatter

router = APIRouter()

date_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+"

date_pattern_out_folder = "%d-%m-%Y_%H-%M-%S-%f"

date_pattern_out_file = "%Y_%m_%d_%H_%M_%S"

datetime_json_pattern = "%Y-%m-%dT%H:%M:%S.%f"


class Commissioning:
    stages = {
        "discovery": {
            "begin": "(?=.*Internal\\ Control\\ start\\ simulated\\ app)",
            "end": "(?=.*Discovered\\ Device)",
        },
        "readCommissioningInfo": {
            "begin": "(?=.*ReadCommissioningInfo)(?=.*Performing)",
            "end": "(?=.*ReadCommissioningInfo)(?=.*Successfully)",
        },
        "PASE": {
            "begin": "(?=.*PBKDFParamRequest)",
            "end": "(?=.*'kEstablishing'\\ \\-\\->\\ 'kActive')",
        },
        "cleanup": {
            "begin": "(?=.*Cleanup)(?=.*Performing)",
            "end": "(?=.*Cleanup)(?=.*Successfully)",
        },
    }

    def __init__(self) -> None:
        self.commissioning: dict[str, Any] = {}

    def __repr__(self) -> str:
        return self.commissioning.__repr__()

    def add_event(self, line: str) -> None:
        for stage, patterns in self.stages.items():
            begin = None
            end = None
            if not (stage in self.commissioning):
                self.commissioning[stage] = {}

            # pattern_begin = f"(?=.*{re.escape(stage)})(?=.*{re.escape(self.step_type[0])})"
            if re.search(patterns["begin"], line) is not None:
                match = re.findall(date_pattern, line)
                if match[0]:
                    begin = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")
                    if stage == "discovery":
                        self.commissioning["begin"] = begin
                    self.commissioning[stage]["begin"] = begin

            # pattern_end = f"(?=.*{re.escape(stage)})(?=.*{re.escape(self.step_type[1])})"
            if re.search(patterns["end"], line) is not None:
                match = re.findall(date_pattern, line)
                if match[0]:
                    end = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")
                    if stage == "cleanup":
                        self.commissioning["end"] = end
                    self.commissioning[stage]["end"] = end


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
) -> TestRunExecution:
    """Create a new test run execution."""

    # TODO: Remove test_run_config completely from the project
    test_run_execution_in.test_run_config_id = None

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


def extract_datetime(line: str) -> Optional[datetime]:
    line_datetime = None
    match = re.findall(date_pattern, line)
    if match[0]:
        line_datetime = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")

    return line_datetime


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
    CONTAINER_BACKEND = os.getenv("PYTHONPATH") or ""
    HOST_OUT_FOLDER = HOST_BACKEND + LOGS_FOLDER
    CONTAINER_OUT_FOLDER = CONTAINER_BACKEND + LOGS_FOLDER
    if os.path.exists(CONTAINER_OUT_FOLDER):
        shutil.rmtree(CONTAINER_OUT_FOLDER)
    os.makedirs(CONTAINER_OUT_FOLDER)

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

    commissioning_method = project_config.dut_config.pairing_mode

    test_run_execution = crud.test_run_execution.get(db=db, id=id)
    if not test_run_execution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Test Run Execution not found"
        )

    log_lines_list = log_utils.convert_execution_log_to_list(
        log=test_run_execution.log, json_entries=False
    )
    log_lines = "\n".join(log_lines_list)

    out_datetime = ""
    if test_run_execution.started_at:
        out_datetime = test_run_execution.started_at.strftime(date_pattern_out_file)
    else:
        out_datetime = datetime.now().strftime(date_pattern_out_file)

    with open(
        CONTAINER_OUT_FOLDER + f"/Performance_Test_Run_{out_datetime}.log", "w"
    ) as f:
        f.write(str(log_lines))

    files = os.listdir(CONTAINER_OUT_FOLDER)

    commissioning_list = []

    execution_begin_time = []
    execution_end_time = []

    execution_logs = []
    execution_status = []

    for file_name in files:
        file_path = os.path.join(CONTAINER_OUT_FOLDER, file_name)
        commissioning_obj: Optional[Commissioning] = None
        file_execution_time = None
        tc_name = ""
        tc_suite = ""
        tc_result = None
        tc_execution_in_file = 0

        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                for line in file:
                    line = line.strip()

                    if not line:
                        continue

                    if not file_execution_time:
                        file_execution_time = extract_datetime(line)

                    if not tc_suite:
                        if line.find("Test Suite Executing:") > 0:
                            tc_suite = line.split(": ")[1]

                    if not tc_name:
                        if line.find("Executing Test Case:") > 0:
                            tc_name = line.split(": ")[1]

                    if not tc_result:
                        if line.find("Test Case Completed[") > 0:
                            extract_datetime(line)

                            m = re.search(r"\[([A-Za-z0-9_]+)\]", line)
                            if m:
                                tc_result = m.group(1)

                                # Add TC result
                                for x in range(0, tc_execution_in_file):
                                    if tc_result == "PASSED":
                                        tc_result = "PASS"
                                    elif tc_result == "FAILED":
                                        tc_result = "FAIL"

                                    execution_status.append(tc_result)

                    pattern_begin = f"(?=.*{re.escape('Begin Commission')})"
                    pattern_end = (
                        f"(?=.*{re.escape('Internal Control stop simulated app')})"
                    )
                    if re.search(pattern_begin, line) is not None:
                        commissioning_obj = Commissioning()
                        continue

                    elif re.search(pattern_end, line) is not None:
                        if commissioning_obj is not None:
                            commissioning_list.append(commissioning_obj)
                            execution_logs.append(file_path)
                            tc_execution_in_file = tc_execution_in_file + 1

                        continue

                    elif commissioning_obj is not None:
                        commissioning_obj.add_event(line)

    durations = []
    read_durations = []
    discovery_durations = []
    PASE_durations = []
    for commissioning in commissioning_list:
        begin = int(commissioning.commissioning["begin"].timestamp() * 1000000)
        end = int(commissioning.commissioning["end"].timestamp() * 1000000)

        execution_begin_time.append(commissioning.commissioning["begin"])
        execution_end_time.append(commissioning.commissioning["end"])

        read_begin = int(
            commissioning.commissioning["readCommissioningInfo"]["begin"].timestamp()
            * 1000000
        )
        read_end = int(
            commissioning.commissioning["readCommissioningInfo"]["end"].timestamp()
            * 1000000
        )

        discovery_begin = int(
            commissioning.commissioning["discovery"]["begin"].timestamp() * 1000000
        )
        discovery_end = int(
            commissioning.commissioning["discovery"]["end"].timestamp() * 1000000
        )

        PASE_begin = int(
            commissioning.commissioning["PASE"]["begin"].timestamp() * 1000000
        )
        PASE_end = int(commissioning.commissioning["PASE"]["end"].timestamp() * 1000000)

        duration = end - begin
        read_duration = read_end - read_begin
        discovery_duration = discovery_end - discovery_begin
        PASE_duration = PASE_end - PASE_begin
        durations.append(duration)
        read_durations.append(read_duration)
        discovery_durations.append(discovery_duration)
        PASE_durations.append(PASE_duration)

    execution_time_folder = execution_begin_time[0].strftime(date_pattern_out_folder)[
        :-3
    ]

    generate_summary(
        execution_logs,
        execution_status,
        execution_time_folder,
        execution_begin_time,
        execution_end_time,
        tc_suite,
        tc_name,
        commissioning_method,
        durations,
        discovery_durations,
        read_durations,
        PASE_durations,
        CONTAINER_OUT_FOLDER,
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


def compute_state(execution_status: list) -> str:
    if any(tc for tc in execution_status if tc == "CANCELLED"):
        return "FAIL"

    if any(tc for tc in execution_status if tc == "ERROR"):
        return "FAIL"

    if any(tc for tc in execution_status if tc == "FAIL"):
        return "FAIL"

    if any(tc for tc in execution_status if tc == "PENDING"):
        return "FAIL"

    return "PASS"


def compute_count_state(execution_status: list, passed: bool = True) -> str:
    # State is computed based test_suite errors and on on test case states.
    #
    # if self.errors is not None and len(self.errors) > 0:
    #     return "ERROR"

    # Note: These loops cannot be easily coalesced as we need to iterate through
    # and assign Test Suite State in order.
    count = 0
    for tc in execution_status:
        if tc == "PASS" and passed or (tc != "PASS" and not passed):
            count = count + 1

    return str(count)


def generate_summary(
    execution_logs: list,
    execution_status: list,
    folder_name: str,
    execution_begin_time: list,
    execution_end_time: list,
    tc_suite: str,
    tc_name: str,
    commissioning_method: str,
    durations: list,
    discovery_durations: list,
    read_durations: list,
    PASE_durations: list,
    container_out_folder: str,
) -> None:
    summary_dict: dict[str, Any] = {}
    summary_dict["run_set_id"] = "d"
    summary_dict["test_summary_record"] = {}
    summary_dict["test_summary_record"]["test_suite_name"] = tc_suite

    summary_dict["test_summary_record"]["test_case_name"] = tc_name
    summary_dict["test_summary_record"]["test_case_id"] = "stress_1_1"
    summary_dict["test_summary_record"]["test_case_class"] = tc_name
    summary_dict["test_summary_record"]["test_case_description"] = None
    summary_dict["test_summary_record"]["test_case_beginned_at"] = execution_begin_time[
        0
    ].strftime(datetime_json_pattern)
    summary_dict["test_summary_record"]["test_case_ended_at"] = execution_end_time[
        len(execution_end_time) - 1
    ].strftime(datetime_json_pattern)
    summary_dict["test_summary_record"]["test_case_status"] = "Test Completed"
    summary_dict["test_summary_record"]["test_case_result"] = compute_state(
        execution_status
    )
    summary_dict["test_summary_record"]["total_number_of_iterations"] = len(durations)
    summary_dict["test_summary_record"]["number_of_iterations_completed"] = len(
        durations
    )
    summary_dict["test_summary_record"][
        "number_of_iterations_passed"
    ] = compute_count_state(execution_status, True)
    summary_dict["test_summary_record"][
        "number_of_iterations_failed"
    ] = compute_count_state(execution_status, False)
    summary_dict["test_summary_record"]["platform"] = "rpi"
    summary_dict["test_summary_record"]["commissioning_method"] = commissioning_method
    summary_dict["test_summary_record"]["list_of_iterations_failed"] = []
    summary_dict["test_summary_record"]["analytics_parameters"] = [
        "durations",
        "discovery_durations",
        "read_durations",
        "PASE_durations",
    ]

    dut_information_record = {}
    dut_information_record["vendor_name"] = "TEST_VENDOR"
    dut_information_record["product_name"] = "TEST_PRODUCT"
    dut_information_record["product_id"] = str(32769)
    dut_information_record["vendor_id"] = str(65521)
    dut_information_record["software_version"] = "1.0"
    dut_information_record["hardware_version"] = "TEST_VERSION"
    dut_information_record["serial_number"] = "TEST_SN"

    summary_dict["dut_information_record"] = dut_information_record

    host_information_record = {}
    host_information_record["host_name"] = "ubuntu"
    host_information_record["ip_address"] = "127.0.1.1"
    host_information_record["mac_address"] = "a9:6a:5a:96:a5:a9"

    summary_dict["host_information_record"] = host_information_record

    list_of_iteration_records = []

    # Create output folder
    if not os.path.exists(container_out_folder):
        os.mkdir(container_out_folder)

    execution_time_folder = container_out_folder + "/" + folder_name
    tc_name_folder = container_out_folder + "/" + folder_name + "/" + tc_name

    if os.path.exists(execution_time_folder):
        shutil.rmtree(execution_time_folder)
    os.mkdir(execution_time_folder)
    os.mkdir(tc_name_folder)

    for x in range(0, len(durations)):
        curr_ite = str(x + 1)
        # Creating iteration folder
        iteration_folder = tc_name_folder + "/" + curr_ite
        os.mkdir(iteration_folder)

        # Copy the execution log to the iteration folder
        shutil.copy(execution_logs[x], iteration_folder)

        iteration_records: dict[str, Any] = {}
        iteration_data = {}

        iteration_tc_execution_data = {}
        iteration_tc_execution_data["iteration_begin_time"] = execution_begin_time[
            x
        ].strftime(datetime_json_pattern)
        iteration_tc_execution_data["iteration_end_time"] = execution_end_time[
            x
        ].strftime(datetime_json_pattern)
        iteration_tc_execution_data["iteration_result"] = execution_status[x]
        iteration_tc_execution_data["exception"] = None

        iteration_tc_analytics_data = {}
        iteration_tc_analytics_data["durations"] = durations[x]
        iteration_tc_analytics_data["discovery_durations"] = discovery_durations[x]
        iteration_tc_analytics_data["read_durations"] = read_durations[x]
        iteration_tc_analytics_data["PASE_durations"] = PASE_durations[x]

        iteration_data["iteration_tc_execution_data"] = iteration_tc_execution_data
        iteration_data["iteration_tc_analytics_data"] = iteration_tc_analytics_data

        iteration_records["iteration_number"] = curr_ite
        iteration_records["iteration_data"] = iteration_data

        list_of_iteration_records.append(iteration_records)

        # Creating iteration.json for each iteration
        json_str = json.dumps(iteration_records, indent=4)

        with open(tc_name_folder + "/" + curr_ite + "/iteration.json", "w") as f:
            f.write(json_str)

    summary_dict["list_of_iteration_records"] = list_of_iteration_records

    json_str = json.dumps(summary_dict, indent=4)

    print(f"Generating {tc_name_folder}/summary.json")
    with open(tc_name_folder + "/summary.json", "w") as f:
        f.write(json_str)

    print("generate_summary process completed!!!")
