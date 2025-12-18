from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TypedDict

import pytest
from typing_extensions import NotRequired

from neuro_api.command import (
    Action,
    ForcePriority,
    IncomingActionMessageSchema,
    action_command,
    actions_force_command,
    actions_register_command,
    actions_result_command,
    actions_unregister_command,
    check_action,
    check_invalid_keys_recursive,
    check_typed_dict,
    context_command,
    convert_parameterized_generic,
    convert_parameterized_generic_nonunion,
    convert_parameterized_generic_union_items,
    format_command,
    reregister_all_command,
    shutdown_graceful_command,
    shutdown_immediate_command,
    shutdown_ready_command,
    startup_command,
)
from neuro_api.json_schema_types import SchemaObject

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_check_invalid_keys_recursive() -> None:
    valid_schema = SchemaObject(
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        },
    )
    invalid_schema = SchemaObject(
        {
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema",  # type: ignore[typeddict-unknown-key]
            "properties": {
                "name": {"type": "string"},
            },
        },
    )

    assert check_invalid_keys_recursive(valid_schema) == []
    assert check_invalid_keys_recursive(invalid_schema) == ["$schema"]


def test_check_invalid_keys_recursive_bad_keys() -> None:
    """Test checking for invalid keys in a schema.

    Copied from neuro-api-tony/tests/test_api.py
    found at https://github.com/Pasu4/neuro-api-tony,
    which is licensed under the MIT License.
    """
    schema = SchemaObject(
        {
            # Extra keys ("valid_key", "another_key") for TypedDict "SchemaObject"
            "valid_key": {},  # type: ignore[typeddict-unknown-key]
            # Incompatible types (expression has type "dict[Never, Never]", TypedDict item "allOf" has type "_SchemaArray")
            "allOf": {},  # type: ignore[typeddict-item]
            "another_key": {
                "$vocabulary": {},
                "3rd level": [
                    {
                        "additionalProperties": "seven",
                        "uses_waffle_iron": True,
                    },
                    "spaghetti",
                ],
            },
        },
    )
    invalid_keys = check_invalid_keys_recursive(schema)

    assert invalid_keys == ["allOf", "$vocabulary", "additionalProperties"]


def test_check_invalid_keys_recursive_unhandled_type() -> None:
    with pytest.raises(ValueError, match="Unhandled schema value type"):
        check_invalid_keys_recursive(
            {
                # Extra key "jerald" for TypedDict "SchemaObject"
                "jerald": set(),  # type: ignore[typeddict-unknown-key]
            },
        )


def test_format_command() -> None:
    command = "test_command"
    game = "Test Game"
    data = {"key": "value"}

    expected_output = (
        b'{"command":"test_command","game":"Test Game","data":{"key":"value"}}'
    )
    assert format_command(command, game, data) == expected_output


def test_format_command_error() -> None:
    # should be str but is set[str]
    command = {"kittens"}
    game = "Waffle Iron Mania III: The Brogleing"

    with pytest.raises(TypeError):
        format_command(command, game)  # type: ignore[arg-type]


def test_startup_command() -> None:
    game = "Test Game"
    expected_output = b'{"command":"startup","game":"Test Game"}'
    assert startup_command(game) == expected_output


def test_context_command() -> None:
    game = "Test Game"
    message = "This is a test message."
    silent = True

    expected_output = b'{"command":"context","game":"Test Game","data":{"message":"This is a test message.","silent":true}}'
    assert context_command(game, message, silent) == expected_output


def test_actions_register_command() -> None:
    game = "Test Game"
    actions = [
        Action(name="test_action", description="A test action", schema=None),
    ]

    expected_output = b'{"command":"actions/register","game":"Test Game","data":{"actions":[{"name":"test_action","description":"A test action","schema":null}]}}'
    assert actions_register_command(game, actions) == expected_output


def test_actions_unregister_command() -> None:
    game = "Test Game"
    action_names = ["test_action"]

    expected_output = b'{"command":"actions/unregister","game":"Test Game","data":{"action_names":["test_action"]}}'
    assert actions_unregister_command(game, action_names) == expected_output


