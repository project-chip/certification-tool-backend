#
# Copyright (c) 2025 Project CHIP Authors
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

import re
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from ...models.sdk_test_folder import SDKTestFolder
from ...python_testing.list_python_tests_classes import (
    TC_FILENAME_PATTERN,
    get_command_list,
    load_ignore_list,
    load_include_list,
)


@pytest.mark.parametrize(
    "filename,should_match",
    [
        # Positive test cases - should match pattern
        ("TC_ACE_1_2.py", True),
        ("TC_CNET_4_12.py", True),
        ("TC_CNET_4_99.py", True),
        ("TC_DA_1_7.py", True),
        ("TC_BINFO_2_1.py", True),
        ("TC_LVL_8_1.py", True),
        ("TC_VERYLONGCLUSTERNAME_99_99.py", True),
        ("TC_CLUSTER_1_1.py", True),
        ("TC_ACE_1_2_3.py", True),  # too many numbers - main fix
        ("TC_ACE_1_2_300.py", True),  # too many numbers - main fix
        ("TC_MCORE_FS_1_4.py", True),  # underscore in cluster name
        ("TC_ACE_1_1-custom.py", True),  # with -custom suffix at end
        ("TC_MCORE_FS_1_4-custom.py", True),  # underscore + custom suffix at end
        ("TC_A_0_0.py", True),  # cluster name too short (1 letter)
        ("TC_test.py", True),
        ("TC_ACE_1.py", True),
        ("TC_ACE_a_b.py", True),
        ("TC_C4_1_1.py", True),
        ("TC_ACE_1_2_extra.py", True),  # extra content after numbers
        ("TC_ACE_.py", True),  # missing second number
        ("TC_ACE_1_.py", True),  # missing second number
        ("TC_ACE__2.py", True),  # missing first number
        ("TC_ANOTHERVERYLONGCLUSTERNAME_99_99.py", True),  # cluster name > 20 chars
        ("TC_ACE_1_1-Custom.py", True),  # with -Custom suffix at end
        ("TC_ACE_1_1-CUSTOM.py", True),  # with -CUSTOM suffix at end
        ("TC_ace_1_2.py", True),  # cluster name with lowercase letters
        ("TC_1test_1_2.py", True),  # cluster name starts with number
        # Negative test cases - should NOT match pattern
        ("helper.py", False),
        ("TC_.py", False),
        ("test_helper.py", False),
        ("XTC_ACE_1_2.py", False),  # wrong prefix
        ("TC_ACE_1_2", False),  # missing .py extension
        ("TC_ACE_1_2.txt", False),  # wrong extension
    ],
)
def test_filename_pattern_validation(filename: str, should_match: bool) -> None:
    """Parametrized test for filename pattern validation."""
    # Use the same constant pattern as the actual implementation
    tc_pattern = re.compile(TC_FILENAME_PATTERN)

    result = tc_pattern.match(filename)
    if should_match:
        assert result is not None, f"Filename '{filename}' should match the pattern"
    else:
        assert result is None, f"Filename '{filename}' should NOT match the pattern"


def test_get_command_list_with_valid_and_invalid_files() -> None:
    """Test get_command_list with valid TC files (integration test)."""
    # This test requires the actual imports to work
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create valid test files
        valid_files = ["TC_ACE_1_2.py", "TC_CNET_4_12.py", "TC_DA_1_7.py"]

        # Create invalid test files
        invalid_files = ["test_TC.py", "helper.py", "TC_.py"]

        # Simple test file content
        test_content = """
            import chip.clusters as Clusters
            from matter_testing_support import MatterBaseTest

            class TestClass(MatterBaseTest):
            def test_TC_example_1_1(self):
                pass
            """

        # Create all files
        for filename in valid_files + invalid_files:
            file_path = temp_path / filename
            file_path.write_text(test_content)

        test_folder = SDKTestFolder(path=temp_path, filename_pattern="*")

        # Mock the heavy processing parts
        with mock.patch("builtins.open", mock.mock_open(read_data=test_content)):
            with mock.patch("ast.parse") as mock_parse:
                with mock.patch(
                    "test_collections.matter.sdk_tests.support.python_testing."
                    "list_python_tests_classes.base_test_classes"
                ) as mock_base_classes:
                    mock_parse.return_value = mock.MagicMock()
                    mock_class = mock.MagicMock()
                    mock_class.name = "TestClass"
                    mock_base_classes.return_value = [mock_class]

                    commands = get_command_list(test_folder)

        # Should only process the 3 valid files
        assert len(commands) == 3

        # Verify only valid files are included
        file_stems = [cmd[0].split("/")[-1] for cmd in commands]
        for valid_file in valid_files:
            assert Path(valid_file).stem in file_stems

        # Verify invalid files are not included
        for invalid_file in invalid_files:
            assert Path(invalid_file).stem not in file_stems


