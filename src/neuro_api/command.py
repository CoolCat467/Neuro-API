"""Command - Neuro API Commands."""

# Programmed by CoolCat467

from __future__ import annotations

# Command - Neuro API Commands
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

__title__ = "command"
__author__ = "CoolCat467"
__license__ = "GNU Lesser General Public License Version 3"


import sys
from types import GenericAlias
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    NamedTuple,
    TypedDict,
    TypeVar,
    cast,
    get_type_hints,
)

import orjson
from typing_extensions import NotRequired, is_typeddict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

T = TypeVar("T")

ACTION_NAME_ALLOWED_CHARS: Final = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789_-",
)

# See https://github.com/VedalAI/neuro-game-sdk/blob/main/API/SPECIFICATION.md#action
INVALID_SCHEMA_KEYS: Final = frozenset(
    {
        "$anchor",
        "$comment",
        "$defs",
        "$dynamicAnchor",
        "$dynamicRef",
        "$id",
        "$ref",
        "$schema",
        "$vocabulary",
        "additionalProperties",
        "allOf",
        "anyOf",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
        "dependentRequired",
        "dependentSchemas",
        "deprecated",
        "description",
        "else",
        "if",
        "maxProperties",
        "minProperties",
        "not",
        "oneOf",
        "patternProperties",
        "readOnly",
        "then",
        "title",
        "unevaluatedItems",
        "unevaluatedProperties",
        "writeOnly",
    },
)


class Action(NamedTuple):
    """Registerable command that Neuro can execute whenever she wants.

    Name should be a unique identifier. This should be a lowercase
    string, with words separated by underscores or dashes (e.g.
    "join_friend_lobby", "use_item").

    Description should be a plaintext description of what this action
    does. This information will be directly received by Neuro.

    Schema is a valid simple JSON schema object that describes how the
    response data should look like. If your action does not have any
    parameters, you can omit this field or set it to {}. This
    information will be directly received by Neuro.
    """

    name: str
    description: str
    schema: dict[str, object] | None = None


