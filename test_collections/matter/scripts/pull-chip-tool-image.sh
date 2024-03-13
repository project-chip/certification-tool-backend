#!/bin/bash -e
set -x
set -e

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


DOCKER_TAG=`python -c "from ..config import matter_settings; print(f'{matter_settings.SDK_DOCKER_IMAGE}:{matter_settings.SDK_DOCKER_TAG}')"`
docker pull $DOCKER_TAG