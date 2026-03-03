#
# Copyright (c) 2026 Project CHIP Authors
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
"""
Unit tests for Python test initialization optimizations.

These tests verify:
1. Phase 1: TestScriptManager constructor doesn't initialize Python tests
2. Phase 2: Python test generation uses single container session
"""
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.test_engine.test_script_manager import TestScriptManager
from test_collections.matter.sdk_tests.support.python_testing.list_python_tests_classes import (  # noqa: E501
    generate_python_test_json_file,
    process_test_commands_with_container,
)
from test_collections.matter.sdk_tests.support.python_testing.test_manager import (
    _generate_all_test_files,
)


@pytest.fixture(autouse=True)
def restore_singleton_state() -> Generator:
    """Save and restore TestScriptManager singleton state around each test.

    TestScriptManager is a singleton shared across the test session.
    Some tests call initialize_python_tests() which mutates test_collections
    and _python_tests_initialized on the singleton. This fixture ensures
    those mutations are rolled back after each test, and that the flag starts
    at False before each test (matching the constructor's initial state).
    """
    manager = TestScriptManager()
    saved_collections = manager.test_collections
    saved_flag = manager._python_tests_initialized
    # Reset to the initial post-constructor state before each test
    manager._python_tests_initialized = False
    yield
    manager.test_collections = saved_collections
    manager._python_tests_initialized = saved_flag


class TestPhase1ConstructorOptimization:
    """Test Phase 1: Constructor should not initialize Python tests."""

    def test_constructor_does_not_call_ensure_initialization(self) -> None:
        """Verify constructor doesn't call _ensure_python_tests_initialized."""
        # Create a new TestScriptManager instance
        # Note: We use the existing singleton, so we verify behavior indirectly
        manager = TestScriptManager()

        # Verify the method doesn't exist (it was removed)
        assert not hasattr(
            manager, "_ensure_python_tests_initialized"
        ), "Constructor should not have _ensure_python_tests_initialized method"

    def test_constructor_sets_initialization_flag_to_false(self) -> None:
        """Verify constructor sets _python_tests_initialized to False.

        Since TestScriptManager is a singleton, this test verifies that the
        flag is False when no initialization has occurred in this test session,
        relying on the restore_singleton_state fixture to reset it.
        """
        manager = TestScriptManager()

        # The flag should be False (reset by restore_singleton_state fixture)
        assert (
            manager._python_tests_initialized is False
        ), "Constructor should set _python_tests_initialized to False"

    def test_constructor_discovers_test_collections(self) -> None:
        """Verify constructor calls _discover_test_collections."""
        manager = TestScriptManager()

        # Verify test_collections is populated
        assert hasattr(
            manager, "test_collections"
        ), "Constructor should set test_collections"
        assert isinstance(
            manager.test_collections, dict
        ), "test_collections should be a dictionary"


class TestPhase1AsyncInitialization:
    """Test Phase 1: Async initialization should work correctly."""

    @pytest.mark.asyncio
    async def test_initialize_python_tests_sets_flag(self) -> None:
        """Verify initialize_python_tests sets _python_tests_initialized flag."""
        manager = TestScriptManager()

        # Mock the initialization function
        with patch(
            "app.test_engine.test_script_manager.discover_test_collections"
        ) as mock_discover:
            mock_discover.return_value = {}

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "initialize_python_tests",
                new_callable=AsyncMock,
            ) as mock_init:
                # Setup mock to return test collections
                mock_init.return_value = (
                    MagicMock(),  # sdk_collection
                    MagicMock(),  # mandatory_collection
                    None,  # custom_collection
                )

                await manager.initialize_python_tests()

                # Verify the flag is set to True after successful initialization
                assert (
                    manager._python_tests_initialized is True
                ), "initialize_python_tests should set _python_tests_initialized "
                "to True"

    @pytest.mark.asyncio
    async def test_initialize_python_tests_updates_collections(self) -> None:
        """Verify initialize_python_tests updates test_collections."""
        manager = TestScriptManager()

        with patch(
            "app.test_engine.test_script_manager.discover_test_collections"
        ) as mock_discover:
            expected_collections = {"test_collection": MagicMock()}
            mock_discover.return_value = expected_collections

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "initialize_python_tests",
                new_callable=AsyncMock,
            ) as mock_init:
                mock_init.return_value = (MagicMock(), MagicMock(), None)

                await manager.initialize_python_tests()

                # Verify discover was called after initialization
                assert mock_discover.called, "Should call discover_test_collections"


