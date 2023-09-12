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
from sqlalchemy.orm import Session

from app import crud
from app.models import TestCaseMetadata
from app.tests.utils.test_case_metadata import random_test_case_metadata_dict
from app.tests.utils.utils import random_lower_string


def test_get_test_case_metadata(db: Session) -> None:
    # Create build new test_case_metadata object
    title = random_lower_string()
    description = random_lower_string()
    test_case_metadata_dict = random_test_case_metadata_dict(
        title=title, description=description
    )
    test_case_metadata = TestCaseMetadata(**test_case_metadata_dict)

    # Save create test_case_metadata in DB
    db.add(test_case_metadata)
    db.commit()

    # load stored test_case_metadata from DB
    stored_test_case_metadata = crud.test_case_metadata.get(
        db=db, id=test_case_metadata.id
    )

    # assert stored values match
    assert stored_test_case_metadata
    assert test_case_metadata.id == stored_test_case_metadata.id
    assert test_case_metadata.title == stored_test_case_metadata.title
    assert test_case_metadata.description == stored_test_case_metadata.description
