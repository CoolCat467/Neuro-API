Command Module
==============

.. currentmodule:: neuro_api.command

The command module provides comprehensive functionality for creating and managing Neuro API websocket commands. This module handles command formatting, action registration, validation, and type checking for communication with the Neuro Game Interaction API.

Overview
--------

The command module contains all the necessary components to build, format, and validate commands for the Neuro API. It provides functions for creating various types of commands (startup, context, actions, etc.) and includes robust validation for action schemas and TypedDict structures.

Constants
---------

.. autodata:: ACTION_NAME_ALLOWED_CHARS

   Frozenset of characters allowed in action names: lowercase letters, digits, underscores, and hyphens.

.. autodata:: INVALID_SCHEMA_KEYS

   Frozenset of JSON Schema keys that are not allowed in action schemas according to the Neuro API specification.

Classes
-------

Action
~~~~~~

.. autoclass:: Action
   :members:

   A named tuple representing a registerable command that Neuro can execute.

   **Attributes:**

   - **name** (str): Unique identifier for the action (lowercase, underscores/hyphens recommended)
   - **description** (str): Plain-text description that Neuro will receive
   - **schema** (dict[str, object] | None): Optional JSON schema for expected response data

   **Examples:**

   .. code-block:: python

      # Simple action without parameters
      action = Action(
          name="jump",
          description="Make the character jump"
      )

      # Action with schema for parameters
      action = Action(
          name="use_item",
          description="Use an item from inventory",
          schema={
              "type": "object",
              "properties": {
                  "item_id": {"type": "string"},
                  "quantity": {"type": "integer", "minimum": 1}
              },
              "required": ["item_id"]
          }
      )

IncomingActionMessageSchema
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: IncomingActionMessageSchema
   :members:

   TypedDict schema for incoming 'action' command messages from the server.

   **Attributes:**

   - **id** (str): Unique identifier for the action message
   - **name** (str): Name of the action being requested
   - **data** (NotRequired[str]): Optional JSON-stringified data for the action

Command Functions
-----------------

Client to Server Commands
~~~~~~~~~~~~~~~~~~~~~~~~~

These functions create commands that clients send to the Neuro server:

.. autofunction:: startup_command

   Creates the initial startup command that must be sent when a game starts.

   .. code-block:: python

      # Send startup command for a game
      command_bytes = startup_command("My Game")
      await client.send_command_data(command_bytes)

.. autofunction:: context_command

   Sends contextual information about game state to Neuro.

   .. code-block:: python

      # Silent context (won't prompt response)
      context_bytes = context_command(
          "My Game",
          "Player entered a new area",
          silent=True
      )

      # Interactive context (may prompt response)
      context_bytes = context_command(
          "My Game",
          "Player is stuck and needs help",
          silent=False
      )

.. autofunction:: actions_register_command

   Registers one or more actions that Neuro can execute.

   .. code-block:: python

      actions = [
          Action("move", "Move the player character"),
          Action("attack", "Attack nearby enemies")
      ]
      register_bytes = actions_register_command("My Game", actions)

.. autofunction:: actions_unregister_command

   Unregisters previously registered actions.

   .. code-block:: python

      unregister_bytes = actions_unregister_command(
          "My Game",
          ["move", "attack"]
      )

.. autofunction:: actions_force_command

   Forces Neuro to execute one of the specified actions immediately.

   .. warning::
      Neuro can only handle one action force at a time. Sending multiple forces simultaneously will cause problems.

   .. code-block:: python

      force_bytes = actions_force_command(
          game="My Game",
          state="Player health: 50%, enemies nearby: 2",
          query="Choose your next action in combat",
          action_names=["attack", "defend", "use_potion"],
          ephemeral_context=True
      )

.. autofunction:: actions_result_command

   Reports the result of an executed action back to Neuro.

   .. code-block:: python

      # Successful action
      result_bytes = actions_result_command(
          "My Game",
          action_id,
          success=True,
          message="Successfully moved to new location"
      )

      # Failed action
      result_bytes = actions_result_command(
          "My Game",
          action_id,
          success=False,
          message="Cannot move - path is blocked"
      )

.. autofunction:: shutdown_ready_command

   Indicates the game is ready for shutdown (game automation API only).

   .. note::
      This is only used for games that Neuro can launch independently.

Server to Client Commands
~~~~~~~~~~~~~~~~~~~~~~~~~

These functions create commands that the server sends to clients:

.. autofunction:: action_command

   Server command to execute a registered action.

.. autofunction:: reregister_all_command

   Server command requesting all actions to be unregistered and re-registered.

   .. warning::
      This is part of the proposed API and may not be supported by all clients.

.. autofunction:: shutdown_graceful_command

   Server command requesting graceful shutdown.

.. autofunction:: shutdown_immediate_command

   Server command requesting immediate shutdown.

Utility Functions
-----------------

Command Formatting
~~~~~~~~~~~~~~~~~~

.. autofunction:: format_command

   Core function for formatting commands as JSON bytes.

   .. code-block:: python

      # Server command (no game field)
      server_cmd = format_command("some_command", data={"key": "value"})

      # Client command (includes game field)
      client_cmd = format_command("some_command", "My Game", {"key": "value"})

Type Conversion and Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: convert_parameterized_generic_nonunion

   Extracts origin types from generic aliases, handling NotRequired types.

