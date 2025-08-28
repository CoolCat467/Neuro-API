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
    """Trio-specific Neuro API."""

    # __slots__ = ("__connection",)

    def __init__(
        self,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize NeuroAPI."""
        super().__init__(game_title)
        self.__connection = connection

    @property
    def not_connected(self) -> bool:
        """Is stream None?."""
        return self.__connection is None

    @property
    def connection(self) -> trio_websocket.WebSocketConnection:
        """Websocket connection or raise RuntimeError."""
        if self.__connection is None:
            raise RuntimeError("Websocket not connected!")
        return self.__connection

    def connect(
        self,
        websocket: trio_websocket.WebSocketConnection | None,
    ) -> None:
        """Set internal websocket to given websocket or set to None."""
        self.__connection = websocket

    async def write_to_websocket(self, data: str) -> None:
        """Write message to websocket.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.
        """
        await self.connection.send_message(data)

    async def read_from_websocket(
        self,
    ) -> bytes | bytearray | memoryview | str:
        """Return message read from websocket.

        Raises `trio_websocket.ConnectionClosed` on websocket connection error.

        Raises `trio.BrokenResourceError` if something has gone wrong,
        and internal memory channel is broken. Probably won't happen.

        Raises `AssertionError` if received types in json message are not
        expected types.
        """
        return await self.connection.get_message()


class TrioNeuroAPIComponent(AbstractNeuroAPIComponent, TrioNeuroAPI):
    """Trio-websocket Neuro API Component."""

    # __slots__ = ("__connection",)

    def __init__(
        self,
        component_name: str,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize Trio-websocket Neuro API Component."""
        AbstractNeuroAPIComponent.__init__(self, component_name, game_title)
        if connection is not None:
            self.connect(connection)

    async def read_message(self) -> None:
        """Read message from Neuro.

        Automatically handles `actions/reregister_all` commands.

        Calls handle_graceful_shutdown_request and handle_immediate_shutdown
        for graceful and immediate shutdown requests respectively.

        Calls handle_action for `action` commands.

        Calls handle_unknown_command for any other command.

        Raises ValueError if extra keys in action command data or
        missing keys in action command data.
        Raises TypeError on action command key type mismatch.
        """
        try:
            await super().read_message()
        except trio_websocket.ConnectionClosed:
            # Stop websocket if connection closed.
            await self.stop()

    def websocket_connect_failed(self) -> None:  # pragma: nocover
        """Handle when websocket connect has handshake failure.

        Default just prints and error message
        """
        print("Failed to connect to websocket.")

    async def websocket_connect_successful(self) -> None:
        """Handle when websocket connect is successful.

        Default just prints and success message
        """
        print("Connected to websocket.")
        await trio.lowlevel.checkpoint()

    async def handle_connect(self, event: Event[str]) -> None:
        """Handle websocket connect event. Does not stop unless you call `stop` function."""
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
        """Close websocket and trigger not connected."""
        if not self.not_connected:
            await self.connection.aclose(code, reason)
            self.connect(None)
        else:
            self.connect(None)
            await trio.lowlevel.checkpoint()