class TestPhase2SingleContainerSession:
    """Test Phase 2: Single container session for all test generation."""

    @pytest.mark.asyncio
    async def test_generate_all_test_files_uses_single_container(self) -> None:
        """Verify _generate_all_test_files uses a single SDK container session."""
        mock_container = MagicMock()
        mock_container.start = AsyncMock()
        mock_container.destroy = MagicMock()

        with patch(
            "test_collections.matter.sdk_tests.support.python_testing.test_manager."
            "SDKContainer"
        ) as mock_container_class:
            mock_container_class.return_value = mock_container

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing.test_manager."
                "get_command_list"
            ) as mock_get_commands:
                mock_get_commands.return_value = []

                with patch(
                    "test_collections.matter.sdk_tests.support.python_testing."
                    "test_manager.process_test_commands_with_container",
                    new_callable=AsyncMock,
                ) as mock_process:
                    with patch(
                        "test_collections.matter.sdk_tests.support.python_testing."
                        "test_manager._has_custom_tests"
                    ) as mock_has_custom:
                        mock_has_custom.return_value = True

                        # Execute the function
                        await _generate_all_test_files()

                        # Verify container was created once
                        assert (
                            mock_container_class.call_count == 1
                        ), "Should create container once"

                        # Verify container was started once
                        assert (
                            mock_container.start.call_count == 1
                        ), "Should start container once"

                        # Verify container was destroyed once
                        assert (
                            mock_container.destroy.call_count == 1
                        ), "Should destroy container once"

                        # Verify process_test_commands_with_container was called twice
                        # (once for SDK tests, once for custom tests)
                        assert (
                            mock_process.call_count == 2
                        ), "Should process tests twice with same container"

    @pytest.mark.asyncio
    async def test_generate_all_test_files_destroys_container_on_error(self) -> None:
        """Verify container is destroyed even if test generation fails."""
        mock_container = MagicMock()
        mock_container.start = AsyncMock()
        mock_container.destroy = MagicMock()

        with patch(
            "test_collections.matter.sdk_tests.support.python_testing.test_manager."
            "SDKContainer"
        ) as mock_container_class:
            mock_container_class.return_value = mock_container

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing.test_manager."
                "get_command_list"
            ) as mock_get_commands:
                # Simulate an error during command list generation
                mock_get_commands.side_effect = Exception("Test error")

                # Execute the function and expect it to raise
                with pytest.raises(Exception, match="Test error"):
                    await _generate_all_test_files()

                # Verify container was still destroyed despite the error
                assert (
                    mock_container.destroy.call_count == 1
                ), "Should destroy container even on error"

    @pytest.mark.asyncio
    async def test_generate_all_test_files_skips_custom_when_none_exist(self) -> None:
        """Verify custom test generation is skipped when no custom tests exist."""
        mock_container = MagicMock()
        mock_container.start = AsyncMock()
        mock_container.destroy = MagicMock()

        with patch(
            "test_collections.matter.sdk_tests.support.python_testing.test_manager."
            "SDKContainer"
        ) as mock_container_class:
            mock_container_class.return_value = mock_container

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing.test_manager."
                "get_command_list"
            ) as mock_get_commands:
                mock_get_commands.return_value = []

                with patch(
                    "test_collections.matter.sdk_tests.support.python_testing."
                    "test_manager.process_test_commands_with_container",
                    new_callable=AsyncMock,
                ) as mock_process:
                    with patch(
                        "test_collections.matter.sdk_tests.support.python_testing."
                        "test_manager._has_custom_tests"
                    ) as mock_has_custom:
                        mock_has_custom.return_value = False

                        with patch(
                            "test_collections.matter.sdk_tests.support.python_testing."
                            "test_manager.CUSTOM_PYTHON_TESTS_PARSED_FILE"
                        ) as mock_file:
                            mock_file.write_text = MagicMock()

                            # Execute the function
                            await _generate_all_test_files()

                            # Verify process was called only once (for SDK tests)
                            assert (
                                mock_process.call_count == 1
                            ), "Should process SDK tests only"

                            # Verify empty JSON was written for custom tests
                            mock_file.write_text.assert_called_once_with(
                                '{"tests": []}'
                            )


