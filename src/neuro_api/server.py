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
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast
from uuid import UUID

import trio
from trio_websocket import (
    WebSocketConnection,
    WebSocketRequest,
    serve_websocket,
)
from typing_extensions import NotRequired

from neuro_api import command, json_schema_types
from neuro_api.api import __version__
from neuro_api.client import AbstractNeuroAPIClient
from neuro_api.command import Action, ForcePriority

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from ssl import SSLContext

if sys.version_info < (3, 11):  # pragma: nocover
    from exceptiongroup import BaseExceptionGroup


class ContextData(TypedDict):
    """Context command data schema.

    Attributes:
        message (str): The context message.
        silent (bool): If `True`, the message will be added to
            Neuro's context without prompting her to respond to it. If
            `False`, Neuro _might_ respond to the message directly,
            unless she is busy talking to someone else or to chat.

    """

    message: str
    silent: bool


class ActionSchema(TypedDict):
    """Action schema definition.

    Attributes:
        name (str): The name of the action.
        description (str): A description of the action.
        schema (NotRequired[dict[str, object]]):
            Optional schema for the action.

    """

    name: str
    description: str
    schema: NotRequired[json_schema_types.SchemaObject]


class RegisterActionsData(TypedDict):
    """Register actions command data schema.

    Attributes:
        actions (list[ActionSchema]): List of actions to register.

    """

    actions: list[ActionSchema]


class UnregisterActionsData(TypedDict):
    """Unregister actions command data schema.

    Attributes:
        action_names (list[str]): List of action names to unregister.

    """

    action_names: list[str]


class ForceActionsData(TypedDict):
    """Force actions command data schema.

    Attributes:
        state (NotRequired[str], optional): Optional state for the actions.
            Defaults to None.
        query (str): The query associated with the actions.
        ephemeral_context (NotRequired[bool], optional):
            Flag for ephemeral context. Defaults to None.
        action_names (list[str]): List of action names to force.
        priority (ForcePriority):
            Determines how urgently Neuro should respond to the action
            force when she is speaking.

    """

    state: NotRequired[str]
    query: str
    ephemeral_context: NotRequired[bool]
    action_names: list[str]
    priority: NotRequired[Literal["low", "medium", "high", "critical"]]


class ActionResultData(TypedDict):
    """Action Result command data schema.

    Attributes:
        id (str): Unique identifier for the action result.
        success (bool): Indicates whether the action was successful.
        message (NotRequired[str]):
            Optional message providing additional details. Defaults to None.

    """

    id: str
    success: bool
    message: NotRequired[str]


def deserialize_actions(data: dict[str, list[object]]) -> list[Action]:
    """Deserialize a dictionary of actions into a list of Action objects.

    Args:
        data (dict[str, object]): A dictionary containing action
            registration data.

    Returns:
        list[Action]: A list of deserialized Action objects.

    Raises:
        ValueError: If the action data is invalid or fails validation.

    """
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
    """Validate that all items in the action names list are strings.

    Args:
        action_names (list[str]): A list of action names to be validated.

    Raises:
        ValueError: If any item in the list is not a string.

    Examples:
        >>> check_action_names_type(['action1', 'action2'])  # Passes
        >>> check_action_names_type(['action1', 123])  # Raises ValueError

    """
    for item in action_names:
        if not isinstance(item, str):
            raise ValueError(f"{item!r} is not a string object")


