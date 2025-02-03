"""Event - Neuro API Component."""

# Programmed by CoolCat467

from __future__ import annotations

# Event - Neuro API Component
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

__title__ = "event"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


from typing import TYPE_CHECKING

import trio
import trio_websocket
from libcomponent.component import Component, Event

from neuro_api.api import AbstractNeuroAPI, NeuroAction

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from neuro_api.command import Action


class NeuroAPIComponent(Component, AbstractNeuroAPI):
    """Neuro API Component."""

    __slots__ = ("_action_map",)

    def __init__(
        self,
        name: str,
        game_title: str,
        websocket: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize Neuro API Component."""
        Component.__init__(self, name)
        AbstractNeuroAPI.__init__(self, game_title, websocket)

        self._action_map: dict[str, str] = {}

    def _send_result_wrapper(
        self,
        handler: Callable[[str | None], Awaitable[tuple[bool, str | None]]],
    ) -> Callable[[Event[NeuroAction]], Awaitable[None]]:
        """Return wrapper to handle neuro action event."""

        async def wrapper(event: Event[NeuroAction]) -> None:
            """Send action result with return value from handler."""
            neuro_action = event.data
            success, message = await handler(neuro_action.data)
            await self.send_action_result(neuro_action.id_, success, message)

        return wrapper

    async def register_neuro_actions_raw_handler(
        self,
        action_handlers: Iterable[
            tuple[
                Action,
                Callable[[Event[NeuroAction]], Awaitable[object]],
            ],
        ],
    ) -> None:
        """Register a Neuro Action and associated handler function.

        action_handlers should be an iterable of (Action,
        NeuroAction event handler function).
        """
        handlers = tuple(action_handlers)
        self.register_handlers(
            {f"neuro_{action.name}": handler for action, handler in handlers},
        )
        await self.register_actions([action for action, _callback in handlers])

    async def register_neuro_actions(
        self,
        action_handlers: Iterable[
            tuple[
                Action,
                Callable[[str | None], Awaitable[tuple[bool, str | None]]],
            ],
        ],
    ) -> None:
        """Register a Neuro Action and associated handler function.

        action_handlers should be an iterable of Action and
        callback function pairs.

        Callback functions accept str | None and return if action is successful
        and optional associated small context message if successful.
        If unsuccessful, 2nd value must be an error message.
        """
        await self.register_neuro_actions_raw_handler(
            (action, self._send_result_wrapper(handler))
            for action, handler in action_handlers
        )

    async def register_temporary_actions(
        self,
        action_handlers: Iterable[
            tuple[
                Action,
                Callable[[str | None], Awaitable[tuple[bool, str | None]]],
            ],
        ],
    ) -> None:
        """Register temporary Neuro Actions and associated handler functions.

        action_handlers should be an iterable of Action and
        callback function pairs.

        Callback functions accept str | None and return if action is successful
        and optional associated small context message if successful.
        If unsuccessful, 2nd value must be an error message.

        If successful, will unregister the associated action.
        """

        def unregister_wrapper(
            action_name: str,
            handler: Callable[
                [str | None],
                Awaitable[tuple[bool, str | None]],
            ],
        ) -> Callable[[str | None], Awaitable[tuple[bool, str | None]]]:
            """Return wrapper function that calls handler, then unregisters action before passing on result."""

            async def wrapper(message: str | None) -> tuple[bool, str | None]:
                success, message = await handler(message)
                if success:
                    await self.unregister_actions([action_name])
                    self.unregister_handler_type(f"neuro_{action_name}")
                return success, message

            return wrapper

        await self.register_neuro_actions(
            (action, unregister_wrapper(action.name, handler))
            for action, handler in action_handlers
        )

    async def handle_action(self, neuro_action: NeuroAction) -> None:
        """Handle an action request from Neuro."""
        event_name = f"neuro_{neuro_action.name}"
        if not self.has_handler(event_name):
            raise ValueError(
                f"Received neuro action with no handler registered: {neuro_action}",
            )
        await self.raise_event(
            Event(
                event_name,
                neuro_action,
            ),
        )

    async def websocket_connect_failed(self) -> None:  # pragma: nocover
        """Handle when websocket connect has handshake failure.

        Default just prints and error message
        """
        print("Failed to connect to websocket.")
        await trio.lowlevel.checkpoint()

    async def websocket_connect_successful(self) -> None:
        """Handle when websocket connect is successful.

        Default just prints and success message
        """
        print("Connected to websocket.")
        await trio.lowlevel.checkpoint()

    async def handle_connect(self, event: Event[str]) -> None:
        """Handle websocket connect event. Does not stop unless you call `stop` function."""
        url = event.data
        try:
            async with trio_websocket.open_websocket_url(url) as websocket:
                self.connect(websocket)
                await self.websocket_connect_successful()
                try:
                    while not self.not_connected:  # pragma: nocover
                        await self.read_message()
                finally:
                    self.connect(None)
        except trio_websocket.HandshakeError:  # pragma: nocover
            await self.websocket_connect_failed()

    async def stop(self, code: int = 1000, reason: str | None = None) -> None:
        """Close websocket and trigger not connected."""
        if not self.not_connected:
            await self.connection.aclose(code, reason)
            self.connect(None)
        else:
            self.connect(None)
            await trio.lowlevel.checkpoint()
