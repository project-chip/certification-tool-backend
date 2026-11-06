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
from typing import Optional

from app.schemas.test_collections import RescanChanges, ScriptError, TestCaseChange

from .models.test_declarations import TestCaseDeclaration, TestCollectionDeclaration

# (collection name, test suite public id, test case public id)
TestCaseKey = tuple[str, str, str]


def _fingerprint(test_case: TestCaseDeclaration) -> str:
    """Value that changes when the discovered definition of a test case changes.

    A test case is "modified" when its parsed metadata changes (title,
    description, version), when its PICS change, or - for Python tests - when
    the parsed script info changes (steps, class name, path, test type). Edits
    to script code that discovery does not read are intentionally not detected.
    """
    parts = [
        repr(sorted(test_case.metadata.items())),
        repr(sorted(test_case.pics)),
    ]
    python_test = getattr(test_case.class_ref, "python_test", None)
    if python_test is not None:
        # PICS is a set whose repr order depends on insertion history, so sort it.
        parts.append(repr(python_test.dict(exclude={"PICS"})))
        parts.append(repr(sorted(python_test.PICS)))
    return "\n".join(parts)


def _snapshot(
    test_collections: dict[str, TestCollectionDeclaration],
) -> dict[TestCaseKey, str]:
    return {
        (collection_name, suite_id, case_id): _fingerprint(case)
        for collection_name, collection in test_collections.items()
        for suite_id, suite in collection.test_suites.items()
        for case_id, case in suite.test_cases.items()
    }


def diff_test_collections(
    before: dict[str, TestCollectionDeclaration],
    after: dict[str, TestCollectionDeclaration],
    errors: Optional[list[ScriptError]] = None,
) -> RescanChanges:
    """Compare the test cases of two sets of test collections."""
    before_snapshot = _snapshot(before)
    after_snapshot = _snapshot(after)

    def change(key: TestCaseKey) -> TestCaseChange:
        return TestCaseChange(collection=key[0], test_suite=key[1], test_case=key[2])

    return RescanChanges(
        added=[change(k) for k in after_snapshot if k not in before_snapshot],
        modified=[
            change(k)
            for k, fingerprint in after_snapshot.items()
            if k in before_snapshot and before_snapshot[k] != fingerprint
        ],
        removed=[change(k) for k in before_snapshot if k not in after_snapshot],
        errors=errors or [],
        collections=list(after.keys()),
    )
