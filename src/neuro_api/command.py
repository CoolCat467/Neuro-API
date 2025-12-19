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
from enum import Enum
from types import GenericAlias, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Literal,
    NamedTuple,
    TypedDict,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from warnings import warn

import orjson
from typing_extensions import NotRequired, is_typeddict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from neuro_api.json_schema_types import SchemaObject

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
        "multipleOf",
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

    A unique, executable action with well-defined characteristics.

    Attributes:
        name (str): A unique identifier for the action.
            Recommended format: lowercase, with words separated
            by underscores or dashes (e.g., "join_friend_lobby", "use_item").

        description (str): A plain-text description of what the action does.
            This description will be directly received by Neuro.

        schema (dict[str, object], optional): A valid JSON schema object
            describing the expected response data structure.
            This information will be directly received by Neuro.

    Notes:
        - If no parameters are needed, omit the schema or set to an empty dict {}.
        - Schemas must have ``"type": "object"``.
        - For non-object type schemas, wrap the schema in an object with a property.

    Examples:
        >>> action = Action(
        ...     name="use_item",
        ...     description="Use an item in the game",
        ...     schema={"type": "object", "properties": {...}}
        ... )

    """

    name: str
    description: str
    schema: SchemaObject | None = None


def check_invalid_keys_recursive(
    sub_schema: SchemaObject,
) -> list[str]:
    """Recursively checks for invalid keys in the schema.

    Args:
        sub_schema (SchemaObject): The schema to check for invalid keys.

    Returns:
        list[str]: A list of invalid keys that were found.

    Note:
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
            # Probably not quite correct to cast to SchemaObject here,
            # should do subtype properly, but for this particular
            # function and usecase probably not an issue.
            invalid_keys.extend(
                check_invalid_keys_recursive(cast("SchemaObject", value)),
            )
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    # Same issue, see above.
                    invalid_keys.extend(
                        check_invalid_keys_recursive(
                            cast("SchemaObject", item),
                        ),
                    )
        else:
            raise ValueError(
                f"Unhandled schema value type {type(value)!r} ({value!r})",
            )
    return invalid_keys


