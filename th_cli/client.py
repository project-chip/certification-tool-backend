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
from th_cli.api_lib_autogen.api_client import ApiClient
from th_cli.config import config
from th_cli.exceptions import ConfigurationError


def get_client() -> ApiClient:
    """Get API client with proper error handling."""
    try:
        return ApiClient(host=f"http://{config.hostname}")
    except Exception as e:
        raise ConfigurationError(
            f"Could not connect to API server at {config.hostname}. "
            f"Please check if the server is running and the hostname is correct. "
            f"Error: {e}"
        )


# [Deprecated] For backward compatibility
client: ApiClient | None = None
try:
    client = get_client()
except ConfigurationError:
    # Don't fail at module level, let commands handle it
    pass
