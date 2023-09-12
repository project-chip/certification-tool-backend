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
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.operator import Operator
from app.schemas.operator import OperatorCreate, OperatorUpdate


class CRUDOperator(CRUDBase[Operator, OperatorCreate, OperatorUpdate]):
    def get_by_name(self, db: Session, name: str) -> Optional[Operator]:
        query = self.select().where(Operator.name == name)
        return db.scalars(query).first()

    def get_or_create(self, db: Session, name: str, commit: bool = True) -> int:
        """
        Look for an Operator in the database with the same name. If none is found,
        create a new Operator.

        Args:
            db (Session): The database session
            name (str): The Operator name to use in the query
            commit (bool): Flag to indicate if the commit should be performed

        Returns:
            int: Operator ID
        """
        if operator := self.get_by_name(db=db, name=name):
            return operator.id

        operator = Operator(name=name)

        db.add(operator)
        db.flush()

        if commit:
            db.commit()

        return operator.id


operator = CRUDOperator(Operator)