def test_empty_folder_scenario() -> None:
    """Test pattern validation with empty folder scenario."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            test_folder = SDKTestFolder(path=Path(temp_dir), filename_pattern="TC*")
            commands = get_command_list(test_folder)
            assert commands == []

    except ImportError:
        pytest.skip("Skipping integration test due to import dependencies")


def test_load_ignore_list_file_exists() -> None:
    """Test load_ignore_list when ignore file exists with valid content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ignore_file = Path(temp_dir) / "python_tests_ignore.txt"
        ignore_content = """# Comment line
TC_PAVST_2_6.py
TC_PAVST_2_7.py

# Another comment
TC_WEBRTCR_2_5.py
"""
        ignore_file.write_text(ignore_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            ignore_file,
        ):
            result = load_ignore_list()

        assert result == {"TC_PAVST_2_6.py", "TC_PAVST_2_7.py", "TC_WEBRTCR_2_5.py"}


def test_load_ignore_list_file_not_exists() -> None:
    """Test load_ignore_list when ignore file does not exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_file = Path(temp_dir) / "non_existent.txt"

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            non_existent_file,
        ):
            result = load_ignore_list()

        assert result == set()


def test_load_ignore_list_empty_file() -> None:
    """Test load_ignore_list with empty file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ignore_file = Path(temp_dir) / "python_tests_ignore.txt"
        ignore_file.write_text("")

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            ignore_file,
        ):
            result = load_ignore_list()

        assert result == set()


def test_load_ignore_list_only_comments() -> None:
    """Test load_ignore_list with file containing only comments."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ignore_file = Path(temp_dir) / "python_tests_ignore.txt"
        ignore_content = """# Only comments here
# No actual files to ignore
"""
        ignore_file.write_text(ignore_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            ignore_file,
        ):
            result = load_ignore_list()

        assert result == set()


def test_load_ignore_list_with_whitespace() -> None:
    """Test load_ignore_list handles whitespace correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        ignore_file = Path(temp_dir) / "python_tests_ignore.txt"
        ignore_content = """  TC_TEST_1_1.py
TC_TEST_2_2.py

    TC_TEST_3_3.py
"""
        ignore_file.write_text(ignore_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            ignore_file,
        ):
            result = load_ignore_list()

        assert result == {"TC_TEST_1_1.py", "TC_TEST_2_2.py", "TC_TEST_3_3.py"}


def test_get_command_list_with_ignore_file() -> None:
    """Test get_command_list respects ignore file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        all_files = ["TC_ACE_1_2.py", "TC_CNET_4_12.py", "TC_DA_1_7.py"]
        files_to_ignore = ["TC_CNET_4_12.py"]

        test_content = """
from matter_testing_support import MatterBaseTest

class TestClass(MatterBaseTest):
    def test_TC_example_1_1(self):
        pass
"""

        for filename in all_files:
            (temp_path / filename).write_text(test_content)

        test_folder = SDKTestFolder(path=temp_path, filename_pattern="*")

        # Mock the load_ignore_list function to return our test data
        mock_path = (
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.load_ignore_list"
        )
        with mock.patch(mock_path, return_value=set(files_to_ignore)):
            with mock.patch("ast.parse") as mock_parse:
                with mock.patch(
                    "test_collections.matter.sdk_tests.support.python_testing."
                    "list_python_tests_classes.base_test_classes"
                ) as mock_base_classes:
                    mock_parse.return_value = mock.MagicMock()
                    mock_class = mock.MagicMock()
                    mock_class.name = "TestClass"
                    mock_base_classes.return_value = [mock_class]

                    commands = get_command_list(test_folder)

        # Should only process 2 files (3 total - 1 ignored)
        assert len(commands) == 2

        # Verify ignored file is not included
        file_stems = [cmd[0].split("/")[-1] for cmd in commands]
        assert "TC_CNET_4_12" not in file_stems

        # Verify non-ignored files are included
        assert "TC_ACE_1_2" in file_stems
        assert "TC_DA_1_7" in file_stems


def test_load_include_list_file_exists() -> None:
    """Test load_include_list when include file exists with valid content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        include_file = Path(temp_dir) / "python_tests_include.txt"
        include_content = """# Special test files
TCP_Tests.py
CUSTOM_Test.py

# Another special file
SPECIAL_CASE.py
"""
        include_file.write_text(include_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            include_file,
        ):
            result = load_include_list()

        assert result == {"TCP_Tests.py", "CUSTOM_Test.py", "SPECIAL_CASE.py"}


