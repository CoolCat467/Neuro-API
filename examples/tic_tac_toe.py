"""Tic Tac Toe - Example game code."""

# Programmed by CoolCat467

from __future__ import annotations

# Tic Tac Toe - Example game code.
# MIT License
# Copyright (c) 2023-2025 CoolCat467
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

__title__ = "Tic Tac Toe"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "MIT License"


import sys
import traceback
from enum import IntEnum, auto
from typing import TYPE_CHECKING, NamedTuple, cast

import trio
from libcomponent.component import Event, ExternalRaiseManager

from neuro_api.command import Action
from neuro_api.trio_ws import TrioNeuroAPIComponent

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from neuro_api.api import NeuroAction

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


class Player(IntEnum):
    """Enum for player status."""

    __slots__ = ()
    MIN = auto()
    MAX = auto()
    CHANCE = auto()


GameValue = tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
]


class State(NamedTuple):
    """State of tic tac toe game.

    -1 = O
    0 = _
    1 = X
    """

    value: GameValue

    def __repr__(self) -> str:
        """Return pretty representation of game state."""
        lines = []
        for ridx in range(3):
            lines.append(
                ", ".join(str(v).rjust(2) for v in self.get_row(ridx)),
            )
        val = "\n" + "\n".join(f"  {v}," for v in lines) + "\n"
        return f"{self.__class__.__name__}(({val}))"

    def __str__(self) -> str:
        """Return string representation of game state."""
        map_ = {-1: "O", 0: "_", 1: "X"}
        lines = []
        for ridx in range(3):
            lines.append(" ".join(map_[v] for v in self.get_row(ridx)))
        val = "\n" + "\n".join(f"  {v}" for v in lines) + "\n"
        return f"{self.__class__.__name__}({val})"

    def get_item(self, row: int, col: int) -> int:
        """Get item at (row, col)."""
        return self.value[row * 3 + col]

    def get_row(self, row: int) -> tuple[int, int, int]:
        """Get all items in given row."""
        v = self.value[row * 3 : (row + 1) * 3]
        assert len(v) == 3
        return v

    def get_col(self, col: int) -> tuple[int, int, int]:
        """Get all items in given column."""
        v = self.value[col:9:3]
        assert len(v) == 3
        return v

    def get_diag(self, right: int) -> tuple[int, int, int]:
        """Get all items in given diagonal.

        Right = top right to bottom left
        """
        start = 2 if right else 0
        delta = 2 if right else 4
        end = 8 if right else 9
        v = self.value[start:end:delta]
        assert len(v) == 3
        return v


class GameAction(NamedTuple):
    """Tic Tac Toe Game GameAction."""

    row: int
    col: int
    player: int


class Game:
    """Tic Tac Toe Minimax.

    Uses convention that X plays first.
    """

    __slots__ = ()

    @staticmethod
    def value(state: State) -> int:
        """Return the value of a given game state."""
        for func_id, function in enumerate(
            (state.get_row, state.get_col, state.get_diag),
        ):
            stop = 2 if func_id == 2 else 3
            for idx in range(stop):
                sum_ = sum(function(idx))
                if sum_ == 3:
                    return 1
                if sum_ == -3:
                    return -1
        return 0

    @staticmethod
    def terminal(state: State) -> bool:
        """Return if given game state is terminal."""
        value = Game.value(state)
        if value in {1, -1}:
            return True
        return 0 not in state.value

    @staticmethod
    def player(state: State) -> Player:
        """Return player status given the state of the game.

        Must return either Player.MIN or Player.MAX
        """
        x_count = state.value.count(1)
        o_count = state.value.count(-1)
        if x_count > o_count:
            return Player.MIN  # O
        # X always plays first
        return Player.MAX  # X

    @classmethod
    def actions(cls, state: State) -> Iterable[GameAction]:
        """Return a collection of all possible actions in a given game state."""
        player = -1 if cls.player(state) == Player.MIN else 1
        for index in range(9):
            row, col = divmod(index, 3)
            if state.value[index] == 0:
                yield GameAction(row, col, player)

    @staticmethod
    def result(state: State, action: GameAction) -> State:
        """Return new game state after performing action on given state."""
        index = action.row * 3 + action.col
        mutable = list(state.value)
        mutable[index] = action.player
        return State(
            cast(
                "tuple[int, int, int, int, int, int, int, int, int]",
                tuple(mutable),
            ),
        )