class AbstractNeuroServerClient(AbstractNeuroAPIClient):
    """Abstract base class for Neuro Server Client communication.

    This class defines the core interface for bidirectional communication
    between a server and client in the Neuro system, providing abstract
    methods and utilities for command exchange.

    Key Responsibilities:
        - Define methods for sending commands from server to client
        - Define methods for receiving and processing commands from client to server
        - Provide a standardized communication protocol for game automation

    Core Communication Patterns:
        - Action registration and unregistration
        - Context management
        - Command execution and result handling
        - Graceful shutdown mechanisms

    Note:
        - This is an abstract base class that MUST be subclassed
        - Subclasses must implement all abstract methods
        - Designed to support flexible, game-agnostic automation workflows

    """

    __slots__ = ()

    @abstractmethod
    def get_next_id(self) -> str:
        """Generate and return the next unique command identifier.

        Returns:
            str: A unique identifier for a command.

        """

    async def send_action_command(
        self,
        name: str,
        data: str | None = None,
    ) -> str:
        """Submit an action request and return the associated command result ID.

        This method attempts to execute a registered action. The server LLM
        should not proceed until it receives the associated action result.

        Args:
            name (str): The name of the action Neuro is attempting to execute.
            data (str, optional): JSON-stringified data for the action.
                This should match the JSON schema provided when registering
                the action. If no schema was provided, this should be None.

        Returns:
            str: Command ID that the associated action result should have.

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
        """Send a command to the client to unregister and reregister all actions.

        This method signals the client to completely reset and re-establish
        its action registration.

        Warning:
            This command is part of a proposed API and is not yet officially
            supported. Some clients may not implement this functionality.

        """
        await self.send_command_data(command.reregister_all_command())

    async def send_graceful_shutdown_command(
        self,
        wants_shutdown: bool,
    ) -> None:
        """Send a graceful shutdown command to the client.

        This method signals the game to save its state and return to the
        main menu, preparing for a potential shutdown.

        Args:
            wants_shutdown (bool): Control flag for shutdown request.
                - True: Request shutdown at the next graceful point
                - False: Cancel a previous shutdown request

        Warning:
            This is part of the game automation API and will only be used
            for games that can be launched automatically by Neuro. Most
            games will not support this command.

        Example:
            >>> await client.send_graceful_shutdown_command(True)  # Request shutdown
            >>> await client.send_graceful_shutdown_command(False)  # Cancel shutdown

        """
        await self.send_command_data(
            command.shutdown_graceful_command(wants_shutdown),
        )

    async def send_immediate_shutdown_command(
        self,
    ) -> None:
        """Send immediate shutdown command to client.

        This method signals the game to shut down immediately, with the
        expectation that it will save its state and send back a
        shutdown-ready message as quickly as possible.

        Warning:
            This is part of the game automation API and will only be used
            for games that can be launched automatically by Neuro. Most
            games will not support this command.

        """
        await self.send_command_data(command.shutdown_immediate_command())

    async def handle_startup(self, game_title: str) -> None:
        """Process the startup command for the client.

        This method is responsible for initializing the client's state
        when a game starts. It MUST clear all previously registered
        actions for this specific client.

        Args:
            game_title (str): The title of the game being started.
                This value should remain consistent for the entire
                websocket client session.

        Note:
            - This method is critical for resetting the client's
              action state before beginning a new game session.
            - Implementations should ensure a clean slate for
              new game interactions.

        """

    async def handle_context(
        self,
        game_title: str,
        message: str,
        silent: bool,
    ) -> None:
        """Process the context command received from the game client.

        This method handles incoming contextual information about
        the game state, which is directly passed to Neuro.

        Args:
            game_title (str): The title of the game. This should
                remain consistent throughout the websocket client
                session.
            message (str): A plaintext description of the current
                game state or event. This information is directly
                received by Neuro to understand the game context.
            silent (bool): Controls Neuro's response behavior:
                - True: Message is added to context silently
                  without prompting a response
                - False: Neuro may respond to the message,
                  subject to her current availability and
                  conversation state

        Note:
            - The `silent` flag provides fine-grained control
              over Neuro's interaction with the context.
            - Even with `silent=False`, Neuro might not respond
              if she is engaged in another conversation or task.

        """

    @abstractmethod
    async def handle_actions_register(
        self,
        game_title: str,
        actions: list[Action],
    ) -> None:
        """Register a list of actions for the game client.

        This abstract method must be implemented by subclasses to handle
        action registration for a specific game client.

        Args:
            game_title (str): The title of the game. This value should
                remain consistent throughout the websocket client session.
            actions (list[Action]): A list of actions to be registered
                for the game client.

        Note:
            - Implementations should handle duplicate action registrations
              by ignoring already registered actions.
            - This method is critical for preparing available actions
              for the game client.

        """

    @abstractmethod
    async def handle_actions_unregister(
        self,
        game_title: str,
        action_names: list[str],
    ) -> None:
        """Unregister specified actions from the game client.

        This abstract method must be implemented by subclasses to handle
        action unregistration for a specific game client.

        Args:
            game_title (str): The title of the game. This value should
                remain consistent throughout the websocket client session.
            action_names (list[str]): Names of actions to be unregistered.

        Note:
            - If an action name to be unregistered is not currently
              registered, it should be silently ignored.
            - Implementations should gracefully handle attempts to
              unregister non-existent actions.

        """

    @abstractmethod
    async def handle_actions_force(
        self,
        game_title: str,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
        priority: ForcePriority,
    ) -> None:
        """Force Neuro to choose and execute actions from a specified list.

        This abstract method provides a mechanism to constrain and direct
        Neuro's action selection for a specific game scenario.

        Args:
            game_title (str): The title of the game. This value should
                remain consistent throughout the websocket client session.
            state (str | None): A detailed description of the current
                game state. Can be in various formats (plaintext, JSON,
                Markdown) and is directly passed to Neuro.
            query (str): A plaintext instruction specifying what Neuro
                should do in the current context. Directly received by Neuro.
            ephemeral_context (bool): Controls context persistence:
                - False: Context (state and query) is remembered after
                  actions force completion
                - True: Context is only remembered during the actions
                  force operation
            action_names (list[str]): Names of actions Neuro MUST choose
                from when executing the force command.
            priority (ForcePriority):
                Determines how urgently Neuro should respond to the
                action force when she is speaking. If Neuro is not
                speaking, this setting has no effect. The default is
                `ForcePriority.LOW`, which will cause Neuro to wait
                until she finishes speaking before responding.
                `ForcePriority.MEDIUM` causes her to finish her current
                utterance sooner. `ForcePriority.HIGH` prompts her to
                process the action force immediately, shortening her
                utterance and then responding. `ForcePriority.CRITICAL`
                will interrupt her speech and make her respond at once.
                Use `ForcePriority.CRITICAL` with caution, as it may
                lead to abrupt and potentially jarring interruptions.

        """

    @abstractmethod
    async def handle_action_result(
        self,
        game_title: str,
        id_: str,
        success: bool,
        message: str | None,
    ) -> None:
        """Process the result of an executed action.

        This abstract method handles the outcome of a previously
        requested action, providing feedback and potential retry
        mechanisms.

        Args:
            game_title (str): The title of the game. This value should
                remain consistent throughout the websocket client session.
            id_ (str): Unique identifier of the action that was executed.
            success (bool): Indicates the action's execution status:
                - True: Action completed successfully
                - False: Action failed. If part of an actions force,
                  the entire actions force MUST be immediately retried
            message (str | None): Detailed information about the action's
                execution:
                - For successful actions: Optional small context about
                  the action's outcome
                - For failed actions: An error message explaining why
                  the action could not be completed

        Note:
            - The message provides direct feedback to Neuro about
              the action's result
            - Failed actions in a force actions context trigger
              an automatic retry mechanism
            - Implementations should carefully handle both successful
              and unsuccessful action scenarios

        """

    async def handle_shutdown_ready(self, game_title: str) -> None:
        """Process the shutdown ready command from the game client.

        This method is called when the client indicates it is prepared
        to be safely closed or disconnected.

        Args:
            game_title (str): The title of the game. This value should
                remain consistent throughout the websocket client session.

        Note:
            - This method signals that the game client has completed
              any necessary cleanup or save operations
            - Implementations should perform any final cleanup or
              resource management required before closing the connection
            - The method is typically part of a graceful shutdown
              sequence for the game client

        """

    @staticmethod
    def deserialize_actions(data: dict[str, list[object]]) -> list[Action]:
        """Deserialize a dictionary of actions into a list of Action objects.

        Args:
            data (dict[str, object]): A dictionary containing action
                registration data.

        Returns:
            list[Action]: A list of deserialized Action objects.

        Raises:
            ValueError: If the action data is invalid or fails validation.

        """
        return deserialize_actions(data)

    @staticmethod
    def check_action_names_type(action_names: list[str]) -> None:
        """Validate that all items in the action names list are strings.

        Args:
            action_names (list[str]): A list of action names to be validated.

        Raises:
            ValueError: If any item in the list is not a string.

        Examples:
            >>> check_action_names_type(['action1', 'action2'])  # Passes
            >>> check_action_names_type(['action1', 123])  # Raises ValueError

        """
        return check_action_names_type(action_names)

    async def read_message(self) -> None:
        """Read and process a message from the client websocket.

        This method is designed to be called in a loop while the websocket
        remains connected. It reads a raw client message and dispatches
        it to the appropriate handler based on the command type.

        Supported Command Types and Their Handlers:
        - "startup": Calls `handle_startup`
        - "context": Calls `handle_context`
        - "actions/register": Calls `handle_actions_register`
        - "actions/unregister": Calls `handle_actions_unregister`
        - "actions/force": Calls `handle_actions_force`
        - "action/result": Calls `handle_action_result`
        - "shutdown/ready": Calls `handle_shutdown_ready`
        - Unknown commands: Calls `handle_unknown_command`

        Raises:
            ValueError: If command data is missing or invalid:
                - Missing `data` attribute for commands requiring it
                - Extra or missing keys in action command data
            TypeError: If action command key types do not match expected types

        Note:
            - Does not catch exceptions raised by `read_raw_client_message`
            - Validates and processes each command type differently
            - Ensures type safety and data integrity before calling handlers

        Example:
            >>> while websocket.is_connected():
            ...     await client.read_message()

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
            # Cast is fine because deserialize_actions will check structure.
            actions = self.deserialize_actions(
                cast("dict[str, list[object]]", data),
            )
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
            self.check_action_names_type(action_names)
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
            self.check_action_names_type(action_names)
            await self.handle_actions_force(
                game_title,
                force_actions_data.get("state", None),
                force_actions_data["query"],
                force_actions_data.get("ephemeral_context", False),
                action_names,
                ForcePriority(force_actions_data.get("priority", "low")),
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


class AbstractHandlerNeuroServerClient(AbstractNeuroServerClient):
    """Abstract base class for Neuro Server Client with enhanced command handling.

    Extends AbstractNeuroServerClient with additional functionality for:
    - Unique ID generation
    - Pending action tracking
    - Game title management
    - Basic logging and error handling

    Attributes:
        game_title (str | None): Current game title, set during startup
        _next_id (int): Internal counter for generating unique command IDs
        _pending_actions (dict): Tracking for in-progress action channels

    Note:
        - Uses __slots__ for memory-efficient attribute management
        - Provides default implementations for common server client methods
        - Requires subclasses to implement specific action handling logic

    """

    __slots__ = (
        "_next_id",
        "_pending_actions",
        "game_title",
    )

    def __init__(self) -> None:
        """Initialize the Neuro Server Client with default state.

        Sets up:
        - Unset game title
        - Zero-initialized ID counter
        - Empty pending actions dictionary
        """
        self.game_title: str | None = None
        self._next_id = 0
        self._pending_actions: dict[
            str,
            trio.MemorySendChannel[tuple[bool, str | None]],
        ] = {}

    def log_warning(self, message: str) -> None:  # pragma: nocover
        """Handle logging a warning.

        Args:
            message (str): Message text.

        """
        print(f"[{self.__class__.__name__}] [warning] {message}")

    async def handle_unknown_command(
        self,
        command: str,
        data: dict[str, object] | None,
    ) -> None:  # pragma: nocover
        """Handle commands that are not recognized by the client.

        Provides a default error handling mechanism for unexpected commands.

        Args:
            command (str): The name of the unrecognized command
            data (dict[str, object] | None): Optional data associated
                with the unknown command

        Note:
            - Logs a warning with the command details
            - Subclasses can override for more sophisticated handling
            - Base implementation just uses ``log_warning`` to log a warning.

        """
        self.log_warning(f"Received unknown command {command!r} {data = }")

    def get_next_id(self) -> str:  # noqa: D102
        value = self._next_id
        self._next_id += 1
        return str(UUID(int=value))

    @abstractmethod
    def clear_registered_actions(self) -> None:
        """Abstract method to clear all registered actions.

        Subclasses must implement a method to reset the action state.
        """

    def check_game_title(self, game_title: str) -> None:
        """Validate the game title against the current client state.

        Performs two key checks:
        - Warns if no game title has been set before an action
        - Prevents changing the game title once it's been set

        Args:
            game_title (str): The game title to validate

        Note:
            - Logs a warning if game title is not set

        """
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
        """Register a single action for the current game session.

        This abstract method must be implemented by subclasses to
        define how individual actions are added to the client's
        available action set.

        Args:
            action (Action): The action to be registered.

        Behavior:
            - If the action is already registered, it should be ignored
            - Implementations should handle action deduplication
            - Should update the client's internal action tracking

        Note:
            - This is a core method for dynamically managing
              available actions during a game session
            - Subclasses must provide a concrete implementation
              that fits their specific action management strategy

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
        """Remove a specific action from the current game session's action set.

        This abstract method must be implemented by subclasses to
        define how individual actions are removed from the client's
        available actions.

        Args:
            action_name (str): The unique identifier of the action
                to be unregistered.

        Behavior:
            - If the action is not currently registered, it should be ignored
            - Implementations should handle action removal gracefully
            - Should update the client's internal action tracking

        Note:
            - Critical for dynamically managing available actions
              during a game session
            - Allows for fine-grained control of action availability
            - Subclasses must provide a concrete implementation
              that fits their specific action management strategy

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
        """Submit an action request and wait for its completion result.

        This method sends an action command to the client and blocks
        until the corresponding action result is received. It handles
        the complete action lifecycle from submission to result
        processing.

        Args:
            name (str): The name of the action to execute. Must be a
                previously registered action name.
            data (str | None, optional): JSON-stringified data for the action.
                Should conform to the JSON schema provided when the
                action was registered. If no schema was provided during
                registration, this should be None. Defaults to None.

        Returns:
            tuple[bool, str | None]: A tuple containing:
                - bool: Success status of the action execution
                    - True: Action completed successfully
                    - False: Action failed to execute
                - str | None: Result message from the action execution
                    - For successful actions: Optional context about the outcome
                    - For failed actions: Error message explaining the failure
                    - None: No additional message provided

        Raises:
            trio.BrokenResourceError: If the underlying communication channel
                is closed while waiting for the result.
            trio.EndOfChannel: If the result channel is unexpectedly closed.

        Note:
            - This method blocks until the action completes
            - Each action gets a unique ID for result correlation
            - Failed actions in force action contexts will trigger automatic retries
            - The result message, if present, is automatically added to Neuro's context

        """
        action_id = await self.send_action_command(name, data)
        # Zero for no buffer
        send, recv = trio.open_memory_channel["tuple[bool, str | None]"](0)
        async with send, recv:
            # Record send channel for handle_action_result
            self._pending_actions[action_id] = send
            try:
                # Wait for result in receive channel
                success, message = await recv.receive()
            finally:
                # Ensure cleanup even if an exception occurs
                self._pending_actions.pop(action_id, None)
            return success, message

    async def handle_action_result(
        self,
        game_title: str,
        id_: str,
        success: bool,
        message: str | None,
    ) -> None:
        """Process the result of a previously submitted action.

        This method handles action result messages from the client, correlating
        them with pending action submissions and delivering results through
        internal communication channels.

        Args:
            game_title (str): The title of the game. Must match the current
                client's game title to prevent cross-client contamination.
            id_ (str): Unique identifier of the completed action. This ID
                was generated when the action was originally submitted.
            success (bool): Execution status of the action:
                - True: Action completed successfully
                - False: Action failed. If this was part of a force actions
                  sequence, the entire sequence will be automatically retried.
            message (str | None): Detailed result information:
                - For successful actions: Optional context about the outcome
                - For failed actions: Error message explaining the failure
                - None: No additional information provided

        Behavior:
            - Validates the game title matches the current session
            - Looks up the pending action by ID
            - If found, delivers the result to the waiting ``submit_action`` call
            - If message is provided, adds it to Neuro's context (silently)
            - Logs a warning if the action ID is not found in pending actions

        Note:
            - This method is called automatically when action results arrive
            - Unknown action IDs are logged as warnings but don't raise errors
            - Result messages are automatically added to context for Neuro's awareness
            - The method ensures proper cleanup of internal tracking state

        Warning:
            If an action ID is not found in pending actions, this indicates
            either a client implementation error or a race condition in the
            communication protocol.

        """
        self.check_game_title(game_title)

        send_channel = self._pending_actions.get(id_)
        if send_channel is None:
            self.log_warning(
                f"Got action result for unknown action id {id_!r} ({success = } {message = })",
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
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        """Select an action and generate its data for a forced action scenario.

        This abstract method must be implemented by subclasses to
        provide the core decision-making logic for forced actions. It
        presents Neuro with the current game state and constraints, then
        returns her chosen action and associated data.

        Args:
            state (str | None): Detailed description of the current game state.
                Can be in any format (plaintext, JSON, Markdown, etc.) and is
                passed directly to Neuro for context understanding. None indicates
                no specific state information is available.
            query (str): Plaintext instruction telling Neuro what she should
                accomplish in this scenario. This directive is passed directly
                to Neuro and guides her action selection process.
            ephemeral_context (bool): Controls context persistence after completion:
                - False: State and query information is retained in Neuro's
                  context memory for future reference
                - True: State and query are only used during this force action
                  and are not retained afterward
            action_names (frozenset[str]): Constrained set of action names that
                Neuro MUST choose from. Her selection is limited to only these
                registered actions.

        Returns:
            tuple[str, str | None]: A tuple containing:
                - str: Selected action name, must be one of the names from
                  the ``action_names`` parameter
                - str | None: JSON-stringified action data that should conform
                  to the action's registered JSON schema. Returns None if the
                  action has no schema or requires no data.

        Note:
            - This method encapsulates the AI decision-making process
            - Implementations should handle Neuro's reasoning and choice logic
            - The returned action name must exactly match one from action_names
            - Action data should be properly formatted JSON or None

        Example Implementation Pattern:
            >>> async def choose_force_action(self, state, query, ephemeral_context, action_names):
            ...     # Present options to Neuro with state and query context
            ...     chosen_action = await self.present_choices_to_neuro(
            ...         state, query, list(action_names), ephemeral_context
            ...     )
            ...     action_data = await self.generate_action_data(chosen_action)
            ...     return chosen_action, action_data

        """

    async def perform_actions_force(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
        priority: ForcePriority,
    ) -> None:
        """Execute a forced action sequence with automatic retry on failure.

        This method orchestrates the complete forced action workflow by
        repeatedly attempting action execution until success is
        achieved. It handles the retry logic for failed actions as
        required by the Neuro API specification.

        Args:
            state (str | None): Current game state description passed to Neuro.
                Format-agnostic (plaintext, JSON, Markdown, etc.).
            query (str): Plaintext instruction for what Neuro should accomplish.
            ephemeral_context (bool): Context retention flag:
                - False: Context is permanently added to Neuro's memory
                - True: Context is only used for this forced action sequence
            action_names (list[str]): Available actions that Neuro can choose from.
                Converted to frozenset for the choice method.

        Behavior:
            1. Calls ``choose_force_action`` to get Neuro's selected action and data
            2. Submits the chosen action via ``submit_action``
            3. If the action fails, immediately retries from step 1
            4. Continues until an action succeeds
            5. Completes when any action in the sequence succeeds

        Note:
            - This method implements the mandatory retry logic for force actions
            - Failed actions trigger immediate re-selection and retry
            - The loop only terminates on successful action completion
            - Each retry allows Neuro to potentially choose a different action

        Warning:
            This method can potentially run indefinitely if all
            available actions consistently fail.

        Example Flow:
            >>> # Neuro chooses "attack_enemy" but it fails
            >>> # Method automatically retries
            >>> # Neuro chooses "flee_combat" and it succeeds
            >>> # Method completes successfully

        """
        success = False
        while not success:
            action_name, json_blob = await self.choose_force_action(
                state,
                query,
                ephemeral_context,
                frozenset(action_names),
                priority,
            )
            success, _message = await self.submit_action(
                action_name,
                json_blob,
            )

    @abstractmethod
    async def submit_call_async_soon(
        self,
        function: Callable[[], Awaitable[Any]],
    ) -> None:
        """Schedule a coroutine function to be executed asynchronously.

        This abstract method provides a mechanism for deferring the
        execution of async operations, typically used to prevent
        blocking during command processing or to manage execution
        ordering.

        Args:
            function (Callable[[], Awaitable[Any]]): A callable that
                returns a coroutine or awaitable object. The function
                should take no arguments and will be called and awaited
                when scheduled for execution.

        Note:
            - The exact scheduling behavior depends on the concrete implementation
            - Common patterns include using task queues, event loops, or nurseries
            - Used primarily for managing async execution flow in command handlers
            - The function will be called without arguments when executed

        Implementation Guidelines:
            - Should handle proper exception propagation from the scheduled function
            - May use frameworks like Trio nurseries, asyncio tasks, or custom queues
            - Should consider execution ordering and concurrency requirements

        Example Implementation Patterns:
            >>> # Using Trio nursery
            >>> async def submit_call_async_soon(self, function):
            ...     self.nursery.start_soon(function)

            >>> # Using asyncio
            >>> async def submit_call_async_soon(self, function):
            ...     asyncio.create_task(function())

        """

    async def handle_actions_force(
        self,
        game_title: str,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: list[str],
        priority: ForcePriority,
    ) -> None:
        """Process a force actions command from the game client.

        This method handles incoming requests to constrain Neuro's
        action choices to a specific set and execute actions until one
        succeeds. It delegates the actual execution to avoid blocking
        the message processing loop.

        Args:
            game_title (str): The title of the game sending the force actions
                command. Must match the current client's game title.
            state (str | None): Current game state description that will be
                passed directly to Neuro for context understanding.
            query (str): Plaintext instruction telling Neuro what she should
                accomplish in the current scenario.
            ephemeral_context (bool): Context persistence control:
                - False: State and query are retained in Neuro's memory
                - True: State and query are only used during this operation
            action_names (list[str]): List of action names that Neuro is
                restricted to choose from during this force sequence.
            priority (ForcePriority):
                Determines how urgently Neuro should respond to the
                action force when she is speaking. If Neuro is not
                speaking, this setting has no effect. The default is
                `ForcePriority.LOW`, which will cause Neuro to wait
                until she finishes speaking before responding.
                `ForcePriority.MEDIUM` causes her to finish her current
                utterance sooner. `ForcePriority.HIGH` prompts her to
                process the action force immediately, shortening her
                utterance and then responding. `ForcePriority.CRITICAL`
                will interrupt her speech and make her respond at once.
                Use `ForcePriority.CRITICAL` with caution, as it may
                lead to abrupt and potentially jarring interruptions.

        Behavior:
            1. Validates the game title matches the current session
            2. Creates a partial function with the force action parameters
            3. Schedules the force action execution asynchronously
            4. Returns immediately without waiting for completion

        Note:
            - This method returns immediately and does not block
            - The actual force action execution happens asynchronously
            - Uses ``submit_call_async_soon`` to delegate execution
            - Ensures the message processing loop remains responsive

        Warning:
            The asynchronous execution means this method completes
            before the force actions are finished. Callers should not
            assume the actions have completed when this method returns.

        """
        self.check_game_title(game_title)

        do_actions_force = partial(
            self.perform_actions_force,
            state,
            query,
            ephemeral_context,
            action_names,
            priority,
        )
        await self.submit_call_async_soon(do_actions_force)


class AbstractRecordingNeuroServerClient(AbstractHandlerNeuroServerClient):
    """Abstract Neuro Server Client with action recording and management capabilities.

    This class extends AbstractHandlerNeuroServerClient by adding
    concrete implementations for action registration, unregistration,
    and tracking. It maintains an in-memory registry of all registered
    actions for the current game session.

    Key Features:
        - **Action Registry**: Maintains a dictionary mapping action names to Action objects
        - **Dynamic Management**: Supports runtime addition and removal of actions
        - **Session Isolation**: Actions are cleared between game sessions
        - **Duplicate Handling**: Automatically handles action name conflicts by replacement

    Attributes:
        actions (dict[str, Action]): Registry mapping action names to their
            corresponding Action objects. Updated dynamically as actions are
            registered and unregistered during the game session.

    Storage Behavior:
        - Actions are stored by name as the dictionary key
        - Registering an action with an existing name replaces the previous action
        - Unregistering non-existent actions is silently ignored
        - All actions are cleared when a new game session starts

    Note:
        - This class still requires subclasses to implement abstract methods
          from parent classes (e.g., ``add_context``, ``choose_force_action``)
        - The action registry persists throughout a single game session
        - Memory usage scales with the number of registered actions

    Example Usage:
        >>> class MyNeuroClient(AbstractRecordingNeuroServerClient):
        ...     async def add_context(self, message, reply_if_not_busy):
        ...         # Implementation specific to your use case
        ...         pass
        ...
        ...     async def choose_force_action(self, state, query, ephemeral_context, action_names):
        ...         # Implementation specific to your use case
        ...         pass
        ...
        >>> client = MyNeuroClient()
        >>> print(len(client.actions))  # 0 - no actions initially
        >>> # Actions get registered through the websocket protocol
        >>> # client.actions will contain registered actions

    """

    __slots__ = ("actions",)

    def __init__(self) -> None:
        """Initialize the recording client with an empty action registry.

        Sets up the parent class state and creates an empty dictionary
        to track registered actions for the current session.
        """
        super().__init__()
        self.actions: dict[str, Action] = {}

    def clear_registered_actions(self) -> None:
        """Remove all registered actions from the current session.

        This method is called automatically during game startup to ensure
        a clean slate for each new game session. It removes all previously
        registered actions from the internal registry.

        Note:
            - Called automatically by ``handle_startup`` method
            - Ensures no action leakage between different game sessions
            - Does not affect the game client's action registrations

        """
        self.actions.clear()

    def register_action(self, action: Action) -> None:
        """Add a single action to the current session's action registry.

        Stores the provided action in the internal registry, making it
        available for future action selection and execution. If an
        action with the same name already exists, it will be replaced.

        Args:
            action (Action): The action object to register. The action's
                name will be used as the registry key.

        Behavior:
            - Action is stored using ``action.name`` as the dictionary key
            - Existing actions with the same name are silently replaced
            - The action becomes immediately available for selection
            - Registry size increases unless replacing an existing action

        Note:
            - No validation is performed on the action object
            - Duplicate names result in replacement, not addition
            - The action persists until explicitly unregistered or session ends

        Example:
            >>> action = Action("move_player", "Move the player character", {...})
            >>> client.register_action(action)
            >>> assert "move_player" in client.actions
            >>> assert client.actions["move_player"] == action

        """
        self.actions[action.name] = action

    def unregister_action(self, action_name: str) -> None:
        """Remove a specific action from the current session's action registry.

        Removes the action with the given name from the internal registry.
        If the action name is not found, the operation is silently ignored.

        Args:
            action_name (str): The name of the action to remove from the registry.
                Must exactly match the name used when the action was registered.

        Behavior:
            - Action is removed from the internal dictionary if it exists
            - Non-existent action names are silently ignored (no error)
            - Registry size decreases if the action was found
            - The action becomes unavailable for future selection

        Note:
            - Case-sensitive string matching is used for action names
            - No validation is performed on whether the action is currently in use
            - Graceful handling of attempts to unregister non-existent actions

        Example:
            >>> client.unregister_action("move_player")
            >>> assert "move_player" not in client.actions
            >>> # Unregistering non-existent actions is safe
            >>> client.unregister_action("non_existent_action")  # No error

        """
        if action_name in self.actions:
            del self.actions[action_name]
        else:
            self.log_warning(
                f"Attempted to unregister non-existent action: {action_name}",
            )

    def get_action(self, action_name: str) -> Action | None:
        """Retrieve a registered action by its name.

        Performs a lookup in the action registry to find the Action object
        associated with the given name.

        Args:
            action_name (str): The exact name of the action to retrieve.
                Must match the name used during registration (case-sensitive).

        Returns:
            Action | None: The Action object if found in the registry,
                None if no action with that name is registered.

        Note:
            - This is a read-only operation that doesn't modify the registry
            - Useful for validation before action execution
            - Returns None for non-existent actions (no exception raised)
            - The returned Action object is the same instance stored during registration

        Example:
            >>> action = Action("jump", "Make player jump", None)
            >>> client.register_action(action)
            >>> retrieved = client.get_action("jump")
            >>> assert retrieved == action
            >>> assert client.get_action("unknown") is None

        """
        return self.actions.get(action_name)

    def has_action(self, action_name: str) -> bool:
        """Check if an action is currently registered.

        Performs a fast membership test to determine if an action with
        the given name exists in the current registry.

        Args:
            action_name (str): The name of the action to check for existence.
                Must be an exact match (case-sensitive).

        Returns:
            bool: True if an action with the given name is registered,
                False otherwise.

        Note:
            - This is a lightweight operation using dictionary key lookup
            - More efficient than ``get_action`` when only existence matters
            - Does not provide access to the Action object itself
            - Useful for validation and conditional logic

        Example:
            >>> client.register_action(Action("attack", "Attack enemy", None))
            >>> assert client.has_action("attack") is True
            >>> assert client.has_action("defend") is False

        """
        return action_name in self.actions

    def get_action_names(self) -> frozenset[str]:
        """Get all currently registered action names.

        Returns an immutable set containing the names of all actions
        currently registered in the session registry.

        Returns:
            frozenset[str]: Immutable set of all registered action names.
                Empty frozenset if no actions are registered.

        Behavior:
            - Creates a snapshot of current action names at call time
            - Returned frozenset is immutable and independent of registry changes
            - Order is not guaranteed (set semantics)
            - Efficient for membership testing and iteration

        Note:
            - The returned frozenset reflects the state at the time of the call
            - Subsequent registry changes don't affect previously returned frozensets
            - Useful for iteration, validation, and constraint checking
            - Compatible with methods expecting immutable action name collections

        Example:
            >>> client.register_action(Action("move", "Move player", None))
            >>> client.register_action(Action("jump", "Jump action", None))
            >>> names = client.get_action_names()
            >>> assert names == frozenset({"move", "jump"})
            >>> # Returned frozenset is independent of later changes
            >>> client.unregister_action("move")
            >>> assert names == frozenset({"move", "jump"})  # Still contains "move"

        """
        return frozenset(self.actions.keys())


class BaseTrioNeuroServerClient(AbstractRecordingNeuroServerClient):
    """Trio-based WebSocket implementation of Neuro Server Client.

    This class provides a concrete WebSocket communication layer using the
    Trio async library and trio-websocket for real-time bidirectional
    communication with Neuro game clients.

    Key Features:
        - **Trio Integration**: Built on Trio's structured concurrency model
        - **WebSocket Communication**: Real-time message exchange with game clients
        - **Action Registry**: Inherits action management from parent class
        - **Connection Management**: Handles WebSocket lifecycle and error conditions

    Architecture:
        - Extends AbstractRecordingNeuroServerClient with concrete WebSocket I/O
        - Provides low-level send/receive operations for the communication protocol
        - Serves as base class for more specialized Neuro client implementations
        - Maintains WebSocket connection state throughout the session

    Attributes:
        websocket (WebSocketConnection): The trio-websocket connection instance
            used for all client communication. Manages the underlying TCP
            connection and WebSocket protocol framing.

    Connection Lifecycle:
        1. WebSocket connection established externally and passed to constructor
        2. Client uses connection for bidirectional message exchange
        3. Connection errors propagate to calling code for handling
        4. No automatic reconnection - connection management is external

    Note:
        - This class still requires subclasses to implement abstract methods
          like ``add_context``, ``choose_force_action``, and ``submit_call_async_soon``
        - WebSocket connection must be established before creating instances
        - Thread-safe within Trio's structured concurrency model
        - Connection errors should be handled by the calling application

    Example Usage:
        >>> import trio
        >>> from trio_websocket import serve_websocket
        >>>
        >>> class MyNeuroClient(BaseTrioNeuroServerClient):
        ...     async def add_context(self, message, reply_if_not_busy):
        ...         # Custom implementation
        ...         pass
        ...     # ... other required methods
        ...
        >>> async def handle_client(request):
        ...     websocket = await request.accept()
        ...     client = MyNeuroClient(websocket)
        ...     # Use client for communication
        ...     await client.read_message()

    """

    __slots__ = ("websocket",)

    def __init__(self, websocket: WebSocketConnection) -> None:
        """Initialize the Trio-based Neuro Server Client.

        Sets up the WebSocket communication layer and inherits action
        management capabilities from the parent class.

        Args:
            websocket (WebSocketConnection): An established trio-websocket
                connection instance. Must be in a connected state and ready
                for message exchange. The connection lifecycle is managed
                externally to this class.

        Note:
            - The WebSocket connection must already be established and accepted
            - This class does not handle connection establishment or cleanup
            - Parent class initialization creates an empty action registry
            - The websocket instance is stored for the lifetime of the client

        Example:
            >>> # Within a websocket handler
            >>> websocket = await request.accept()
            >>> client = BaseTrioNeuroServerClient(websocket)
            >>> # Client is ready for message processing

        """
        super().__init__()
        self.websocket = websocket

    async def write_to_websocket(self, data: str) -> None:
        """Send a message to the connected game client via WebSocket.

        Transmits a string message over the WebSocket connection to the
        game client. This method handles the low-level WebSocket framing
        and transmission details.

        Args:
            data (str): The message content to send to the client. Should be
                properly formatted according to the Neuro API protocol
                (typically JSON-formatted command data).

        Raises:
            trio_websocket.ConnectionClosed: If the WebSocket connection has been
                closed by either the client or server, or if the connection is
                in the process of closing.
            trio.BrokenResourceError: If the underlying network connection
                experiences an unexpected failure.
            OSError: For low-level network errors (connection reset, timeout, etc.).

        Behavior:
            - Message is sent immediately (no buffering)
            - Blocks until message transmission is complete or fails
            - WebSocket protocol handles message framing automatically
            - String data is encoded as UTF-8 text frames

        Note:
            - This is a low-level communication primitive
            - Higher-level methods should use ``send_command_data`` instead
            - Connection errors indicate the client has disconnected
            - No automatic retry or reconnection is attempted

        """
        await self.websocket.send_message(data)

    async def read_from_websocket(
        self,
    ) -> bytes | bytearray | memoryview | str:
        """Receive a message from the connected game client via WebSocket.

        Reads the next available message from the WebSocket connection,
        blocking until a message arrives or the connection fails.

        Returns:
            bytes | bytearray | memoryview | str: The received message data.
                - str: Text messages (recommended and expected for JSON protocol data)
                - bytes/bytearray/memoryview: Binary messages (supported by this code
                  but not properly handled by the original Neuro implementation)
                The specific type depends on the message frame type sent by the client.

        Raises:
            trio_websocket.ConnectionClosed: If the WebSocket connection has been
                closed by the client or server, or encounters a protocol error.
            trio.BrokenResourceError: If the internal message channel is broken,
                typically due to resource cleanup or cancellation. This is rare
                in normal operation.
            AssertionError: If the received message type is unexpected or invalid
                according to the WebSocket protocol specification.

        Behavior:
            - Blocks until a message is received or connection fails
            - Returns immediately when a message is available
            - Handles WebSocket protocol framing automatically
            - Preserves message boundaries as sent by the client

        Warning:
            While this method can receive binary messages (bytes,
            bytearray, or memoryview), the original Neuro implementation
            does not properly handle binary message processing. Clients
            should send only text messages containing JSON-formatted
            command data to ensure compatibility with the real Neuro.

        Note:
            - This is a low-level communication primitive
            - Higher-level methods should use ``read_raw_client_message`` instead
            - Text messages are typically JSON-formatted command data
            - Binary messages should be avoided in practice despite code support
            - Connection errors indicate the client has disconnected

        Example:
            >>> message = await client.read_from_websocket()
            >>> if isinstance(message, str):
            ...     # Process JSON command data (recommended path)
            ...     command_data = json.loads(message)
            >>> else:
            ...     # Handle binary data (avoid in practice)
            ...     print("Warning: Received binary message, may not be processed correctly")
            ...     binary_data = bytes(message)

        """
        return await self.websocket.get_message()


class TrioNeuroServerClient(BaseTrioNeuroServerClient):
    """Concrete Trio-based Neuro Server Client with server integration.

    This class provides a complete implementation of the Neuro Server Client
    by integrating with an AbstractTrioNeuroServer instance. It delegates
    high-level operations like context management and action selection to
    the server while handling client-specific WebSocket communication.

    Key Features:
        - **Server Integration**: Delegates AI operations to a parent server instance
        - **Weak Reference Management**: Uses weak references to prevent circular references
        - **Enhanced Logging**: Includes client identification in log messages
        - **Action Coordination**: Bridges client actions with server-side AI processing
        - **Structured Concurrency**: Leverages Trio nurseries for async task management

    Architecture:
        - Acts as a bridge between WebSocket clients and the Neuro server
        - Maintains a weak reference to prevent memory leaks
        - Forwards context and action requests to the server for AI processing
        - Handles client-specific state while server manages global AI state

    Attributes:
        _server_ref (weakref.ref[AbstractTrioNeuroServer]): Weak reference to the
            parent server instance. Prevents circular references that could cause
            memory leaks while allowing access to server functionality.

    Lifecycle Management:
        - Server reference is established during initialization
        - Weak reference allows server to be garbage collected independently
        - Dead reference detection prevents operations on destroyed servers
        - Client can outlive server in certain shutdown scenarios

    Note:
        - This is a complete, ready-to-use implementation
        - No abstract methods remain to be implemented by subclasses
        - Server must remain alive for the client to function properly
        - Designed for use within Trio-based server applications

    Example Usage:
        >>> async def handle_websocket_client(request):
        ...     websocket = await request.accept()
        ...     client = TrioNeuroServerClient(websocket, neuro_server)
        ...     try:
        ...         while True:
        ...             await client.read_message()
        ...     except trio_websocket.ConnectionClosed:
        ...         # Client disconnected
        ...         pass

    """

    __slots__ = ("_server_ref",)

    def __init__(
        self,
        websocket: WebSocketConnection,
        server: AbstractTrioNeuroServer,
    ) -> None:
        """Initialize the Trio Neuro Server Client with server integration.

        Sets up the WebSocket communication layer and establishes a weak
        reference to the parent server for AI operation delegation.

        Args:
            websocket (WebSocketConnection): An established trio-websocket
                connection instance ready for message exchange with the game client.
            server (AbstractTrioNeuroServer): The parent Neuro server instance
                that will handle AI operations, context management, and action
                selection for this client.

        Note:
            - Creates a weak reference to the server to prevent circular references
            - Server must remain alive for the client to function properly
            - WebSocket connection must already be established and accepted
            - Parent class initialization sets up action registry and base state

        """
        super().__init__(websocket)
        self._server_ref = weakref.ref(server)

    @property
    def server(self) -> AbstractTrioNeuroServer:
        """Access the parent server instance.

        Dereferences the weak reference to obtain the server instance,
        with validation to ensure the server is still alive.

        Returns:
            AbstractTrioNeuroServer: The parent server instance that handles
                AI operations and coordinates multiple clients.

        Raises:
            ValueError: If the server instance has been garbage collected
                and the weak reference is dead. This indicates the server
                has been destroyed while the client is still active.

        Note:
            - Uses weak reference to prevent circular reference memory leaks
            - Server lifetime is managed independently of client lifetime
            - Dead reference indicates abnormal shutdown or cleanup order
            - Should be checked before any server operations

        Example:
            >>> try:
            ...     server = client.server
            ...     server.add_context(game_title, message, True)
            ... except ValueError:
            ...     print("Server has been destroyed")

        """
        value = self._server_ref()
        if value is None:
            raise ValueError("Reference to server is dead.")
        return value

    def log_warning(self, message: str) -> None:
        """Log a warning message with client identification context.

        Enhances the base logging functionality by including the game title
        and client connection information for better debugging and monitoring.

        Args:
            message (str): The warning message to log. Will be prefixed with
                client identification information including game title and
                remote connection details.

        Behavior:
            - Extracts remote connection information (IP:port or string identifier)
            - Formats message with game title and connection details
            - Delegates actual logging to the parent server's logging system
            - Provides context for debugging multi-client scenarios

        Note:
            - Remote connection format depends on the underlying transport
            - Game title may be None if startup hasn't completed
            - Logging behavior is determined by the server implementation
            - Useful for identifying which client generated warnings

        Example:
            >>> client.log_warning("Action validation failed")
            >>> # Logs: "[MyGame (192.168.1.100:12345)] Action validation failed"

        """
        remote = self.websocket.remote
        if not isinstance(remote, str):
            remote = f"{remote.address}:{remote.port}"
        self.server.log_warning(f"[{self.game_title} ({remote})] {message}")

    def add_context(self, message: str, reply_if_not_busy: bool) -> None:
        """Add contextual information to Neuro's understanding.

        Forwards context messages from the game client to the parent server
        for integration into Neuro's contextual awareness.

        Args:
            message (str): Plaintext description of the current game state
                or event. This information is passed directly to Neuro for
                contextual understanding.
            reply_if_not_busy (bool): Controls Neuro's response behavior:
                - True: Neuro may respond to the message if she's not busy
                - False: Message is added silently without prompting a response

        Note:
            - Context is associated with this client's game title
            - Server coordinates context across multiple clients if needed
            - Message content is passed through unchanged to Neuro
            - Response behavior depends on Neuro's current conversation state

        Example:
            >>> client.add_context("Player entered the forest", True)
            >>> # Neuro receives context and may respond about the forest

        """
        self.server.add_context(self.game_title, message, reply_if_not_busy)

    async def choose_force_action(
        self,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        action_names: frozenset[str],
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        """Delegate action selection to the parent server.

        Forwards force action requests to the server's AI system for
        processing, converting action names to full Action objects.

        Args:
            state (str | None): Current game state description for Neuro's context.
            query (str): Instruction telling Neuro what she should accomplish.
            ephemeral_context (bool): Whether context should persist after completion.
            action_names (frozenset[str]): Set of action names Neuro must choose from.
            priority (ForcePriority): Action force priority level.

        Returns:
            tuple[str, str | None]: Tuple containing:
                - str: Selected action name from the provided set
                - str | None: JSON-stringified action data or None if no data needed

        Behavior:
            - Looks up full Action objects from the client's action registry
            - Passes complete Action objects to the server for AI processing
            - Server handles the actual AI decision-making and data generation
            - Returns the server's choice formatted for client consumption

        Note:
            - All action names must exist in the client's action registry
            - Server receives full Action objects with schemas for validation
            - AI processing happens on the server side, not in the client
            - Game title is automatically included for server context

        Example:
            >>> action_name, data = await client.choose_force_action(
            ...     "Player at crossroads", "Choose direction", False,
            ...     frozenset(["go_north", "go_south"])
            ... )
            >>> # Returns something like ("go_north", '{"speed": "fast"}')

        """
        return await self.server.choose_force_action(
            self.game_title,
            state,
            query,
            ephemeral_context,
            tuple(self.actions[name] for name in action_names),
        )

    async def submit_call_async_soon(  # noqa: D102
        self,
        function: Callable[[], Any],
    ) -> None:
        self.server.handler_nursery.start_soon(function)


class AbstractTrioNeuroServer(metaclass=ABCMeta):
    """Abstract base class for Trio-based Neuro AI servers.

    This class provides the core WebSocket server infrastructure for
    hosting Neuro AI game integration services. It manages client
    connections, handles the WebSocket protocol, and defines the
    interface for AI-powered game interaction capabilities.

    Key Features:
        - **Multi-Client Management**: Handles multiple simultaneous game client connections
        - **Structured Concurrency**: Built on Trio's async framework for reliable task management
        - **WebSocket Server**: Complete WebSocket server implementation with SSL support
        - **AI Integration Interface**: Abstract methods for connecting to Neuro AI systems
        - **Connection Lifecycle**: Automatic client registration, cleanup, and error handling

    Architecture:
        - Serves as the central coordination point for multiple game clients
        - Delegates AI operations to concrete implementations via abstract methods
        - Manages WebSocket connections and protocol handling automatically
        - Provides logging infrastructure for monitoring and debugging

    Attributes:
        clients (dict[str, TrioNeuroServerClient]): Registry of active client
            connections, keyed by remote address (IP:port format). Updated
            automatically as clients connect and disconnect.
        handler_nursery (trio.Nursery): Trio nursery for managing background
            tasks and client operations. Set during server startup and used
            for structured concurrency management.

    Connection Management:
        - Clients are registered by remote address when they connect
        - Connection lifecycle is managed automatically with proper cleanup
        - Failed connections are logged and handled gracefully
        - Multiple clients can be active simultaneously with independent state

    Abstract Methods:
        Subclasses must implement:
        - ``add_context``: Handle contextual information from game clients
        - ``choose_force_action``: Implement AI-driven action selection logic

    Note:
        - This is an abstract base class requiring concrete implementation
        - SSL/TLS support is available but optional
        - Server runs until manually stopped or encounters critical errors
        - Designed for integration with external Neuro AI systems

    Example Usage:
        >>> class MyNeuroServer(AbstractTrioNeuroServer):
        ...     def add_context(self, game_title, message, reply_if_not_busy):
        ...         # Forward to Neuro AI system
        ...         pass
        ...
        ...     async def choose_force_action(self, game_title, state, query, ephemeral_context, actions):
        ...         # Implement AI action selection
        ...         return selected_action_name, action_data
        ...
        >>> server = MyNeuroServer()
        >>> await server.run("localhost", 8080)

    """

    __slots__ = (
        "__weakref__",
        "clients",
        "handler_nursery",
    )

    def __init__(self) -> None:
        """Initialize the abstract Neuro server with default state.

        Sets up the basic server infrastructure including client registry
        and prepares for nursery assignment during server startup.

        Note:
            - Creates empty client registry for connection tracking
            - Handler nursery is assigned during ``run()`` method execution
            - Server is not ready to accept connections until ``run()`` is called

        """
        self.clients: dict[str, TrioNeuroServerClient] = {}
        self.handler_nursery: trio.Nursery

    def log_info(self, message: str) -> None:
        """Log an informational message to the console.

        Args:
            message (str): The informational message to log.

        Note:
            - Uses simple console output with INFO prefix
            - Subclasses can override for more sophisticated logging
            - Useful for tracking server operations and client activity

        """
        print(f"[INFO] {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message to the console.

        Args:
            message (str): The warning message to log.

        Note:
            - Uses simple console output with WARNING prefix
            - Indicates non-critical issues that should be monitored
            - Subclasses can override for more sophisticated logging

        """
        print(f"[WARNING] {message}")

    def log_critical(self, message: str) -> None:
        """Log a critical error message to the console.

        Args:
            message (str): The critical error message to log.

        Note:
            - Uses simple console output with CRITICAL prefix
            - Indicates serious issues that may affect server operation
            - Subclasses can override for more sophisticated logging

        """
        print(f"[CRITICAL] {message}")

    @abstractmethod
    def add_context(
        self,
        game_title: str | None,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        """Add contextual information to the Neuro AI system.

        This abstract method must be implemented by subclasses to handle
        contextual information from game clients and forward it to the
        Neuro AI system for processing.

        Args:
            game_title (str | None): The title of the game providing context.
                None may indicate context from an unidentified or system source.
            message (str): Plaintext description of the current game state or
                event. This information is intended to be passed directly to
                Neuro for contextual understanding.
            reply_if_not_busy (bool): Controls Neuro's response behavior:
                - False: Message is added to context silently without prompting
                  a response from Neuro
                - True: Neuro may respond to the message directly, subject to
                  her current availability and conversation state

        Implementation Requirements:
            - Must forward message content to the Neuro AI system
            - Should handle game title association for multi-client scenarios
            - Must respect the reply_if_not_busy flag for response control
            - Should handle None game titles gracefully

        Note:
            - Message content is passed directly to Neuro without modification
            - Response behavior depends on Neuro's current conversation state
            - Multiple clients may provide context simultaneously
            - Implementation should be thread-safe for concurrent access

        Example Implementation:
            >>> def add_context(self, game_title, message, reply_if_not_busy):
            ...     context_data = {
            ...         "game": game_title,
            ...         "message": message,
            ...         "can_reply": reply_if_not_busy
            ...     }
            ...     self.neuro_api.send_context(context_data)

        """

    @abstractmethod
    async def choose_force_action(
        self,
        game_title: str | None,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        actions: tuple[Action, ...],
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        """Select an action for Neuro to perform from a constrained set.

        This abstract method must be implemented by subclasses to
        provide AI-driven action selection logic when games request
        forced actions.

        Args:
            game_title (str | None): The title of the requesting game. May be
                None if the request comes from an unidentified source.
            state (str | None): Detailed description of the current game state.
                Can be in any format (plaintext, JSON, Markdown, etc.) and is
                intended for direct consumption by the Neuro AI system.
            query (str): Plaintext instruction describing what Neuro should
                accomplish in the current scenario. Passed directly to Neuro
                for decision-making guidance.
            ephemeral_context (bool): Context persistence control:
                - False: State and query information is retained in Neuro's
                  memory after the action selection completes
                - True: State and query are only used during this selection
                  process and are not retained afterward
            actions (tuple[Action, ...]): Immutable sequence of Action objects
                that Neuro must choose from. Each Action contains name,
                description, and optional JSON schema for data validation.
            priority (ForcePriority): Force action priority.

        Returns:
            tuple[str, str | None]: A tuple containing:
                - str: Selected action name, must exactly match the name of one
                  of the provided Action objects
                - str | None: JSON-stringified action data conforming to the
                  action's registered schema, or None if no data is required

        Implementation Requirements:
            - Must return an action name that exists in the provided actions tuple
            - Action data must conform to the selected action's JSON schema
            - Should handle ephemeral context appropriately in the AI system
            - Must process state and query information for AI decision-making

        Note:
            - This method encapsulates the core AI decision-making process
            - Selection should be based on the provided state and query context
            - Action data generation must respect the action's schema constraints
            - Multiple concurrent force action requests may be processed

        Example Implementation:
            >>> async def choose_force_action(self, game_title, state, query, ephemeral_context, actions):
            ...     ai_request = {
            ...         "game": game_title,
            ...         "state": state,
            ...         "instruction": query,
            ...         "ephemeral": ephemeral_context,
            ...         "available_actions": [action.to_dict() for action in actions]
            ...     }
            ...     response = await self.neuro_ai.request_action_selection(ai_request)
            ...     return response["action_name"], response["action_data"]

        """

    async def run(
        self,
        address: str,
        port: int,
        ssl_context: SSLContext | None = None,
    ) -> None:
        """Start the WebSocket server and run until termination.

        Initializes the server infrastructure, starts accepting client
        connections, and runs indefinitely until manually stopped or
        a critical error occurs.

        Args:
            address (str): The network address to bind the server to.
                Use "localhost" for local-only access or "0.0.0.0"
                for all interfaces.
            port (int): The TCP port number to listen on. Must be
                available and not in use by other services.
            ssl_context (SSLContext | None, optional): SSL context for
                HTTPS/WSS encryption. If None, server runs in plain
                HTTP/WS mode. Defaults to None.

        Behavior:
            - Creates a Trio nursery for managing all server tasks
            - Starts the WebSocket server with the provided configuration
            - Accepts and handles client connections indefinitely
            - Performs structured cleanup on shutdown or error

        Raises:
            OSError: If the server cannot bind to the specified address/port.
            Exception: For other critical server startup or runtime errors.
                All exceptions are logged before re-raising.

        Note:
            - This method blocks until the server is shut down
            - SSL context enables secure WebSocket (WSS) connections
            - Server automatically handles client connection lifecycle
            - Uses structured concurrency for reliable resource management

        """
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
        """Process an incoming WebSocket connection request.

        Handles the initial WebSocket handshake and delegates connection
        management to the client connection handler.

        Args:
            request (WebSocketRequest): The incoming WebSocket connection
                request containing client information and connection details.

        Behavior:
            - Extracts client remote address for logging
            - Logs the connection request for monitoring
            - Accepts the WebSocket connection
            - Delegates to ``handle_client_connection`` for lifecycle management

        Note:
            - This method is called automatically by the WebSocket server
            - Connection acceptance happens unconditionally
            - Client filtering should be implemented here if needed
            - Remote address formatting handles both string and socket address types

        """
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
        """Manage the complete lifecycle of a client WebSocket connection.

        Handles client registration, message processing, and cleanup for
        an established WebSocket connection throughout its entire lifetime.

        Args:
            websocket (WebSocketConnection): An accepted WebSocket connection
                ready for bidirectional message exchange with the game client.

        Behavior:
            - Registers the client in the active clients dictionary
            - Creates a TrioNeuroServerClient instance for the connection
            - Processes incoming messages in a continuous loop
            - Automatically handles connection cleanup on disconnection
            - Logs connection events and errors for monitoring

        Connection Lifecycle:
            1. Client registration with remote address as key
            2. Continuous message processing until disconnection
            3. Automatic cleanup of client registry on exit
            4. Exception logging for debugging connection issues

        Exception Handling:
            - All exceptions are logged with full traceback
            - Connection is automatically cleaned up via context manager
            - Client is removed from registry when connection ends
            - Exceptions are re-raised for proper error propagation

        Note:
            - Method runs until client disconnects or error occurs
            - Uses WebSocket context manager for automatic cleanup
            - Client registry is updated automatically
            - Message processing happens in ``TrioNeuroServerClient.read_message``

        Example Flow:
            >>> # Client connects -> logged and registered
            >>> # Client sends messages -> processed continuously
            >>> # Client disconnects -> logged and cleaned up

        """
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


class ConsoleInteractiveNeuroServer(AbstractTrioNeuroServer):
    """Console-based interactive implementation of Neuro Server for development and testing.

    This concrete implementation provides a human-operated interface for
    testing Neuro API integration without requiring a full AI system.
    It uses console input/output to simulate Neuro's decision-making
    process, making it ideal for development, debugging, and demonstration.

    Key Features:
        - **Interactive Console Interface**: Human operator makes decisions via console
        - **Development Testing**: Test game clients without full AI infrastructure
        - **Action Visualization**: Clear display of available actions and context
        - **Schema Support**: Handles JSON schema validation and data input
        - **Real-time Feedback**: Immediate console output for context messages

    Use Cases:
        - Development and testing of game client integrations
        - Debugging WebSocket communication protocols
        - Demonstrating Neuro API capabilities to stakeholders
        - Educational purposes for understanding the Neuro system

    Limitations:
        - Requires human operator interaction for all decisions
        - Not suitable for production or automated scenarios
        - Console-based interface may not scale for complex interactions
        - No persistent state or learning capabilities

    Note:
        - This implementation is synchronous from the operator's perspective
        - Trio checkpoints are used to maintain cooperative multitasking
        - All AI decision-making is replaced with human console interaction
        - Suitable only for development and demonstration environments

    Example Usage:
        >>> server = ConsoleInteractiveNeuroServer()
        >>> await server.run("localhost", 8000)
        >>> # Server will prompt operator for all AI decisions via console

    """

    __slots__ = ("console_command_lock",)

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self.console_command_lock = trio.Lock()

    def add_context(
        self,
        game_title: str | None,
        message: str,
        reply_if_not_busy: bool,
    ) -> None:
        """Display context information to the console operator.

        Prints contextual information from game clients to the console,
        allowing the human operator to understand the current game state
        and events.

        Args:
            game_title (str | None): The title of the game providing context.
                Displayed to help the operator track multiple clients.
            message (str): The contextual message describing game state or
                events. Displayed directly to the console operator.
            reply_if_not_busy (bool): Flag indicating whether Neuro should
                respond to this context. Displayed for operator awareness
                but does not affect behavior in this implementation.

        Behavior:
            - Prints context message with clear formatting
            - Shows the reply_if_not_busy flag for operator information
            - Uses distinct [CONTEXT] prefix for easy identification
            - No interactive response required from operator

        Note:
            - This method provides information only, no decisions required
            - Multiple context messages may appear rapidly during gameplay
            - Operator can observe game state changes through these messages
            - The reply_if_not_busy flag is informational in this implementation

        Example Output:
            >>> [CONTEXT] Player entered the dark forest
            >>> reply_if_not_busy = True

        """
        print(f"\n[CONTEXT] {message}\n{reply_if_not_busy = }")

    def show_help(self) -> None:
        """Display help information for console commands."""
        self.log_info("Available Commands:")
        self.log_info(
            "send <client_id> <action_name> - Send action to specific client",
        )
        self.log_info(
            "list - Show all connected clients and their available actions",
        )
        self.log_info("help - Show this help message")
        self.log_info("<enter> - Continue without sending actions")

    def list_client_actions(self, client: TrioNeuroServerClient) -> None:
        """Display available actions for client."""
        self.log_info(f"Game: {client.game_title}")
        if client.actions:
            self.log_info("  Available actions:")
            for action_name, action in client.actions.items():
                self.log_info(f"    {action_name}: {action.description}")
        else:
            self.log_info("  No actions registered")

    def ask_action_json(self, action: Action) -> str | None:
        """Prompt console operator to provide optional data for an action.

        Args:
            action (Action): Action to display info about.

        Returns:
            str | None: Json blob string or None if not entered.

        """
        json_blob: str | None = None
        if action.schema is not None:
            print(
                f"{action.name}\n\t{action.description}\n\n{action.schema = }\n",
            )
            if input("Do json blob? (y/N) > ").lower() == "y":
                json_blob = input("Json blob > ")
        return json_blob

    async def console_input_command(
        self,
        client: TrioNeuroServerClient,
    ) -> None:
        """Have user input command from console.

        Args:
            client (TrioNeuroServerClient): Client to send command to.

        """
        async with self.console_command_lock:
            while True:
                try:
                    await trio.sleep(0.1)
                    command = input("Enter command > ").strip()
                    if not command:
                        break

                    parts = command.split()
                    if not parts:
                        continue

                    cmd = parts[0].lower()

                    if cmd == "help":
                        self.show_help()
                    elif cmd == "list":
                        self.list_client_actions(client)
                    elif cmd == "send" and len(parts) >= 1:
                        action_name = parts[1]

                        action = client.get_action(action_name)

                        if action is None:
                            self.log_critical(
                                f"Action '{action_name}' not available for client",
                            )
                            continue

                        json_data = self.ask_action_json(action)
                        self.log_info(
                            f"Sending action '{action_name}' to client...",
                        )

                        success, message = await client.submit_action(
                            action_name,
                            json_data,
                        )

                        if success:
                            self.log_info(
                                f"Action {action_name!r} completed successfully",
                            )
                            if message:
                                self.log_info(f"  Result: {message}")
                        else:
                            self.log_info(f"Action {action_name!r} failed")
                            if message:
                                self.log_info(f"  Error: {message}")
                    else:
                        self.log_warning(
                            "Invalid command. Type 'help' for available commands.",
                        )
                except Exception as exc:
                    self.log_critical(f"Error processing command: {exc}")

    def start_console_input_command(
        self,
        client: TrioNeuroServerClient,
    ) -> None:
        """Start console input command if not already active."""
        if self.console_command_lock.locked():
            return
        self.handler_nursery.start_soon(self.console_input_command, client)

    async def handle_client_connection(  # noqa: D102
        self,
        websocket: WebSocketConnection,
    ) -> None:
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
                    # Start console input command if no messages for 8 seconds
                    with trio.move_on_after(8):
                        await client.read_message()
                        continue
                    self.start_console_input_command(client)

        except BaseException:
            traceback.print_exc()
            raise

    async def choose_force_action(
        self,
        game_title: str | None,
        state: str | None,
        query: str,
        ephemeral_context: bool,
        actions: tuple[Action, ...],
        priority: ForcePriority = ForcePriority.LOW,
    ) -> tuple[str, str | None]:
        """Prompt console operator to select an action and provide data.

        Presents the force action scenario to the console operator and
        prompts for action selection and optional JSON data input.

        Args:
            game_title (str | None): The requesting game's title, displayed
                for operator context and multi-client tracking.
            state (str | None): Current game state description, displayed
                to help the operator understand the scenario.
            query (str): Instruction describing what should be accomplished,
                displayed to guide the operator's decision.
            ephemeral_context (bool): Context persistence flag, displayed
                for operator information.
            actions (tuple[Action, ...]): Available actions the operator
                must choose from, displayed with descriptions.

        Returns:
            tuple[str, str | None]: Tuple containing:
                - str: Name of the action selected by the operator
                - str | None: JSON data provided by the operator, or None
                  if no data was provided or the action has no schema

        Interactive Process:
            1. Displays game context (title, state, query)
            2. Shows numbered list of available actions with descriptions
            3. Prompts operator to select action by number
            4. If selected action has a schema, optionally prompts for JSON data
            5. Returns the selected action name and data

        Behavior:
            - Uses Trio checkpoints to maintain cooperative multitasking
            - Validates operator input (action number must be valid)
            - Shows action schema when prompting for JSON data
            - Allows operator to skip JSON data input even for schema actions

        Note:
            - Blocking operation that waits for operator input
            - Input validation is minimal - operator must provide valid numbers
            - JSON data validation is not performed by this method
            - Multiple concurrent force actions will be processed sequentially

        Example Interaction:
            >>> [Force Action] game_title = 'MyGame'
            >>> state = 'Player at crossroads'
            >>> query = 'Choose direction to explore'
            >>> Options:
            >>> 1: go_north
            >>>     Move towards the mountain path
            >>> 2: go_south
            >>>     Head toward the village
            >>> Action > 1
            >>> action.schema = {...}
            >>> Do json blob? (y/N) > y
            >>> Json blob > {"speed": "fast"}

        """
        action_str = "\n".join(
            f"{idx + 1}: {action.name}\n\t{action.description}"
            for idx, action in enumerate(actions)
        )

        print(
            f"\n\n[Force Action] {game_title = }\n{state = }\n{query = }\n{priority = }\nOptions:\n{action_str}",
        )
        action = actions[int(input("Action > ")) - 1]

        # Handle other tasks
        await trio.lowlevel.checkpoint()

        json_blob = self.ask_action_json(action)
        return action.name, json_blob


async def run_development_server() -> None:
    """Start the development server with exception handling.

    Initializes and runs the console interactive Neuro server for
    development and testing purposes. Includes proper exception handling
    and logging.

    Behavior:
        - Creates a ConsoleInteractiveNeuroServer instance
        - Runs server on localhost:8000 for local development
        - Catches and logs any exception groups that occur
        - Provides a clean entry point for development testing

    Note:
        - Server runs indefinitely until manually stopped
        - Uses localhost binding for security in development
        - Exception logging helps debug server and client issues

    """
    server = ConsoleInteractiveNeuroServer()
    try:
        await server.run("localhost", 8000)
    except BaseExceptionGroup:
        traceback.print_exc()


def run() -> None:
    """Run the development server program.

    Main entry point that displays program information and starts the
    Trio-based development server. Provides a clean interface for
    launching the interactive Neuro server.

    Behavior:
        - Displays program title, version, and author information
        - Starts the Trio event loop with the development server
        - Handles the complete server lifecycle from start to finish

    Note:
        - This function blocks until the server is terminated
        - Uses Trio.run for proper async context management
        - Suitable for use as a main program entry point

    """
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
    trio.run(run_development_server)


if __name__ == "__main__":
    run()