def test_actions_force_command() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"low"}}'
    assert (
        actions_force_command(game, state, query, action_names)
        == expected_output
    )


def test_actions_force_command_ephemeral() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"low","ephemeral_context":true}}'
    assert (
        actions_force_command(game, state, query, action_names, True)
        == expected_output
    )


def test_actions_force_command_priority_medium() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]
    priority = ForcePriority.MEDIUM

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"medium"}}'
    assert (
        actions_force_command(
            game,
            state,
            query,
            action_names,
            priority=priority,
        )
        == expected_output
    )


def test_actions_force_command_priority_high() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]
    priority = ForcePriority.HIGH

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"high"}}'
    assert (
        actions_force_command(
            game,
            state,
            query,
            action_names,
            priority=priority,
        )
        == expected_output
    )


def test_actions_force_command_priority_critical() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]
    priority = ForcePriority.CRITICAL

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"critical"}}'
    assert (
        actions_force_command(
            game,
            state,
            query,
            action_names,
            priority=priority,
        )
        == expected_output
    )


def test_actions_force_command_priority_explicit_low() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]
    priority = ForcePriority.LOW

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"priority":"low"}}'
    assert (
        actions_force_command(
            game,
            state,
            query,
            action_names,
            False,
            priority,
        )
        == expected_output
    )


def test_actions_result_command() -> None:
    game = "Test Game"
    id_ = "12345"
    success = True
    message = "Action executed successfully."

    expected_output = b'{"command":"action/result","game":"Test Game","data":{"id":"12345","success":true,"message":"Action executed successfully."}}'
    assert (
        actions_result_command(game, id_, success, message) == expected_output
    )


def test_actions_result_command_success_message_omitted() -> None:
    game = "Test Game"
    id_ = "12345"
    success = True

    expected_output = b'{"command":"action/result","game":"Test Game","data":{"id":"12345","success":true}}'
    assert actions_result_command(game, id_, success) == expected_output


def test_actions_result_command_error_message_omitted() -> None:
    game = "Test Game"
    id_ = "12345"
    success = False

    with pytest.raises(
        ValueError,
        match="Message can only be omitted if successful, otherwise should be error message",
    ):
        actions_result_command(game, id_, success)


def test_shutdown_ready_command() -> None:
    game = "Test Game"
    expected_output = b'{"command":"shutdown/ready","game":"Test Game"}'
    assert shutdown_ready_command(game) == expected_output


def test_check_action_valid() -> None:
    action = Action(
        name="valid_action",
        description="A valid action",
        schema={},
    )
    check_action(action)


def test_check_action_valid_no_schema() -> None:
    action = Action(
        name="valid_action",
        description="A valid action",
    )
    check_action(action)


def test_check_action_invalid_name() -> None:
    action = Action(
        name="invalid action!",
        description="An invalid action",
        schema={},
    )
    with pytest.raises(
        ValueError,
        match="Following invalid characters found in name",
    ):
        check_action(action)


def test_check_action_invalid_schema_key() -> None:
    action = Action(
        name="valid_action",
        description="A valid action",
        schema={"$schema": {}},  # type: ignore[arg-type]
    )
    with pytest.warns(
        UserWarning,
        match="Discouraged keys found in schema",
    ):
        check_action(action)


def test_check_typed_dict() -> None:
    data = {
        "id": "waffles",
        "name": "ur mom",
    }
    value = check_typed_dict(data, IncomingActionMessageSchema)
    assert value == data


def test_check_typed_dict_with_data() -> None:
    data = {
        "id": "waffles",
        "name": "ur mom",
        "data": "this is text",
    }
    value = check_typed_dict(data, IncomingActionMessageSchema)
    assert value == data


def test_check_typed_dict_bad_type() -> None:
    data = {
        "id": 27,
        "name": "ur mom",
    }
    with pytest.raises(TypeError):
        check_typed_dict(data, IncomingActionMessageSchema)


def test_check_typed_dict_data_bad_type() -> None:
    data = {
        "id": "waffles",
        "name": "ur mom",
        "data": b"this is bytes",
    }
    with pytest.raises(TypeError):
        check_typed_dict(data, IncomingActionMessageSchema)