def format_command(
    command: str,
    game: str | None = None,
    data: Mapping[str, object] | None = None,
) -> bytes:
    """Return json bytes blob from command details.

    Args:
        command (str): The websocket command.
        game (str | None): The game name. This is used to identify the
            game. It should _always_ be the same and should not change.
            You should use the game's display name, including any spaces
            and symbols (e.g. `"Buckshot Roulette"`).
            MUST not be present for server messages.
            Defaults to None.
        data (Mapping[str, object], optional): The command data.
            This object is different depending on which command you are
            sending/receiving, and some commands may not have any data,
            in which case this object will be either `undefined` or `{}`.
            Defaults to None.

    Returns:
        bytes: JSON bytes blob representing the formatted command.

    """
    payload: dict[str, Any] = {
        "command": command,
    }
    if game is not None:
        payload["game"] = game
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

    Client to Server command.

    This message should be sent as soon as the game starts, to let
    Neuro know that the game is running.

    This message clears all previously registered actions for this game
    and does initial setup, and as such should be the very first message
    that you send.

    Args:
        game (str): The name of the game to start up.

    Returns:
        bytes: A formatted startup command for the specified game.

    """
    return format_command("startup", game)


def context_command(
    game: str,
    message: str,
    silent: bool = True,
) -> bytes:
    """Return formatted context command.

    Client to Server command.

    This message can be sent to let Neuro know about something that is
    happening in game.

    Args:
        game (str): The name of the game context is being sent for.
        message (str): A plaintext message that describes what is
            happening in the game. **This information will be directly
            received by Neuro.**
        silent (bool, optional): If True, the message will be added to
            Neuro's context without prompting her to respond to it.
            If False, Neuro _might_ respond to the message directly,
            unless she is busy talking to someone else or to chat.
            Defaults to True.

    Returns:
        bytes: A formatted context command for the specified game.

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

    Client to Server command.

    This message registers one or more actions for Neuro to use.

    Args:
        game (str): The name of the game for which actions are being registered.
        actions (list[Action]): A list of actions to be registered.
            If you try to register an action that is already registered,
            it will be ignored.

    Returns:
        bytes: A formatted command to register the specified actions for the game.

    Raises:
        AssertionError: If the actions list is empty. At least one action must be registered.

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

    Client to Server command.
    This message unregisters one or more actions, preventing Neuro from
    using them anymore.

    Args:
        game (str): The name of the game for which actions are being unregistered.
        action_names (Sequence[str]): The names of the actions to unregister.
            If you try to unregister an action that isn't registered,
            there will be no problem.

    Returns:
        bytes: A formatted command to unregister the specified actions for the game.

    Raises:
        AssertionError: If the action_names sequence is empty. At least one
        action name must be provided to unregister.

    """
    assert action_names, "Must unregister at least one action."
    return format_command(
        "actions/unregister",
        game,
        {"action_names": list(action_names)},
    )


class ForcePriority(str, Enum):
    """`actions/force` `priority` field values."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def actions_force_command(
    game: str,
    state: str,
    query: str,
    action_names: Sequence[str],
    ephemeral_context: bool = False,
    priority: ForcePriority = ForcePriority.LOW,
) -> bytes:
    """Return formatted actions/force command.

    Client to Server command.

    This message forces Neuro to execute one of the listed actions as
    soon as possible. Note that this might take a bit if she is already
    talking.

    Neuro can only handle one action force at a time.
    Sending an action force while another one is in progress will cause
    problems!

    Args:
        game (str): The name of the game for which actions are being forced.
        state (str): An arbitrary string that describes the current state
            of the game. This can be plaintext, JSON, Markdown, or any
            other format. **This information will be directly received
            by Neuro.**
        query (str): A plaintext message that tells Neuro what she is
            currently supposed to be doing (e.g. `"It is now your turn.
            Please perform an action. If you want to use any items, you
            should use them before picking up the shotgun."`).
            **This information will be directly received by Neuro.**
        action_names (Sequence[str]): The names of the actions that
            Neuro should choose from.
        ephemeral_context (bool, optional): If False, the context
            provided in the `state` and `query` parameters will be
            remembered by Neuro after the actions force is completed.
            If True, Neuro will only remember it for the duration of
            the actions force. Defaults to False.
        priority (ForcePriority):
            Determines how urgently Neuro should respond to the action
            force when she is speaking. If Neuro is not speaking, this
            setting has no effect. The default is `ForcePriority.LOW`,
            which will cause Neuro to wait until she finishes speaking
            before responding. `ForcePriority.MEDIUM` causes her to
            finish her current utterance sooner. `ForcePriority.HIGH`
            prompts her to process the action force immediately,
            shortening her utterance and then responding.
            `ForcePriority.CRITICAL` will interrupt her speech and make
            her respond at once. Use `ForcePriority.CRITICAL` with
            caution, as it may lead to abrupt and potentially jarring
            interruptions.

    Returns:
        bytes: A formatted command to force actions for the specified game.

    Warning:
        Neuro can only handle one action force at a time. Sending an
        action force while another one is in progress will cause problems!

    """
    assert action_names, "Must force at least one action name."
    payload: dict[str, object] = {
        "state": state,
        "query": query,
        "action_names": list(action_names),
        "priority": priority.value,
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

    Client to Server command.

    This message needs to be sent as soon as possible after an action is
    validated, to allow Neuro to continue.

    Until you send an action result, Neuro will just be waiting for the
    result of her action!
    Please make sure to send this as soon as possible.
    It should usually be sent after validating the action parameters,
    before it is actually executed in-game.

    Args:
        game (str): The name of the game for which the action result is being reported.
        id_ (str): The id of the action that this result is for. This is
            grabbed from the action message directly.
        success (bool): Whether or not the action was successful. _If this
            is `false` and this action is part of an actions force, the
            whole actions force will be immediately retried by Neuro._
        message (str, optional): A plaintext message that describes what
            happened when the action was executed. If not successful, this
            should be an error message. If successful, this can either be
            empty, or provide a _small_ context to Neuro regarding the
            action she just took (e.g. `"Remember to not share this with
            anyone."`). **This information will be directly received by Neuro.**
            Defaults to None.

    Returns:
        bytes: A formatted command to report the result of an action.

    Note:
        Since setting `success` to `false` will retry the action force if
        there was one, if the action was not successful but you don't want
        it to be retried, you should set `success` to `true` and provide
        an error message in the `message` field.

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

    Client to Server command.

    This is part of the game automation API, which will only be used for
    games that Neuro can launch by herself. As such, most games will not
    need to implement this.

    Args:
        game (str): The name of the game that is ready to be shut down.

    Returns:
        bytes: A formatted command indicating the game is ready for shutdown.

    Note:
        This message should be sent as a response to a graceful or an
        imminent shutdown request, after progress has been saved. After this
        is sent, Neuro will close the game herself by terminating the
        process, so to reiterate you must definitely ensure that progress
        has already been saved.

    Warning:
        This API is only applicable to games that Neuro can launch
        independently. Most games will not need to use this function.

    """
    return format_command(
        "shutdown/ready",
        game,
    )


def action_command(
    id_: str,
    name: str,
    data: str | None = None,
) -> bytes:
    """Return formatted action command.

    Server to Client command.

    Attempt to execute a registered action.

    Args:
        id_ (str): A unique id for the action.
        name (str): The name of the action that Neuro is trying to execute.
        data (str): JSON-stringified data for the action. This
            **_should_** be an object that matches the JSON schema
            provided when registering the action. If schema was not
            provided, this should be `None`.

    Returns:
        bytes: A formatted command to attempt to execute the registered
            action.

    """
    command_data: dict[str, str] = {
        "id": id_,
        "name": name,
    }
    if data is not None:
        command_data["data"] = data
    return format_command("action", data=command_data)


def reregister_all_command() -> bytes:
    """Return formatted actions/reregister_all command.

    Server to Client command.

    This signals to the game to unregister all actions and reregister them.

    Returns:
        bytes: A formatted command to unregister all actions and
            reregister them.

    Warning:
        This command is part of the proposed API and is not officially
        supported yet. Some clients may not support it.

    Reference:
        Specification details:
        https://github.com/VedalAI/neuro-game-sdk/blob/main/API/PROPOSALS.md#reregister-all-actions

    """
    return format_command("actions/reregister_all")


def shutdown_graceful_command(wants_shutdown: bool) -> bytes:
    """Return formatted shutdown/graceful command.

    Server to Client command.

    This message will be sent when Neuro decides to stop playing a game,
    or upon manual intervention from the dashboard. Signals game to save
    and quit to main menu and send back a shutdown ready message.

    Args:
        wants_shutdown (bool): Whether the game should shutdown at the
            next graceful shutdown point. `True` means shutdown is
            requested, `False` means to cancel the previous shutdown
            request.

    Returns:
        bytes: A formatted command to request or cancel a graceful
            shutdown.

    Warning:
        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself. Most games will not
        support it this command.

    Reference:
        Specification details:
        https://github.com/VedalAI/neuro-sdk/blob/main/API/PROPOSALS.md#graceful-shutdown

    """
    return format_command(
        "shutdown/graceful",
        data={"wants_shutdown": wants_shutdown},
    )


def shutdown_immediate_command() -> bytes:
    """Return formatted shutdown/immediate command.

    Server to Client command.

    This signals to the game that it needs to be shutdown immediately
    and needs to send back a shutdown ready message as soon as the game
    has saved.

    Returns:
        bytes: A formatted command to inform clients about pending
            immediate shutdown.

    Warning:
        This is part of the game automation API, which will only be used
        for games that Neuro can launch by herself. Most games will not
        support it this command.

    Reference:
        Specification details:
        https://github.com/VedalAI/neuro-sdk/blob/main/API/PROPOSALS.md#immediate-shutdown

    """
    return format_command("shutdown/immediate")


def convert_parameterized_generic_nonunion(
    generic: GenericAlias | T,
) -> T | type:
    """Return origin type of aliases.

    This function extracts the base type from various generic type aliases,
    handling different type representations and special cases.

    Args:
        generic (GenericAlias | T): The generic type or alias to be converted.
            Can be a GenericAlias or any other type.

    Returns:
        T | type: The origin type of the input generic alias.
            - For GenericAlias, returns the original type.
            - For NotRequired types, returns the wrapped type.
            - For other types, returns the input type as-is.

    Note:
        This function handles special cases like NotRequired from typing
        and typing_extensions modules.

    """
    if isinstance(generic, GenericAlias):
        return cast("type", generic.__origin__)
    if repr(generic).startswith("typing.NotRequired[") or repr(
        generic,
    ).startswith(
        "typing_extensions.NotRequired[",
    ):  # pragma: nocover
        inner = get_args(generic)[0]
        return convert_parameterized_generic_nonunion(inner)
    if repr(generic).startswith("typing.Optional[") or repr(
        generic,
    ).startswith(
        "typing_extensions.Optional[",
    ):  # pragma: nocover
        inner = get_args(generic)[0]
        return convert_parameterized_generic_nonunion(inner)
    if is_typeddict(generic):
        return dict
    return generic


def convert_parameterized_generic_union_items(
    generic: UnionType | T,
) -> T | tuple[type, ...]:
    """Return tuple of based types from union of parameterized generic types.

    Args:
        generic (UnionType | Union | T): The generic type or alias to be
            converted. Can be a UnionType or any other type.

    Returns:
        T | tuple[type, ...]:
            - For UnionType types, returns items as a tuple of types.
            - For other types, returns the input type as-is.

    """
    if isinstance(generic, UnionType):
        items = get_args(generic)
        return tuple(map(convert_parameterized_generic_nonunion, items))
    return generic


def convert_parameterized_generic(
    generic: GenericAlias | UnionType | T,
) -> T | type | tuple[type, ...]:
    """Return origin type of parameterized generics.

    This function extracts the base type from various generic type aliases,
    handling different type representations and special cases.

    Args:
        generic (GenericAlias | UnionType | T): The generic type or
            alias to be converted. Can be a GenericAlias, UnionType, or
            any other type.

    Returns:
        T | type | tuple[type, ...]: The origin type of the input generic alias.
            - For GenericAlias, returns the original type.
            - For NotRequired types, returns the wrapped type.
            - For UnionType types, returns items as a tuple of types.
            - For other types, returns the input type as-is.

    Note:
        This function handles special cases like NotRequired from typing
        and typing_extensions modules.

    """
    result: T | type | tuple[type, ...] = (
        convert_parameterized_generic_union_items(
            convert_parameterized_generic_nonunion(generic),
        )
    )
    # print(f"[convert_parameterized_generic] {result = }")
    # print(f"[convert_parameterized_generic] {type(result) = }")
    if sys.version_info < (3, 11):
        if type(result) is GenericAlias:
            return convert_parameterized_generic(result)
    return result


def check_typed_dict(data: Mapping[str, object], typed_dict: type[T]) -> T:
    """Ensure data matches TypedDict definition and return it as a typed dict.

    This function validates that the input data conforms to a TypedDict
    definition by checking for:
    - Presence of required keys
    - Absence of extra keys
    - Type correctness of values

    Args:
        data (Mapping[str, object]): The input data to be validated.
        typed_dict (type[T]): The TypedDict class used for validation.

    Returns:
        T: The input data converted to the specified TypedDict type.

    Raises:
        ValueError: If:
            - Extra keys are present in the data
            - Required keys are missing from the data
        TypeError: If the type of any key's value does not match its
        annotated type.

    Warning:
        - This function does not work properly for nested types.
        - Optional keys (NotRequired) are handled, but nested type
          checking is limited.

    Note:
        The function uses type hints and custom type conversion to
        perform thorough type checking.

    """
    assert is_typeddict(typed_dict)
    required = typed_dict.__required_keys__  # type: ignore[attr-defined]

    extra = set(data) - required
    if extra:
        extra_str = ", ".join(map(repr, extra))
        raise ValueError(f"Following extra keys were found: {extra_str}")

    try:
        full_annotations = get_type_hints(typed_dict, include_extras=True)
    except NameError as exc:
        if sys.version_info >= (3, 11):
            exc.add_note(f"{typed_dict = }")
            exc.add_note("Very likely you forgot to import something")
        else:
            print(f"{typed_dict = }", file=sys.stderr)
        raise

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
        try:
            isinstance_result = isinstance(
                data[key],
                convert_parameterized_generic(annotations[key]),
            )
        except TypeError as exc:
            if sys.version_info >= (3, 11):
                exc.add_note(f"{annotations[key] = }")
            else:
                print(f"{annotations[key] = }", file=sys.stderr)
            raise
        if not isinstance_result:
            raise TypeError(
                f"{data[key]!r} (key {key!r}) is not instance of {annotations[key]!r}",
            )

    for key in optional:
        if key in data and data is not None:
            try:
                key_type = convert_parameterized_generic(annotations[key])
                if get_origin(key_type) is Literal:
                    literal_values = list(
                        map(convert_parameterized_generic, get_args(key_type)),
                    )
                    isinstance_result = data[key] in literal_values
                else:
                    isinstance_result = isinstance(
                        data[key],
                        key_type,
                    )
            except TypeError as exc:
                if sys.version_info >= (3, 11):
                    exc.add_note(f"{annotations[key] = }")
                else:
                    print(f"{annotations[key] = }", file=sys.stderr)
                raise
            if not isinstance_result:
                raise TypeError(
                    f"{data[key]!r} (key {key!r}) is not instance of {annotations[key]!r}",
                )

    return typed_dict(data)  # type: ignore[call-arg]


class IncomingActionMessageSchema(TypedDict):
    """Schema for incoming 'action' command message fields.

    Represents the structure of an action message as specified in the
    Neuro Game SDK API documentation.

    Attributes:
        id (str): Unique identifier for the action message.
        name (str): Name of the action being requested.
        data (str, optional): Additional data associated with the action.
            This field is not required and can be omitted.

    Reference:
        Specification details:
        https://github.com/VedalAI/neuro-game-sdk/blob/main/API/SPECIFICATION.md#action-1

    """

    id: str
    name: str
    data: NotRequired[str]


def check_action(action: Action) -> None:
    """Validate an action before registration.

    Performs comprehensive validation of an action to ensure it meets
    the required naming and schema constraints before being registered.

    Args:
        action (Action): The action to be validated before registration.

    Raises:
        ValueError: If:
            - The action name contains invalid characters
            - The action schema contains invalid keys

    Note:
        - Invalid characters for action names are defined by
          ACTION_NAME_ALLOWED_CHARS
        - Schema validation is performed recursively using
          check_invalid_keys_recursive()

    """
    name_bad_chars = set(action.name) - ACTION_NAME_ALLOWED_CHARS
    if name_bad_chars:
        raise ValueError(
            f"Following invalid characters found in name {action.name!r}: {name_bad_chars}",
        )

    if action.schema is not None:
        bad_schema_keys = check_invalid_keys_recursive(action.schema)
        if bad_schema_keys:
            warn(
                f"Discouraged keys found in schema: {bad_schema_keys} ({action.name = })\nPlease make sure you accurately check for them in your integration.",
                stacklevel=2,
            )
