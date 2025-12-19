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
__version__ = "3.1.1"
__license__ = "GNU Lesser General Public License Version 3"


from abc import abstractmethod
from typing import TYPE_CHECKING, NamedTuple

from neuro_api import command
from neuro_api.client import AbstractNeuroAPIClient

if TYPE_CHECKING:
    from collections.abc import Sequence

    from neuro_api.json_schema_types import SchemaObject


class NeuroAction(NamedTuple):
    """Representation of a Neuro Action with its associated details.

    A NamedTuple that encapsulates the essential information for an
    action in the Neuro game interaction system.

    Attributes:
        id_ (str): Unique identifier for the action.
            The trailing underscore is used to avoid conflicts with
            Python's built-in `id` keyword.
        name (str): Name of the action to be performed.
        data (str | None): Optional additional data associated with
            the action. Can be None if no additional information
            is required.

    """

    id_: str
    name: str
    data: str | None


class AbstractNeuroAPI(AbstractNeuroAPIClient):
    """Abstract base class for the Neuro Game Interaction API.

    Provides a foundational interface for managing game actions and
    interactions with the Neuro system. This class is designed to be
    subclassed by specific game implementations.

    Attributes:
        game_title (str): The title or name of the game being integrated.

    Note:
        This is an abstract base class that requires implementation
        of specific game interaction methods in subclasses.

    """

    # __slots__ = ("_currently_registered", "game_title")

    def __init__(
        self,
        game_title: str,
    ) -> None:
        """Initialize the Neuro API for a specific game.

        Args:
            game_title (str): The name of the game to be integrated
                with the Neuro system.

        Note:
            Initializes the internal action registry to track
            currently registered actions.

        """
        self.game_title = game_title
        # Keep track of currently registered actions to be able to handle
        # `actions/reregister_all` command.
        self._currently_registered: dict[
            str,
            tuple[str, SchemaObject | None],
        ] = {}

    def get_registered(self) -> tuple[str, ...]:
        """Return the names of all currently registered actions.

        Returns:
            tuple[str, ...]: A tuple containing the names of all
            actions currently registered in the Neuro API.

        Note:
            This method provides a snapshot of registered actions
            at the time of calling.

        """
        return tuple(self._currently_registered)

    async def send_startup_command(self) -> None:
        """Send startup command to initialize the game with Neuro.

        This method sends the initial message to the Neuro system when
        a game starts. It serves two critical purposes:
        - Inform Neuro that the game is now running
        - Clear and reset any previously registered actions

        Note:
            This should be the very first message sent after game
            initialization.

        Raises:
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the startup command.

        Warning:
            Sends a command that clears all previously registered actions
            for this game, performing a complete action registry reset.

        """
        await self.send_command_data(command.startup_command(self.game_title))

    async def send_context(self, message: str, silent: bool = True) -> None:
        """Send a contextual message to Neuro about the game state.

        Allows communication of game events or state information to Neuro
        without necessarily requiring an immediate response.

        Args:
            message (str): A plaintext description of what is happening
                in the game. **This information will be directly received
                by Neuro.**
            silent (bool, optional): Controls Neuro's response behaviour:
                - If True (default): Message is added to context silently
                  without prompting a response.
                - If False: Neuro _might_ respond directly, unless she is
                  busy talking to someone else or to chat.

        Raises:
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the context command.

        Note:
            This method provides a flexible way to keep Neuro informed
            about game events without disrupting ongoing interactions.

        """
        await self.send_command_data(
            command.context_command(self.game_title, message, silent),
        )

    async def register_actions(self, actions: list[command.Action]) -> None:
        """Register a list of actions with Neuro.

        Validates and registers multiple actions for Neuro to use during
        game interaction. This method performs two key operations:
        - Validates each action's name and schema
        - Sends the actions to Neuro for registration

        Args:
            actions (list[command.Action]): A list of actions to be registered.
                If an action is already registered, it will be ignored.

        Raises:
            ValueError: If any action:
                - Contains invalid characters in its name
                - Has an invalid schema key
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the action registration.

        Note:
            - Each action is validated before registration
            - Previously registered actions with the same name will not
              be overwritten
            - The method maintains an internal registry of registered actions

        """
        for action in actions:
            command.check_action(action)

            self._currently_registered[action.name] = (
                action.description,
                action.schema,
            )
        await self.send_command_data(
            command.actions_register_command(self.game_title, actions),
        )

    async def unregister_actions(self, action_names: Sequence[str]) -> None:
        """Unregister specified Neuro actions.

        Removes actions from both the internal registry and Neuro's
        action set, preventing these actions from being used in future
        interactions.

        Args:
            action_names (Sequence[str]): The names of the actions to
                unregister. Attempting to unregister an action that
                isn't registered will not cause any errors.

        Raises:
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the action unregistration.

        Note:
            - No error is raised for non-existent actions

        """
        for action_name in action_names:
            self._currently_registered.pop(action_name, None)
        await self.send_command_data(
            command.actions_unregister_command(self.game_title, action_names),
        )

    async def send_force_action(
        self,
        state: str,
        query: str,
        action_names: Sequence[str],
        ephemeral_context: bool = False,
        priority: command.ForcePriority = command.ForcePriority.LOW,
    ) -> None:
        """Force Neuro to execute an action with specific context.

        Sends a command to Neuro that compels her to choose and execute
        one of the specified actions, providing detailed game state and
        action instructions.

        Args:
            state (str): An arbitrary string describing the current game
                state. Can be plaintext, JSON, Markdown, or any other
                format. **This information will be directly received by Neuro.**
            query (str): A plaintext message instructing Neuro on her
                current task (e.g., `"It is now your turn. Please perform
                an action. If you want to use any items, you should use
                them before picking up the shotgun."`). **This information
                will be directly received by Neuro.**
            action_names (Sequence[str]): Names of actions Neuro can choose
                from during this force action.
            ephemeral_context (bool, optional): Controls context persistence:
                - If False (default): The `state` and `query` context will
                  be remembered after actions force completion.
                - If True: Neuro will only remember the context during the
                  actions force.
            priority (command.ForcePriority):
                Determines how urgently Neuro should respond to the
                action force when she is speaking. If Neuro is not
                speaking, this setting has no effect. The default is
                `command.ForcePriority.LOW`, which will cause Neuro to
                wait until she finishes speaking before responding.
                `command.ForcePriority.MEDIUM` causes her to finish her
                current utterance sooner. `command.ForcePriority.HIGH`
                prompts her to process the action force immediately,
                shortening her utterance and then responding.
                `command.ForcePriority.CRITICAL` will interrupt her
                speech and make her respond at once. Use
                `command.ForcePriority.CRITICAL` with caution, as it may
                lead to abrupt and potentially jarring interruptions.

        Raises:
            ValueError: If any specified action name is not currently
                registered.
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the action force command.

        Warning:
            - Neuro can only handle one action force at a time.
            - Sending an action force while another is in progress
              will cause problems.

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
                priority,
            ),
        )

    async def send_action_result(
        self,
        id_: str,
        success: bool,
        message: str | None = None,
    ) -> None:
        """Report the result of a Neuro-initiated action.

        Communicates the outcome of an action to Neuro, allowing her to
        proceed with her decision-making process. This method is critical
        for maintaining the flow of game interactions.

        Args:
            id_ (str): The unique identifier of the action being reported.
                This ID is directly obtained from the original action message.
            success (bool): Indicates the action's outcome:
                - If True: Action was successfully executed.
                - If False: Action failed. **Note:** If this action is part
                  of an actions force, Neuro will immediately retry the
                  entire actions force.
            message (str, optional): A descriptive message about the action's
                execution:
                - For unsuccessful actions: Should be an error message.
                - For successful actions: Can be empty or provide a _small_
                  context about the action (e.g., `"Remember to not share
                  this with anyone."`).
                **This information will be directly received by Neuro.**

        Raises:
            UnicodeDecodeError: If the command data cannot be decoded
                (highly unlikely).
            orjson.JSONEncodeError: If unable to encode the JSON data
                for the action result.

        Warning:
            - Until an action result is sent, Neuro will be waiting
              and unable to proceed.
            - Send this method call as soon as possible after action
              validation, preferably before in-game execution.

        Note:
            To prevent automatic retrying of a failed action:
            - Set `success` to True
            - Provide an error message in the `message` field

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

        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself. As such, most games
        will not need to implement this.

        This should be sent as a response to a graceful or an imminent
        shutdown request, after progress has been saved. After this is
        sent, Neuro will close the game herself by terminating the
        process, so to reiterate you must definitely ensure that
        progress has already been saved.

        Raises:
            UnicodeDecodeError: If data is unable to be decoded
                (though this is unlikely to happen).
            orjson.JSONEncodeError: If unable to encode JSON data.

        """
        await self.send_command_data(
            command.shutdown_ready_command(self.game_title),
        )

    @abstractmethod
    async def handle_action(self, action: NeuroAction) -> None:
        """Handle an Action request from Neuro.

        Args:
            action (NeuroAction): Parsed Neuro action request data.

        Warning:
            Should call ``send_action_result`` with this action's id as
            soon as scheduling action processing is complete, or else
            Neuro will be stuck frozen, waiting.

        """

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

        Args:
            wants_shutdown (bool): Whether the game should shutdown at
                the next graceful shutdown point.
                - If True: Shutdown is requested
                - If False: Cancel the prior shutdown request

        Warning:
            Please don't actually close the game, just quit to main
            menu. Neuro will close the game herself.

        Note:
            Base implementation sends that shutdown is ready.

        """
        if wants_shutdown:
            await self.send_shutdown_ready()

    async def handle_immediate_shutdown(self) -> None:
        """Handle immediate shutdown alert from Neuro.

        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself. As such, most games
        will not need to implement this.

        This message will be sent when the game needs to be shutdown
        immediately. You have only a handful of seconds to save as much
        progress as possible. After you have saved, you can send back a
        shutdown ready message.

        Warning:
            Please don't actually close the game, just save the current
            progress that can be saved. Neuro will close the game
            herself.

        Note:
            Base implementation sends that shutdown is ready.

        """
        await self.send_shutdown_ready()

    async def read_message(self) -> None:
        """Read message from Neuro websocket.

        You should call this function in a loop as long as the websocket
        is still connected.

        Automatically handles `actions/reregister_all` commands.

        Calls ``handle_graceful_shutdown_request`` and
        ``handle_immediate_shutdown`` for graceful and immediate
        shutdown requests respectively.

        Calls ``handle_action`` for `action` commands.

        Calls ``handle_unknown_command`` for any other command.

        Raises:
            ValueError: If extra keys in action command data or
                missing keys in action command data.
            TypeError: If action command key type mismatch

        Note:
            Does not catch any exceptions ``read_raw_server_message`` raises.

        """
        # Read message from server
        command_type, data = await self.read_raw_server_message()
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
                        ) in self._currently_registered.items()
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
