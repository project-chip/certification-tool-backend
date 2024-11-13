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
from typing import Any, Optional

date_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+"
date_pattern_out_folder = "%d-%m-%Y_%H-%M-%S-%f"
datetime_json_pattern = "%Y-%m-%dT%H:%M:%S.%f"


# Creates the file structure and content required by matter_qa visualization tool.
# Returns the test case name and the folder name where the report is save.
def create_summary_report(
    timestamp: str, log_lines: list, commissioning_method: str
) -> tuple[str, str]:
    tc_name = ""
    tc_suite = ""
    log_lines_list = "\n".join(log_lines)

    LOGS_FOLDER = "/test_collections/logs"
    CONTAINER_BACKEND = os.getenv("PYTHONPATH") or ""
    CONTAINER_OUT_FOLDER = CONTAINER_BACKEND + LOGS_FOLDER
    if os.path.exists(CONTAINER_OUT_FOLDER):
        shutil.rmtree(CONTAINER_OUT_FOLDER)
    os.makedirs(CONTAINER_OUT_FOLDER)

    with open(
        CONTAINER_OUT_FOLDER + f"/Performance_Test_Run_{timestamp}.log", "w"
    ) as f:
        f.write(str(log_lines_list))

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
                        if line.find("Test Case Completed [") > 0:
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

    return (tc_name, execution_time_folder)


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


def extract_datetime(line: str) -> Optional[datetime]:
    line_datetime = None
    match = re.findall(date_pattern, line)
    if match[0]:
        line_datetime = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")

    return line_datetime


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

            # pattern_begin:
            # f"(?=.*{re.escape(stage)})(?=.*{re.escape(self.step_type[0])})"
            if re.search(patterns["begin"], line) is not None:
                match = re.findall(date_pattern, line)
                if match[0]:
                    begin = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")
                    if stage == "discovery":
                        self.commissioning["begin"] = begin
                    self.commissioning[stage]["begin"] = begin

            # pattern_end:
            # f"(?=.*{re.escape(stage)})(?=.*{re.escape(self.step_type[1])})"
            if re.search(patterns["end"], line) is not None:
                match = re.findall(date_pattern, line)
                if match[0]:
                    end = datetime.strptime(match[0], "%Y-%m-%d %H:%M:%S.%f")
                    if stage == "cleanup":
                        self.commissioning["end"] = end
                    self.commissioning[stage]["end"] = end
