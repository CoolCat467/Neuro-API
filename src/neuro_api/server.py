"""Server - Neuro Websocket API Server Implementation."""

# Programmed by CoolCat467

from __future__ import annotations

# Server - Neuro Websocket API Server Implementation
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

__title__ = "Neuro Websocket API Server"
__author__ = "CoolCat467"
__license__ = "GNU General Public License Version 3"


import sys
import traceback
import weakref
from abc import ABCMeta, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict
from uuid import UUID

import trio
from trio_websocket import (
    WebSocketConnection,
    WebSocketRequest,
    serve_websocket,
)
from typing_extensions import NotRequired

from neuro_api import command
from neuro_api.api import __version__
from neuro_api.client import AbstractNeuroAPIClient
from neuro_api.command import Action

if TYPE_CHECKING:
    from collections.abc import Callable
    from ssl import SSLContext

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup


class ContextData(TypedDict):
    """Context command data schema."""

    message: str
    silent: bool


class ActionSchema(TypedDict):
    """Action schema."""

    name: str
    description: str
    schema: NotRequired[dict[str, object] | None]


class RegisterActionsData(TypedDict):
    """Register actions command data schema."""

    actions: list[ActionSchema]


class UnregisterActionsData(TypedDict):
    """Action names command data schema."""

    action_names: list[str]


class ForceActionsData(TypedDict):
    """Force actions command data schema."""

    state: NotRequired[str]
    query: str
    ephemeral_context: NotRequired[bool]
    action_names: list[str]


class ActionResultData(TypedDict):
    """Action Result command data schema."""

    id: str
    success: bool
    message: NotRequired[str | None]


def deserialize_actions(data: dict[str, object]) -> list[Action]:
    """Deserialize and return list of Action objects."""
    actions_data = command.check_typed_dict(data, RegisterActionsData)

    actions: list[Action] = []
    for raw_action in actions_data["actions"]:
        action_data = command.check_typed_dict(
            raw_action,
            ActionSchema,
        )
        action = Action(
            action_data["name"],
            action_data["description"],
            action_data.get("schema"),
        )
        command.check_action(action)
        actions.append(action)
    return actions


def check_action_names_type(action_names: list[str]) -> None:
    """Return action names from command data."""
    for item in action_names:
        if not isinstance(item, str):
            raise ValueError(f"{item!r} is not a string object")


