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
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.crud.base import CRUDBaseDelete, CRUDBaseRead, CRUDBaseUpdate
from app.default_environment_config import default_environment_config
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils import program_class


class CRUDProject(
    CRUDBaseRead[Project],
    CRUDBaseDelete[Project],
    CRUDBaseUpdate[Project, ProjectUpdate],
):
    def get_multi(
        self,
        db: Session,
        *,
        archived: Optional[bool] = False,
        order_by: Optional[str] = None,
        skip: Optional[int] = 0,
        limit: Optional[int] = 100,
    ) -> Sequence[Project]:
        query = self.select()

        if archived:
            query = query.filter(self.model.archived_at.isnot(None))
        else:
            query = query.filter(self.model.archived_at.is_(None))

        if order_by is None:
            query = query.order_by(self.model.id)
        else:
            query = query.order_by(order_by)

        query = query.offset(skip).limit(limit)

        return db.scalars(query).all()

    def archive(self, db: Session, db_obj: Project) -> Project:
        return self.update(db=db, db_obj=db_obj, obj_in={"archived_at": datetime.now()})

    def unarchive(self, db: Session, db_obj: Project) -> Project:
        return self.update(db=db, db_obj=db_obj, obj_in={"archived_at": None})

    def __validate_model(self, obj_in: dict) -> bool:
        func_name = "validate_model"
        func_validate_model = getattr(program_class, func_name, None)

        if not func_validate_model:
            raise AttributeError(f"{func_name} is not a method of {program_class}")
        if not callable(func_validate_model):
            raise TypeError(f"{func_name} is not callable")

        return func_validate_model(program_class, obj_in)

    # We use a custom create method, to add default config if config is missing
    # and validate de project configuration
    def create(self, db: Session, *, obj_in: ProjectCreate) -> Project:
        json_obj_in = jsonable_encoder(obj_in)

        if obj_in.config is None or len(obj_in.config) == 0:
            obj_in.config = default_environment_config.__dict__
            json_obj_in = jsonable_encoder(obj_in)
        # Try to instantiate the program class in order to validate the input data
        if program_class:
            program_class(**json_obj_in["config"])

        obj_in_data = json_obj_in
        db_obj = Project(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # We use a custom update method, to add default config if config is missing
    # and validate de project configuration
    def update(
        self,
        db: Session,
        *,
        db_obj: Project,
        obj_in: Union[ProjectUpdate, Dict[str, Any]],
    ) -> Project:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        # Try to instantiate the program class in order to validate the input data
        if program_class:
            program_class(**jsonable_encoder(db_obj)["config"])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


project = CRUDProject(Project)
