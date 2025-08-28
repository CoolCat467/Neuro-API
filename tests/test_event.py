from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import trio
from libcomponent.component import ComponentManager, Event

from neuro_api.api import NeuroAction
from neuro_api.command import Action
from neuro_api.trio_ws import TrioNeuroAPIComponent

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    import trio_websocket


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Fixture to create a mock websocket connection."""
    websocket = MagicMock()
    websocket.send_message = AsyncMock(return_value=None)
    websocket.aclose = AsyncMock(return_value=None)
    return websocket


@pytest.fixture
def neuro_api_component(
    mock_websocket: trio_websocket.WebSocketConnection,
) -> Generator[TrioNeuroAPIComponent, None, None]:
    """Fixture to create an instance of TrioNeuroAPIComponent."""
    component = TrioNeuroAPIComponent(
        "test_component",
        "Test Game",
        mock_websocket,
    )
    component.connect(mock_websocket)
    manager = ComponentManager("manager")
    with manager.temporary_component(component) as component:
        yield component


@pytest.mark.trio
async def test_register_neuro_actions(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test registering neuro actions."""
    action = Action("test_action", "A test action", {"type": "string"})
    handler = AsyncMock(return_value=(True, "Action executed successfully."))

    await neuro_api_component.register_neuro_actions([(action, handler)])

    # Check if the action is registered
    assert neuro_api_component.has_handler("neuro_test_action")


@pytest.mark.trio
async def test_handle_action(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test handling an action."""
    action = Action("test_action", "A test action", {"type": "string"})
    handler = AsyncMock(return_value=(True, "Action executed successfully."))
    await neuro_api_component.register_neuro_actions([(action, handler)])

    neuro_action = NeuroAction(
        "1",
        "test_action",
        "jerald data",
    )
    await neuro_api_component.handle_action(neuro_action)

    # Check if the handler was called
    handler.assert_awaited_once_with(neuro_action)


@pytest.mark.trio
async def test_handle_action_no_handler(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test handling an action with no registered handler."""
    neuro_action = NeuroAction("1", "nonexistent_action", None)

    with pytest.raises(
        ValueError,
        match="Received neuro action with no handler registered",
    ):
        await neuro_api_component.handle_action(neuro_action)


@pytest.mark.trio
async def test_register_temporary_actions(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test registering temporary actions."""
    action = Action("temp_action", "A temporary action", {"type": "string"})
    handler = AsyncMock(return_value=(True, "Temporary action executed."))

    await neuro_api_component.register_temporary_actions([(action, handler)])

    # Check if the action is registered
    assert neuro_api_component.has_handler("neuro_temp_action")

    # Simulate handling the action
    neuro_action = NeuroAction("1", "temp_action", "jerald")
    await neuro_api_component.handle_action(neuro_action)

    # Check if the handler was called and the action was unregistered
    handler.assert_awaited_once_with(neuro_action)
    assert not neuro_api_component.has_handler("neuro_temp_action")


@pytest.mark.trio
async def test_register_temporary_actions_unsuccessful_remains(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test registering temporary actions."""
    action = Action("temp_action", "A temporary action", {"type": "string"})
    handler = AsyncMock(return_value=(False, "Temporary action failed."))

    await neuro_api_component.register_temporary_actions([(action, handler)])

    # Check if the action is registered
    assert neuro_api_component.has_handler("neuro_temp_action")

    # Simulate handling the action
    neuro_action = NeuroAction("1", "temp_action", "jerald")
    await neuro_api_component.handle_action(neuro_action)

    # Check if the handler was called and the action still registered
    handler.assert_awaited_once_with(neuro_action)
    assert neuro_api_component.has_handler("neuro_temp_action")


@pytest.mark.trio
async def test_handle_connect(
    neuro_api_component: TrioNeuroAPIComponent,
    mock_websocket: trio_websocket.WebSocketConnection,
) -> None:
    """Test handling websocket connect event."""
    event = Event("connect", "ws://localhost:8000")

    @asynccontextmanager
    async def with_statement() -> AsyncGenerator[
        trio_websocket.WebSocketConnection
    ]:
        yield mock_websocket

    async def handle_shutdown() -> None:
        raise EOFError("jerald waz here")

    neuro_api_component.handle_immediate_shutdown = handle_shutdown  # type: ignore[method-assign]

    async def send_shutdown() -> str:
        return '{"command":"shutdown/immediate"}'

    mock_websocket.get_message = send_shutdown  # type: ignore[method-assign]

    with patch("trio_websocket.open_websocket_url") as mock_function:
        mock_function.return_value = with_statement()
        with pytest.raises(EOFError, match="jerald waz here"):
            await neuro_api_component.handle_connect(event)

        # Ensure disconnect happens after error
        assert neuro_api_component.not_connected


@pytest.mark.trio
async def test_stop(
    neuro_api_component: TrioNeuroAPIComponent,
    mock_websocket: trio_websocket.WebSocketConnection,
) -> None:
    """Test stopping the component."""
    await neuro_api_component.stop()

    # Check if the websocket was closed
    cast("AsyncMock", mock_websocket.aclose).assert_awaited_once()


@pytest.mark.trio
async def test_stop_when_not_connected(
    neuro_api_component: TrioNeuroAPIComponent,
) -> None:
    """Test stopping the component when not connected."""
    neuro_api_component.connect(None)  # Simulate not connected
    await neuro_api_component.stop()

    # Ensure no exception is raised and the checkpoint is called
    await trio.lowlevel.checkpoint()
