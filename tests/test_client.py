from __future__ import annotations

import sys
from unittest.mock import AsyncMock

import orjson
import pytest

from neuro_api.client import AbstractNeuroAPIClient, NeuroMessage


@pytest.fixture
async def client() -> tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock]:
    read_mock = AsyncMock()
    write_mock = AsyncMock()

    class TestClient(AbstractNeuroAPIClient):
        """Test client implementation."""

        async def read_from_websocket(self) -> str:
            return await read_mock()  # type: ignore[no-any-return]

        async def write_to_websocket(self, data: str) -> None:
            await write_mock(data)

    client = TestClient()
    return client, read_mock, write_mock


@pytest.mark.trio
async def test_send_command_data(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, _, write_mock = client
    data = b'{"command":"test","game":"TestGame"}'

    await client_obj.send_command_data(data)

    write_mock.assert_awaited_once_with('{"command":"test","game":"TestGame"}')


@pytest.mark.trio
async def test_send_command_data_unicode_error(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, _, _ = client
    # Invalid UTF-8 bytes
    invalid_data = b"\xff\xfe"

    with pytest.raises(UnicodeDecodeError):
        await client_obj.send_command_data(invalid_data)


@pytest.mark.trio
async def test_read_raw_full_message_valid_json(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "test", "data": {"key": "value"}}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    result = await client_obj.read_raw_full_message()

    assert result == message


@pytest.mark.trio
async def test_read_raw_full_message_minimal(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "test"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    result = await client_obj.read_raw_full_message()

    assert result == message
    assert "data" not in result
    assert "game" not in result


@pytest.mark.trio
async def test_read_raw_full_message_with_game(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "test", "game": "TestGame"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    result = await client_obj.read_raw_full_message()

    assert result == message


@pytest.mark.trio
async def test_read_raw_full_message_invalid_json(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    read_mock.return_value = "invalid json {"

    with pytest.raises(orjson.JSONDecodeError):
        await client_obj.read_raw_full_message()


@pytest.mark.trio
async def test_read_raw_full_message_invalid_json_with_note(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    read_mock.return_value = "invalid json {"

    if sys.version_info >= (3, 11):
        with pytest.raises(orjson.JSONDecodeError) as exc_info:
            await client_obj.read_raw_full_message()

        # Check that the note was added
        assert hasattr(exc_info.value, "__notes__")
        assert len(exc_info.value.__notes__) > 0
        assert "content = " in exc_info.value.__notes__[0]


@pytest.mark.trio
async def test_read_raw_full_message_bytes_input(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    read_mock = AsyncMock()
    write_mock = AsyncMock()

    class BytesClient(AbstractNeuroAPIClient):
        """Test client that returns bytes."""

        async def read_from_websocket(self) -> bytes:
            return await read_mock()  # type: ignore[no-any-return]

        async def write_to_websocket(self, data: str) -> None:
            await write_mock(data)

    client_obj = BytesClient()
    message = {"command": "test", "data": {"key": "value"}}
    read_mock.return_value = orjson.dumps(message)

    result = await client_obj.read_raw_full_message()

    assert result == message


@pytest.mark.trio
async def test_read_raw_server_message(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {
        "command": "action",
        "data": {"id": "123", "name": "test_action"},
    }
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    command, data = await client_obj.read_raw_server_message()

    assert command == "action"
    assert data == {"id": "123", "name": "test_action"}


@pytest.mark.trio
async def test_read_raw_server_message_no_data(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "shutdown/immediate"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    command, data = await client_obj.read_raw_server_message()

    assert command == "shutdown/immediate"
    assert data is None


@pytest.mark.trio
async def test_read_raw_client_message(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {
        "command": "startup",
        "game": "TestGame",
        "data": {"version": "1.0"},
    }
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    command, game, data = await client_obj.read_raw_client_message()

    assert command == "startup"
    assert game == "TestGame"
    assert data == {"version": "1.0"}


@pytest.mark.trio
async def test_read_raw_client_message_no_data(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "startup", "game": "TestGame"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    command, game, data = await client_obj.read_raw_client_message()

    assert command == "startup"
    assert game == "TestGame"
    assert data is None


@pytest.mark.trio
async def test_read_raw_client_message_missing_game(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "startup"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    with pytest.raises(
        TypeError,
        match=r"`game` field missing in client response\.",
    ):
        await client_obj.read_raw_client_message()


@pytest.mark.trio
async def test_handle_unknown_command(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_obj, _, _ = client

    await client_obj.handle_unknown_command(
        "unknown_command",
        {"test": "data"},
    )

    captured = capsys.readouterr()
    assert (
        "[neuro_api.api] Received unknown command 'unknown_command'"
        in captured.out
    )
    assert "data = {'test': 'data'}" in captured.out


@pytest.mark.trio
async def test_handle_unknown_command_no_data(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_obj, _, _ = client

    await client_obj.handle_unknown_command("unknown_command", None)

    captured = capsys.readouterr()
    assert (
        "[neuro_api.api] Received unknown command 'unknown_command'"
        in captured.out
    )
    assert "data = None" in captured.out


@pytest.mark.trio
async def test_read_message(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "unknown_test", "data": {"test": "value"}}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    # Mock handle_unknown_command to verify it gets called
    client_obj.handle_unknown_command = AsyncMock()  # type: ignore[method-assign]

    await client_obj.read_message()

    client_obj.handle_unknown_command.assert_awaited_once_with(
        "unknown_test",
        {"test": "value"},
    )


@pytest.mark.trio
async def test_read_message_no_data(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    client_obj, read_mock, _ = client
    message = {"command": "unknown_test"}
    read_mock.return_value = orjson.dumps(message).decode("utf-8")

    # Mock handle_unknown_command to verify it gets called
    client_obj.handle_unknown_command = AsyncMock()  # type: ignore[method-assign]

    await client_obj.read_message()

    client_obj.handle_unknown_command.assert_awaited_once_with(
        "unknown_test",
        None,
    )


def test_neuro_message_typing() -> None:
    """Test that NeuroMessage TypedDict works as expected."""
    # Test minimal message
    minimal: NeuroMessage = {"command": "test"}
    assert minimal["command"] == "test"

    # Test full message
    full: NeuroMessage = {
        "command": "test",
        "game": "TestGame",
        "data": {"key": "value"},
    }
    assert full["command"] == "test"
    assert full["game"] == "TestGame"
    assert full["data"] == {"key": "value"}


@pytest.mark.trio
async def test_abstract_methods_not_implemented() -> None:
    """Test that abstract methods raise NotImplementedError when not implemented."""

    class IncompleteClient(AbstractNeuroAPIClient):
        """Client missing required abstract method implementations."""

    # Should not be able to instantiate due to abstract methods
    with pytest.raises(TypeError):
        IncompleteClient()  # type: ignore[abstract]


@pytest.mark.trio
async def test_read_from_websocket_different_return_types(
    client: tuple[AbstractNeuroAPIClient, AsyncMock, AsyncMock],
) -> None:
    """Test that different return types from read_from_websocket work."""
    # Test with bytearray
    read_mock = AsyncMock()
    write_mock = AsyncMock()

    class ByteArrayClient(AbstractNeuroAPIClient):
        async def read_from_websocket(self) -> bytearray:
            return await read_mock()  # type: ignore[no-any-return]

        async def write_to_websocket(self, data: str) -> None:
            await write_mock(data)

    bytes_client_obj = ByteArrayClient()
    message = {"command": "test"}
    read_mock.return_value = bytearray(orjson.dumps(message))

    result = await bytes_client_obj.read_raw_full_message()
    assert result == message

    # Test with memoryview
    class MemoryViewClient(AbstractNeuroAPIClient):
        async def read_from_websocket(self) -> memoryview:
            return await read_mock()  # type: ignore[no-any-return]

        async def write_to_websocket(self, data: str) -> None:
            await write_mock(data)

    memoryview_client_obj = MemoryViewClient()
    read_mock.return_value = memoryview(orjson.dumps(message))

    result = await memoryview_client_obj.read_raw_full_message()
    assert result == message