class AbstractNeuroServerClient(AbstractNeuroAPIClient):
    """Abstract Neuro Server Client.

    Abstract class implementing methods for sending server to client
    commands and receiving client to server commands.

    This class is designed to be subclassed by specific server-side
    client implementations.
    """

    __slots__ = ()

    @abstractmethod
    def get_next_id(self) -> str:
        """Return next unique command id."""

    async def send_action_command(
        self,
        name: str,
        data: str | None = None,
    ) -> str:
        """Submit action request and return associated command result id.

        Attempt to execute a registered action.

        Server LLM shouldn't do anything until receives associated
        action result.

        Args:
            name (str): The name of the action that Neuro is trying to
                execute.
            data (str): JSON-stringified data for the action. This
                **_should_** be an object that matches the JSON schema
                provided when registering the action. If schema was not
                provided, this should be `None`.

        Returns:
            str: Command ID that associated action result should have.

        """
        id_ = self.get_next_id()
        await self.send_command_data(
            command.action_command(
                id_,
                name,
                data,
            ),
        )
        return id_

    async def send_reregister_all_command(self) -> None:
        """Send reregister all command to client.

        This signals to the client to unregister all actions and
        reregister them.

        Warning:
            This command is part of the proposed API and is not officially
            supported yet. Some clients may not support it.

        """
        await self.send_command_data(command.reregister_all_command())

    async def send_graceful_shutdown_command(
        self,
        wants_shutdown: bool,
    ) -> None:
        """Send graceful shutdown command to client.

        This signals game to save and quit to main menu and send back a
        shutdown ready message.

        Args:
            wants_shutdown (bool): Whether the game should shutdown at
                the next graceful shutdown point. `True` means shutdown
                is requested, `False` means to cancel the previous
                shutdown request.

        Warning:
            This is part of the game automation API, which will only be used
            for games that Neuro can launch by herself. Most games will not
            support it this command.

        """
        await self.send_command_data(
            command.shutdown_graceful_command(wants_shutdown),
        )

    async def send_immediate_shutdown_command(
        self,
        wants_shutdown: bool,
    ) -> None:
        """Send immediate shutdown command to client.

        This signals to the game that it needs to be shutdown
        immediately and needs to send back a shutdown ready message as
        soon as the game has saved.

        Warning:
            This is part of the game automation API, which will only be used
            for games that Neuro can launch by herself. Most games will not
            support it this command.

        """
        await self.send_command_data(command.shutdown_immediate_command())

    async def handle_startup(self, game_title: str) -> None:
        """Handle startup command.

        This command MUST clear all previously registered actions for this
        client.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.

        """

    async def handle_context(
        self,
        game_title: str,
        message: str,
        silent: bool,
    ) -> None:
        """Handle context command.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.
            message (str): A plaintext message that describes what is
                happening in the game. **This information will be directly
                received by Neuro.**
            silent (bool): If `True`, the message will be added to
                Neuro's context without prompting her to respond to it.
                If `False`, Neuro _might_ respond to the message
                directly, unless she is busy talking to someone else or
                to chat.

        """

    @abstractmethod
    async def handle_actions_register(
        self,
        game_title: str,
        actions: list[Action],
    ) -> None:
        """Handle register actions command.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.
            actions (list[Action]): An list of ``Action``s to be
                registered. You should ignore actions that are already
                registered.

        """

    @abstractmethod
    async def handle_actions_unregister(
        self,
        game_title: str,
        action_names: list[str],
    ) -> None:
        """Handle unregister actions command.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.
            action_names: The names of the actions to unregister. If
                client tries to unregister an action that isn't
                registered, ignore it.

        """

    @abstractmethod
    async def handle_actions_force(
        self,
        game_title: str,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
    ) -> None:
        """Handle force action command.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.
            state (str | None): An arbitrary string that describes the
                current state of the game. This can be plaintext, JSON,
                Markdown, or any other format. **This information will
                be directly received by Neuro.**
            query (str): A plaintext message that tells Neuro what she
                is currently supposed to be doing. **This information
                will be directly received by Neuro.**
            ephemeral_context (bool): If `False`, the context provided
                in the `state` and `query` parameters will be remembered
                after the actions force is completed. If `True`, MUST
                only remember it for the duration of the actions force.
            action_names (list[str]): The names of the actions that
                Neuro MUST choose from.

        """

    @abstractmethod
    async def handle_action_result(
        self,
        game_title: str,
        id_: str,
        success: bool,
        message: str | None,
    ) -> None:
        """Handle action result command.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.
            id_ (str): The id of the action that this result is for.
            success (bool):  Whether or not the action was successful.
                _If this is `False` and this action is part of an
                actions force, the whole actions force MUST be
                immediately retried._
            message (str | None): A plaintext message that describes
                what happened when the action was executed. If not
                successful, this should be an error message. If
                successful, this can either be empty, or provide a
                _small_ context to Neuro regarding the action she just
                took. **This information will be directly received by
                Neuro.**

        """

    async def handle_shutdown_ready(self, game_title: str) -> None:
        """Handle shutdown ready command.

        Client has indicated that they are ready to be closed.

        Args:
            game_title (str): Game title. Should not change for
                websocket client.

        """

    async def read_message(self) -> None:
        """Read message from client websocket.

        You should call this function in a loop as long as the websocket
        is still connected.

        Calls ``handle_startup`` for `startup` commands.

        Calls ``handle_context`` for `context` commands.

        Calls ``handle_actions_register`` for `actions/register` commands

        Calls ``handle_actions_unregister`` for `actions/unregister` commands.

        Calls ``handle_actions_force`` for `actions/force` commands.

        Calls ``handle_action_result`` for `action/result` commands.

        Calls ``handle_shutdown_ready`` for `shutdown/ready` commands.

        Calls ``handle_unknown_command`` for any other command.

        Raises:
            ValueError: If extra keys in action command data or
                missing keys in action command data.
            TypeError: If action command key type mismatch

        Note:
            Does not catch any exceptions ``read_raw_client_message`` raises.

        """
        # Read message from server
        command_type, game_title, data = await self.read_raw_client_message()

        if command_type == "startup":
            await self.handle_startup(game_title)
        elif command_type == "context":
            if data is None:
                raise ValueError(
                    f"`data` attribute must be set for {command_type!r} commands",
                )
            context = command.check_typed_dict(data, ContextData)
            await self.handle_context(
                game_title,
                context["message"],
                context["silent"],
            )
        elif command_type == "actions/register":
            if data is None:
                raise ValueError(
                    f"`data` attribute must be set for {command_type!r} commands",
                )
            actions = deserialize_actions(data)
            await self.handle_actions_register(game_title, actions)
        elif command_type == "actions/unregister":
            if data is None:
                raise ValueError(
                    f"`data` attribute must be set for {command_type!r} commands",
                )
            action_names_data = command.check_typed_dict(
                data,
                UnregisterActionsData,
            )
            action_names = action_names_data["action_names"]
            check_action_names_type(action_names)
            await self.handle_actions_unregister(game_title, action_names)
        elif command_type == "actions/force":
            if data is None:
                raise ValueError(
                    f"`data` attribute must be set for {command_type!r} commands",
                )
            force_actions_data = command.check_typed_dict(
                data,
                ForceActionsData,
            )
            action_names = force_actions_data["action_names"]
            check_action_names_type(action_names)
            await self.handle_actions_force(
                game_title,
                force_actions_data.get("state", None),
                force_actions_data["query"],
                force_actions_data.get("ephemeral_context", False),
                action_names,
            )
        elif command_type == "action/result":
            if data is None:
                raise ValueError(
                    f"`data` attribute must be set for {command_type!r} commands",
                )
            result = command.check_typed_dict(data, ActionResultData)
            await self.handle_action_result(
                game_title,
                result["id"],
                result["success"],
                result.get("message", None),
            )
        elif command_type == "shutdown/ready":
            await self.handle_shutdown_ready(game_title)
        else:
            await self.handle_unknown_command(command_type, data)


