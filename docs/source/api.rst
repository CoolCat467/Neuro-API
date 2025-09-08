API Module
==========

.. currentmodule:: neuro_api.api

The API module provides a high-level interface for building Neuro API game clients. This module builds upon the foundational client and command modules to offer a complete, abstract base class for game integration with the Neuro system.

Overview
--------

The API module contains the main ``AbstractNeuroAPI`` class that game developers should inherit from to create their Neuro-integrated games. It handles action registration, command processing, and provides hooks for game-specific implementations. This module abstracts away much of the low-level command formatting and message handling.

Classes
-------

NeuroAction
~~~~~~~~~~~

.. autoclass:: NeuroAction
   :members:

   A named tuple representing an action request from Neuro with all necessary details.

   **Attributes:**

   - **id_** (str): Unique identifier for the action (underscore avoids Python's ``id`` keyword)
   - **name** (str): Name of the action to be performed
   - **data** (str | None): Optional JSON-stringified data for the action

   **Example:**

   .. code-block:: python

      action = NeuroAction(
          id_="action_123",
          name="move_player",
          data='{"direction": "north", "steps": 3}'
      )

AbstractNeuroAPI
~~~~~~~~~~~~~~~~

.. autoclass:: AbstractNeuroAPI
   :members:
   :special-members: __init__

   High-level abstract base class for Neuro API game clients.

   This class provides a complete framework for integrating games with the Neuro system. It handles:

   - Action registration and management
   - Command processing and routing
   - Context communication with Neuro
   - Shutdown handling for automated games
   - Internal state tracking

   **Attributes:**

   - **game_title** (str): The name of the integrated game

Initialization
~~~~~~~~~~~~~~

.. automethod:: AbstractNeuroAPI.__init__

   Initialize the Neuro API client for a specific game.

   The game title should be the display name of your game, including spaces and symbols (e.g., "Buckshot Roulette", "Among Us").

Core Methods
~~~~~~~~~~~~

These methods provide the primary functionality for game integration:

.. automethod:: AbstractNeuroAPI.send_startup_command

   **Critical:** This must be the first command sent when your game starts.

   .. code-block:: python

      async def game_startup():
          api = MyGameAPI("My Game")
          await api.send_startup_command()  # Clear previous state
          # Now register actions...

.. automethod:: AbstractNeuroAPI.send_context

   Communicate game events and state to Neuro.

   .. code-block:: python

      # Silent context (no response expected)
      await api.send_context("Player entered the forest area")

      # Interactive context (may prompt response)
      await api.send_context("Player seems confused and stuck", silent=False)

.. automethod:: AbstractNeuroAPI.register_actions

   Register actions that Neuro can execute in your game.

   .. code-block:: python

      from neuro_api.command import Action

      actions = [
          Action(
              name="move_player",
              description="Move the player character",
              schema={
                  "type": "object",
                  "properties": {
                      "direction": {"type": "string"},
                      "distance": {"type": "integer", "minimum": 1}
                  },
                  "required": ["direction"]
              }
          ),
          Action("jump", "Make the player jump"),
          Action("attack", "Attack nearby enemies")
      ]

      await api.register_actions(actions)

.. automethod:: AbstractNeuroAPI.unregister_actions

   Remove actions that are no longer available.

   .. code-block:: python

      # Remove specific actions
      await api.unregister_actions(["attack", "use_magic"])

.. automethod:: AbstractNeuroAPI.send_force_action

   Force Neuro to choose from specific actions immediately.

   .. warning::
      Only one action force can be active at a time. Multiple concurrent forces will cause problems.

   .. code-block:: python

      await api.send_force_action(
          state="Player HP: 25/100, Enemy HP: 50/100, In combat",
          query="Choose your action for this turn in combat",
          action_names=["attack", "defend", "use_potion", "flee"],
          ephemeral_context=True  # Don't remember this context after action
      )

.. automethod:: AbstractNeuroAPI.send_action_result

   Report the outcome of an action execution.

   .. important::
      Send this immediately after validating the action, not after executing it in-game.

   .. code-block:: python

      # Successful action
      await api.send_action_result(
          action.id_,
          success=True,
          message="Successfully moved north"
      )

      # Failed action
      await api.send_action_result(
          action.id_,
          success=False,
          message="Cannot move - path blocked by wall"
      )

Utility Methods
~~~~~~~~~~~~~~~

.. automethod:: AbstractNeuroAPI.get_registered

   Get names of currently registered actions.

   .. code-block:: python

      registered = api.get_registered()
      print(f"Available actions: {', '.join(registered)}")

Abstract Methods
~~~~~~~~~~~~~~~~

These methods must be implemented in your game-specific subclass:

.. automethod:: AbstractNeuroAPI.handle_action

   **Required implementation:** Process action requests from Neuro.

   This is the main method where your game logic handles Neuro's actions.

   .. code-block:: python

      async def handle_action(self, action: NeuroAction):
          try:
              # Parse action data if present
              data = None
              if action.data:
                  data = json.loads(action.data)

              # Validate action
              if action.name not in self.get_registered():
                  await self.send_action_result(
                      action.id_,
                      False,
                      f"Unknown action: {action.name}"
                  )
                  return

              # Execute action based on name
              if action.name == "move_player":
                  success = await self.execute_move(data["direction"])
                  message = "Moved successfully" if success else "Move failed"
              elif action.name == "attack":
                  success = await self.execute_attack()
                  message = "Attack executed" if success else "Attack failed"
              else:
                  success = False
                  message = f"Unhandled action: {action.name}"

              # Always send result
              await self.send_action_result(action.id_, success, message)

          except Exception as e:
              # Handle errors gracefully
              await self.send_action_result(
                  action.id_,
                  False,
                  f"Action failed: {str(e)}"
              )

Websocket Methods (from AbstractNeuroAPIClient)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These must be implemented to handle websocket communication:

.. automethod:: AbstractNeuroAPI.write_to_websocket
.. automethod:: AbstractNeuroAPI.read_from_websocket

Game Automation Methods
~~~~~~~~~~~~~~~~~~~~~~~

These methods handle automated game launching (most games won't need these):

.. automethod:: AbstractNeuroAPI.send_shutdown_ready
.. automethod:: AbstractNeuroAPI.handle_graceful_shutdown_request
.. automethod:: AbstractNeuroAPI.handle_immediate_shutdown

Message Processing
~~~~~~~~~~~~~~~~~~

.. automethod:: AbstractNeuroAPI.read_message

   Main message processing loop. Call this continuously while connected.

   The method automatically handles:

   - ``action`` commands → calls ``handle_action()``
   - ``actions/reregister_all`` → re-registers all current actions
   - ``shutdown/graceful`` → calls ``handle_graceful_shutdown_request()``
   - ``shutdown/immediate`` → calls ``handle_immediate_shutdown()``
   - Unknown commands → calls ``handle_unknown_command()``

Complete Usage Example
----------------------

Here's a complete example of implementing a Neuro API client:

.. code-block:: python

   import asyncio
   import json
   import websockets
   from neuro_api.api import AbstractNeuroAPI, NeuroAction
   from neuro_api.command import Action

   class MyGameAPI(AbstractNeuroAPI):
       def __init__(self, websocket):
           super().__init__("My Awesome Game")
           self.websocket = websocket
           self.player_position = {"x": 0, "y": 0}
           self.player_health = 100

       # Required websocket methods
       async def write_to_websocket(self, data: str) -> None:
           await self.websocket.send(data)

       async def read_from_websocket(self) -> str:
           return await self.websocket.recv()

       # Required action handler
       async def handle_action(self, action: NeuroAction) -> None:
           try:
               success = False
               message = ""

               if action.name == "move":
                   data = json.loads(action.data) if action.data else {}
                   direction = data.get("direction", "north")
                   success = await self.move_player(direction)
                   message = f"Moved {direction}" if success else "Move blocked"

               elif action.name == "heal":
                   success = await self.heal_player()
                   message = "Healed successfully" if success else "No healing items"

               elif action.name == "status":
                   success = True
                   message = f"Health: {self.player_health}, Position: {self.player_position}"

               else:
                   message = f"Unknown action: {action.name}"

               await self.send_action_result(action.id_, success, message)

           except Exception as e:
               await self.send_action_result(
                   action.id_,
                   False,
                   f"Error executing action: {str(e)}"
               )

       # Game logic methods
       async def move_player(self, direction: str) -> bool:
           moves = {
               "north": (0, 1), "south": (0, -1),
               "east": (1, 0), "west": (-1, 0)
           }

           if direction in moves:
               dx, dy = moves[direction]
               self.player_position["x"] += dx
               self.player_position["y"] += dy

               # Send context about the move
               await self.send_context(
                   f"Player moved {direction} to {self.player_position}"
               )
               return True
           return False

       async def heal_player(self) -> bool:
           if self.player_health < 100:
               self.player_health = min(100, self.player_health + 25)
               return True
           return False

       async def initialize_game(self):
           # Send startup command
           await self.send_startup_command()

           # Register available actions
           actions = [
               Action(
                   name="move",
                   description="Move the player in a direction",
                   schema={
                       "type": "object",
                       "properties": {
                           "direction": {
                               "type": "string",
                               "enum": ["north", "south", "east", "west"]
                           }
                       },
                       "required": ["direction"]
                   }
               ),
               Action("heal", "Heal the player character"),
               Action("status", "Check player status")
           ]

           await self.register_actions(actions)

           # Send initial context
           await self.send_context("Game initialized, player ready for action")

   async def main():
       uri = "ws://localhost:8765"
       async with websockets.connect(uri) as websocket:
           api = MyGameAPI(websocket)
           await api.initialize_game()

           # Main game loop
           try:
               while True:
                   await api.read_message()
           except websockets.exceptions.ConnectionClosed:
               print("Connection to Neuro closed")

   if __name__ == "__main__":
       asyncio.run(main())

Best Practices
--------------

**Initialization Sequence**
   Always follow this order when starting your game:

   .. code-block:: python

      # 1. Send startup command (clears previous state)
      await api.send_startup_command()

      # 2. Register your actions
      await api.register_actions(actions)

      # 3. Send initial context
      await api.send_context("Game ready")

**Action Result Timing**
   Send action results immediately after validation, not after game execution:

   .. code-block:: python

      async def handle_action(self, action: NeuroAction):
          # Validate first
          if not self.is_valid_action(action):
              await self.send_action_result(action.id_, False, "Invalid action")
              return

          # Send success result immediately
          await self.send_action_result(action.id_, True, "Action validated")

          # Then execute in game (this can be slow)
          await self.execute_action_in_game(action)

**Error Handling**
   Always handle errors gracefully and send appropriate results:

   .. code-block:: python

      async def handle_action(self, action: NeuroAction):
          try:
              # Action logic here
              await self.send_action_result(action.id_, True, "Success")
          except ValidationError as e:
              await self.send_action_result(action.id_, False, f"Validation failed: {e}")
          except Exception as e:
              await self.send_action_result(action.id_, False, f"Unexpected error: {e}")

**Context Updates**
   Use context messages to keep Neuro informed about important game events:

   .. code-block:: python

      # Good context examples
      await api.send_context("Player entered boss room")
      await api.send_context("Enemy defeated, gained 100 XP")
      await api.send_context("Low health warning: 15/100 HP")

**Action Design**
   Design actions that are atomic and clear:

   .. code-block:: python

      # Good - specific actions
      Action("move_north", "Move player one step north")
      Action("attack_sword", "Attack with equipped sword")
      Action("use_health_potion", "Use a health potion from inventory")

      # Avoid - overly generic actions
      Action("do_something", "Do something in the game")
      Action("action", "Perform an action")

Error Handling
--------------

The API module handles various error conditions:

**Action Validation Errors**
   When registering actions with invalid names or schemas:

   .. code-block:: python

      try:
          await api.register_actions(actions)
      except ValueError as e:
          print(f"Action registration failed: {e}")

**Command Processing Errors**
   When receiving malformed action commands:

   .. code-block:: python

      # The read_message() method handles these automatically
      # and logs appropriate error messages

**Websocket Errors**
   Connection issues should be handled in your main loop:

   .. code-block:: python

      try:
          while True:
              await api.read_message()
      except websockets.exceptions.ConnectionClosed:
          print("Lost connection to Neuro")
      except Exception as e:
          print(f"Unexpected error: {e}")

Deprecated Methods
------------------

.. deprecated:: 2.1.0
   ``read_raw_message`` has been deprecated. Use ``read_raw_server_message`` from the parent class instead.

Dependencies
------------

This module builds upon:

- ``neuro_api.client``: Abstract websocket client interface
- ``neuro_api.command``: Command formatting and validation
- ``neuro_api._deprecate``: Deprecation utilities

License
-------

This module is licensed under the GNU Lesser General Public License Version 3.

.. note::
   Copyright (C) 2025 CoolCat467. This program is free software and comes with ABSOLUTELY NO WARRANTY.
