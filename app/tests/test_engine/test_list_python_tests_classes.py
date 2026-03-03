#
# Copyright (c) 2026 Project CHIP Authors
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
"""
Unit tests for list_python_tests_classes module.

Covers:
- load_ignore_list / load_include_list  : file parsing with comments and blanks
- _is_matter_base_test_class            : recursive AST inheritance resolution
- base_test_classes                     : module-level class filtering
- get_command_list                      : full discovery pipeline
"""
import ast
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_collections.matter.sdk_tests.support.python_testing.list_python_tests_classes import (  # noqa
    MATTER_BASE_TEST_CLASS_NAME,
    _is_matter_base_test_class,
    base_test_classes,
    get_command_list,
    load_ignore_list,
    load_include_list,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str) -> ast.Module:
    """Parse a source string into an AST module."""
    return ast.parse(textwrap.dedent(source))


def _make_sdk_folder(tmp_path: Path, files: dict[str, str]) -> MagicMock:
    """Write *files* into *tmp_path* and return a mock SDKTestFolder."""
    for name, content in files.items():
        (tmp_path / name).write_text(textwrap.dedent(content))

    folder = MagicMock()
    folder.file_paths.return_value = sorted(
        [tmp_path / name for name in files],
        key=lambda p: p.name,
    )
    return folder


# ---------------------------------------------------------------------------
# load_ignore_list / load_include_list
# ---------------------------------------------------------------------------


class TestLoadFileList:
    def test_returns_empty_set_when_file_missing(self, tmp_path: Path) -> None:
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            tmp_path / "nonexistent.txt",
        ):
            result = load_ignore_list()
        assert result == set()

    def test_loads_filenames_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("TC_FOO.py\nTC_BAR.py\n")
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            f,
        ):
            result = load_ignore_list()
        assert result == {"TC_FOO.py", "TC_BAR.py"}

    def test_skips_comment_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("# this is a comment\nTC_FOO.py\n")
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            f,
        ):
            result = load_ignore_list()
        assert result == {"TC_FOO.py"}

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("\n\nTC_FOO.py\n\n")
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            f,
        ):
            result = load_ignore_list()
        assert result == {"TC_FOO.py"}

    def test_include_list_uses_separate_file(self, tmp_path: Path) -> None:
        f = tmp_path / "include.txt"
        f.write_text("TCP_Tests.py\n")
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            f,
        ):
            result = load_include_list()
        assert result == {"TCP_Tests.py"}


# ---------------------------------------------------------------------------
# _is_matter_base_test_class
# ---------------------------------------------------------------------------