class ForceActionContext(NamedTuple):
    """Force action context data."""

    temporary: bool
    state: str | None
    query: str


class ForceAction(NamedTuple):
    """Force Action data."""

    action_names: frozenset[str]
    context: ForceActionContext


class AbstractHandlerNeuroServerClient(AbstractNeuroServerClient):
    __slots__ = (
        "_force_actions",
        "_next_id",
        "_pending_actions",
        "game_title",
    )

    def __init__(self) -> None:
        self.game_title: str | None = None
        self._next_id = 0
        self._force_actions: list[ForceAction] = []
        self._pending_actions: dict[
            str,
            trio.MemorySendChannel[tuple[bool, str | None]],
        ] = {}

    def log_warning(self, message: str) -> None:
        """Handle logging a warning.

        Args:
            message (str): Message text.

        """
        print(f"[{self.__class__.__name__}] [warning] {message}")

    async def handle_unknown_command(
        self,
        command: str,
        data: dict[str, object] | None,
    ) -> None:
        """Handle unknown command from Neuro.

        Args:
            command (str): Unhandled command name
            data (dict[str, object] | None):
                Data associated with unknown command.

        Note:
            Base implementation just uses ``log_warning`` to log a warning.

        """
        self.log_warning(f"Received unknown command {command!r} {data = }")

    def get_next_id(self) -> str:  # noqa: D102
        value = self._next_id
        self._next_id += 1
        return str(UUID(int=value))

    @abstractmethod
    def clear_registered_actions(self) -> None:
        """Clear registered actions."""

    def check_game_title(self, game_title: str) -> None:
        """Check if game title matches recorded."""
        if self.game_title is None:
            self.log_warning(
                "A non-setup action fired before setup action, game title not set.",
            )
        if self.game_title != game_title:
            self.log_warning(
                f"Attempted to change game title from {self.game_title!r} to {game_title!r}, not allowed",
            )

    async def handle_startup(self, game_title: str) -> None:  # noqa: D102
        if self.game_title is None:
            self.game_title = game_title
        self.check_game_title(game_title)

        self.clear_registered_actions()

    @abstractmethod
    def add_context(self, message: str, reply_if_not_busy: bool) -> None:
        """Add message to context.

        Args:
            message (str): A plaintext message that describes what is
                happening in the game. **This information will be directly
                received by Neuro.**
            reply_if_not_busy (bool): If `False`, the message will be
                added to Neuro's context without prompting her to
                respond to it. If `True`, Neuro _might_ respond to the
                message directly, unless she is busy talking to someone
                else or to chat.

        """

    async def handle_context(  # noqa: D102
        self,
        game_title: str,
        message: str,
        silent: bool,
    ) -> None:
        self.check_game_title(game_title)

        self.add_context(message, not silent)

    @abstractmethod
    def register_action(self, action: Action) -> None:
        """Register an action.

        Actions that are already registered should be ignored.

        Args:
            action (Action): Action to register.

        """

    async def handle_actions_register(  # noqa: D102
        self,
        game_title: str,
        actions: list[Action],
    ) -> None:
        self.check_game_title(game_title)

        for action in actions:
            self.register_action(action)

    @abstractmethod
    def unregister_action(self, action_name: str) -> None:
        """Unregister an action.

        Actions that are not registered should be ignored.

        Args:
            action_name (str): Name of action to unregister.

        """

    async def handle_actions_unregister(  # noqa: D102
        self,
        game_title: str,
        action_names: list[str],
    ) -> None:
        self.check_game_title(game_title)

        for action_name in action_names:
            self.unregister_action(action_name)

    async def submit_action(
        self,
        name: str,
        data: str | None = None,
    ) -> tuple[bool, str | None]:
        """Return result of submitting an action request."""
        action_id = await self.send_action_command(name, data)
        # Zero for no buffer
        send, recv = trio.open_memory_channel[tuple[bool, str | None]](0)
        async with send, recv:
            # Record send channel for handle_action_result
            self._pending_actions[action_id] = send
            # Wait for result in receive channel
            print("[submit_action] post checkpoint, start wait")
            success, message = await recv.receive()
            # Clean up memory, action ids are unique
            del self._pending_actions[action_id]
            return success, message

    async def handle_action_result(
        self,
        game_title: str,
        id_: str,
        success: bool,
        message: str | None,
    ) -> None:
        self.check_game_title(game_title)

        send_channel = self._pending_actions.get(id_)
        if send_channel is None:
            self.log_warning(
                f"Got action result for unknown action id {id!r} ({success = } {message = })",
            )
            return
        if message:
            self.add_context(message, False)
        await send_channel.send((success, message))

    @abstractmethod
    async def choose_force_action(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: frozenset[str],
    ) -> tuple[str, str | None]:
        """Return selected action name and action data for force action request.

        Args:
            state (str | None): An arbitrary string that describes the
                current state of the game. This can be plaintext, JSON,
                Markdown, or any other format. **This information will
                be directly received by Neuro.**
            query (str): A plaintext message that tells Neuro what she
                is currently supposed to be doing. **This information
                will be directly received by Neuro.**
            ephemeral_context (bool): If `False`, the context provided
                in the `state` and `query` parameters will be remembered
                after the actions force is completed. If `True`, MUST
                only remember it for the duration of the actions force.
            action_names (frozenset[str]): List of action names that
                Neuro MUST choose from.

        Returns:
            tuple[str, str]: Tuple of
                - One of the action names from the `action_names` argument
                - JSON-stringified data for the action. This
                    **_should_** be an object that matches the JSON
                    schema provided when registering the action. If
                    schema was not provided, this should be `None`.

        """

    async def perform_actions_force(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
    ) -> None:
        success = False
        while not success:
            action_name, json_blob = await self.choose_force_action(
                state,
                query,
                ephemeral_context,
                frozenset(action_names),
            )
            success, _message = await self.submit_action(
                action_name,
                json_blob,
            )

    @abstractmethod
    async def submit_call_async_soon(
        self,
        function: Callable[[], Any],
    ) -> None:
        """Submit function to be called and awaited.

        Args:
            function (Callable[[], Any]): Function to call and await.

        """

    async def handle_actions_force(
        self,
        game_title: str,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
    ) -> None:
        self.check_game_title(game_title)

        do_actions_force = partial(
            self.perform_actions_force,
            state,
            query,
            ephemeral_context,
            action_names,
        )
        await self.submit_call_async_soon(do_actions_force)


