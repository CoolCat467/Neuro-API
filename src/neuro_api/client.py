"""Client - Neuro API Websocket Client."""

# Programmed by CoolCat467

from __future__ import annotations

# Client - Neuro API Websocket Client.
# Copyright (C) 2025  CoolCat467
#
#     This program is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this program.  If not, see
#     <https://www.gnu.org/licenses/>.

__title__ = "client"
__author__ = "CoolCat467"
__license__ = "GNU Lesser General Public License Version 3"


import sys
from abc import ABCMeta, abstractmethod
from typing import TypedDict

import orjson
from typing_extensions import NotRequired

from neuro_api import command


class NeuroMessage(TypedDict):
    """Schema for incoming message.

    Represents the structure of both a server or client message as
    specified in the Neuro Game SDK API documentation.

    Attributes:
        command (str): Unique identifier for the websocket command.
        game (NotRequired[str]): Game name, used as an identifier.
            Messages from server will not include this field, but should
            always be present in messages from clients.
        data (NotRequired[dict[str, object]): Data associated with the command.
            This field is not required and can be omitted for some commands.

    Reference:
        Specification details:
        https://github.com/VedalAI/neuro-sdk/blob/main/API/SPECIFICATION.md#neuro-api-specification

    """

    command: str
    game: NotRequired[str]
    data: NotRequired[dict[str, object]]


class AbstractNeuroAPIClient(metaclass=ABCMeta):
    """Abstract client for the Neuro Game Interaction API.

    Provides a foundational interface for interactions with the Neuro
    system. This class is designed to be subclassed by specific client
    implementations.

    Note:
        This is an abstract base class that requires implementation
        of specific game interaction methods in subclasses.

    """

    __slots__ = ()

    @abstractmethod
    async def write_to_websocket(self, data: str) -> None:
        """Abstract method to write a message to the websocket.

        This method must be implemented by subclasses to define
        the specific mechanism for sending data over a websocket.

        Args:
            data (str): The message to be sent over the websocket.

        """

    @abstractmethod
    async def read_from_websocket(
        self,
    ) -> bytes | bytearray | memoryview | str:
        """Abstract method to read a message from the websocket.

        This method must be implemented by subclasses to define
        the specific mechanism for receiving data from a websocket.

        Returns:
            bytes | bytearray | memoryview | str: The message
            received from the websocket, supporting anything
            ``orjson.loads`` can handle.

        """

    async def send_command_data(self, data: bytes) -> None:
        """Send command data over the websocket.

        Converts the input bytes to a UTF-8 encoded string and
        writes it to the websocket.

        Args:
            data (bytes): The command data to be sent over the websocket.

        Raises:
            UnicodeDecodeError: If the input data cannot be decoded
            using UTF-8 encoding.

        """
        await self.write_to_websocket(data.decode("utf-8"))

    async def read_raw_full_message(self) -> NeuroMessage:
        """Read a command and its associated data from Neuro websocket connection.

        Waits and reads a message from the websocket. The method will not
        return until a message is successfully read.

        Returns:
            NeuroMessage: Server or client Neuro API message.

        Raises:
            orjson.JSONDecodeError: If the received message is invalid JSON.
            AssertionError: If the received JSON message contains
                unexpected types for command or data.

        """
        content = await self.read_from_websocket()
        try:
            message = orjson.loads(content)
        except orjson.JSONDecodeError as exc:
            if sys.version_info >= (3, 11):  # pragma: nocover
                exc.add_note(f"{content = }")
            raise
        return command.check_typed_dict(message, NeuroMessage)

    async def read_raw_server_message(
        self,
    ) -> tuple[str, dict[str, object] | None]:
        """Read a command and its associated data from Neuro websocket server.

        Waits and reads a message from the websocket. The method will not
        return until a message is successfully read.

        Returns:
            tuple[str, dict[str, object] | None]: A tuple containing:
                - The command name as a string
                - Associated data as a dictionary or None

        Raises:
            orjson.JSONDecodeError: If the received message is invalid JSON.
            AssertionError: If the received JSON message contains
                unexpected types for command or data.

        """
        message = await self.read_raw_full_message()
        command = message["command"]
        data = message.get("data")
        return command, data

    async def read_raw_client_message(
        self,
    ) -> tuple[str, str, dict[str, object] | None]:
        """Read a command and its associated data from Neuro websocket client.

        Waits and reads a message from the websocket. The method will not
        return until a message is successfully read.

        Returns:
            tuple[str, str, dict[str, object] | None]: A tuple containing:
                - The command name as a string
                - The name of the game client connected as a string
                - Associated data as a dictionary or None

        Raises:
            orjson.JSONDecodeError: If the received message is invalid JSON.
            AssertionError: If the received JSON message contains
                unexpected types for command or data.

        """
        message = await self.read_raw_full_message()
        command = message["command"]
        game = message.get("game")
        if game is None:
            raise TypeError("`game` field missing in client response.")
        data = message.get("data")
        return command, game, data

    async def handle_unknown_command(
        self,
        command: str,
        data: dict[str, object] | None,
    ) -> None:  # pragma: nocover
        """Handle unknown command from Neuro.

        Args:
            command (str): Unhandled command name
            data (dict[str, object] | None):
                Data associated with unknown command.

        Note:
            Base implementation just prints an error message.

        """
        print(
            f"[neuro_api.api] Received unknown command {command!r} {data = }",
        )

    async def read_message(self) -> None:
        """Read message from Neuro websocket.

        You should call this function in a loop as long as the websocket
        is still connected.

        Calls ``handle_unknown_command`` for all commands.
        Implement specific handling in a subclass.

        Note:
            Does not catch any exceptions ``read_raw_server_message`` raises.

        """
        # Read message from server
        command_type, data = await self.read_raw_server_message()
        await self.handle_unknown_command(command_type, data)
