"""Trio-websocket specific implementation."""

# Programmed by CoolCat467

from __future__ import annotations

# Trio-websocket specific implementation
# Copyright (C) 2025  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "Trio-websocket specific implementation"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"


from typing import TYPE_CHECKING

import trio
import trio_websocket
from exceptiongroup import catch

from neuro_api.api import AbstractNeuroAPI
from neuro_api.event import AbstractNeuroAPIComponent

if TYPE_CHECKING:
    from libcomponent.component import Event


class TrioNeuroAPI(AbstractNeuroAPI):
    """Trio-websocket specific Neuro API implementation."""

    # __slots__ = ("__connection",)

    def __init__(
        self,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize NeuroAPI.

        Args:
            game_title (str): The title of the game being managed.
            connection (trio_websocket.WebSocketConnection, optional):
                Initial websocket connection. Defaults to None.

        """
        super().__init__(game_title)
        self.__connection = connection

    @property
    def not_connected(self) -> bool:
        """Check if websocket connection is not established.

        Returns:
            bool: True if connection is None, False otherwise.

        """
        return self.__connection is None

    @property
    def connection(self) -> trio_websocket.WebSocketConnection:
        """Get current websocket connection.

        Returns:
            trio_websocket.WebSocketConnection: The active websocket connection.

        Raises:
            RuntimeError: If no websocket connection is established.

        """
        if self.__connection is None:
            raise RuntimeError("Websocket not connected!")
        return self.__connection

    def connect(
        self,
        websocket: trio_websocket.WebSocketConnection | None,
    ) -> None:
        """Set the internal websocket connection.

        Args:
            websocket (trio_websocket.WebSocketConnection | None):
                Websocket connection to set. Can be None to clear connection.

        """
        self.__connection = websocket

    async def write_to_websocket(self, data: str) -> None:
        """Write a message to the websocket.

        Args:
            data (str): Message to be sent over the websocket.

        Raises:
            ConnectionClosed: If websocket connection is closed or closing.

        """
        await self.connection.send_message(data)

    async def read_from_websocket(
        self,
    ) -> bytes | bytearray | memoryview | str:
        """Read a message from the websocket.

        Returns:
            bytes | bytearray | memoryview | str: The received message.

        Raises:
            trio_websocket.ConnectionClosed: On websocket connection error.
            trio.BrokenResourceError: If internal memory channel is broken
                (rarely occurs).
            AssertionError: If received message types are unexpected.

        """
        return await self.connection.get_message()


class TrioNeuroAPIComponent(AbstractNeuroAPIComponent, TrioNeuroAPI):
    """Trio-websocket Neuro API Component.

    Combines AbstractNeuroAPIComponent and TrioNeuroAPI functionality
    for Trio-based websocket interactions with Neuro.
    """

    # __slots__ = ("__connection",)

    def __init__(
        self,
        component_name: str,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize Trio-websocket Neuro API Component.

        Args:
            component_name (str): Name of the component.
            game_title (str): Title of the game being managed.
            connection (trio_websocket.WebSocketConnection, optional):
                Initial websocket connection. Defaults to None.

        """
        AbstractNeuroAPIComponent.__init__(self, component_name, game_title)
        self.connect(connection)

    async def read_message(self) -> None:
        """Read message from Neuro websocket.

        Automatically processes various types of commands:
        - `actions/reregister_all`
        - Graceful and immediate shutdown requests
        - Action commands
        - Unknown commands

        Raises:
            ValueError: If extra or missing keys in action command data.
            TypeError: On action command key type mismatch.
            trio_websocket.ConnectionClosed: If websocket connection is lost.

        """
        try:
            await super().read_message()
        except trio_websocket.ConnectionClosed:
            # Stop websocket if connection closed.
            await self.stop()

    def websocket_connect_failed(self) -> None:  # pragma: nocover
        """Handle websocket connection handshake failure.

        Default behavior is to print an error message.
        This method can be overridden for custom error handling.
        """
        print("Failed to connect to websocket.")

    async def websocket_connect_successful(self) -> None:
        """Handle successful websocket connection.

        Default behavior is to print a success message and
        create a trio checkpoint.

        This method can be overridden for custom connection handling.
        """
        print("Connected to websocket.")
        await trio.lowlevel.checkpoint()

    async def handle_connect(self, event: Event[str]) -> None:
        """Handle websocket connection event.

        Manages the full websocket connection process, including:
        - Opening the websocket
        - Handling connection errors
        - Reading messages until disconnected

        Args:
            event (Event[str]): Connection event containing the websocket URL.

        Note:
            Does not stop unless `stop()` function is explicitly called.

        """
        url = event.data

        def handle_handshake_error(exc: object) -> None:
            self.websocket_connect_failed()

        with catch({trio_websocket.HandshakeError: handle_handshake_error}):
            async with trio_websocket.open_websocket_url(url) as websocket:
                self.connect(websocket)
                await self.websocket_connect_successful()
                try:
                    while not self.not_connected:  # pragma: nocover
                        await self.read_message()
                finally:
                    self.connect(None)

    async def stop(self, code: int = 1000, reason: str | None = None) -> None:
        """Close websocket and trigger disconnection.

        Args:
            code (int, optional): Websocket close code. Defaults to 1000
                (normal closure).
            reason (str, optional): Reason for closing the connection.
                Defaults to None.

        """
        if not self.not_connected:
            await self.connection.aclose(code, reason)
            self.connect(None)
        else:
            self.connect(None)
            await trio.lowlevel.checkpoint()