def test_check_typed_dict_missing_required_key() -> None:
    data = {
        "name": "ur mom",
    }
    with pytest.raises(
        ValueError,
        match=r"'id' is missing \(type <class 'str'>\)",
    ):
        check_typed_dict(data, IncomingActionMessageSchema)


def test_check_typed_dict_extra_keys() -> None:
    data = {
        "name": "ur mom",
        "contains_eggs": True,
        "needs_spaghetti": True,
    }
    with pytest.raises(ValueError, match="Following extra keys were found: "):
        check_typed_dict(data, IncomingActionMessageSchema)


def test_check_typed_dict_parameterized_generic() -> None:
    class Data(TypedDict):
        entry: str
        attributes: dict[str, str]

    data = {
        "entry": "2025/02/03",
        "attributes": {
            "armchair": "underground",
            "waffle_iron": "plugged in",
            "hamster_ball": "unbreakable",
        },
    }

    assert check_typed_dict(data, Data) == data


# ... (keep all existing tests) ...


# NEW TESTS - Add these to improve coverage:


def test_format_command_no_game() -> None:
    """Test format_command without game parameter."""
    command = "test_command"
    data = {"key": "value"}

    expected_output = b'{"command":"test_command","data":{"key":"value"}}'
    assert format_command(command, data=data) == expected_output


def test_format_command_no_data() -> None:
    """Test format_command without data parameter."""
    command = "test_command"
    game = "Test Game"

    expected_output = b'{"command":"test_command","game":"Test Game"}'
    assert format_command(command, game) == expected_output


def test_format_command_minimal() -> None:
    """Test format_command with only command parameter."""
    command = "test_command"

    expected_output = b'{"command":"test_command"}'
    assert format_command(command) == expected_output


def test_format_command_error_with_note() -> None:
    """Test format_command error handling with note (Python 3.11+)."""
    if sys.version_info >= (3, 11):
        command = {"invalid"}  # Invalid type
        game = "Test Game"

        with pytest.raises(TypeError) as exc_info:
            format_command(command, game)  # type: ignore[arg-type]

        # Check that the note was added
        assert hasattr(exc_info.value, "__notes__")


def test_context_command_not_silent() -> None:
    """Test context_command with silent=False."""
    game = "Test Game"
    message = "This is a test message."
    silent = False

    expected_output = b'{"command":"context","game":"Test Game","data":{"message":"This is a test message.","silent":false}}'
    assert context_command(game, message, silent) == expected_output


def test_actions_register_command_empty_assertion() -> None:
    """Test actions_register_command with empty actions list."""
    game = "Test Game"
    actions: list[Action] = []

    with pytest.raises(
        AssertionError,
        match="Must register at least one action",
    ):
        actions_register_command(game, actions)


def test_actions_unregister_command_empty_assertion() -> None:
    """Test actions_unregister_command with empty action_names."""
    game = "Test Game"
    action_names: Sequence[str] = []

    with pytest.raises(
        AssertionError,
        match="Must unregister at least one action",
    ):
        actions_unregister_command(game, action_names)


def test_actions_force_command_empty_assertion() -> None:
    """Test actions_force_command with empty action_names."""
    game = "Test Game"
    state = "Game state"
    query = "Please act"
    action_names: Sequence[str] = []

    with pytest.raises(
        AssertionError,
        match="Must force at least one action name",
    ):
        actions_force_command(game, state, query, action_names)


# NEW SERVER-TO-CLIENT COMMANDS:


def test_action_command() -> None:
    """Test server-to-client action command."""
    id_ = "12345"
    name = "test_action"
    data = '{"key": "value"}'

    expected_output = b'{"command":"action","data":{"id":"12345","name":"test_action","data":"{\\"key\\": \\"value\\"}"}}'
    assert action_command(id_, name, data) == expected_output


def test_action_command_no_data() -> None:
    """Test action command without data."""
    id_ = "12345"
    name = "test_action"

    expected_output = (
        b'{"command":"action","data":{"id":"12345","name":"test_action"}}'
    )
    assert action_command(id_, name) == expected_output


