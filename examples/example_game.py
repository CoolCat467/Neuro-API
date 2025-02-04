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

import trio
from libcomponent.component import Event, ExternalRaiseManager

from neuro_api.command import Action
from neuro_api.event import NeuroAPIComponent

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


async def run() -> None:
    """Run test."""
    url = "ws://localhost:8000"
    async with trio.open_nursery(strict_exception_groups=True) as nursery:
        manager = ExternalRaiseManager("name", nursery)

        neuro_component = NeuroAPIComponent("neuro_api", "Jerald Game")
        manager.add_component(neuro_component)

        neuro_component.register_handler(
            "connect",
            neuro_component.handle_connect,
        )

        await manager.raise_event(Event("connect", url))
        await trio.sleep(0.01)

        if neuro_component.not_connected:
            return

        await neuro_component.send_startup_command()

        async def handler(
            name: str,
        ) -> tuple[bool, str | None]:
            print(f"{name = }")
            return name == '"jerald"', f"{name = }"

        await neuro_component.register_temporary_actions(
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
        await neuro_component.send_force_action(
            "state",
            "query",
            ["set_name"],
        )
        await trio.sleep(20)
        await neuro_component.stop()


if __name__ == "__main__":
    try:
        trio.run(run)
    except ExceptionGroup as exc:
        traceback.print_exception(exc)
