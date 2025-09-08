from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import trio_websocket

from neuro_api import command
from neuro_api.api import AbstractNeuroAPI, NeuroAction
from neuro_api.command import Action


@pytest.fixture
async def neuro_api() -> tuple[AbstractNeuroAPI, AsyncMock]:
    websocket = AsyncMock()

    class TestNeuroAPI(AbstractNeuroAPI):
        """Test Neuro API."""

        def __init__(self, game_title: str) -> None:
            super().__init__(game_title)
            self._websocket = websocket

        async def handle_action(self, action: NeuroAction) -> None:
            """Mock implementation for testing."""

        async def read_from_websocket(self) -> str:
            return await websocket.get_message()  # type: ignore[no-any-return]

        async def write_to_websocket(self, data: str) -> None:
            await websocket.send_message(data)

    api = TestNeuroAPI("Test Game")
    return api, websocket


@pytest.mark.trio
async def test_send_command_data(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()

    await api.send_command_data(b"test command")

    websocket.send_message.assert_awaited_once_with("test command")


@pytest.mark.trio
async def test_send_startup_command(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()

    await api.send_startup_command()

    websocket.send_message.assert_awaited_once_with(
        command.startup_command("Test Game").decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_context(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    message = "hellos neuro!"
    websocket.send_message = AsyncMock()

    await api.send_context(message)

    websocket.send_message.assert_awaited_once_with(
        command.context_command("Test Game", message, True).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_context_not_silent(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    message = "hellos neuro!"
    websocket.send_message = AsyncMock()

    await api.send_context(message, silent=False)

    websocket.send_message.assert_awaited_once_with(
        command.context_command("Test Game", message, False).decode("utf-8"),
    )


@pytest.mark.trio
async def test_register_actions(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    action = command.Action("test_action", "Test Action")
    websocket.send_message = AsyncMock()

    await api.register_actions([action])

    assert "test_action" in api.get_registered()
    websocket.send_message.assert_awaited_once_with(
        command.actions_register_command("Test Game", [action]).decode(
            "utf-8",
        ),
    )


@pytest.mark.trio
async def test_unregister_actions(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    action = command.Action("test_action", "Test Action", None)
    websocket.send_message = AsyncMock()
    await api.register_actions([action])

    await api.unregister_actions(["test_action"])

    assert "test_action" not in api.get_registered()
    websocket.send_message.assert_awaited_with(
        command.actions_unregister_command(
            "Test Game",
            ["test_action"],
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_force_action(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    action_names = ["test_action"]
    action = command.Action("test_action", "Test Action", None)
    websocket.send_message = AsyncMock()
    await api.register_actions([action])

    await api.send_force_action("state", "query", action_names)

    # Should have been called twice: once for register_actions, once for send_force_action
    assert websocket.send_message.await_count == 2
    websocket.send_message.assert_awaited_with(
        command.actions_force_command(
            "Test Game",
            "state",
            "query",
            action_names,
            False,
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_force_action_with_ephemeral_context(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    action_names = ["test_action"]
    action = command.Action("test_action", "Test Action", None)
    websocket.send_message = AsyncMock()
    await api.register_actions([action])

    await api.send_force_action(
        "state",
        "query",
        action_names,
        ephemeral_context=True,
    )

    # Should have been called twice: once for register_actions, once for send_force_action
    assert websocket.send_message.await_count == 2
    websocket.send_message.assert_awaited_with(
        command.actions_force_command(
            "Test Game",
            "state",
            "query",
            action_names,
            True,
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_force_action_unregistered(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api

    with pytest.raises(
        ValueError,
        match=r"'test_action' is not currently registered\.",
    ):
        await api.send_force_action("state", "query", ["test_action"])


@pytest.mark.trio
async def test_send_action_result(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()
    id_ = "id_name"
    success = True
    message = "waffles"

    await api.send_action_result(id_, success, message)

    websocket.send_message.assert_awaited_once_with(
        command.actions_result_command(
            "Test Game",
            id_,
            success,
            message,
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_action_result_no_message(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()
    id_ = "id_name"
    success = True

    await api.send_action_result(id_, success)

    websocket.send_message.assert_awaited_once_with(
        command.actions_result_command(
            "Test Game",
            id_,
            success,
            None,
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_send_shutdown_ready(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()

    await api.send_shutdown_ready()

    websocket.send_message.assert_awaited_once_with(
        command.shutdown_ready_command(
            "Test Game",
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_read_raw_server_message(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.get_message = AsyncMock(
        return_value=b'{"command":"action","data":{"id":"1","name":"test_action"}}',
    )

    command_type, data = await api.read_raw_server_message()
    assert command_type == "action"
    assert data == {"id": "1", "name": "test_action"}


@pytest.mark.trio
async def test_handle_graceful_shutdown_request(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.handle_graceful_shutdown_request(True)

    api.send_shutdown_ready.assert_awaited_once()


@pytest.mark.trio
async def test_handle_graceful_shutdown_request_false(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.handle_graceful_shutdown_request(False)

    api.send_shutdown_ready.assert_not_awaited()


@pytest.mark.trio
async def test_handle_immediate_shutdown(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.handle_immediate_shutdown()

    api.send_shutdown_ready.assert_awaited_once()


@pytest.mark.trio
async def test_read_message_action_command(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("action", {"id": "1", "name": "test_action"}),
    )
    api.handle_action = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_action.assert_awaited_once_with(
        NeuroAction("1", "test_action", None),
    )


@pytest.mark.trio
async def test_read_message_action_command_with_data(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=(
            "action",
            {"id": "1", "name": "test_action", "data": "some_data"},
        ),
    )
    api.handle_action = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_action.assert_awaited_once_with(
        NeuroAction("1", "test_action", "some_data"),
    )


@pytest.mark.trio
async def test_read_message_unknown_command(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("unknown_command", None),
    )
    api.handle_unknown_command = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_unknown_command.assert_awaited_once_with(
        "unknown_command",
        None,
    )


@pytest.mark.trio
async def test_read_message_reregister(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()

    action = command.Action("test_action", "Test Action")
    await api.register_actions([action])

    # Mock the read_raw_server_message to return reregister_all command
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("actions/reregister_all", None),
    )

    await api.read_message()

    # Should have been called twice: once for initial register, once for reregister
    assert websocket.send_message.await_count == 2


@pytest.mark.trio
async def test_read_message_reregister_no_actions(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.send_message = AsyncMock()

    # Don't register any actions first

    # Mock the read_raw_server_message to return reregister_all command
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("actions/reregister_all", None),
    )

    await api.read_message()

    # Should not have been called since no actions were registered
    websocket.send_message.assert_not_awaited()


@pytest.mark.trio
async def test_read_message_graceful_shutdown(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("shutdown/graceful", {"wants_shutdown": True}),
    )
    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.send_shutdown_ready.assert_awaited_once()


@pytest.mark.trio
async def test_read_message_graceful_shutdown_false(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("shutdown/graceful", {"wants_shutdown": False}),
    )
    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.send_shutdown_ready.assert_not_awaited()


@pytest.mark.trio
async def test_read_message_immediate_shutdown(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_server_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("shutdown/immediate", None),
    )
    api.handle_immediate_shutdown = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_immediate_shutdown.assert_awaited_once()


@pytest.mark.trio
async def test_get_registered(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api

    # Initially empty
    assert api.get_registered() == ()

    # Register some actions
    action1 = command.Action("action1", "Action 1")
    action2 = command.Action("action2", "Action 2")
    await api.register_actions([action1, action2])

    registered = api.get_registered()
    assert "action1" in registered
    assert "action2" in registered
    assert len(registered) == 2


async def run() -> None:
    """Run program."""
    from neuro_api.trio_ws import TrioNeuroAPI

    class Game(TrioNeuroAPI):
        """Game context."""

        __slots__ = ()

        async def handle_action(self, action: NeuroAction) -> None:
            """Handle action."""
            print(f"{action = }")
            await self.send_action_result(action.id_, True, "it's jerald time")

    url = "ws://localhost:8000"
    ssl_context = None
    async with trio_websocket.open_websocket_url(
        url,
        ssl_context,
    ) as connection:
        context = Game("Jerald Game", connection)
        await context.send_startup_command()
        await context.register_actions(
            [
                Action(
                    "trigger_jerald_time",
                    "become ultimate jerald",
                ),
            ],
        )
        await context.send_force_action(
            "State here",
            "query",
            ["trigger_jerald_time"],
        )
        await context.read_message()
