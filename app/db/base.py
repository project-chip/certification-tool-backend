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
# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.operator import Operator  # noqa
from app.models.project import Project  # noqa
from app.models.test_case_execution import TestCaseExecution  # noqa
from app.models.test_case_metadata import TestCaseMetadata  # noqa
from app.models.test_run_execution import TestRunExecution  # noqa
from app.models.test_step_execution import TestStepExecution  # noqa
from app.models.test_suite_execution import TestSuiteExecution  # noqa
from app.models.test_suite_metadata import TestSuiteMetadata  # noqa
