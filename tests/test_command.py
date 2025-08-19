from __future__ import annotations

from typing import TypedDict

import pytest

from neuro_api.command import (
    Action,
    IncomingActionMessageSchema,
    actions_force_command,
    actions_register_command,
    actions_result_command,
    actions_unregister_command,
    check_action,
    check_invalid_keys_recursive,
    check_typed_dict,
    context_command,
    format_command,
    shutdown_ready_command,
    startup_command,
)


def test_check_invalid_keys_recursive() -> None:
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
    }
    invalid_schema = {
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema",
        "properties": {
            "name": {"type": "string"},
        },
    }

    assert check_invalid_keys_recursive(valid_schema) == []
    assert check_invalid_keys_recursive(invalid_schema) == ["$schema"]


def test_check_invalid_keys_recursive_bad_keys() -> None:
    """Test checking for invalid keys in a schema.

    Copied from neuro-api-tony/tests/test_api.py
    found at https://github.com/Pasu4/neuro-api-tony,
    which is licensed under the MIT License.
    """
    schema = {
        "valid_key": {},
        "allOf": {},
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
    }
    invalid_keys = check_invalid_keys_recursive(schema)

    assert invalid_keys == ["allOf", "$vocabulary", "additionalProperties"]


def test_check_invalid_keys_recursive_unhandled_type() -> None:
    with pytest.raises(ValueError, match="Unhandled schema value type"):
        check_invalid_keys_recursive(
            {
                "jerald": set(),
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

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"]}}'
    assert (
        actions_force_command(game, state, query, action_names)
        == expected_output
    )


def test_actions_force_command_ephemeral() -> None:
    game = "Test Game"
    state = "Game is in progress."
    query = "Please take your turn."
    action_names = ["test_action"]

    expected_output = b'{"command":"actions/force","game":"Test Game","data":{"state":"Game is in progress.","query":"Please take your turn.","action_names":["test_action"],"ephemeral_context":true}}'
    assert (
        actions_force_command(game, state, query, action_names, True)
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
        schema={"$schema": {}},
    )
    with pytest.raises(
        ValueError,
        match="Following invalid keys found in schema",
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
