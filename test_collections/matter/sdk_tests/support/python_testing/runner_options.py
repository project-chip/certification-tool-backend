#
# Copyright (c) 2023-2026 Project CHIP Authors
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


"""Options accepted by the SDK test runner (test_harness_client.py).

The valid options are only known to the runner inside the SDK container. They are
read from its ``--help`` whenever the Python test files are generated (backend
startup / rescan) and cached in a JSON file, so that test parameters can be
validated in places where no container is running, e.g. when a test run is
created through the API.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from app.test_engine.logger import test_engine_logger as logger

SDK_TESTS_PATH = Path(__file__).parent.parent.parent
RUNNER_OPTIONS_FILE = SDK_TESTS_PATH / "runner_options.json"

# Long option names (e.g. "--int-arg") as printed by the runner's --help.
_LONG_OPTION_PATTERN = re.compile(r"--([A-Za-z0-9][A-Za-z0-9_-]*)")

# Minimum similarity for a "did you mean" suggestion. The default (0.6) is too
# lenient: it suggests the unrelated "--timeout" for "--prompt-timeout" and
# "--tests" for "--tests-list", which would send the user to the wrong option.
# A wrong suggestion is worse than none, and real typos score well above this.
_SUGGESTION_CUTOFF = 0.8


def parse_runner_options(help_text: str) -> set[str]:
    """Long option names (without the leading dashes) listed in the runner's --help."""
    return set(_LONG_OPTION_PATTERN.findall(help_text))


def save_runner_options(options: set[str], path: Path = RUNNER_OPTIONS_FILE) -> None:
    path.write_text(json.dumps(sorted(options), indent=2))


def clear_runner_options(path: Path = RUNNER_OPTIONS_FILE) -> None:
    """Drop the cache, e.g. when the options could not be read, so a stale list from
    a previous SDK version is never used. Never raises.

    If the file cannot be deleted it is emptied instead, which the loader treats as
    "no options" (no validation).
    """
    try:
        path.unlink(missing_ok=True)
        return
    except OSError as error:
        logger.warning(f"Could not delete the SDK runner options {path}: {error}")

    try:
        path.write_text("[]")
    except OSError as error:
        logger.warning(f"Could not empty the SDK runner options {path}: {error}")


def load_runner_options(path: Path = RUNNER_OPTIONS_FILE) -> set[str] | None:
    """Cached runner options, or None if they are unavailable.

    None means "don't validate": callers must not reject anything on a guess.
    """
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        logger.warning(f"Could not read the SDK runner options from {path}: {error}")
        return None

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        logger.warning(f"Ignoring unexpected SDK runner options content in {path}")
        return None
    return set(data) or None


def _is_accepted_by_runner(name: str, runner_options: set[str]) -> bool:
    if name in runner_options:
        return True
    return sum(option.startswith(name) for option in runner_options) == 1


def _find_invalid_test_parameters(
    test_parameters: dict, runner_options: set[str]
) -> list[str]:
    """One message per test parameter the runner would not accept.

    Mirrors argparse: an exact option name is always accepted, otherwise the name must
    be an abbreviation of exactly one long option.
    """
    problems = []
    for name in test_parameters:
        if not name or _is_accepted_by_runner(name, runner_options):
            continue
        close = difflib.get_close_matches(
            name.replace("_", "-"), runner_options, n=1, cutoff=_SUGGESTION_CUTOFF
        )
        problems.append(
            f"'--{name}'" + (f" (did you mean '--{close[0]}'?)" if close else "")
        )
    return problems


def describe_invalid_test_parameters(
    test_parameters: dict | None, runner_options: set[str]
) -> str | None:
    """Error message for test parameters the runner would reject, None if all are ok."""
    if not test_parameters:
        return None
    problems = _find_invalid_test_parameters(test_parameters, runner_options)
    if not problems:
        return None
    return (
        "Invalid test parameter(s) for the SDK test runner: "
        + ", ".join(problems)
        + ". Test parameters are passed to test_harness_client.py as '--<name>"
        " <value>'; no test was started."
    )
