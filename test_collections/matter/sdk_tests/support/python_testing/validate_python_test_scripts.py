import sys
from pathlib import Path

from app.test_engine.logger import test_engine_logger as logger

# flake8: noqa: E501
from test_collections.matter.sdk_tests.support.python_testing.models.python_test_models import (
    PythonTest,
    PythonTestType,
)

# flake8: noqa: E501
from test_collections.matter.sdk_tests.support.python_testing.models.python_test_parser import (
    parse_python_script,
)


def log_message(message: str, break_line: bool = True) -> None:
    text = f">>>>>>>>>> {message} <<<<<<<<<<"
    if break_line:
        text += "\n\n"

    logger.info(text)


def log_parsed_scripts(type: PythonTestType) -> None:
    log_message(f"{type.name} rated scripts", False)
    for script in parsed_scripts[type]:
        logger.info(script)
    log_message(f"{type.name} rated scripts")


log_file = sys.argv[1]
script_paths = sys.argv[2:]

logger.add(log_file, format="{message}")
log_message("Starting script parsing. Errors will be listed below (If any)", False)

parsed_scripts: dict[PythonTestType, list[str]] = {}
parsed_scripts[PythonTestType.COMMISSIONING] = []
parsed_scripts[PythonTestType.NO_COMMISSIONING] = []
parsed_scripts[PythonTestType.LEGACY] = []
parsed_scripts[PythonTestType.MANDATORY] = []

for script in script_paths:
    path: Path = Path(script)
    result: list[PythonTest] = parse_python_script(path)
    for parsed in result:
        parsed_scripts[parsed.python_test_type].append(
            f"Name: {parsed.class_name}, Description: {parsed.description}"
        )

log_message("Script parsing finished")
log_message("All scripts were analyzed and separated into categories")

for key in parsed_scripts:
    log_parsed_scripts(key)
