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
import inspect

import click
from pydantic import BaseModel

from th_cli.api_lib_autogen import models

# Update forward references for all models
for model in inspect.getmembers(models, inspect.isclass):
    if model[1].__module__ == "th_cli.api_lib_autogen.models":
        model_class = model[1]
        if issubclass(model_class, BaseModel):
            try:
                model_class.update_forward_refs()
            except Exception as e:
                # Some models might not need forward ref updates or might fail
                # This is okay, we'll continue with other models
                click.echo(f"Warning: Could not update forward refs for {model_class.__name__} on first pass: {e}")

# Try to update forward references again after all models are processed
# This handles circular dependencies
for model in inspect.getmembers(models, inspect.isclass):
    if model[1].__module__ == "th_cli.api_lib_autogen.models":
        model_class = model[1]
        if issubclass(model_class, BaseModel):
            try:
                model_class.update_forward_refs()
            except Exception as e:
                # If it still fails, that's okay
                click.echo(f"Warning: Could not update forward refs for {model_class.__name__} on second pass: {e}")
