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


from pathlib import Path
from unittest import mock

import pytest

from ...python_testing import test_manager
from ...python_testing.runner_options import (
    clear_runner_options,
    describe_invalid_test_parameters,
    load_runner_options,
    parse_runner_options,
    save_runner_options,
)

HELP = (
    "usage: test_harness_client.py [-h] [--tests test_NAME [test_NAME ...]]\n"
    "                              [--timeout TIMEOUT] [--PICS PICS]\n"
    "                              [--int-arg NAME:VALUE [NAME:VALUE ...]]\n"
    "                              [--enable-spec-errata-ci-only-disallowed]\n"
)
OPTIONS = {
    "tests",
    "timeout",
    "PICS",
    "int-arg",
    "enable-spec-errata-ci-only-disallowed",
}


def test_parse_runner_options() -> None:
    assert parse_runner_options(HELP) == OPTIONS
    assert parse_runner_options("no options here") == set()


def test_save_and_load_runner_options(tmp_path: Path) -> None:
    path = tmp_path / "runner_options.json"

    save_runner_options(OPTIONS, path)

    assert load_runner_options(path) == OPTIONS


def test_load_runner_options_missing_file(tmp_path: Path) -> None:
    assert load_runner_options(tmp_path / "missing.json") is None


@pytest.mark.parametrize("content", ["not json", "[]", "5", '{"a": 1}'])
def test_load_runner_options_unusable_file_means_no_validation(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "runner_options.json"
    path.write_text(content)

    # A corrupt or empty cache must never cause a run to be rejected.
    assert load_runner_options(path) is None


def test_clear_runner_options(tmp_path: Path) -> None:
    path = tmp_path / "runner_options.json"
    save_runner_options(OPTIONS, path)

    clear_runner_options(path)
    clear_runner_options(path)  # already gone: must not fail

    assert not path.exists()


@pytest.mark.parametrize("test_parameters", [None, {}])
def test_describe_invalid_test_parameters_nothing_to_check(test_parameters) -> None:
    assert describe_invalid_test_parameters(test_parameters, OPTIONS) is None


def test_describe_invalid_test_parameters_known_and_abbreviated() -> None:
    parameters = {"int-arg": "A:1", "timeout": 5, "enable-spec": "1"}

    assert describe_invalid_test_parameters(parameters, OPTIONS) is None


def test_describe_invalid_test_parameters_unknown_option() -> None:
    message = describe_invalid_test_parameters(
        {"int-arg": "A:1", "verbosity": "5"}, OPTIONS
    )

    assert message is not None
    assert "'--verbosity'" in message
    assert "'--int-arg'" not in message
    assert "no test was started" in message


def test_describe_invalid_test_parameters_rejects_ambiguous_prefix() -> None:
    """argparse rejects an abbreviation matching several options ("t": tests, timeout)."""
    message = describe_invalid_test_parameters({"t": "5"}, OPTIONS)

    assert message is not None
    assert "'--t'" in message


def test_describe_invalid_test_parameters_exact_name_beats_longer_options() -> None:
    options = {"time", "timeout"}

    assert describe_invalid_test_parameters({"time": "5"}, options) is None
    assert describe_invalid_test_parameters({"tim": "5"}, options) is not None


@pytest.mark.parametrize(
    "name", ["timeuot", "int_arg", "intarg", "enable-spec-errata-ci-only-dissallowed"]
)
def test_describe_invalid_test_parameters_suggests_close_match(name: str) -> None:
    message = describe_invalid_test_parameters({name: "5"}, OPTIONS)

    assert message is not None
    assert "did you mean" in message


def test_clear_runner_options_falls_back_to_emptying_the_file(tmp_path: Path) -> None:
    """If the cache can't be deleted it must still stop being used, and not raise."""
    path = tmp_path / "runner_options.json"
    save_runner_options(OPTIONS, path)

    with mock.patch.object(Path, "unlink", side_effect=PermissionError("read-only")):
        clear_runner_options(path)

    assert load_runner_options(path) is None


@pytest.mark.parametrize("name", ["prompt_timeout", "prompt-timeout", "tests_list"])
def test_describe_invalid_test_parameters_no_misleading_suggestion(name: str) -> None:
    """These only resemble unrelated runner options (--timeout, --tests)."""
    message = describe_invalid_test_parameters({name: "5"}, OPTIONS)

    assert message is not None
    assert f"'--{name}'" in message
    assert "did you mean" not in message


@pytest.mark.asyncio
async def test_refresh_runner_options_saves_options() -> None:
    with (
        mock.patch.object(test_manager, "read_runner_options", return_value=OPTIONS),
        mock.patch.object(test_manager, "save_runner_options") as save,
        mock.patch.object(test_manager, "clear_runner_options") as clear,
    ):
        await test_manager._refresh_runner_options(mock.MagicMock())

    save.assert_called_once_with(OPTIONS)
    clear.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, RuntimeError("docker down")])
async def test_refresh_runner_options_drops_stale_cache_when_unreadable(
    failure,
) -> None:
    read = (
        mock.Mock(return_value=None)
        if failure is None
        else mock.Mock(side_effect=failure)
    )
    with (
        mock.patch.object(test_manager, "read_runner_options", read),
        mock.patch.object(test_manager, "save_runner_options") as save,
        mock.patch.object(test_manager, "clear_runner_options") as clear,
    ):
        # Must not raise: it should never break the test file generation.
        await test_manager._refresh_runner_options(mock.MagicMock())

    save.assert_not_called()
    clear.assert_called_once_with()


@pytest.mark.asyncio
async def test_refresh_runner_options_survives_cache_write_failure() -> None:
    """A read-only cache location must not abort the test file generation."""
    with (
        mock.patch.object(test_manager, "read_runner_options", return_value=OPTIONS),
        mock.patch.object(
            test_manager,
            "save_runner_options",
            side_effect=PermissionError("read-only"),
        ),
        mock.patch.object(test_manager, "clear_runner_options") as clear,
    ):
        await test_manager._refresh_runner_options(mock.MagicMock())

    # The previous cache is dropped so a list from an older SDK is never used.
    clear.assert_called_once_with()