def test_reregister_all_command() -> None:
    """Test reregister all command."""
    expected_output = b'{"command":"actions/reregister_all"}'
    assert reregister_all_command() == expected_output


def test_shutdown_graceful_command() -> None:
    """Test graceful shutdown command."""
    expected_output = (
        b'{"command":"shutdown/graceful","data":{"wants_shutdown":true}}'
    )
    assert shutdown_graceful_command(True) == expected_output

    expected_output = (
        b'{"command":"shutdown/graceful","data":{"wants_shutdown":false}}'
    )
    assert shutdown_graceful_command(False) == expected_output


def test_shutdown_immediate_command() -> None:
    """Test immediate shutdown command."""
    expected_output = b'{"command":"shutdown/immediate"}'
    assert shutdown_immediate_command() == expected_output


# TYPE CONVERSION TESTS:


def test_convert_parameterized_generic_nonunion_generic_alias() -> None:
    """Test convert_parameterized_generic_nonunion with GenericAlias."""
    generic = list[str]
    result = convert_parameterized_generic_nonunion(generic)
    assert result is list


def test_convert_parameterized_generic_nonunion_regular_type() -> None:
    """Test convert_parameterized_generic_nonunion with regular type."""
    result = convert_parameterized_generic_nonunion(str)
    assert result is str


def test_convert_parameterized_generic_union_items_union() -> None:
    """Test convert_parameterized_generic_union_items with UnionType."""
    union = str | int
    result = convert_parameterized_generic_union_items(union)
    assert result == (str, int)


def test_convert_parameterized_generic_union_items_regular_type() -> None:
    """Test convert_parameterized_generic_union_items with regular type."""
    result = convert_parameterized_generic_union_items(str)
    assert result is str


def test_convert_parameterized_generic() -> None:
    """Test convert_parameterized_generic with various types."""
    # Test with regular type
    assert convert_parameterized_generic(str) is str

    # Test with GenericAlias
    assert convert_parameterized_generic(list[str]) is list

    # Test with UnionType
    result = convert_parameterized_generic(str | int)
    assert result == (str, int)


# NEW TESTS FOR BETTER COVERAGE:


def test_check_typed_dict_name_error() -> None:
    """Test check_typed_dict with NameError in get_type_hints."""

    class BadTypedDict(TypedDict):
        # F821 Undefined name `NonExistentType`
        field: NonExistentType  # type: ignore[name-defined]  # noqa: F821

    data = {"field": "value"}

    with pytest.raises(NameError):
        check_typed_dict(data, BadTypedDict)


def test_check_typed_dict_optional_field_none() -> None:
    """Test check_typed_dict with optional field that has None value."""

    class OptionalData(TypedDict):
        required: str
        optional: NotRequired[str]

    data = {
        "required": "test",
        "optional": None,  # This should fail validation
    }

    with pytest.raises(
        TypeError,
        match="None \\(key 'optional'\\) is not instance of",
    ):
        check_typed_dict(data, OptionalData)


def test_check_invalid_keys_recursive_nested_list() -> None:
    """Test check_invalid_keys_recursive with nested lists containing dicts."""
    schema = SchemaObject(
        {
            "items": [
                {"type": "string"},
                # Invalid key
                {"$ref": "#/definitions/test"},  # type: ignore[list-item]
                "plain_string",  # type: ignore[list-item]
                {"additionalProperties": False},  # Another invalid key
            ],
        },
    )

    invalid_keys = check_invalid_keys_recursive(schema)
    assert "$ref" in invalid_keys
    assert "additionalProperties" in invalid_keys


def test_check_invalid_keys_recursive_deeply_nested() -> None:
    """Test deeply nested schema validation."""
    schema = SchemaObject(
        {
            "level1": {  # type: ignore[typeddict-unknown-key]
                "level2": {
                    "level3": [
                        {
                            "level4": {
                                "$schema": "invalid",  # Should be found
                                "valid_key": "value",
                            },
                        },
                    ],
                },
            },
        },
    )

    invalid_keys = check_invalid_keys_recursive(schema)
    assert "$schema" in invalid_keys