class TestIsMatterBaseTestClass:
    # --- positive: direct inheritance ---

    def test_direct_inheritance_from_matter_base_test(self) -> None:
        module = _parse(
            f"""
            class MyTest({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=None) is True

    # --- positive: same-file intermediate base ---

    def test_same_file_intermediate_base_class(self) -> None:
        module = _parse(
            f"""
            class IntermediateBase({MATTER_BASE_TEST_CLASS_NAME}):
                pass

            class MyTest(IntermediateBase):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=None) is True

    # --- positive: local file resolution (dot-to-slash) ---

    def test_resolves_flat_local_import(self, tmp_path: Path) -> None:
        base_file = tmp_path / "MyBase.py"
        base_file.write_text(
            textwrap.dedent(
                f"""
            class MyBase({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
            )
        )
        module = _parse(
            """
            from MyBase import MyBase

            class MyTest(MyBase):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=tmp_path) is True

    def test_resolves_package_local_import_with_dot_to_slash(
        self, tmp_path: Path
    ) -> None:
        pkg = tmp_path / "support_modules"
        pkg.mkdir()
        (pkg / "idm_support.py").write_text(
            textwrap.dedent(
                f"""
            class IDMBaseTest({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
            )
        )
        module = _parse(
            """
            from support_modules.idm_support import IDMBaseTest

            class TC_IDM_1_2(IDMBaseTest):
                pass
        """
        )
        assert (
            _is_matter_base_test_class("TC_IDM_1_2", module, search_dir=tmp_path)
            is True
        )

    def test_resolves_aliased_import(self, tmp_path: Path) -> None:
        (tmp_path / "SomeBase.py").write_text(
            textwrap.dedent(
                f"""
            class RealBase({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
            )
        )
        module = _parse(
            """
            from SomeBase import RealBase as AliasBase

            class MyTest(AliasBase):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=tmp_path) is True

    # --- positive: matter.testing fallback ---

    def test_matter_testing_fallback_when_no_local_file(self) -> None:
        module = _parse(
            """
            from matter.testing.basic_composition import BasicCompositionTests

            class TC_DA_1_2(BasicCompositionTests):
                pass
        """
        )
        assert _is_matter_base_test_class("TC_DA_1_2", module, search_dir=None) is True

    # --- negative ---

    def test_returns_false_for_unrelated_class(self) -> None:
        module = _parse(
            """
            class NotATest:
                pass
        """
        )
        assert _is_matter_base_test_class("NotATest", module, search_dir=None) is False

    def test_returns_false_when_class_not_in_module(self) -> None:
        module = _parse(
            f"""
            class OtherTest({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
        )
        assert _is_matter_base_test_class("Missing", module, search_dir=None) is False

    def test_returns_false_when_local_file_exists_but_no_inheritance(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "SomeHelper.py").write_text(
            textwrap.dedent(
                """
            class SomeHelper:
                pass
        """
            )
        )
        module = _parse(
            """
            from SomeHelper import SomeHelper

            class MyTest(SomeHelper):
                pass
        """
        )
        assert (
            _is_matter_base_test_class("MyTest", module, search_dir=tmp_path) is False
        )

    def test_returns_false_for_non_matter_testing_package(self) -> None:
        module = _parse(
            """
            from some.other.package import SomeBase

            class MyTest(SomeBase):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=None) is False

    # --- edge cases ---

    def test_cycle_guard_prevents_infinite_recursion(self) -> None:
        # A -> B -> A  (circular reference in same module)
        module = _parse(
            """
            class A(B):
                pass

            class B(A):
                pass
        """
        )
        assert _is_matter_base_test_class("A", module, search_dir=None) is False

    def test_skips_local_file_with_syntax_error(self, tmp_path: Path) -> None:
        (tmp_path / "BrokenBase.py").write_text("def broken(:\n")
        module = _parse(
            """
            from BrokenBase import BrokenBase

            class MyTest(BrokenBase):
                pass
        """
        )
        # Should not raise; returns False because the file can't be parsed
        assert (
            _is_matter_base_test_class("MyTest", module, search_dir=tmp_path) is False
        )

    def test_ignores_non_name_bases(self) -> None:
        # Attribute access (e.g. module.Base) is an ast.Attribute, not ast.Name
        module = _parse(
            """
            import some_module

            class MyTest(some_module.MatterBaseTest):
                pass
        """
        )
        assert _is_matter_base_test_class("MyTest", module, search_dir=None) is False


# ---------------------------------------------------------------------------
# base_test_classes
# ---------------------------------------------------------------------------


class TestBaseTestClasses:
    def test_returns_only_matter_base_test_subclasses(self) -> None:
        module = _parse(
            f"""
            class GoodTest({MATTER_BASE_TEST_CLASS_NAME}):
                pass

            class NotATest:
                pass

            class AnotherGoodTest({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
        )
        result = base_test_classes(module)
        names = [c.name for c in result]
        assert names == ["GoodTest", "AnotherGoodTest"]

    def test_returns_empty_list_when_no_subclasses(self) -> None:
        module = _parse(
            """
            class Util:
                pass
        """
        )
        assert base_test_classes(module) == []

    def test_passes_search_dir_for_local_resolution(self, tmp_path: Path) -> None:
        (tmp_path / "TC_MyBase.py").write_text(
            textwrap.dedent(
                f"""
            class TC_MyBase({MATTER_BASE_TEST_CLASS_NAME}):
                pass
        """
            )
        )
        module = _parse(
            """
            from TC_MyBase import TC_MyBase

            class TC_CERT_1_1(TC_MyBase):
                pass
        """
        )
        result = base_test_classes(module, search_dir=tmp_path)
        assert len(result) == 1
        assert result[0].name == "TC_CERT_1_1"


# ---------------------------------------------------------------------------
# get_command_list
# ---------------------------------------------------------------------------


class TestGetCommandList:
    def test_includes_tc_files_with_matter_base_test_subclass(
        self, tmp_path: Path
    ) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_FOO_1_1.py": f"""
                class TC_FOO_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        assert len(result) == 1
        assert result[0][1] == "TC_FOO_1_1"

    def test_excludes_non_tc_filenames(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "helper.py": f"""
                class Helper({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        assert result == []

    def test_excludes_files_in_ignore_list(self, tmp_path: Path) -> None:
        ignore_file = tmp_path / "ignore.txt"
        ignore_file.write_text("TC_IGNORED_1_1.py\n")
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_IGNORED_1_1.py": f"""
                class TC_IGNORED_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_IGNORE_FILE",
            ignore_file,
        ):
            result = get_command_list(folder)
        assert result == []

    def test_includes_non_tc_file_from_include_list(self, tmp_path: Path) -> None:
        include_file = tmp_path / "include.txt"
        include_file.write_text("TCP_Tests.py\n")
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TCP_Tests.py": f"""
                class TCP_Tests({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing"
            ".list_python_tests_classes.PYTHON_TESTS_INCLUDE_FILE",
            include_file,
        ):
            result = get_command_list(folder)
        assert len(result) == 1
        assert result[0][1] == "TCP_Tests"

    def test_skips_files_with_syntax_errors(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_BROKEN_1_1.py": "def broken(:\n",
            },
        )
        result = get_command_list(folder)
        assert result == []

    def test_skips_tc_file_with_no_base_test_subclass(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_UTIL_1_1.py": """
                class TC_UTIL_1_1:
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        assert result == []

    def test_command_format_contains_path_and_class_name(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_FOO_1_1.py": f"""
                class TC_FOO_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        assert len(result) == 1
        path_part, class_part = result[0]
        assert class_part == "TC_FOO_1_1"
        assert "TC_FOO_1_1" in path_part

    def test_resolves_local_base_class_file(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_TLSCERT_Base.py": f"""
                class TC_TLSCERT_Base({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
                "TC_TLSCERT_2_1.py": """
                from TC_TLSCERT_Base import TC_TLSCERT_Base

                class TC_TLSCERT_2_1(TC_TLSCERT_Base):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        class_names = [cmd[1] for cmd in result]
        # TC_TLSCERT_2_1 must be discovered via local base file resolution
        assert "TC_TLSCERT_2_1" in class_names
        # TC_TLSCERT_Base.py matches TC_*.py and directly inherits MatterBaseTest,
        # so it is also a valid command entry
        assert "TC_TLSCERT_Base" in class_names

    def test_multiple_classes_in_one_file_each_become_command(
        self, tmp_path: Path
    ) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_MULTI_1_1.py": f"""
                class TC_MULTI_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass

                class TC_MULTI_1_2({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        class_names = [cmd[1] for cmd in result]
        assert "TC_MULTI_1_1" in class_names
        assert "TC_MULTI_1_2" in class_names

    def test_results_are_sorted_by_filename(self, tmp_path: Path) -> None:
        folder = _make_sdk_folder(
            tmp_path,
            {
                "TC_B_1_1.py": f"""
                class TC_B_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
                "TC_A_1_1.py": f"""
                class TC_A_1_1({MATTER_BASE_TEST_CLASS_NAME}):
                    pass
            """,
            },
        )
        result = get_command_list(folder)
        class_names = [cmd[1] for cmd in result]
        assert class_names == ["TC_A_1_1", "TC_B_1_1"]
