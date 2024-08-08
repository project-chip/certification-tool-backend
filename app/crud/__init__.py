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
from .base import CRUDOperationNotSupported
from .crud_operator import operator
from .crud_project import project
from .crud_test_case_execution import test_case_execution
from .crud_test_case_metadata import test_case_metadata
from .crud_test_collection_execution import test_collection_execution
from .crud_test_collection_metadata import test_collection_metadata
from .crud_test_run_config import test_run_config
from .crud_test_run_execution import test_run_execution
from .crud_test_step_execution import test_step_execution
from .crud_test_suite_execution import test_suite_execution
from .crud_test_suite_metadata import test_suite_metadata

# For a new basic set of CRUD operations you could just do

# from .base import CRUDBase
# from app.models.item import Item
# from app.schemas.item import ItemCreate, ItemUpdate

# item = CRUDBase[Item, ItemCreate, ItemUpdate](Item)
