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
from app.models import TestSuiteMetadata
from app.tests.utils.test_suite_metadata import random_test_suite_metadata_dict
from app.tests.utils.utils import random_lower_string


def test_get_test_suite_metadata(db: Session) -> None:
    # Create build new test_suite_metadata object
    title = random_lower_string()
    description = random_lower_string()
    test_suite_metadata_dict = random_test_suite_metadata_dict(
        title=title, description=description
    )
    test_suite_metadata = TestSuiteMetadata(**test_suite_metadata_dict)

    # Save create test_suite_metadata in DB
    db.add(test_suite_metadata)
    db.commit()

    # load stored test_suite_metadata from DB
    stored_test_suite_metadata = crud.test_suite_metadata.get(
        db=db, id=test_suite_metadata.id
    )

    # assert stored values match
    assert stored_test_suite_metadata
    assert test_suite_metadata.id == stored_test_suite_metadata.id
    assert test_suite_metadata.title == stored_test_suite_metadata.title
    assert test_suite_metadata.description == stored_test_suite_metadata.description
