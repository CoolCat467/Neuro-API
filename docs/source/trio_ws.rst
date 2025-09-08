trio_ws Module
==============

Overview
--------
Trio-websocket specific implementation for Neuro API interactions.

This module provides concrete implementations of the Neuro API using the
trio-websocket library for asynchronous websocket communication. It includes
both a basic API client and a full event-driven component for integration
with the libcomponent system.

Key Features
------------
* Async websocket communication using trio-websocket
* Automatic connection management and error handling
* Integration with trio's structured concurrency
* Event-driven component architecture
* Graceful connection cleanup and shutdown

Classes
-------

TrioNeuroAPI
~~~~~~~~~~~~

.. autoclass:: neuro_api.trio_ws.TrioNeuroAPI
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   A concrete implementation of AbstractNeuroAPI using trio-websocket
   for websocket communication. This class provides the core websocket
   functionality without the event system integration.

   **Connection Management:**

   * Manages websocket connection state
   * Provides connection status checking
   * Handles graceful connection setup and teardown

TrioNeuroAPIComponent
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: neuro_api.trio_ws.TrioNeuroAPIComponent
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   A full-featured component combining event-driven architecture with
   trio-websocket communication. This is the recommended class for most
   game integrations.

   **Event Handling:**

   * Automatic websocket connection management
   * Built-in message reading loop
   * Connection event handling
   * Graceful shutdown support

Usage Examples
--------------

Basic Usage with Component Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import trio
   from libcomponent.component import Event, ExternalRaiseManager
   from neuro_api.trio_ws import TrioNeuroAPIComponent

   async def main():
       async with trio.open_nursery() as nursery:
           manager = ExternalRaiseManager("game_manager", nursery)

           component = TrioNeuroAPIComponent("neuro_api", "My Game")
           manager.add_component(component)

           # Connect to websocket
           await manager.raise_event(Event("connect", "ws://localhost:8000"))

           # Wait for connection and setup
           await component.wait_for_websocket()

           if not component.not_connected:
               # Game logic here
               await trio.sleep(10)
               await component.stop()

Custom Connection Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class CustomGameComponent(TrioNeuroAPIComponent):
       def __init__(self, name, title):
           super().__init__(name, title)
           self.connection_ready = trio.Event()

       def websocket_connect_failed(self):
           print("Connection failed - retrying...")
           self.connection_ready.set()

       async def websocket_connect_successful(self):
           print("Successfully connected to Neuro!")
           await self.send_startup_command()
           await self.send_context("Game is ready!")
           self.connection_ready.set()

       async def wait_for_connection(self):
           await self.connection_ready.wait()

Direct API Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

   import trio
   import trio_websocket
   from neuro_api.trio_ws import TrioNeuroAPI

   async def direct_usage():
       async with trio_websocket.open_websocket_url("ws://localhost:8000") as ws:
           api = TrioNeuroAPI("My Game", ws)

           await api.send_startup_command()
           await api.send_context("Hello from my game!")

           # Read messages manually
           while True:
               try:
                   await api.read_message()
               except trio_websocket.ConnectionClosed:
                   break

Connection Management
---------------------

Connection States
~~~~~~~~~~~~~~~~~

The component manages several connection states:

* **Disconnected**: No websocket connection (``not_connected`` returns ``True``)
* **Connecting**: Websocket handshake in progress
* **Connected**: Active websocket connection ready for communication
* **Closing**: Connection shutdown initiated

Error Handling
~~~~~~~~~~~~~~

The implementation handles various error conditions:

* **HandshakeError**: Connection setup failures
* **ConnectionClosed**: Unexpected disconnections
* **BrokenResourceError**: Internal trio channel issues

Connection events trigger appropriate callbacks:

.. code-block:: python

   def websocket_connect_failed(self):
       """Called when websocket handshake fails"""
       # Custom error handling

   async def websocket_connect_successful(self):
       """Called when websocket connects successfully"""
       # Custom setup logic

Message Processing
------------------

The component automatically processes various message types:

* **action**: Neuro action requests
* **actions/reregister_all**: Action re-registration requests
* **shutdown/graceful**: Graceful shutdown requests
* **shutdown/immediate**: Immediate shutdown requests

Message processing runs in a continuous loop until the connection is closed
or ``stop()`` is called.

Component Management
~~~~~~~~~~~~~~~~~~~~

The ``TrioNeuroAPIComponent`` is designed to work with libcomponent's
``ExternalRaiseManager``. The component must be added to a manager
and the connection initiated through a "connect" event.

Shutdown Handling
~~~~~~~~~~~~~~~~~

The component supports graceful shutdown:

.. code-block:: python

   # Graceful shutdown with custom close code
   await component.stop(code=1001, reason="Game ended")

The ``stop()`` method cleanly closes the websocket connection and
sets the component to a disconnected state.
