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
import ast
import importlib
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Tuple, Type

import emails
from emails.template import JinjaTemplate
from jose import jwt
from loguru import logger

from app.core.config import settings
from app.models import TestRunExecution
from app.schemas import TestSelection

TEST_COLLECTIONS = "test_collections"
TEST_ENVIRONMENT_CONFIG_NAME = "default_project.config"
TEST_ENVIRONMENT_CONFIG_PYTHON = "test_environment_config.py"
TEST_ENVIRONMENT_CONFIG_MODULE = "test_environment_config"
TEST_ENVIRONMENT_CONFIG_BASE_CLASS_NAME = "TestEnvironmentConfig"


class InvalidProgramConfigurationError(Exception):
    """'Exception raised when the program configuration is invalid"""


def send_email(
    email_to: str,
    subject_template: str = "",
    html_template: str = "",
    environment: Dict[str, Any] = {},
) -> None:
    assert settings.EMAILS_ENABLED, "no provided configuration for email variables"
    message = emails.Message(
        subject=JinjaTemplate(subject_template),
        html=JinjaTemplate(html_template),
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, render=environment, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def send_test_email(email_to: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "test_email.html") as f:
        template_str = f.read()
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={"project_name": settings.PROJECT_NAME, "email": email_to},
    )


def send_reset_password_email(email_to: str, email: str, token: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "reset_password.html") as f:
        template_str = f.read()
    server_host = settings.SERVER_HOST
    link = f"{server_host}/reset-password?token={token}"
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )


def send_new_account_email(email_to: str, username: str, password: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "new_account.html") as f:
        template_str = f.read()
    link = settings.SERVER_HOST
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": link,
        },
    )


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return decoded_token["email"]
    except jwt.JWTError:
        return None


def read_information_from_file(filepath: Path) -> str:
    """This method reads the first line in the file and returns the string.

    Returns:
        str: String information on successful read. Returns unknown in case of an
        error.
    """
    if not filepath.exists():
        logger.warning(f"File at #{filepath} is missing")
        return "Unknown"
    elif filepath.stat().st_size <= 0:
        logger.warning(f"File at #{filepath} is empty")
        return "Unknown"
    else:
        # Read the first line in the file.
        logger.debug(f"Read #{filepath} file contents")
        with open(filepath) as f:
            return f.readline().rstrip()


def selected_tests_from_execution(run: TestRunExecution) -> TestSelection:
    selected_tests: TestSelection = {}

    for suite in run.test_suite_executions:
        selected_tests.setdefault(suite.collection_id, {})
        selected_tests[suite.collection_id].setdefault(suite.public_id, {})
        selected_tests[suite.collection_id][suite.public_id]
        for case in suite.test_case_executions:
            if (
                case.public_id
                in selected_tests[suite.collection_id][suite.public_id].keys()
            ):
                selected_tests[suite.collection_id][suite.public_id][
                    case.public_id
                ] += 1
            else:
                case_count = (
                    int(case.test_case_metadata.count)
                    if case.test_case_metadata.count
                    else 1
                )
                selected_tests[suite.collection_id][suite.public_id].update(
                    {case.public_id: case_count}
                )

    return selected_tests


def formated_datetime_now_str() -> str:
    """Returns the string for the date and time now, with a specific format.
    The date format used is: '_YYYY_MM_DD_hh_mm_ss'
    """
    return datetime.now().strftime("_%Y_%m_%d_%H_%M_%S")


def remove_title_date(title: str) -> str:
    """Use regex to remove the date suffix of the title string
    The date format expected is: '_YYYY_MM_DD_hh_mm_ss'
    """
    return re.sub(r"\_\d{4}(\_\d{2}){5}", "", title)


def __retrieve_program_module(test_folder_file_name: Path) -> ModuleType:
    """Retrives the program module"""
    items = str(test_folder_file_name).split("/")
    program = items[items.index(TEST_COLLECTIONS) + 1]
    module = importlib.import_module(
        f"{TEST_COLLECTIONS}.{program}.{TEST_ENVIRONMENT_CONFIG_MODULE}"
    )
    return module


def __retrieve_program_class(test_folder_file_name: Path) -> str:
    """Looking for a class, inside the given path, that extends TestEnvironmentConfig"""
    with open(test_folder_file_name, "r") as python_file:
        parsed_python_file = ast.parse(python_file.read())

        classes = [
            c
            for c in parsed_python_file.body
            if isinstance(c, ast.ClassDef)
            and any(
                b
                for b in c.bases
                if isinstance(b, ast.Name)
                and b.id == TEST_ENVIRONMENT_CONFIG_BASE_CLASS_NAME
            )
        ]

    # It should have only one occurrence for a class that extends TestEnvironmentConfig
    if not classes or len(classes) == 0:
        raise InvalidProgramConfigurationError(
            "At least one class definition is required"
        )
    return classes[0].name


def __retrieve_program_conf() -> Tuple[Optional[Type], Optional[Path]]:
    PROJECT_ROOT = Path(__file__).parent.parents[0]

    test_collection_folder = os.listdir(PROJECT_ROOT / TEST_COLLECTIONS)

    # Iterate through the folders inside test_collections in order to find the first
    # occurency for the default_project.config file
    for program_folder in test_collection_folder:
        test_folder_file_name = (
            PROJECT_ROOT
            / TEST_COLLECTIONS
            / program_folder
            / TEST_ENVIRONMENT_CONFIG_PYTHON
        )
        # Currently, only one program is supported, so it should consider the first
        # occurency for default_project.config file
        if test_folder_file_name.is_file():
            ProgramConfigClassReference = getattr(
                __retrieve_program_module(test_folder_file_name),
                __retrieve_program_class(test_folder_file_name),
            )
            default_config_file = (
                PROJECT_ROOT
                / TEST_COLLECTIONS
                / program_folder
                / TEST_ENVIRONMENT_CONFIG_NAME
            )

            return ProgramConfigClassReference, default_config_file

    return None, None


program_class, program_config_path = __retrieve_program_conf()