class AbstractRecordingNeuroServerClient(AbstractHandlerNeuroServerClient):
    __slots__ = ("actions",)

    def __init__(self) -> None:
        super().__init__()
        self.actions: dict[str, Action] = {}

    def clear_registered_actions(self) -> None:
        self.actions.clear()

    def register_action(self, action: Action) -> None:
        self.actions[action.name] = action

    def unregister_action(self, action_name: str) -> None:
        if action_name in self.actions:
            del self.actions[action_name]


class BaseTrioNeuroServerClient(AbstractRecordingNeuroServerClient):
    __slots__ = ("websocket",)

    def __init__(self, websocket: WebSocketConnection) -> None:
        """Initialize BaseNeuroServerClient.

        Args:
            websocket (WebSocketConnection): Websocket used for communication.

        """
        super().__init__()
        self.websocket = websocket

    async def write_to_websocket(self, data: str) -> None:
        """Write a message to the websocket.

        Args:
            data (str): Message to be sent over the websocket.

        Raises:
            ConnectionClosed: If websocket connection is closed or closing.

        """
        await self.websocket.send_message(data)

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
        return await self.websocket.get_message()


class TrioNeuroServerClient(BaseTrioNeuroServerClient):
    __slots__ = ("_server_ref",)

    def __init__(
        self,
        websocket: WebSocketConnection,
        server: AbstractTrioNeuroServer,
    ) -> None:
        super().__init__(websocket)
        self._server_ref = weakref.ref(server)

    @property
    def server(self) -> AbstractTrioNeuroServer:
        value = self._server_ref()
        if value is None:
            raise ValueError("Reference to server is dead.")
        return value

    def log_warning(self, message: str) -> None:
        remote = self.websocket.remote
        if not isinstance(remote, str):
            remote = f"{remote.address}:{remote.port}"
        self.server.log_warning(f"[{self.game_title} ({remote})] {message}")

    def add_context(self, message: str, reply_if_not_busy: bool) -> None:
        self.server.add_context(self.game_title, message, reply_if_not_busy)

    async def choose_force_action(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: frozenset[str],
    ) -> tuple[str, str | None]:
        return await self.server.choose_force_action(
            self.game_title,
            state,
            query,
            ephemeral_context,
            tuple(self.actions[name] for name in action_names),
        )

    async def submit_call_async_soon(
        self,
        function: Callable[[], Any],
    ) -> None:
        self.server.handler_nursery.start_soon(function)


