"""API - Neuro API Game Client."""

# Programmed by CoolCat467

from __future__ import annotations

# API - Neuro API Game Client
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

__title__ = "api"
__author__ = "CoolCat467"
__version__ = "1.1.0"
__license__ = "GNU Lesser General Public License Version 3"


from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, NamedTuple

import orjson
import trio

from neuro_api import command

if TYPE_CHECKING:
    from collections.abc import Sequence

    import trio_websocket


class NeuroAction(NamedTuple):
    """Neuro Action object."""

    id_: str
    name: str
    data: str | None


class AbstractNeuroAPI(metaclass=ABCMeta):
    """Neuro API."""

    # __slots__ = ("__connection", "__currently_registered", "game_title")

    def __init__(
        self,
        game_title: str,
        connection: trio_websocket.WebSocketConnection | None = None,
    ) -> None:
        """Initialize NeuroAPI."""
        self.game_title = game_title
        self.__connection = connection
        # Keep track of currently registered actions to be able to handle
        # `actions/reregister_all` command.
        self.__currently_registered: dict[
            str,
            tuple[str, dict[str, object] | None],
        ] = {}

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

    def get_registered(self) -> tuple[str, ...]:
        """Return all currently registered Neuro action names."""
        return tuple(self.__currently_registered)

    async def send_command_data(self, data: bytes) -> None:
        """Send command data over the websocket.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded.
        """
        await self.connection.send_message(data.decode("utf-8"))

    async def send_startup_command(self) -> None:
        """Send startup command.

        This message should be sent as soon as the game starts, to let
        Neuro know that the game is running.

        This message clears all previously registered actions for this game
        and does initial setup, and as such should be the very first message
        that you send.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.
        """
        await self.send_command_data(command.startup_command(self.game_title))

    async def send_context(self, message: str, silent: bool = True) -> None:
        """Send a message to add to Neuro's context.

        This can let Neuro know about something that is happening in
        game.

        Arguments:
        - `message`:
            A plaintext message that describes what is happening in the
            game. **This information will be directly received by Neuro.**
        - `silent`:
            If True, the message will be added to Neuro's context without
            prompting her to respond to it. If False, Neuro _might_
            respond to the message directly, unless she is busy talking to
            someone else or to chat.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.

        """
        await self.send_command_data(
            command.context_command(self.game_title, message, silent),
        )

    async def register_actions(self, actions: list[command.Action]) -> None:
        """Register actions with Neuro.

        This registers one or more actions for Neuro to use.

        actions:
            A list of actions to be registered. If you try to register an
            action that is already registered, it will be ignored.

        Raises `ValueError` if action name has invalid characters or bad
        schema key.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.
        """
        for action in actions:
            command.check_action(action)

            self.__currently_registered[action.name] = (
                action.description,
                action.schema,
            )
        await self.send_command_data(
            command.actions_register_command(self.game_title, actions),
        )

    async def unregister_actions(self, action_names: Sequence[str]) -> None:
        """Unregister actions with Neuro.

        This unregisters one or more actions, preventing Neuro from
        using them anymore.

        action_names:
            The names of the actions to unregister. If you try to unregister
            an action that isn't registered, there will be no problem.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.
        """
        for action_name in action_names:
            self.__currently_registered.pop(action_name, None)
        await self.send_command_data(
            command.actions_unregister_command(self.game_title, action_names),
        )

    async def send_force_action(
        self,
        state: str,
        query: str,
        action_names: Sequence[str],
        ephemeral_context: bool = False,
    ) -> None:
        """Send force action start to Neuro.

        This message forces Neuro to execute one of the listed actions as
        soon as possible. Note that this might take a bit if she is already
        talking.

        Neuro can only handle one action force at a time.
        Sending an action force while another one is in progress will cause
        problems!

        Parameters
        ----------
        - `state`:
            An arbitrary string that describes the current state of the
            game. This can be plaintext, JSON, Markdown, or any other
            format. **This information will be directly received by Neuro.**
        - `query`:
            A plaintext message that tells Neuro what she is currently
            supposed to be doing (e.g. `"It is now your turn. Please perform
            an action. If you want to use any items, you should use them
            before picking up the shotgun."`). **This information will be
            directly received by Neuro.**
        - `ephemeral_context`:
            If False, the context provided in the `state` and `query`
            parameters will be remembered by Neuro after the actions force
            is completed. If True, Neuro will only remember it for the
            duration of the actions force.
        - `action_names`:
            The names of the actions that Neuro should choose from.

        Raises `ValueError` if any action name is not currently registered.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.

        """
        for name in action_names:
            if name not in self.get_registered():
                raise ValueError(f"{name!r} is not currently registered.")
        await self.send_command_data(
            command.actions_force_command(
                self.game_title,
                state,
                query,
                action_names,
                ephemeral_context,
            ),
        )

    async def send_action_result(
        self,
        id_: str,
        success: bool,
        message: str | None = None,
    ) -> None:
        """Send action result.

        This message needs to be sent as soon as possible after an action is
        validated, to allow Neuro to continue.

        Until you send an action result, Neuro will just be waiting for the
        result of her action!
        Please make sure to send this as soon as possible.
        It should usually be sent after validating the action parameters,
        before it is actually executed in-game

        Parameters
        ----------
        - `id_`:
            The id of the action that this result is for. This is grabbed
            from the action message directly.
        - `success`:
            Whether or not the action was successful. _If this is `false`
            and this action is part of an actions force, the whole actions
            force will be immediately retried by Neuro._
        - `message`:
            A plaintext message that describes what happened when the action
            was executed. If not successful, this should be an error
            message. If successful, this can either be empty, or provide a
            _small_ context to Neuro regarding the action she just took
            (e.g. `"Remember to not share this with anyone."`). **This
            information will be directly received by Neuro.**

        Since setting `success` to `false` will retry the action force if
        there was one, if the action was not successful but you don't want
        it to be retried, you should set `success` to `true` and provide an
        error message in the `message` field.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.

        """
        await self.send_command_data(
            command.actions_result_command(
                self.game_title,
                id_,
                success,
                message,
            ),
        )

    async def send_shutdown_ready(self) -> None:
        """Send shutdown ready response.

        This is part of the game automation API, which will only be used for
        games that Neuro can launch by herself. As such, most games will not
        need to use implement this.

        This should be sent as a response to a graceful or an imminent
        shutdown request, after progress has been saved. After this is
        sent, Neuro will close the game herself by terminating the
        process, so to reiterate you must definitely ensure that
        progress has already been saved.

        Raises `ConnectionClosed` if websocket connection is closed, or
        being closed.

        Could raise `UnicodeDecodeError` if data is unable to be decoded,
        but probably won't happen.

        Raises `orjson.JSONEncodeError` if unable to encode json data.
        """
        await self.send_command_data(
            command.shutdown_ready_command(self.game_title),
        )

    async def read_raw_message(
        self,
    ) -> tuple[str, dict[str, object] | None]:
        """Return command name and associated data from Neuro.

        Will not return until message read from websocket.

        Raises `orjson.JSONDecodeError` on invalid message.

        Raises `trio_websocket.ConnectionClosed` on websocket connection error.

        Raises `trio.BrokenResourceError` if something has gone wrong,
        and internal memory channel is broken. Probably won't happen.

        Raises `AssertionError` if received types in json message are not
        expected types.
        """
        message = orjson.loads(await self.connection.get_message())
        command = message["command"]
        assert isinstance(command, str)
        raw_data = message.get("data")
        assert isinstance(raw_data, dict) or raw_data is None
        data: dict[str, object] | None = raw_data
        return command, data

    @abstractmethod
    async def handle_action(self, action: NeuroAction) -> None:
        """Handle an Action from Neuro."""

    async def handle_graceful_shutdown_request(
        self,
        wants_shutdown: bool,
    ) -> None:
        """Handle a graceful shutdown request from Neuro.

        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself.
        As such, most games will not need to implement this.

        This message will be sent when Neuro decides to stop playing a
        game, or upon manual intervention from the dashboard. You should
        create or identify graceful shutdown points where the game can
        be closed gracefully after saving progress. You should store the
        latest received wants_shutdown value, and if it is true when a
        graceful shutdown point is reached, you should save the game and
        quit to main menu, then send back a shutdown ready message.

        Important:
        Please don't actually close the game, just quit to main menu.
        Neuro will close the game herself.

        Arguments:
        wants_shutdown:
            Whether the game should shutdown at the next graceful
            shutdown point. True means shutdown is requested, False
            means to cancel the previous shutdown request.

        Default implementation sends that shutdown is ready.

        """
        if wants_shutdown:
            await self.send_shutdown_ready()
            return
        await trio.lowlevel.checkpoint()  # pragma: nocover

    async def handle_immediate_shutdown(self) -> None:
        """Handle immediate shutdown alert from Neuro.

        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself. As such, most games
        will not need to implement this.

        This message will be sent when the game needs to be shutdown
        immediately. You have only a handful of seconds to save as much
        progress as possible. After you have saved, you can send back a
        shutdown ready message.

        Important:
        Please don't actually close the game, just save the
        current progress that can be saved. Neuro will close the game
        herself.

        Default implementation sends that shutdown is ready.

        """
        await self.send_shutdown_ready()

    async def handle_unknown_command(
        self,
        command: str,
        data: dict[str, object] | None,
    ) -> None:  # pragma: nocover
        """Handle unknown command from Neuro.

        On default, just prints.
        """
        print(
            f"[neuro_api.api] Received unknown command {command!r} {data = }",
        )
        await trio.lowlevel.checkpoint()

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

        Does not catch any exceptions `read_raw_message` raises.
        """
        command_type, data = await self.read_raw_message()
        if command_type == "action":
            assert data is not None
            action_data = command.check_typed_dict(
                data,
                command.IncomingActionMessageSchema,
            )
            await self.handle_action(
                NeuroAction(
                    action_data["id"],
                    action_data["name"],
                    action_data.get("data"),
                ),
            )
        elif command_type == "actions/reregister_all":
            # Neuro crashed, re-register all actions.
            if self.get_registered():
                await self.register_actions(
                    [
                        command.Action(name, desc, schema)
                        for name, (
                            desc,
                            schema,
                        ) in self.__currently_registered.items()
                    ],
                )
        elif command_type == "shutdown/graceful":
            # If wants_shutdown is True, save and return to title
            # whenever next possible.
            # If False, cancel previous shutdown request.
            assert data is not None
            await self.handle_graceful_shutdown_request(
                bool(data["wants_shutdown"]),
            )
        elif command_type == "shutdown/immediate":
            await self.handle_immediate_shutdown()
        else:
            await self.handle_unknown_command(command_type, data)
