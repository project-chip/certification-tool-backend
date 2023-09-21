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
# -*- coding: utf-8 -*-
"""
Pydantic data models for the server.
"""

from typing import List, Optional

from pydantic import BaseModel


class FormPostResponse(BaseModel):
    """Response from the form testing"""

    length: int = 0
    hash: Optional[str] = None
    token: Optional[str] = None
    content_type: Optional[str] = None


class ListTagsResponse(BaseModel):
    """Response from lists in query test"""

    tags: List[str]
