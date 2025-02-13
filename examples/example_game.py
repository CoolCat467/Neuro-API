"""Example Game."""

# Programmed by CoolCat467

from __future__ import annotations

# Example Game
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

__title__ = "Example Game"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"


import sys
import traceback
from typing import TYPE_CHECKING

import trio
from libcomponent.component import Event, ExternalRaiseManager

from neuro_api.command import Action
from neuro_api.event import NeuroAPIComponent

if TYPE_CHECKING:
    from neuro_api.api import NeuroAction

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


class JeraldGame(NeuroAPIComponent):
    """Jerald Game - The Game."""

    __slots__ = ("wait_connect_event",)

    def __init__(self, component_name: str) -> None:
        """Initialize Jerald Game Neuro component."""
        super().__init__(component_name, "Jerald Game")
        self.wait_connect_event = trio.Event()

    def bind_handlers(self) -> None:
        """Register event handlers."""
        self.register_handler(
            "connect",
            self.handle_connect,
        )

    def websocket_connect_failed(self) -> None:
        """Handle websocket connection failure."""
        self.wait_connect_event.set()

        # Do default print message
        super().websocket_connect_failed()

    async def websocket_connect_successful(self) -> None:
        """Handle websocket connection success."""
        self.wait_connect_event.set()

        await self.send_startup_command()

        await self.send_context(
            """You are playing Jerald Game - The Game.""",
        )

        # Do default print message
        await super().websocket_connect_successful()

    async def wait_for_websocket(self) -> None:
        """Blocking until websocket connection trial ends."""
        await self.wait_connect_event.wait()


async def run() -> None:
    """Run test."""
    url = "ws://localhost:8000"
    async with trio.open_nursery(strict_exception_groups=True) as nursery:
        manager = ExternalRaiseManager("name", nursery)

        jerald_game = JeraldGame("neuro_api")
        manager.add_component(jerald_game)

        await manager.raise_event(Event("connect", url))

        await jerald_game.wait_for_websocket()

        if jerald_game.not_connected:
            print("Neuro not connected, stopping.")
            return

        async def handler(
            neuro_action: NeuroAction,
        ) -> tuple[bool, str | None]:
            response = f"{neuro_action.data = }"
            print(response)
            return neuro_action.data == '"jerald"', response

        await jerald_game.register_temporary_actions(
            (
                (
                    Action(
                        "set_name",
                        "Sets your name. Enter jerald to have success.",
                        {"type": "string"},
                    ),
                    handler,
                ),
            ),
        )
        await jerald_game.send_force_action(
            "state",
            "query",
            ["set_name"],
        )
        await trio.sleep(20)
        await jerald_game.stop()


if __name__ == "__main__":
    try:
        trio.run(run)
    except ExceptionGroup as exc:
        traceback.print_exception(exc)