class TicTacToeNeuroComponent(TrioNeuroAPIComponent):
    """Tic Tac Toe game Neuro component."""

    __slots__ = ("wait_connect_event",)

    def __init__(self, component_name: str) -> None:
        """Initialize Tic Tac Toe Neuro component."""
        super().__init__(component_name, "Tic Tac Toe")
        self.wait_connect_event = trio.Event()

    def bind_handlers(self) -> None:
        """Register event handlers."""
        self.register_handler("connect", self.handle_connect)

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
            """You are playing a tic tac toe game.""",
        )

        # Do default print message
        await super().websocket_connect_successful()

    async def wait_for_websocket(self) -> None:
        """Blocking until websocket connection trial ends."""
        await self.wait_connect_event.wait()


async def run() -> None:
    """Run test of module."""
    url = "ws://localhost:8000"
    async with trio.open_nursery(strict_exception_groups=True) as nursery:
        manager = ExternalRaiseManager("name", nursery)

        tic_tac_toe = TicTacToeNeuroComponent("neuro_api")
        manager.add_component(tic_tac_toe)

        await manager.raise_event(Event("connect", url))

        await tic_tac_toe.wait_for_websocket()

        if tic_tac_toe.not_connected:
            print("Neuro not connected, stopping.")
            return

        game = Game()
        state = State((0, 0, 0, 0, 0, 0, 0, 0, 0))

        map_ = {-1: "O", 0: "No one (tie)", 1: "X"}
        neuro_played = trio.Event()

        def game_action_mapper(
            game_action: GameAction,
        ) -> tuple[
            Action,
            Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]],
        ]:
            player = map_[game_action.player]
            to_neuro_action = Action(
                f"play_{game_action.row}_{game_action.col}",
                f"Plays an {player} at row {game_action.row} column {game_action.col}",
                {},
            )

            async def handler(
                neuro_action: NeuroAction,
            ) -> tuple[bool, str | None]:
                print(f"Got {to_neuro_action.name}")
                nonlocal state
                state = game.result(state, game_action)
                neuro_played.set()
                return (
                    True,
                    f"Played an {player} at row {game_action.row} column {game_action.col}",
                )

            return (to_neuro_action, handler)

        while not game.terminal(state):
            if game.player(state) == Player.MAX:
                print(str(state))
                actions_group = (
                    await tic_tac_toe.register_temporary_actions_group(
                        game_action_mapper(game_action)
                        for game_action in game.actions(state)
                    )
                )
                if actions_group:
                    await tic_tac_toe.send_force_action(
                        "Neuro's Turn",
                        "It is your turn now. Please select a play to make on the tic tac toe board.",
                        actions_group,
                    )

                    print("\nWaiting for Neuro to make a move...")
                    await neuro_played.wait()
                    neuro_played = trio.Event()
            else:
                actions = tuple(game.actions(state))
                while True:
                    print(str(state))
                    for idx, action in enumerate(actions):
                        print(f"{idx + 1}: {action}")
                    try:
                        index = int(input("Your choice: "))
                    except ValueError:
                        print("Bad choice try again\n")
                    if index < 1 or index > len(actions):
                        print("Bad choice try again\n")
                    else:
                        break
                game_action = actions[index - 1]
                state = game.result(state, game_action)
                player = map_[game_action.player]
                await tic_tac_toe.send_context(
                    f"Opponent played an {player} at row {game_action.row} column {game_action.col}\n"
                    f"Current game board: {state}",
                )
        print(str(state))
        value = game.value(state)
        win_message = f"{map_[value]} wins!"
        print(win_message)
        await tic_tac_toe.send_context(win_message, silent=False)
        await tic_tac_toe.stop()


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    try:
        trio.run(run)
    except ExceptionGroup as exc:
        traceback.print_exception(exc)