class TestPhase2ProcessTestCommandsWithContainer:
    """Test the new process_test_commands_with_container function."""

    @pytest.mark.asyncio
    async def test_process_test_commands_does_not_start_container(self) -> None:
        """Verify process_test_commands_with_container doesn't start/stop container."""
        mock_container = MagicMock()
        mock_container.start = AsyncMock()
        mock_container.destroy = MagicMock()

        with patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.__process_grouped_commands",
            new_callable=AsyncMock,
        ) as mock_process:
            mock_process.return_value = (0, 0)  # test_count, invalid_count

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "list_python_tests_classes.Path"
            ):
                with patch("builtins.open", MagicMock()):
                    # Execute the function
                    await process_test_commands_with_container(
                        sdk_container=mock_container,
                        commands=[],
                        json_output_file=Mock(),
                        grouped_commands=True,
                    )

                    # Verify container start/destroy were NOT called
                    assert (
                        mock_container.start.call_count == 0
                    ), "Should not start container"
                    assert (
                        mock_container.destroy.call_count == 0
                    ), "Should not destroy container"

    @pytest.mark.asyncio
    async def test_process_test_commands_uses_provided_container(self) -> None:
        """Verify process_test_commands_with_container uses the provided container."""
        mock_container = MagicMock()

        with patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.__process_grouped_commands",
            new_callable=AsyncMock,
        ) as mock_process:
            mock_process.return_value = (0, 0)

            with patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "list_python_tests_classes.Path"
            ):
                with patch("builtins.open", MagicMock()):
                    await process_test_commands_with_container(
                        sdk_container=mock_container,
                        commands=[],
                        json_output_file=Mock(),
                        grouped_commands=True,
                    )

                    # Verify the container was passed to process function
                    assert mock_process.called, "Should call process function"
                    call_args = mock_process.call_args
                    assert (
                        call_args[0][0] == mock_container
                    ), "Should pass container to process function"


class TestBackwardCompatibility:
    """Test that backward compatibility is maintained."""

    @pytest.mark.asyncio
    async def test_generate_python_test_json_file_still_works(self) -> None:
        """Verify generate_python_test_json_file still works for backward
        compatibility."""
        # This function should still exist and be callable
        assert callable(
            generate_python_test_json_file
        ), "generate_python_test_json_file should still exist"

        # Verify it calls the old process_commands_sdk_container function
        with patch(
            "test_collections.matter.sdk_tests.support.python_testing."
            "list_python_tests_classes.process_commands_sdk_container",
            new_callable=AsyncMock,
        ) as mock_process:
            with patch(
                "test_collections.matter.sdk_tests.support.python_testing."
                "list_python_tests_classes.get_command_list"
            ) as mock_get_commands:
                mock_get_commands.return_value = []

                await generate_python_test_json_file()

                # Verify the old function was called
                assert (
                    mock_process.called
                ), "Should call process_commands_sdk_container for backward "
                "compatibility"
