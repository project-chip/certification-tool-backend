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

from app import crud, models
from app.schemas.operator import OperatorCreate
from app.tests.utils.utils import random_lower_string


def create_random_operator(db: Session) -> models.Operator:
    name = random_lower_string()
    operator_in = OperatorCreate(name=name)
    return crud.operator.create(db=db, obj_in=operator_in)


operator_base_dict = {"name": "John Doe"}
