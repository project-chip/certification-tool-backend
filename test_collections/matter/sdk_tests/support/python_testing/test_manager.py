#
# Copyright (c) 2025 Project CHIP Authors
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

import asyncio
import logging
import sys

from app.test_engine.models.test_declarations import TestCollectionDeclaration

from .list_python_tests_classes import (
    CUSTOM_PYTHON_SCRIPTS_FOLDER,
    CUSTOM_PYTHON_TESTS_PARSED_FILE,
    generate_python_test_json_file,
)
from .sdk_python_tests import (
    _create_custom_python_test_collection,
    sdk_mandatory_python_test_collection,
    sdk_python_test_collection,
)

logger = logging.getLogger(__name__)


def _update_module_collections(
    sdk_collection: TestCollectionDeclaration,
    mandatory_collection: TestCollectionDeclaration,
    custom_collection: TestCollectionDeclaration | None,
) -> None:
    """
    Update module references for Python test collections.

    This handles the critical step of updating both the python_testing module
    and the matter module that imports these collections.
    """
    # Update python_testing module
    init_module = sys.modules[__name__.rsplit(".", 1)[0]]
    collections = {
        "sdk_python_collection": sdk_collection,
        "sdk_mandatory_python_collection": mandatory_collection,
        "custom_python_collection": custom_collection,
    }

    for name, collection in collections.items():
        setattr(init_module, name, collection)
        init_module.__dict__[name] = collection

    # Update matter module's imported references
    matter_module = sys.modules.get("test_collections.matter")
    if matter_module:
        logger.debug(
            "Updating matter module references after Python test initialization"
        )
        for name, collection in collections.items():
            setattr(matter_module, name, collection)
            matter_module.__dict__[name] = collection


async def _generate_all_test_files() -> None:
    """Generate both standard and custom test JSON files in a single container session."""
    logger.info("Starting test file generation with shared container session")

    try:
        # Generate standard SDK tests first
        await generate_python_test_json_file(grouped_commands=True)
        logger.info("Standard SDK tests generated successfully")

        # Generate custom tests using the same container session context
        await generate_python_test_json_file(
            test_folder=CUSTOM_PYTHON_SCRIPTS_FOLDER,
            json_output_file=CUSTOM_PYTHON_TESTS_PARSED_FILE,
            grouped_commands=True,
        )
        logger.info("Custom tests generated successfully")

    except Exception as e:
        logger.error(f"Failed to generate test files: {e}")
        raise


def _create_collections() -> (
    tuple[
        TestCollectionDeclaration,
        TestCollectionDeclaration,
        TestCollectionDeclaration | None,
    ]
):
    """Create and return all Python test collection declarations."""
    return (
        sdk_python_test_collection(),
        sdk_mandatory_python_test_collection(),
        _create_custom_python_test_collection(),
    )


def initialize_python_tests_sync() -> (
    tuple[
        TestCollectionDeclaration,
        TestCollectionDeclaration,
        TestCollectionDeclaration | None,
    ]
):
    """
    Synchronous version for test environments.

    Uses asyncio.run() which is safe in test environments without a running event loop.

    Returns:
        Tuple of (sdk_collection, mandatory_collection, custom_collection)
    """
    logger.info("Initializing Python test collections (sync)")

    try:
        # Generate test files and create collections
        asyncio.run(_generate_all_test_files())
        sdk_collection, mandatory_collection, custom_collection = _create_collections()

        # Update module references
        _update_module_collections(
            sdk_collection, mandatory_collection, custom_collection
        )

        logger.info("Python test collections initialized successfully (sync)")
        return sdk_collection, mandatory_collection, custom_collection

    except Exception as e:
        logger.error(f"Failed to initialize Python test collections (sync): {e}")
        raise


async def initialize_python_tests() -> tuple[
    TestCollectionDeclaration,
    TestCollectionDeclaration,
    TestCollectionDeclaration | None,
]:
    """
    Async version for application startup.

    Generates test JSON files using a single container session and creates
    test collection declarations for use in the application.

    Returns:
        Tuple of (sdk_collection, mandatory_collection, custom_collection)
    """
    logger.info("Initializing Python test collections (async)")

    try:
        # Generate test files and create collections
        await _generate_all_test_files()
        sdk_collection, mandatory_collection, custom_collection = _create_collections()

        # Update module references
        _update_module_collections(
            sdk_collection, mandatory_collection, custom_collection
        )

        logger.info("Python test collections initialized successfully (async)")
        return sdk_collection, mandatory_collection, custom_collection

    except Exception as e:
        logger.error(f"Failed to initialize Python test collections (async): {e}")
        raise
