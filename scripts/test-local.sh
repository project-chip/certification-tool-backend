#!/usr/bin/env bash
set -e
set -x

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

#!/bin/sh
for arg in "$@"; do
    case $arg in
    --run-platform-dependant)
        RUN_ALL_TESTS=1
        shift # Remove --run-all from processing
        ;;
    *)
        OTHER_ARGUMENTS+=("$1")
        shift # Remove generic argument from processing
        ;;
    esac
done

if [[ $RUN_ALL_TESTS -eq 1 ]]; then
    echo "Running all tests"
    pytest --cov-config=.coveragerc --cov=app --cov=test_collections --cov-report=term-missing app/tests test_collections/matter/sdk_tests/support/tests "${@}"
else
    echo "Skipping platform dependant tests"
    pytest --cov-config=.coveragerc --cov=app --cov=test_collections --cov-report=term-missing --ignore=app/tests/platform_dependent_tests app/tests test_collections/matter/sdk_tests/support/tests "${@}"
fi