def check_invalid_keys_recursive(
    sub_schema: dict[str, Any],
) -> list[str]:
    """Recursively checks for invalid keys in the schema.

    Returns a list of invalid keys that were found.

    Copied from neuro-api-tony/src/neuro_api_tony/api.py
    found at https://github.com/Pasu4/neuro-api-tony,
    which is licensed under the MIT License.
    """
    invalid_keys = []

    for key, value in sub_schema.items():
        if key in INVALID_SCHEMA_KEYS:
            invalid_keys.append(key)
        elif isinstance(value, (str, int, bool)):
            pass
        elif isinstance(value, dict):
            invalid_keys.extend(check_invalid_keys_recursive(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    invalid_keys.extend(
                        check_invalid_keys_recursive(item),
                    )
        else:
            raise ValueError(
                f"Unhandled schema value type {type(value)!r} ({value!r})",
            )
    return invalid_keys


def format_command(
    command: str,
    game: str,
    data: Mapping[str, object] | None = None,
) -> bytes:
    """Return json bytes blob from command details.

    Arguments:
    - `command`: The websocket command.
    - `game`: The game name.
        This is used to identify the game. It should _always_ be the
        same and should not change. You should use the game's display
        name, including any spaces and symbols (e.g. `"Buckshot
        Roulette"`).
    - `data`: The command data.
        This object is different depending on which command you are
        sending/receiving, and some commands may not have any data, in
        which case this object will be either `undefined` or `{}`.

    """
    payload: dict[str, Any] = {
        "command": command,
        "game": game,
    }
    if data is not None:
        payload["data"] = data
    try:
        return orjson.dumps(payload)
    except TypeError as exc:
        if sys.version_info >= (3, 11):  # pragma: nocover
            exc.add_note(f"{payload = }")
        raise


def startup_command(game: str) -> bytes:
    """Return formatted startup command.

    This message should be sent as soon as the game starts, to let
    Neuro know that the game is running.

    This message clears all previously registered actions for this game
    and does initial setup, and as such should be the very first message
    that you send.
    """
    return format_command("startup", game)


def context_command(
    game: str,
    message: str,
    silent: bool = True,
) -> bytes:
    """Return formatted context command.

    This message can be sent to let Neuro know about something that is
    happening in game.

    Arguments:
    - `message`:
        A plaintext message that describes what is happening in the
        game. **This information will be directly received by Neuro.**
    - `silent`:
        If True, the message will be added to Neuro's context without
        prompting her to respond to it. If False, Neuro _might_
        respond to the message directly, unless she is busy talking to
        someone else or to chat.

    """
    return format_command(
        "context",
        game,
        {"message": message, "silent": silent},
    )


def actions_register_command(
    game: str,
    actions: list[Action],
) -> bytes:
    """Return formatted action/register command.

    This message registers one or more actions for Neuro to use.

    actions:
        A list of actions to be registered. If you try to register an
        action that is already registered, it will be ignored.
    """
    assert actions, "Must register at least one action."
    return format_command(
        "actions/register",
        game,
        {"actions": [action._asdict() for action in actions]},
    )


def actions_unregister_command(
    game: str,
    action_names: Sequence[str],
) -> bytes:
    """Return formatted action/unregister command.

    This message unregisters one or more actions, preventing Neuro from
    using them anymore.

    action_names:
        The names of the actions to unregister. If you try to unregister
        an action that isn't registered, there will be no problem.
    """
    assert action_names, "Must unregister at least one action."
    return format_command(
        "actions/unregister",
        game,
        {"action_names": list(action_names)},
    )


def actions_force_command(
    game: str,
    state: str,
    query: str,
    action_names: Sequence[str],
    ephemeral_context: bool = False,
) -> bytes:
    """Return formatted actions/force command.

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

    """
    assert action_names, "Must force at least one action name."
    payload: dict[str, object] = {
        "state": state,
        "query": query,
        "action_names": list(action_names),
    }
    if ephemeral_context:
        payload["ephemeral_context"] = True

    return format_command(
        "actions/force",
        game,
        payload,
    )


def actions_result_command(
    game: str,
    id_: str,
    success: bool,
    message: str | None = None,
) -> bytes:
    """Return formatted action/result command.

    This message needs to be sent as soon as possible after an action is
    validated, to allow Neuro to continue.

    Until you send an action result, Neuro will just be waiting for the
    result of her action!
    Please make sure to send this as soon as possible.
    It should usually be sent after validating the action parameters,
    before it is actually executed in-game

    Parameters
    ----------
    - `id`:
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

    """
    payload = {
        "id": id_,
        "success": success,
    }
    if message is not None:
        payload["message"] = message
    elif not success:
        raise ValueError(
            "Message can only be omitted if successful, otherwise should be error message.",
        )
    return format_command(
        "action/result",
        game,
        payload,
    )


def shutdown_ready_command(game: str) -> bytes:
    """Return formatted shutdown/ready command.

    This is part of the game automation API, which will only be used for
    games that Neuro can launch by herself. As such, most games will not
    need to use implement this.

    This message should be sent as a response to a graceful or an
    imminent shutdown request, after progress has been saved. After this
    is sent, Neuro will close the game herself by terminating the
    process, so to reiterate you must definitely ensure that progress
    has already been saved.
    """
    return format_command(
        "shutdown/ready",
        game,
    )


def convert_parameterized_generic(generic: GenericAlias | T) -> T | type:
    """Return origin type of aliases."""
    if isinstance(generic, GenericAlias):
        return cast("type", generic.__origin__)
    if repr(generic).startswith("typing.NotRequired[") or repr(
        generic,
    ).startswith(
        "typing_extensions.NotRequired[",
    ):  # pragma: nocover
        return generic.__args__[0]  # type: ignore
    return generic


def check_typed_dict(data: Mapping[str, object], typed_dict: type[T]) -> T:
    """Ensure data matches TypedDict definition. Return data as given typed dict.

    Raises ValueError if extra keys in data or missing keys in data.
    Raises TypeError on key type mismatch.

    Will not work properly for nested types.
    """
    assert is_typeddict(typed_dict)
    required = typed_dict.__required_keys__  # type: ignore[attr-defined]

    extra = set(data) - required
    if extra:
        extra_str = ", ".join(map(repr, extra))
        raise ValueError(f"Following extra keys were found: {extra_str}")

    full_annotations = get_type_hints(typed_dict, include_extras=True)

    optional = {
        k
        for k, v in full_annotations.items()
        if (
            repr(v).startswith("typing.NotRequired[")
            or repr(v).startswith("typing_extensions.NotRequired[")
        )
    }
    required -= optional

    annotations = get_type_hints(typed_dict)

    for key in required:
        if key not in data:
            raise ValueError(f"{key!r} is missing (type {annotations[key]!r})")
        if not isinstance(
            data[key],
            convert_parameterized_generic(annotations[key]),
        ):
            raise TypeError(
                f"{data[key]!r} (key {key!r}) is not instance of {annotations[key]!r}",
            )

    for key in optional:
        if (
            key in data
            and data is not None
            and not isinstance(
                data[key],
                convert_parameterized_generic(annotations[key]),
            )
        ):
            raise TypeError(
                f"{data[key]!r} (key {key!r}) is not instance of {annotations[key]!r}",
            )

    return typed_dict(data)  # type: ignore[call-arg]


class IncomingActionMessageSchema(TypedDict):
    """Incoming 'action' command message field.

    Data field from
    https://github.com/VedalAI/neuro-game-sdk/blob/main/API/SPECIFICATION.md#action-1
    """

    id: str
    name: str
    data: NotRequired[str]


def check_action(action: Action) -> None:
    """Check to make sure action to register is valid.

    Raises ValueError if action name has invalid characters or bad
    schema key.
    """
    name_bad_chars = set(action.name) - ACTION_NAME_ALLOWED_CHARS
    if name_bad_chars:
        raise ValueError(
            f"Following invalid characters found in name {action.name!r}: {name_bad_chars}",
        )

    if action.schema is not None:
        bad_schema_keys = check_invalid_keys_recursive(action.schema)
        if bad_schema_keys:
            raise ValueError(
                f"Following invalid keys found in schema: {bad_schema_keys} ({action.name = })",
            )