class AbstractTrioNeuroServer(metaclass=ABCMeta):
    """Trio Neuro Server."""

    __slots__ = (
        "__weakref__",
        "clients",
        "handler_nursery",
    )

    def __init__(self) -> None:
        self.clients: dict[str, TrioNeuroServerClient] = {}
        self.handler_nursery: trio.Nursery

    def log_info(self, message: str) -> None:
        """Log info message."""
        print(f"[INFO] {message}")

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        print(f"[WARNING] {message}")

    def log_critical(self, message: str) -> None:
        """Log critical message."""
        print(f"[CRITICAL] {message}")

    @abstractmethod
    def add_context(
        self,
        game_title: str | None,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        """Add message to context.

        Args:
            message (str): A plaintext message that describes what is
                happening in the game. **This information will be directly
                received by Neuro.**
            reply_if_not_busy (bool): If `False`, the message will be
                added to Neuro's context without prompting her to
                respond to it. If `True`, Neuro _might_ respond to the
                message directly, unless she is busy talking to someone
                else or to chat.

        """

    @abstractmethod
    async def choose_force_action(
        self,
        game_title: str | None,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        actions: tuple[Action, ...],
    ) -> tuple[str, str | None]:
        """Return selected action name and action data for force action request.

        Args:
            game_title (str): Title of the game that is submitting this
                request.
            state (str | None): An arbitrary string that describes the
                current state of the game. This can be plaintext, JSON,
                Markdown, or any other format. **This information will
                be directly received by Neuro.**
            query (str): A plaintext message that tells Neuro what she
                is currently supposed to be doing. **This information
                will be directly received by Neuro.**
            ephemeral_context (bool): If `False`, the context provided
                in the `state` and `query` parameters will be remembered
                after the actions force is completed. If `True`, MUST
                only remember it for the duration of the actions force.
            actions (tuple[Action, ...]): Tuple of ``Action``s that
                Neuro MUST choose from.

        Returns:
            tuple[str, str]: Tuple of
                - One of the action names from the `action_names` argument
                - JSON-stringified data for the action. This
                    **_should_** be an object that matches the JSON
                    schema provided when registering the action. If
                    schema was not provided, this should be `None`.

        """

    async def run(
        self,
        address: str,
        port: int,
        ssl_context: SSLContext | None = None,
    ) -> None:
        """Server run root function."""
        self.log_info(f"Starting websocket server on ws://{address}:{port}.")
        try:
            async with trio.open_nursery() as self.handler_nursery:
                self.handler_nursery.start_soon(
                    partial(
                        serve_websocket,
                        self.handle_websocket_request,
                        address,
                        port,
                        ssl_context=ssl_context,
                        handler_nursery=self.handler_nursery,
                    ),
                )
        except Exception as exc:
            self.log_critical(f"Failed to start websocket server:\n{exc}")
            raise

    async def handle_websocket_request(
        self,
        request: WebSocketRequest,
    ) -> None:
        """Handle websocket connection request."""
        remote = request.remote
        if not isinstance(remote, str):
            remote = f"{remote.address}:{remote.port}"
        self.log_info(
            f"Client connection request from {remote}",
        )
        # Accept connection
        await self.handle_client_connection(
            await request.accept(),
        )

    async def handle_client_connection(
        self,
        websocket: WebSocketConnection,
    ) -> None:
        """Handle websocket connection lifetime."""
        remote = websocket.remote
        if not isinstance(remote, str):
            remote = f"{remote.address}:{remote.port}"

        self.log_info(
            f"Accepted connection request ({remote})",
        )
        # Start running connection read and write tasks in the background
        try:
            async with websocket:
                client = TrioNeuroServerClient(websocket, self)
                self.clients[remote] = client

                while True:
                    await client.read_message()
        except BaseException:
            traceback.print_exc()
            raise


class TrioNeuroServer(AbstractTrioNeuroServer):
    __slots__ = ()

    def add_context(
        self,
        tame_title: str | None,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        print(f"\n[CONTEXT] {message}\n{reply_if_not_busy = }")

    async def choose_force_action(
        self,
        game_title: str | None,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        actions: tuple[Action, ...],
    ) -> tuple[str, str | None]:
        action_str = "\n".join(
            f"{idx + 1}: {action.name}\n\t{action.description}"
            for idx, action in enumerate(actions)
        )

        print(
            f"\n\n[Force Action] {game_title = }\n{state = }\n{query = }\nOptions:\n{action_str}",
        )
        action = actions[int(input("Action > ")) - 1]

        # Handle other tasks
        await trio.lowlevel.checkpoint()

        json_blob: str | None = None
        if action.schema is not None:
            print(f"\n{action.schema = }\n")
            if input("Do json blob? (y/N) > ").lower() == "y":
                # Handle other tasks
                await trio.lowlevel.checkpoint()
                json_blob = input("Json blob > ")
            # Handle other tasks
            await trio.lowlevel.checkpoint()
        return action.name, json_blob


async def run_async() -> None:
    server = TrioNeuroServer()
    try:
        await server.run("localhost", 8000)
    except BaseExceptionGroup:
        traceback.print_exc()


def run() -> None:
    """Run program."""
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    trio.run(run_async)


if __name__ == "__main__":
    run()
