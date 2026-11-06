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
from typing import Any, Optional
from unittest.mock import MagicMock

from pydantic import BaseModel

from app.schemas.test_collections import (
    CustomFileChange,
    CustomFileChanges,
    ScriptError,
)
from app.test_engine.models.test_declarations import (
    TestCaseDeclaration,
    TestCollectionDeclaration,
    TestSuiteDeclaration,
)
from app.test_engine.test_collection_diff import (
    diff_custom_files,
    diff_test_collections,
)


class FakePythonTest(BaseModel):
    """Stand-in for PythonTest: a pydantic model with a PICS set and steps."""

    name: str = "TC-A-1.1"
    PICS: set[str] = set()
    steps: list[str] = []


def _case(
    public_id: str,
    description: str = "desc",
    pics: Optional[set[str]] = None,
    python_test: Any = None,
) -> TestCaseDeclaration:
    class_ref = MagicMock()
    class_ref.metadata = {
        "public_id": public_id,
        "version": "0.0.1",
        "title": public_id,
        "description": description,
    }
    class_ref.public_id.return_value = public_id
    class_ref.pics.return_value = pics or set()
    class_ref.python_test = python_test
    return TestCaseDeclaration(class_ref)


def _collections(
    spec: dict[str, dict[str, list[TestCaseDeclaration]]],
) -> dict[str, TestCollectionDeclaration]:
    """spec maps collection name -> suite id -> test cases."""
    collections = {}
    for collection_name, suites in spec.items():
        collection = TestCollectionDeclaration(path="", name=collection_name)
        for suite_id, cases in suites.items():
            suite_ref = MagicMock()
            suite_ref.public_id.return_value = suite_id
            suite = TestSuiteDeclaration(suite_ref)
            for case in cases:
                suite.add_test_case(case)
            collection.add_test_suite(suite)
        collections[collection_name] = collection
    return collections


def _keys(changes: list) -> list[tuple[str, str, str]]:
    return [(c.collection, c.test_suite, c.test_case) for c in changes]


def test_no_changes() -> None:
    before = _collections({"custom": {"suite": [_case("TC-A-1.1")]}})
    after = _collections({"custom": {"suite": [_case("TC-A-1.1")]}})

    changes = diff_test_collections(before, after)

    assert changes.added == []
    assert changes.modified == []
    assert changes.removed == []
    assert changes.errors == []
    assert changes.collections == ["custom"]


def test_added_test_case() -> None:
    before = _collections({"custom": {"suite": [_case("TC-A-1.1")]}})
    after = _collections(
        {"custom": {"suite": [_case("TC-A-1.1"), _case("TC-FAKE-1.1-custom")]}}
    )

    changes = diff_test_collections(before, after)

    assert _keys(changes.added) == [("custom", "suite", "TC-FAKE-1.1-custom")]
    assert changes.modified == []
    assert changes.removed == []


def test_removed_test_case() -> None:
    before = _collections(
        {"custom": {"suite": [_case("TC-A-1.1"), _case("TC-OLD-1.1-custom")]}}
    )
    after = _collections({"custom": {"suite": [_case("TC-A-1.1")]}})

    changes = diff_test_collections(before, after)

    assert _keys(changes.removed) == [("custom", "suite", "TC-OLD-1.1-custom")]
    assert changes.added == []
    assert changes.modified == []


def test_added_and_removed_collection() -> None:
    before = _collections({"old": {"suite": [_case("TC-A-1.1")]}})
    after = _collections({"new": {"suite": [_case("TC-A-1.1")]}})

    changes = diff_test_collections(before, after)

    assert _keys(changes.added) == [("new", "suite", "TC-A-1.1")]
    assert _keys(changes.removed) == [("old", "suite", "TC-A-1.1")]


def test_same_test_case_id_in_different_suites_is_not_confused() -> None:
    before = _collections({"c": {"s1": [_case("TC-A-1.1")]}})
    after = _collections({"c": {"s2": [_case("TC-A-1.1")]}})

    changes = diff_test_collections(before, after)

    assert _keys(changes.added) == [("c", "s2", "TC-A-1.1")]
    assert _keys(changes.removed) == [("c", "s1", "TC-A-1.1")]


