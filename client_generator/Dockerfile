
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
FROM python:3.7-slim

RUN apt-get update && apt-get install -y build-essential dos2unix
RUN pip install black autoflake isort httpx fastapi typing_extensions
ADD scripts/util/postprocess-docker.sh /

# Fix EOL in case the Docker build process runs on Windows
RUN dos2unix /postprocess-docker.sh

ENTRYPOINT ["/postprocess-docker.sh"]
