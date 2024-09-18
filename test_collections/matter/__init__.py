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
import os

# Verify if this execution comes from python_tests_validator.
if not os.getenv("DRY_RUN"):
    from .python_tests import onboarding_payload_collection
    from .sdk_tests.support.performance_tests import sdk_performance_collection
    from .sdk_tests.support.python_testing import (
        custom_python_collection,
        sdk_mandatory_python_collection,
        sdk_python_collection,
    )
    from .sdk_tests.support.yaml_tests import custom_collection, sdk_collection