def test_modified_when_metadata_changes() -> None:
    before = _collections({"c": {"s": [_case("TC-A-1.1", description="old")]}})
    after = _collections({"c": {"s": [_case("TC-A-1.1", description="new")]}})

    changes = diff_test_collections(before, after)

    assert _keys(changes.modified) == [("c", "s", "TC-A-1.1")]
    assert changes.added == []
    assert changes.removed == []


def test_modified_when_pics_change() -> None:
    before = _collections({"c": {"s": [_case("TC-A-1.1", pics={"A.S.A0000"})]}})
    after = _collections({"c": {"s": [_case("TC-A-1.1", pics={"A.S.A0001"})]}})

    changes = diff_test_collections(before, after)

    assert _keys(changes.modified) == [("c", "s", "TC-A-1.1")]


def test_modified_when_parsed_python_test_changes() -> None:
    before = _collections(
        {"c": {"s": [_case("TC-A-1.1", python_test=FakePythonTest(steps=["1"]))]}}
    )
    after = _collections(
        {"c": {"s": [_case("TC-A-1.1", python_test=FakePythonTest(steps=["1", "2"]))]}}
    )

    changes = diff_test_collections(before, after)

    assert _keys(changes.modified) == [("c", "s", "TC-A-1.1")]


def test_python_test_pics_order_does_not_count_as_modification() -> None:
    pics = [f"X{i}.S" for i in range(50)]
    # Sets built from the same values in a different order may repr differently
    before = _collections(
        {"c": {"s": [_case("TC-A-1.1", python_test=FakePythonTest(PICS=set(pics)))]}}
    )
    after = _collections(
        {
            "c": {
                "s": [
                    _case(
                        "TC-A-1.1",
                        python_test=FakePythonTest(PICS=set(reversed(pics))),
                    )
                ]
            }
        }
    )

    assert diff_test_collections(before, after).modified == []


def test_pics_order_does_not_count_as_modification() -> None:
    before = _collections({"c": {"s": [_case("TC-A-1.1", pics={"X.S", "Y.S"})]}})
    after = _collections({"c": {"s": [_case("TC-A-1.1", pics={"Y.S", "X.S"})]}})

    assert diff_test_collections(before, after).modified == []


def test_errors_are_passed_through() -> None:
    collections = _collections({"c": {"s": [_case("TC-A-1.1")]}})
    errors = [ScriptError(script="TC_BAD_1_1.py", reason="Syntax error: oops")]

    changes = diff_test_collections(collections, collections, errors)

    assert changes.errors == errors


def test_custom_files_are_passed_through() -> None:
    collections = _collections({"c": {"s": [_case("TC-A-1.1")]}})
    custom_files = CustomFileChanges(added=[CustomFileChange(name="TC_Base.py")])

    changes = diff_test_collections(collections, collections, None, custom_files)

    assert changes.custom_files == custom_files


def test_custom_files_default_to_empty() -> None:
    collections = _collections({"c": {"s": [_case("TC-A-1.1")]}})

    changes = diff_test_collections(collections, collections)

    assert changes.custom_files == CustomFileChanges()


def test_diff_custom_files_added_modified_removed() -> None:
    before = {"Keep.py": "1", "Edit.py": "1", "Gone.py": "1"}
    after = {"Keep.py": "1", "Edit.py": "2", "New.py": "1"}

    changes = diff_custom_files(before, after)

    assert [c.name for c in changes.added] == ["New.py"]
    assert [c.name for c in changes.modified] == ["Edit.py"]
    assert [c.name for c in changes.removed] == ["Gone.py"]


def test_diff_custom_files_no_changes() -> None:
    snapshot = {"Keep.py": "1"}

    assert diff_custom_files(snapshot, dict(snapshot)) == CustomFileChanges()


def test_diff_custom_files_flags_files_replacing_an_sdk_module() -> None:
    changes = diff_custom_files(
        {"Helper.py": "1", "TC_ACE_1_3.py": "1"},
        {"Helper.py": "2", "TC_ACE_1_3.py": "2"},
        replacing_sdk={"Helper.py"},
    )

    by_name = {c.name: c.replaces_sdk for c in changes.modified}
    assert by_name == {"Helper.py": True, "TC_ACE_1_3.py": False}


def test_diff_custom_files_flags_a_removed_file_that_replaced_an_sdk_module() -> None:
    changes = diff_custom_files({"Helper.py": "1"}, {}, replacing_sdk={"Helper.py"})

    assert changes.removed == [CustomFileChange(name="Helper.py", replaces_sdk=True)]
