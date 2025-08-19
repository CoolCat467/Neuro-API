from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import trio_websocket

from neuro_api import command
from neuro_api.api import AbstractNeuroAPI, NeuroAction
from neuro_api.command import Action


@pytest.fixture
async def neuro_api() -> tuple[AbstractNeuroAPI, AsyncMock]:
    class TestNeuroAPI(AbstractNeuroAPI):
        """Test Neuro API."""

        async def handle_action(self, action: NeuroAction) -> None:
            """Mock implementation for testing."""

    websocket = AsyncMock()
    api = TestNeuroAPI("Test Game", websocket)
    return api, websocket


@pytest.mark.trio
async def test_not_connected_property(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.connect(None)
    assert api.not_connected

    api.connect(AsyncMock())
    assert not api.not_connected


@pytest.mark.trio
async def test_connection_property(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.connect(None)
    with pytest.raises(RuntimeError):
        _ = api.connection

    assert api.not_connected


@pytest.mark.trio
async def test_send_command_data(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    data = b"test command"
    websocket.send_message = AsyncMock()

    await api.send_command_data(data)

    websocket.send_message.assert_awaited_once_with(data.decode("utf-8"))


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
    api, _ = neuro_api
    action = command.Action("test_action", "Test Action", None)
    await api.register_actions([action])

    await api.unregister_actions(["test_action"])

    assert "test_action" not in api.get_registered()


@pytest.mark.trio
async def test_send_force_action(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    action_names = ["test_action"]
    action = command.Action("test_action", "Test Action", None)
    await api.register_actions([action])

    api.send_command_data = AsyncMock()  # type: ignore[method-assign]

    await api.send_force_action("state", "query", action_names)

    api.send_command_data.assert_awaited_once()


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
async def test_read_raw_message(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.get_message = AsyncMock(
        return_value=b'{"command":"action","data":{"id":"1","name":"test_action"}}',
    )

    command, data = await api.read_raw_message()
    assert command == "action"
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
    api.read_raw_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("action", {"id": "1", "name": "test_action"}),
    )
    api.handle_action = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_action.assert_awaited_once()


@pytest.mark.trio
async def test_read_message_unknown_command(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, _ = neuro_api
    api.read_raw_message = AsyncMock(  # type: ignore[method-assign]
        return_value=("unknown_command", None),
    )
    api.handle_unknown_command = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_unknown_command.assert_awaited_once()


@pytest.mark.trio
async def test_read_raw_message_reregister(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.get_message = AsyncMock(
        return_value=b'{"command":"actions/reregister_all"}',
    )

    action = command.Action("test_action", "Test Action")
    await api.register_actions([action])

    websocket.send_message = AsyncMock()

    await api.read_message()

    websocket.send_message.assert_awaited_once_with(
        command.actions_register_command(
            "Test Game",
            [action],
        ).decode("utf-8"),
    )


@pytest.mark.trio
async def test_read_raw_message_graceful_shutdown(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.get_message = AsyncMock(
        return_value=b'{"command":"shutdown/graceful","data":{"wants_shutdown":true}}',
    )

    api.send_shutdown_ready = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.send_shutdown_ready.assert_awaited_once()


@pytest.mark.trio
async def test_read_raw_message_immediate_shutdown(
    neuro_api: tuple[AbstractNeuroAPI, AsyncMock],
) -> None:
    api, websocket = neuro_api
    websocket.get_message = AsyncMock(
        return_value=b'{"command":"shutdown/immediate"}',
    )

    api.handle_immediate_shutdown = AsyncMock()  # type: ignore[method-assign]

    await api.read_message()

    api.handle_immediate_shutdown.assert_awaited_once()


async def run() -> None:
    """Run program."""

    class Game(AbstractNeuroAPI):
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