.. autofunction:: convert_parameterized_generic_union_items

   Converts union types to tuples of base types.

.. autofunction:: convert_parameterized_generic

   Main function for converting parameterized generic types to their origins.

.. autofunction:: check_typed_dict

   Validates data against TypedDict definitions with comprehensive type checking.

   .. code-block:: python

      # Validate incoming message data
      try:
          validated_action = check_typed_dict(raw_data, IncomingActionMessageSchema)
          action_id = validated_action["id"]
          action_name = validated_action["name"]
      except (ValueError, TypeError) as e:
          print(f"Invalid message format: {e}")

Schema Validation
~~~~~~~~~~~~~~~~~

.. autofunction:: check_invalid_keys_recursive

   Recursively validates JSON schemas for invalid keys.

.. autofunction:: check_action

   Comprehensive validation of actions before registration.

   .. code-block:: python

      action = Action(
          name="invalid-name!",  # Contains invalid character
          description="Test action"
      )

      try:
          check_action(action)
      except ValueError as e:
          print(f"Action validation failed: {e}")

Usage Examples
--------------

Complete Game Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a complete example showing how to integrate commands in a game client:

.. code-block:: python

   from neuro_api.command import *
   from neuro_api.client import AbstractNeuroAPIClient

   class GameClient(AbstractNeuroAPIClient):
       def __init__(self, websocket, game_name):
           self.websocket = websocket
           self.game_name = game_name
           self.registered_actions = []

       async def write_to_websocket(self, data: str) -> None:
           await self.websocket.send(data)

       async def read_from_websocket(self) -> str:
           return await self.websocket.recv()

       async def initialize_game(self):
           # Send startup command
           startup_cmd = startup_command(self.game_name)
           await self.send_command_data(startup_cmd)

           # Register actions
           actions = [
               Action("move", "Move the player character", {
                   "type": "object",
                   "properties": {"direction": {"type": "string"}},
                   "required": ["direction"]
               }),
               Action("jump", "Make the player jump")
           ]

           # Validate actions before registering
           for action in actions:
               check_action(action)

           register_cmd = actions_register_command(self.game_name, actions)
           await self.send_command_data(register_cmd)
           self.registered_actions = actions

       async def handle_unknown_command(self, command: str, data: dict | None):
           if command == "action":
               await self.handle_action(data)
           else:
               await super().handle_unknown_command(command, data)

       async def handle_action(self, data: dict):
           try:
               action_data = check_typed_dict(data, IncomingActionMessageSchema)
               action_id = action_data["id"]
               action_name = action_data["name"]

               # Execute the action
               success = await self.execute_action(action_name, action_data.get("data"))

               # Send result
               result_cmd = actions_result_command(
                   self.game_name,
                   action_id,
                   success,
                   "Action completed successfully" if success else "Action failed"
               )
               await self.send_command_data(result_cmd)

           except (ValueError, TypeError) as e:
               print(f"Invalid action message: {e}")

Error Handling
--------------

The module provides comprehensive error handling for various scenarios:

**JSON Serialization Errors**
   ``orjson.JSONDecodeError`` when parsing malformed JSON messages.

**Type Validation Errors**
   ``TypeError`` when data doesn't match expected types in TypedDict validation.

**Schema Validation Errors**
   ``ValueError`` when actions contain invalid names or schema keys.

**Command Format Errors**
   ``AssertionError`` when required parameters are missing (e.g., empty action lists).

.. code-block:: python

   try:
       command_bytes = actions_register_command("My Game", [])
   except AssertionError:
       print("Must register at least one action")

   try:
       check_typed_dict(invalid_data, IncomingActionMessageSchema)
   except ValueError as e:
       print(f"Missing required fields: {e}")
   except TypeError as e:
       print(f"Type mismatch: {e}")

Best Practices
--------------

**Action Naming**
   Use lowercase names with underscores or hyphens: ``"use_item"``, ``"join-lobby"``

**Schema Design**
   Always use ``"type": "object"`` at the root level, even for simple types:

   .. code-block:: python

      # Good
      schema = {
          "type": "object",
          "properties": {
              "value": {"type": "string"}
          }
      }

      # Avoid
      schema = {"type": "string"}  # Should be wrapped in object

**Error Handling**
   Always validate actions before registration and handle command errors gracefully:

   .. code-block:: python

      for action in actions:
          try:
              check_action(action)
          except ValueError as e:
              print(f"Skipping invalid action {action.name}: {e}")
              continue

**Action Results**
   Send action results immediately after validation, not after execution:

   .. code-block:: python

      # Validate parameters first
      if not is_valid_move(direction):
          await send_action_result(action_id, False, "Invalid direction")
          return

      # Send success result before executing
      await send_action_result(action_id, True, "Move validated")

      # Then execute the actual move
      await execute_move(direction)

API Reference
-------------

For complete API specification details, see:

- `Neuro SDK API Specification <https://github.com/VedalAI/neuro-sdk/blob/main/API/SPECIFICATION.md>`_
- `Neuro SDK API Proposals <https://github.com/VedalAI/neuro-game-sdk/blob/main/API/PROPOSALS.md>`_

Dependencies
------------

This module requires:

- ``orjson``: Fast JSON parsing and serialization
- ``typing_extensions``: Extended type hints (``NotRequired``, ``is_typeddict``)
