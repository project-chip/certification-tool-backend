
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
FROM ubuntu:22.04

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Sets timezone so the container build is not waiting for a prompt
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -y && apt-get install -y python3-pip python3-venv libpq-dev curl git 

RUN ln -s /usr/bin/python3.10 /usr/local/bin/python

# Configure Gunicorn
RUN pip install --no-cache-dir "uvicorn[standard]==0.15.0" gunicorn

COPY ./gunicorn/start.sh /start.sh
RUN chmod +x /start.sh

COPY ./gunicorn/gunicorn_conf.py /gunicorn_conf.py

COPY ./gunicorn/start-reload.sh /start-reload.sh
RUN chmod +x /start-reload.sh

# Use /app to host app
WORKDIR /app/
ENV PYTHONPATH=/app

# Workaround poetry wheel issue by pre-installing the psycopg package
RUN pip install psycopg2_binary==2.9.1

# Lark is needed for Matter IDL parser
RUN pip install build lark stringcase

# Install Poetry
ENV POETRY_VERSION=1.6.1
ENV POETRY_HOME=/opt/poetry 
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Install Docker
RUN curl -sSL https://get.docker.com/ | sh

# Install nodejs, npm and spell checker
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g npm@latest
RUN npm install -g cspell@latest

# Allow installing dev dependencies to run tests
# Copy poetry dependecy files and install dependencies
# We copy install dependencies before copying all app source to reuse the dependency install step in docker.
COPY ./pyproject.toml ./poetry.lock* /app/
# ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi"

# # Copy Source files
COPY . /app

# Record git SHA
ARG GIT_SHA
ENV GIT_SHA=${GIT_SHA}
RUN echo $GIT_SHA > .sha_information

# Run the start script, it will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Gunicorn with Uvicorn
CMD ["/start.sh"]
