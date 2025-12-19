from __future__ import annotations

import weakref
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
import trio
from trio_websocket import WebSocketConnection, WebSocketRequest

from neuro_api.command import Action, ForcePriority, check_typed_dict
from neuro_api.server import (
    AbstractHandlerNeuroServerClient,
    AbstractNeuroServerClient,
    AbstractRecordingNeuroServerClient,
    AbstractTrioNeuroServer,
    BaseTrioNeuroServerClient,
    ConsoleInteractiveNeuroServer,
    ForceActionsData,
    TrioNeuroServerClient,
    check_action_names_type,
    deserialize_actions,
)


def test_deserialize_actions() -> None:
    """Test deserialize_actions function with valid data."""
    data = {
        "actions": [
            {
                "name": "test_action",
                "description": "A test action",
                "schema": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
            },
            {
                "name": "simple_action",
                "description": "Simple action without schema",
            },
        ],
    }

    actions = deserialize_actions(data)

    assert len(actions) == 2
    assert actions[0].name == "test_action"
    assert actions[0].description == "A test action"
    assert actions[0].schema is not None
    assert actions[1].name == "simple_action"
    assert actions[1].schema is None


def test_deserialize_actions_invalid_data() -> None:
    """Test deserialize_actions with invalid data structure."""
    data: dict[str, list[object]] = {"invalid_key": []}

    with pytest.raises(
        ValueError,
        match="Following extra keys were found: 'invalid_key'",
    ):
        deserialize_actions(data)