def test_load_include_list_file_not_exists() -> None:
    """Test load_include_list when include file does not exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_file = Path(temp_dir) / "non_existent.txt"

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            non_existent_file,
        ):
            result = load_include_list()

        assert result == set()


def test_load_include_list_empty_file() -> None:
    """Test load_include_list with empty file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        include_file = Path(temp_dir) / "python_tests_include.txt"
        include_file.write_text("")

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            include_file,
        ):
            result = load_include_list()

        assert result == set()


def test_load_include_list_only_comments() -> None:
    """Test load_include_list with file containing only comments."""
    with tempfile.TemporaryDirectory() as temp_dir:
        include_file = Path(temp_dir) / "python_tests_include.txt"
        include_content = """# Only comments here
# No actual files to include
"""
        include_file.write_text(include_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            include_file,
        ):
            result = load_include_list()

        assert result == set()


def test_load_include_list_with_whitespace() -> None:
    """Test load_include_list handles whitespace correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        include_file = Path(temp_dir) / "python_tests_include.txt"
        include_content = """  TCP_Tests.py
CUSTOM_Test.py

    SPECIAL_CASE.py
"""
        include_file.write_text(include_content)

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            include_file,
        ):
            result = load_include_list()

        assert result == {"TCP_Tests.py", "CUSTOM_Test.py", "SPECIAL_CASE.py"}


def test_get_command_list_with_include_file() -> None:
    """Test get_command_list includes files from include list regardless of pattern."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files - mix of matching and non-matching patterns
        all_files = ["TC_ACE_1_2.py", "TCP_Tests.py", "CUSTOM_Test.py"]

        test_content = """
from matter_testing_support import MatterBaseTest

class TestClass(MatterBaseTest):
    def test_TC_example_1_1(self):
        pass
"""

        for filename in all_files:
            (temp_path / filename).write_text(test_content)

        test_folder = SDKTestFolder(path=temp_path, filename_pattern="*")

        # Mock load_include_list to return files that don't match pattern
        files_to_include = ["TCP_Tests.py", "CUSTOM_Test.py"]

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.load_include_list",
            return_value=set(files_to_include),
        ):
            with mock.patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "list_python_tests_classes.load_ignore_list",
                return_value=set(),
            ):
                with mock.patch("ast.parse") as mock_parse:
                    with mock.patch(
                        "test_collections.matter.sdk_tests.support.python_testing."
                        "list_python_tests_classes.base_test_classes"
                    ) as mock_base_classes:
                        mock_parse.return_value = mock.MagicMock()
                        mock_class = mock.MagicMock()
                        mock_class.name = "TestClass"
                        mock_base_classes.return_value = [mock_class]

                        commands = get_command_list(test_folder)

        # Should process all 3 files (1 matching pattern + 2 in include list)
        assert len(commands) == 3

        # Verify all files are included
        file_stems = [cmd[0].split("/")[-1] for cmd in commands]
        assert "TC_ACE_1_2" in file_stems
        assert "TCP_Tests" in file_stems
        assert "CUSTOM_Test" in file_stems


def test_get_command_list_include_overrides_pattern() -> None:
    """Test that include list bypasses pattern matching."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # File that doesn't match TC_ pattern but is in include list
        special_file = "TCP_Special.py"

        test_content = """
from matter_testing_support import MatterBaseTest

class TestClass(MatterBaseTest):
    def test_TC_example_1_1(self):
        pass
"""

        (temp_path / special_file).write_text(test_content)

        test_folder = SDKTestFolder(path=temp_path, filename_pattern="*")

        with mock.patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.load_include_list",
            return_value={special_file},
        ):
            with mock.patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "list_python_tests_classes.load_ignore_list",
                return_value=set(),
            ):
                with mock.patch("ast.parse") as mock_parse:
                    with mock.patch(
                        "test_collections.matter.sdk_tests.support.python_testing."
                        "list_python_tests_classes.base_test_classes"
                    ) as mock_base_classes:
                        mock_parse.return_value = mock.MagicMock()
                        mock_class = mock.MagicMock()
                        mock_class.name = "TestClass"
                        mock_base_classes.return_value = [mock_class]

                        commands = get_command_list(test_folder)

        # Should include the file even though it doesn't match TC_ pattern
        assert len(commands) == 1
        assert "TCP_Special" in commands[0][0]
