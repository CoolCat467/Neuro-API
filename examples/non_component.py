"""Package Name Title."""

# Programmed by CoolCat467

from __future__ import annotations

# Example Game
# MIT License
# Copyright (c) 2025 CoolCat467
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__title__ = "Example Game"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "MIT License"

import os
import sys
import traceback
from typing import TYPE_CHECKING, Any, Final

# neuro_api uses orjson, so no extra dependencies
import orjson
import trio
import trio_websocket

from neuro_api.command import Action
from neuro_api.trio_ws import TrioNeuroAPI

# Things we need imported for type checking reasons but not at runtime
if TYPE_CHECKING:
    from neuro_api.api import NeuroAction

# For compatibility with Python versions below 3.11, use the backported
# ExceptionGroup
if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup


WEBSOCKET_ENV_VAR: Final = "NEURO_SDK_WS_URL"
DEFAULT_WEBSOCKET: Final = "ws://localhost:8000"
WEBSOCKET_CONNECTION_WAIT_TIME: Final = 3


class API(TrioNeuroAPI):
    """API."""

    __slots__ = ("running",)

    def __init__(
        self,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize API."""
        super().__init__(game_title, connection)
        print("INFO: " + f"Initialized with game title: {game_title!r}")

        self.running = True

    async def startup(self) -> None:
        """Send startup command and start game."""
        await self.send_startup_command()
        await self.register_actions(
            [
                Action("set_name", "Set name", {"type": "string"}),
            ],
        )
        await self.send_context(
            f"You are currently playing {self.game_title}.",
        )
        await self.send_force_action(
            "startup_state",
            "Please set up the game",
            ["set_name"],
            ephemeral_context=False,
        )

    async def handle_action(self, action: NeuroAction) -> None:
        """Handle an Action from Neuro."""
        print(f"INFO: Received {action = }")

        data: Any | None = None
        if action.data is not None:
            try:
                data = orjson.loads(action.data)
            except orjson.JSONDecodeError as exc:
                message = f"Failed to read response: {exc}"
                print(f"INFO: {message}")
                await self.send_action_result(action.id_, False, message)
                return
        print(f"INFO: Action {data = }")

        # Would suggest doing something like this:
        # In __init__:
        # self.action_map: dict[str, tuple[object, Callable[[NeuroAction], tuple[bool, str | None]]]] = {}
        # In class body somewhere:
        # @staticmethod
        # def invalid_action_handler(action: NeuroAction) -> tuple[bool, str | None]:
        #     return True, f"Action {action.name!r} is not currently implemented/does not exist."
        # schema, action_handler = self.action_map.get(action.name, ({}, self.invalid_action_handler))
        # # do schema validation things, returning False and error message if nonmatch
        # await self.send_action_result(action.id_, *action_handler(action))

        success = True
        message = f"Action {action.name!r} is not currently implemented."
        print(f"INFO: {message}")
        await self.send_action_result(action.id_, success, message)

        # Close game (demo purposes, likely wouldn't do this in practice)
        self.running = False


async def handle_websocket_success(
    websocket: trio_websocket.WebSocketConnection,
) -> None:
    """Handle successful websocket connection."""
    api = API(__title__, websocket)
    await api.startup()

    try:
        while api.running:
            # Read messages while running.
            await api.read_message()
    except Exception as exc:
        traceback.print_exc()
        # Don't have to close, `with` block will close for sure, but
        # this allows us to specify a reason why websocket is closing.
        await websocket.aclose(reason=f"Internal Server Error: {exc}")
    else:
        message = "Game shutting down"
        await api.send_context(message)
        # See above
        await websocket.aclose(reason=message)
        print(message)


async def main_async() -> None:
    """Run the app."""
    websocket_url = os.environ.get(WEBSOCKET_ENV_VAR, DEFAULT_WEBSOCKET)

    async with trio.open_nursery() as nursery:
        connect_failure = True
        while connect_failure:
            try:
                async with await trio_websocket.connect_websocket_url(
                    nursery,
                    websocket_url,
                ) as websocket:
                    connect_failure = False
                    await handle_websocket_success(websocket)
            except OSError as exc:
                print(f"Error Connecting to websocket: {exc}", file=sys.stderr)
            await trio.sleep(WEBSOCKET_CONNECTION_WAIT_TIME)


def cli_run() -> None:
    """CLI entry point."""
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    try:
        trio.run(main_async)
    except BaseExceptionGroup:
        # Do not catch BaseExceptionGroup in main code, use
        # ExceptionGroup, BaseExceptionGroup catches KeyboardInterrupt
        # and SystemExit
        traceback.print_exc()


if __name__ == "__main__":
    cli_run()
