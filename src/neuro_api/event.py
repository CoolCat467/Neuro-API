"""Event - Neuro API Component."""

# Programmed by CoolCat467

from __future__ import annotations

# Event - Neuro API Component
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

__title__ = "event"
__author__ = "CoolCat467"
__license__ = "GNU Lesser General Public License Version 3"


from typing import TYPE_CHECKING

from libcomponent.component import Component, Event

from neuro_api.api import AbstractNeuroAPI, NeuroAction

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from neuro_api.command import Action


class AbstractNeuroAPIComponent(Component, AbstractNeuroAPI):
    """Abstract Neuro API Component.

    Combines Component and AbstractNeuroAPI functionality for Neuro game
    interactions.
    """

    # __slots__ = ()

    def __init__(
        self,
        component_name: str,
        game_title: str,
    ) -> None:
        """Initialize Neuro API Component.

        Args:
            component_name (str): Name of the component.
            game_title (str): Title of the game being managed.

        """
        Component.__init__(self, component_name)
        AbstractNeuroAPI.__init__(self, game_title)

    def _send_result_wrapper(
        self,
        handler: Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]],
    ) -> Callable[[Event[NeuroAction]], Awaitable[None]]:
        """Return wrapper to handle neuro action event.

        Creates a wrapper function that calls the handler and sends
        the action result back to Neuro.

        Args:
            handler (Callable): A function that processes a NeuroAction
                and returns a tuple of (success, message).

        Returns:
            Callable: A wrapped handler function that automatically
            sends action results.

        """

        async def wrapper(event: Event[NeuroAction]) -> None:
            """Send action result with return value from handler."""
            neuro_action = event.data
            success, message = await handler(neuro_action)
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

        Args:
            action_handlers (Iterable): An iterable of tuples containing
                (Action, NeuroAction event handler function).

        Raises:
            AttributeError: If this component is not bound to a manager.
            ValueError: If action name has invalid characters or bad
                schema key.

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
                Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]],
            ],
        ],
    ) -> None:
        """Register a Neuro Action and associated handler function.

        Args:
            action_handlers (Iterable): An iterable of Action and
                callback function pairs.

        Details:
            Callback functions accept `NeuroAction` and return if action
            is successful and optional associated small context message
            if successful. If unsuccessful, 2nd value must be an error
            message.

        """
        await self.register_neuro_actions_raw_handler(
            (action, self._send_result_wrapper(handler))
            for action, handler in action_handlers
        )

    async def register_temporary_actions_group(
        self,
        grouped_action_handlers: Iterable[
            tuple[
                Action,
                Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]],
            ],
        ],
    ) -> tuple[str, ...]:
        """Register a group of temporary Neuro Actions and associated handler functions.

        This method allows registering a group of actions that will be automatically
        unregistered if any action in the group is successfully completed.

        Args:
            grouped_action_handlers (Iterable): An iterable of tuples containing
                (Action, callback function) pairs.

        Details:
            Callback functions accept `NeuroAction` and return:
            - A boolean indicating action success
            - An optional small context message if successful
            - An error message if unsuccessful

            If any handler in the group is successful, all actions in this group
            will be automatically unregistered.

        Returns:
            tuple[str, ...]: A tuple of names for all actions in this group,
            which can be used with `send_force_action`.

        Example:
            Typical usage involves creating a group of related actions that
            should be removed once any of them succeed.

        """
        group = tuple(grouped_action_handlers)
        group_action_names = [action.name for action, _handler in group]

        def unregister_wrapper(
            handler: Callable[
                [NeuroAction],
                Awaitable[tuple[bool, str | None]],
            ],
        ) -> Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]]:
            """Call handler, then unregisters actions group before passing on result."""

            async def wrapper(
                neuro_action: NeuroAction,
            ) -> tuple[bool, str | None]:
                success, message = await handler(neuro_action)
                if success:
                    await self.unregister_actions(group_action_names)
                    for action_name in group_action_names:
                        self.unregister_handler_type(f"neuro_{action_name}")
                return success, message

            return wrapper

        await self.register_neuro_actions(
            (action, unregister_wrapper(handler)) for action, handler in group
        )

        return tuple(group_action_names)

    async def register_temporary_actions(
        self,
        action_handlers: Iterable[
            tuple[
                Action,
                Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]],
            ],
        ],
    ) -> None:
        """Register temporary Neuro Actions and associated handler functions.

        Args:
            action_handlers (Iterable): An iterable of tuples containing
                (Action, callback function) pairs.

        Details:
            Callback functions accept `NeuroAction` and return:
            - A boolean indicating action success
            - An optional small context message if successful
            - An error message if unsuccessful

            If an action is successful, it will be automatically unregistered.

        Note:
            This method is useful for one-time or short-lived actions
            that should be removed after successful completion.

        """

        def unregister_wrapper(
            handler: Callable[
                [NeuroAction],
                Awaitable[tuple[bool, str | None]],
            ],
        ) -> Callable[[NeuroAction], Awaitable[tuple[bool, str | None]]]:
            """Call handler, then unregisters action before passing on result."""

            async def wrapper(
                neuro_action: NeuroAction,
            ) -> tuple[bool, str | None]:
                success, message = await handler(neuro_action)
                if success:
                    await self.unregister_actions([neuro_action.name])
                    self.unregister_handler_type(f"neuro_{neuro_action.name}")
                return success, message

            return wrapper

        await self.register_neuro_actions(
            (action, unregister_wrapper(handler))
            for action, handler in action_handlers
        )

    async def handle_action(self, neuro_action: NeuroAction) -> None:
        """Handle an action request from Neuro.

        Processes a Neuro action by raising a corresponding event
        for registered handlers.

        Args:
            neuro_action (NeuroAction): The action request received from Neuro.

        Raises:
            ValueError: If no handler is registered for the specific
                action name.

        Note:
            - The event name is the action name prefixed with 'neuro_'.

        """
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