def test_deserialize_actions_invalid_action() -> None:
    """Test deserialize_actions with invalid action data."""
    data = {
        "actions": [
            {
                "name": "invalid action!",  # Invalid characters
                "description": "Invalid action",
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="Following invalid characters found in name",
    ):
        deserialize_actions(data)  # type: ignore[arg-type]


def test_check_action_names_type_valid() -> None:
    """Test check_action_names_type with valid string list."""
    action_names = ["action1", "action2", "action3"]
    # Should not raise any exception
    check_action_names_type(action_names)


def test_check_action_names_type_invalid() -> None:
    """Test check_action_names_type with invalid types."""
    action_names = ["action1", 123, "action3"]

    with pytest.raises(ValueError, match="123 is not a string object"):
        check_action_names_type(action_names)  # type: ignore[arg-type]


def test_actions_force_check_typed_dict() -> None:
    """Test `actions/force` check_typed_dict."""
    data = {
        "query": "Enter waffle ID",
        "action_names": ["choose_waffle"],
        "priority": "low",
    }

    result = check_typed_dict(
        data,
        ForceActionsData,
    )
    assert result == data


class TestAbstractNeuroServerClient:
    """Tests for AbstractNeuroServerClient."""

    @pytest.fixture
    def server_client(self) -> AbstractNeuroServerClient:
        """Create a concrete implementation for testing."""

        class TestServerClient(AbstractNeuroServerClient):
            def __init__(self) -> None:
                self._next_id = 0
                self.sent_data: list[bytes] = []
                self.received_data: list[str] = []

            def get_next_id(self) -> str:
                value = self._next_id
                self._next_id += 1
                return str(UUID(int=value))

            async def write_to_websocket(self, data: str) -> None:
                self.sent_data.append(data.encode())

            async def read_from_websocket(self) -> str:
                if self.received_data:
                    return self.received_data.pop(0)
                return "{}"

            async def handle_action_result(
                self,
                game_title: str,
                id_: str,
                success: bool,
                message: str | None,
            ) -> None:
                raise NotImplementedError()

            async def handle_actions_force(
                self,
                game_title: str,
                state: str | None,
                query: str,
                ephemeral_context: bool,
                action_names: list[str],
                priority: ForcePriority,
            ) -> None:
                raise NotImplementedError()

            async def handle_actions_register(
                self,
                game_title: str,
                actions: list[Action],
            ) -> None:
                raise NotImplementedError()

            async def handle_actions_unregister(
                self,
                game_title: str,
                action_names: list[str],
            ) -> None:
                raise NotImplementedError()

        return TestServerClient()

    @pytest.mark.trio
    async def test_send_action_command(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test sending action command."""
        action_id = await server_client.send_action_command(
            "test_action",
            '{"key": "value"}',
        )

        assert isinstance(action_id, str)
        # Verify UUID format
        UUID(action_id)  # Should not raise
        assert len(server_client.sent_data) == 1  # type: ignore[attr-defined]

    @pytest.mark.trio
    async def test_send_action_command_no_data(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test sending action command without data."""
        action_id = await server_client.send_action_command("test_action")

        assert isinstance(action_id, str)
        UUID(action_id)  # Should not raise

    @pytest.mark.trio
    async def test_send_reregister_all_command(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test sending reregister all command."""
        await server_client.send_reregister_all_command()

        assert len(server_client.sent_data) == 1  # type: ignore[attr-defined]

    @pytest.mark.trio
    async def test_send_graceful_shutdown_command(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test sending graceful shutdown command."""
        await server_client.send_graceful_shutdown_command(True)

        assert len(server_client.sent_data) == 1  # type: ignore[attr-defined]

    @pytest.mark.trio
    async def test_send_immediate_shutdown_command(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test sending immediate shutdown command."""
        await server_client.send_immediate_shutdown_command()

        assert len(server_client.sent_data) == 1  # type: ignore[attr-defined]

    @pytest.mark.trio
    async def test_handle_startup(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test handle_startup method (base implementation is empty)."""
        await server_client.handle_startup("Test Game")
        # Base implementation does nothing, should not raise

    @pytest.mark.trio
    async def test_handle_context(
        self,
        server_client: AbstractNeuroServerClient,
    ) -> None:
        """Test handle_context method (base implementation is empty)."""
        await server_client.handle_context("Test Game", "Test message", True)
        # Base implementation does nothing, should not raise


class TestHandlerClient(AbstractHandlerNeuroServerClient):
    def __init__(self) -> None:
        super().__init__()
        self.sent_data: list[bytes] = []
        self.context_messages: list[tuple[str, bool]] = []
        self.registered_actions: dict[str, Action] = {}

    async def write_to_websocket(self, data: str) -> None:
        self.sent_data.append(data.encode())

    async def read_from_websocket(self) -> str:
        return "{}"

    def clear_registered_actions(self) -> None:
        self.registered_actions.clear()

    def add_context(
        self,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        self.context_messages.append((message, reply_if_not_busy))

    def register_action(self, action: Action) -> None:
        self.registered_actions[action.name] = action

    def unregister_action(self, action_name: str) -> None:
        self.registered_actions.pop(action_name, None)

    async def choose_force_action(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: frozenset[str],
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        return next(iter(action_names)), None

    async def submit_call_async_soon(self, function: Any) -> None:
        await function()


class TestAbstractHandlerNeuroServerClient:
    """Tests for AbstractHandlerNeuroServerClient."""

    @pytest.fixture
    def handler_client(self) -> TestHandlerClient:
        """Create a concrete implementation for testing."""
        return TestHandlerClient()

    def test_get_next_id(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test unique ID generation."""
        id1 = handler_client.get_next_id()
        id2 = handler_client.get_next_id()

        assert id1 != id2
        # Should be valid UUIDs
        UUID(id1)
        UUID(id2)

    def test_check_game_title_none(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test check_game_title with None game title."""
        with patch.object(handler_client, "log_warning") as mock_log:
            handler_client.check_game_title("Test Game")
            mock_log.assert_called_with(
                "Attempted to change game title from None to 'Test Game', not allowed",
            )

    def test_check_game_title_mismatch(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test check_game_title with mismatched game title."""
        handler_client.game_title = "Original Game"

        with patch.object(handler_client, "log_warning") as mock_log:
            handler_client.check_game_title("Different Game")
            mock_log.assert_called_with(
                "Attempted to change game title from 'Original Game' to 'Different Game', not allowed",
            )

    @pytest.mark.trio
    async def test_handle_startup(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test handle_startup sets game title and clears actions."""
        action = Action("test", "desc")
        handler_client.registered_actions["test"] = action

        await handler_client.handle_startup("Test Game")

        assert handler_client.game_title == "Test Game"
        assert len(handler_client.registered_actions) == 0

    @pytest.mark.trio
    async def test_handle_context(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test handle_context adds message to context."""
        handler_client.game_title = "Test Game"

        await handler_client.handle_context("Test Game", "Test message", True)

        assert len(handler_client.context_messages) == 1
        assert handler_client.context_messages[0] == (
            "Test message",
            False,
        )  # silent=True -> reply_if_not_busy=False

    @pytest.mark.trio
    async def test_handle_actions_register(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test handle_actions_register registers actions."""
        handler_client.game_title = "Test Game"
        actions = [Action("test1", "desc1"), Action("test2", "desc2")]

        await handler_client.handle_actions_register("Test Game", actions)

        assert len(handler_client.registered_actions) == 2
        assert "test1" in handler_client.registered_actions
        assert "test2" in handler_client.registered_actions

    @pytest.mark.trio
    async def test_handle_actions_unregister(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test handle_actions_unregister removes actions."""
        handler_client.game_title = "Test Game"
        handler_client.registered_actions["test1"] = Action("test1", "desc1")
        handler_client.registered_actions["test2"] = Action("test2", "desc2")

        await handler_client.handle_actions_unregister("Test Game", ["test1"])

        assert len(handler_client.registered_actions) == 1
        assert "test1" not in handler_client.registered_actions
        assert "test2" in handler_client.registered_actions

    @pytest.mark.trio
    async def test_submit_action(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test submit_action workflow."""
        with patch.object(
            handler_client,
            "send_action_command",
            return_value="test-id",
        ) as mock_send:
            # Simulate action result coming back
            async def simulate_result() -> None:
                await handler_client.handle_action_result(
                    "Test Game",
                    "test-id",
                    True,
                    "Success",
                )

            handler_client.game_title = "Test Game"

            async with trio.open_nursery() as nursery:
                nursery.start_soon(simulate_result)
                success, message = await handler_client.submit_action(
                    "test_action",
                    '{"data": "value"}',
                )

            assert success is True
            assert message == "Success"
            mock_send.assert_called_once_with(
                "test_action",
                '{"data": "value"}',
            )

    @pytest.mark.trio
    async def test_handle_action_result_unknown_id(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test handle_action_result with unknown action ID."""
        handler_client.game_title = "Test Game"

        with patch.object(handler_client, "log_warning") as mock_log:
            await handler_client.handle_action_result(
                "Test Game",
                "unknown-id",
                True,
                "Success",
            )
            mock_log.assert_called_with(
                "Got action result for unknown action id 'unknown-id' (success = True message = 'Success')",
            )

    @pytest.mark.trio
    async def test_perform_actions_force_success_first_try(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test perform_actions_force succeeds on first try."""
        with patch.object(
            handler_client,
            "choose_force_action",
            return_value=("action1", None),
        ):
            with patch.object(
                handler_client,
                "submit_action",
                return_value=(True, "Success"),
            ):
                await handler_client.perform_actions_force(
                    "state",
                    "query",
                    False,
                    ["action1", "action2"],
                    ForcePriority.LOW,
                )

                # Should only be called once since first attempt succeeded
                handler_client.submit_action.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.trio
    async def test_perform_actions_force_retry_on_failure(
        self,
        handler_client: TestHandlerClient,
    ) -> None:
        """Test perform_actions_force retries on failure."""
        call_count = 0

        async def mock_submit_action(*args: Any) -> tuple[bool, str | None]:
            nonlocal call_count
            call_count += 1
            return (call_count > 2), "Success" if call_count > 2 else "Failed"

        with patch.object(
            handler_client,
            "choose_force_action",
            return_value=("action1", None),
        ):
            with patch.object(
                handler_client,
                "submit_action",
                side_effect=mock_submit_action,
            ):
                await handler_client.perform_actions_force(
                    "state",
                    "query",
                    False,
                    ["action1", "action2"],
                    ForcePriority.LOW,
                )

                assert call_count == 3  # Should retry until success


class TestAbstractRecordingNeuroServerClient:
    """Tests for AbstractRecordingNeuroServerClient."""

    @pytest.fixture
    def recording_client(self) -> AbstractRecordingNeuroServerClient:
        """Create a concrete implementation for testing."""

        class TestRecordingClient(AbstractRecordingNeuroServerClient):
            def __init__(self) -> None:
                super().__init__()
                self.sent_data: list[bytes] = []
                self.context_messages: list[tuple[str, bool]] = []

            async def write_to_websocket(self, data: str) -> None:
                self.sent_data.append(data.encode())

            async def read_from_websocket(self) -> str:
                return "{}"

            def add_context(
                self,
                message: str,
                reply_if_not_busy: bool,
            ) -> None:
                self.context_messages.append((message, reply_if_not_busy))

            async def choose_force_action(
                self,
                state: str | None,
                query: str,
                ephemeral_context: bool,
                action_names: frozenset[str],
                priority: ForcePriority = ForcePriority.LOW,
            ) -> tuple[str, str | None]:
                return next(iter(action_names)), None

            async def submit_call_async_soon(self, function: Any) -> None:
                await function()

        return TestRecordingClient()

    def test_clear_registered_actions(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test clearing registered actions."""
        action = Action("test", "description")
        recording_client.actions["test"] = action

        recording_client.clear_registered_actions()

        assert len(recording_client.actions) == 0

    def test_register_action(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test registering an action."""
        action = Action("test_action", "Test action")

        recording_client.register_action(action)

        assert "test_action" in recording_client.actions
        assert recording_client.actions["test_action"] == action

    def test_unregister_action_existing(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test unregistering an existing action."""
        action = Action("test_action", "Test action")
        recording_client.actions["test_action"] = action

        recording_client.unregister_action("test_action")

        assert "test_action" not in recording_client.actions

    def test_unregister_action_nonexistent(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test unregistering a non-existent action."""
        with patch.object(recording_client, "log_warning") as mock_log:
            recording_client.unregister_action("nonexistent")
            mock_log.assert_called_with(
                "Attempted to unregister non-existent action: nonexistent",
            )

    def test_get_action_existing(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test getting an existing action."""
        action = Action("test_action", "Test action")
        recording_client.actions["test_action"] = action

        result = recording_client.get_action("test_action")

        assert result == action

    def test_get_action_nonexistent(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test getting a non-existent action."""
        result = recording_client.get_action("nonexistent")

        assert result is None

    def test_has_action(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test checking if action exists."""
        action = Action("test_action", "Test action")
        recording_client.actions["test_action"] = action

        assert recording_client.has_action("test_action") is True
        assert recording_client.has_action("nonexistent") is False

    def test_get_action_names(
        self,
        recording_client: AbstractRecordingNeuroServerClient,
    ) -> None:
        """Test getting action names."""
        action1 = Action("action1", "Action 1")
        action2 = Action("action2", "Action 2")
        recording_client.actions["action1"] = action1
        recording_client.actions["action2"] = action2

        names = recording_client.get_action_names()

        assert names == frozenset({"action1", "action2"})


class TestBaseClient(BaseTrioNeuroServerClient):
    def __init__(self, websocket: Mock) -> None:
        super().__init__(websocket)
        self.websocket: Mock  # type: ignore[mutable-override]

    def add_context(
        self,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        pass

    async def choose_force_action(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: frozenset[str],
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        return next(iter(action_names)), None

    async def submit_call_async_soon(self, function: Any) -> None:
        await function()


class TestBaseTrioNeuroServerClient:
    """Tests for BaseTrioNeuroServerClient."""

    @pytest.fixture
    def mock_websocket(self) -> Mock:
        """Create a mock websocket connection."""
        mock_ws = Mock(spec=WebSocketConnection)
        mock_ws.send_message = AsyncMock()
        mock_ws.get_message = AsyncMock(return_value="test message")
        return mock_ws

    @pytest.fixture
    def base_client(self, mock_websocket: Mock) -> TestBaseClient:
        """Create a concrete implementation for testing."""
        return TestBaseClient(mock_websocket)

    @pytest.mark.trio
    async def test_write_to_websocket(
        self,
        base_client: TestBaseClient,
    ) -> None:
        """Test writing to websocket."""
        await base_client.write_to_websocket("test message")

        base_client.websocket.send_message.assert_called_once_with(
            "test message",
        )

    @pytest.mark.trio
    async def test_read_from_websocket(
        self,
        base_client: TestBaseClient,
    ) -> None:
        """Test reading from websocket."""
        result = await base_client.read_from_websocket()

        assert result == "test message"
        base_client.websocket.get_message.assert_called_once()


class TestTrioNeuroServerClient:
    """Tests for TrioNeuroServerClient."""

    @pytest.fixture
    def mock_server(self) -> Mock:
        """Create a mock server."""
        mock_server = Mock()
        mock_server.log_warning = Mock()
        mock_server.add_context = Mock()
        mock_server.choose_force_action = AsyncMock(
            return_value=("action1", None),
        )
        mock_server.handler_nursery = Mock()
        mock_server.handler_nursery.start_soon = Mock()
        return mock_server

    @pytest.fixture
    def mock_websocket(self) -> Mock:
        """Create a mock websocket connection."""
        mock_ws = Mock(spec=WebSocketConnection)
        mock_ws.remote = Mock()
        mock_ws.remote.address = "127.0.0.1"
        mock_ws.remote.port = 12345
        return mock_ws

    @pytest.fixture
    def trio_client(
        self,
        mock_websocket: Mock,
        mock_server: Mock,
    ) -> TrioNeuroServerClient:
        """Create a TrioNeuroServerClient for testing."""
        return TrioNeuroServerClient(mock_websocket, mock_server)

    def test_server_property_valid(
        self,
        trio_client: TrioNeuroServerClient,
        mock_server: Mock,
    ) -> None:
        """Test server property with valid reference."""
        result = trio_client.server
        assert result == mock_server

    def test_server_property_dead_reference(
        self,
        mock_websocket: Mock,
        mock_server: Mock,
    ) -> None:
        """Test server property with dead weak reference."""
        client = TrioNeuroServerClient(mock_websocket, mock_server)
        # Manually break the weak reference
        client._server_ref = weakref.ref(
            lambda: None,  # type: ignore[arg-type]
        )
        # Reference to a lambda that will be GC'd

        with pytest.raises(ValueError, match="Reference to server is dead"):
            _ = client.server

    def test_log_warning(
        self,
        trio_client: TrioNeuroServerClient,
        mock_server: Mock,
    ) -> None:
        """Test log_warning with client identification."""
        trio_client.game_title = "Test Game"

        trio_client.log_warning("Test warning")

        mock_server.log_warning.assert_called_once_with(
            "[Test Game (127.0.0.1:12345)] Test warning",
        )

    def test_log_warning_string_remote(self, mock_server: Mock) -> None:
        """Test log_warning with string remote address."""
        mock_ws = Mock()
        mock_ws.remote = "string_remote"
        client = TrioNeuroServerClient(mock_ws, mock_server)
        client.game_title = "Test Game"

        client.log_warning("Test warning")

        mock_server.log_warning.assert_called_once_with(
            "[Test Game (string_remote)] Test warning",
        )

    def test_add_context(
        self,
        trio_client: TrioNeuroServerClient,
        mock_server: Mock,
    ) -> None:
        """Test add_context delegates to server."""
        trio_client.game_title = "Test Game"

        trio_client.add_context("Test message", True)

        mock_server.add_context.assert_called_once_with(
            "Test Game",
            "Test message",
            True,
        )

    @pytest.mark.trio
    async def test_choose_force_action(
        self,
        trio_client: TrioNeuroServerClient,
        mock_server: Mock,
    ) -> None:
        """Test choose_force_action delegates to server."""
        trio_client.game_title = "Test Game"
        action = Action("test_action", "Test action")
        trio_client.actions["test_action"] = action

        result = await trio_client.choose_force_action(
            "state",
            "query",
            False,
            frozenset(["test_action"]),
            ForcePriority.LOW,
        )

        assert result == ("action1", None)
        mock_server.choose_force_action.assert_called_once()

    @pytest.mark.trio
    async def test_submit_call_async_soon(
        self,
        trio_client: TrioNeuroServerClient,
        mock_server: Mock,
    ) -> None:
        """Test submit_call_async_soon delegates to server nursery."""
        test_func = Mock()

        await trio_client.submit_call_async_soon(test_func)

        mock_server.handler_nursery.start_soon.assert_called_once_with(
            test_func,
        )


class TestAbstractTrioNeuroServer:
    """Tests for AbstractTrioNeuroServer."""

    @pytest.fixture
    def mock_server(self) -> AbstractTrioNeuroServer:
        """Create a concrete implementation for testing."""

        class TestServer(AbstractTrioNeuroServer):
            def add_context(
                self,
                game_title: str | None,
                message: str,
                reply_if_not_busy: bool,
            ) -> None:
                pass

            async def choose_force_action(
                self,
                game_title: str | None,
                state: str | None,
                query: str,
                ephemeral_context: bool,
                actions: tuple[Action, ...],
                priority: ForcePriority = ForcePriority.LOW,
            ) -> tuple[str, str | None]:
                return actions[0].name, None

        return TestServer()

    def test_log_methods(
        self,
        mock_server: AbstractTrioNeuroServer,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test logging methods."""
        mock_server.log_info("Test info")
        mock_server.log_warning("Test warning")
        mock_server.log_critical("Test critical")

        captured = capsys.readouterr()
        assert "[INFO] Test info" in captured.out
        assert "[WARNING] Test warning" in captured.out
        assert "[CRITICAL] Test critical" in captured.out

    @pytest.mark.trio
    async def test_handle_websocket_request(
        self,
        mock_server: AbstractTrioNeuroServer,
    ) -> None:
        """Test handle_websocket_request."""
        mock_request = Mock(spec=WebSocketRequest)
        mock_request.remote = Mock()
        mock_request.remote.address = "127.0.0.1"
        mock_request.remote.port = 12345
        mock_request.accept = AsyncMock()

        with patch.object(
            mock_server,
            "handle_client_connection",
        ) as mock_handle:
            await mock_server.handle_websocket_request(mock_request)

            mock_request.accept.assert_called_once()
            mock_handle.assert_called_once()


class TestConsoleInteractiveNeuroServer:
    """Tests for ConsoleInteractiveNeuroServer."""

    @pytest.fixture
    def console_server(self) -> ConsoleInteractiveNeuroServer:
        """Create a console server for testing."""
        return ConsoleInteractiveNeuroServer()

    def test_add_context(
        self,
        console_server: ConsoleInteractiveNeuroServer,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test add_context prints to console."""
        console_server.add_context("Test Game", "Test message", True)

        captured = capsys.readouterr()
        assert "[CONTEXT] Test message" in captured.out
        assert "reply_if_not_busy = True" in captured.out

    def test_show_help(
        self,
        console_server: ConsoleInteractiveNeuroServer,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test show_help method."""
        console_server.show_help()

        captured = capsys.readouterr()
        assert "Available Commands:" in captured.out
        assert "send <client_id> <action_name>" in captured.out
        assert "list - Show all connected clients" in captured.out

    def test_list_client_actions_with_actions(
        self,
        console_server: ConsoleInteractiveNeuroServer,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test list_client_actions with registered actions."""
        mock_client = Mock()
        mock_client.game_title = "Test Game"
        mock_client.actions = {
            "action1": Action("action1", "Action 1 description"),
            "action2": Action("action2", "Action 2 description"),
        }

        console_server.list_client_actions(mock_client)

        captured = capsys.readouterr()
        assert "Game: Test Game" in captured.out
        assert "Available actions:" in captured.out
        assert "action1: Action 1 description" in captured.out
        assert "action2: Action 2 description" in captured.out

    def test_list_client_actions_no_actions(
        self,
        console_server: ConsoleInteractiveNeuroServer,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test list_client_actions with no registered actions."""
        mock_client = Mock()
        mock_client.game_title = "Test Game"
        mock_client.actions = {}

        console_server.list_client_actions(mock_client)

        captured = capsys.readouterr()
        assert "Game: Test Game" in captured.out
        assert "No actions registered" in captured.out

    def test_ask_action_json_no_schema(
        self,
        console_server: ConsoleInteractiveNeuroServer,
    ) -> None:
        """Test ask_action_json with action that has no schema."""
        action = Action("test", "Test action", None)

        result = console_server.ask_action_json(action)

        assert result is None

    def test_ask_action_json_with_schema_no_input(
        self,
        console_server: ConsoleInteractiveNeuroServer,
    ) -> None:
        """Test ask_action_json with schema but user chooses not to provide JSON."""
        action = Action("test", "Test action", {"type": "object"})

        with patch("builtins.input", return_value="n"):
            result = console_server.ask_action_json(action)

        assert result is None

    def test_ask_action_json_with_schema_and_input(
        self,
        console_server: ConsoleInteractiveNeuroServer,
    ) -> None:
        """Test ask_action_json with schema and user provides JSON."""
        action = Action("test", "Test action", {"type": "object"})

        with patch("builtins.input", side_effect=["y", '{"key": "value"}']):
            result = console_server.ask_action_json(action)

        assert result == '{"key": "value"}'

    @pytest.mark.trio
    async def test_choose_force_action(
        self,
        console_server: ConsoleInteractiveNeuroServer,
    ) -> None:
        """Test choose_force_action interactive selection."""
        actions = (
            Action("action1", "First action"),
            Action("action2", "Second action"),
        )

        with patch(
            "builtins.input",
            side_effect=["1", "n"],
        ):  # Select first action, no JSON
            result = await console_server.choose_force_action(
                "Test Game",
                "Test state",
                "Test query",
                False,
                actions,
                ForcePriority.LOW,
            )

        assert result == ("action1", None)
