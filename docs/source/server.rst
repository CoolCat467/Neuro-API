Server Module
=============

Overview
--------
Neuro Websocket API Server Implementation.

The server module provides a complete WebSocket server infrastructure for hosting
Neuro AI game integration services. It manages client connections, handles the
WebSocket protocol, and provides both abstract interfaces and concrete implementations
for AI-powered game interaction capabilities.

Key Features
------------
* **Multi-Client Management**: Handle multiple simultaneous game client connections
* **Structured Concurrency**: Built on Trio's async framework for reliable task management
* **WebSocket Server**: Complete WebSocket server implementation with SSL support
* **Action Registry**: Dynamic action management with registration and unregistration
* **Development Tools**: Interactive console server for testing and debugging

Architecture Overview
---------------------

The server module follows a layered architecture:

**Base Layer (AbstractNeuroServerClient)**
  Abstract interface defining the core client communication protocol

**Handler Layer (AbstractHandlerNeuroServerClient)**
  Adds ID generation, action tracking, and basic command handling

**Recording Layer (AbstractRecordingNeuroServerClient)**
  Implements action registry management and storage

**Implementation Layer (BaseTrioNeuroServerClient, TrioNeuroServerClient)**
  Concrete WebSocket communication using trio-websocket

**Server Layer (AbstractTrioNeuroServer)**
  Server coordination and multi-client management

Classes
-------

Data Types
~~~~~~~~~~

.. autoclass:: neuro_api.server.ContextData
   :members:
   :undoc-members:

.. autoclass:: neuro_api.server.ActionSchema
   :members:
   :undoc-members:

.. autoclass:: neuro_api.server.RegisterActionsData
   :members:
   :undoc-members:

.. autoclass:: neuro_api.server.UnregisterActionsData
   :members:
   :undoc-members:

.. autoclass:: neuro_api.server.ForceActionsData
   :members:
   :undoc-members:

.. autoclass:: neuro_api.server.ActionResultData
   :members:
   :undoc-members:

Utility Functions
~~~~~~~~~~~~~~~~~

.. autofunction:: neuro_api.server.deserialize_actions

.. autofunction:: neuro_api.server.check_action_names_type

Abstract Base Classes
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: neuro_api.server.AbstractNeuroServerClient
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Abstract base class for Neuro Server Client communication. Defines the core
   interface for bidirectional communication between server and client.

.. autoclass:: neuro_api.server.AbstractHandlerNeuroServerClient
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Extends AbstractNeuroServerClient with ID generation, action tracking,
   and basic command handling infrastructure.

.. autoclass:: neuro_api.server.AbstractRecordingNeuroServerClient
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Adds concrete action registry management with dynamic registration,
   unregistration, and storage capabilities.

Concrete Implementations
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: neuro_api.server.BaseTrioNeuroServerClient
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Trio-based WebSocket implementation providing concrete communication layer.

.. autoclass:: neuro_api.server.TrioNeuroServerClient
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Complete client implementation with server integration for production use.

Server Classes
~~~~~~~~~~~~~~

.. autoclass:: neuro_api.server.AbstractTrioNeuroServer
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Abstract base class for Trio-based Neuro AI servers providing WebSocket
   server infrastructure and multi-client management.

.. autoclass:: neuro_api.server.ConsoleInteractiveNeuroServer
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Console-based interactive server implementation for development and testing.

Usage Examples
--------------

Basic Server Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from neuro_api.server import AbstractTrioNeuroServer
   from neuro_api.command import Action

   class MyNeuroServer(AbstractTrioNeuroServer):
       def add_context(self, game_title, message, reply_if_not_busy):
           print(f"[{game_title}] Context: {message}")
           # Forward to your AI system

       async def choose_force_action(self, game_title, state, query,
                                   ephemeral_context, actions):
           # Implement AI decision logic
           selected_action = actions[0]  # Simple selection
           action_data = '{"param": "value"}'  # Generate data
           return selected_action.name, action_data

   # Start server
   server = MyNeuroServer()
   await server.run("localhost", 8000)

Development Server
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from neuro_api.server import ConsoleInteractiveNeuroServer
   import trio

   async def main():
       server = ConsoleInteractiveNeuroServer()
       await server.run("localhost", 8000)

   trio.run(main)

Custom Client Handler
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from neuro_api.server import AbstractRecordingNeuroServerClient

   class CustomClient(AbstractRecordingNeuroServerClient):
       def add_context(self, message, reply_if_not_busy):
           # Custom context handling
           self.log_info(f"Game context: {message}")

       async def choose_force_action(self, state, query, ephemeral_context, action_names):
           # Custom AI integration
           return await self.ai_system.choose_action(
               state, query, list(action_names)
           )

       async def submit_call_async_soon(self, function):
           # Schedule with custom task manager
           await self.task_scheduler.schedule(function)

Protocol Flow
-------------

Connection Lifecycle
~~~~~~~~~~~~~~~~~~~~

1. **Client Connection**

   * WebSocket handshake
   * Client registration in server registry
   * TrioNeuroServerClient instance creation

2. **Game Initialization**

   * Client sends ``startup`` command
   * Server clears previous actions
   * Game title registration

3. **Action Management**

   * Client registers actions via ``actions/register``
   * Actions stored in client registry
   * Dynamic registration/unregistration supported

4. **Game Interaction**

   * Context updates via ``context`` command
   * Forced actions via ``actions/force``
   * Action execution and results

5. **Disconnection**

   * Automatic cleanup of client registry
   * Resource cleanup via context managers

Message Processing
~~~~~~~~~~~~~~~~~~

The server processes these command types:

* ``startup``: Initialize game session
* ``context``: Add contextual information
* ``actions/register``: Register new actions
* ``actions/unregister``: Remove actions
* ``actions/force``: Force action selection
* ``action/result``: Report action outcomes
* ``shutdown/ready``: Confirm shutdown readiness

Action Force Flow
~~~~~~~~~~~~~~~~~

.. code-block:: text

   Client                    Server                     AI System
   ------                    ------                     ---------
   actions/force      -->    choose_force_action  -->   [AI Decision]
                       <--   action command        <--
   action/result      -->    handle_action_result
                       <--   [retry if failed]

Error Handling
--------------

Connection Errors
~~~~~~~~~~~~~~~~~

* **WebSocket Disconnection**: Automatic client cleanup
* **Protocol Errors**: Logged and connection terminated
* **Invalid Commands**: Error responses sent to client

Action Errors
~~~~~~~~~~~~~

* **Invalid Action Names**: Validation and error reporting
* **Schema Violations**: JSON schema validation failures
* **Missing Actions**: Graceful handling of unregistered actions

Server Errors
~~~~~~~~~~~~~

* **Startup Failures**: Critical error logging and shutdown
* **Resource Exhaustion**: Proper error propagation
* **AI System Failures**: Graceful degradation where possible

Configuration
-------------

Server Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Basic configuration
   await server.run("localhost", 8000)

   # SSL/TLS configuration
   import ssl
   ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
   ssl_context.load_cert_chain("server.crt", "server.key")
   await server.run("0.0.0.0", 8443, ssl_context=ssl_context)

Development and Testing
-----------------------

Interactive Development Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``ConsoleInteractiveNeuroServer`` provides a human-operated interface:

.. code-block:: bash

   $ python -m neuro_api.server

   # Interactive commands available:
   # help - Show available commands
   # list - Show connected clients and actions
   # send <client> <action> - Manually trigger actions
   # <enter> - Continue without action

Testing Client Connections
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Test with multiple clients
   import trio
   from neuro_api.trio_ws import TrioNeuroAPIComponent

   async def test_client():
       component = TrioNeuroAPIComponent("test_client", "Test Game")
       # Connect and test...

Performance Considerations
--------------------------

* **Memory Usage**: Scales with number of active clients and registered actions
* **Concurrency**: Built on Trio's structured concurrency for efficient scaling
* **Network I/O**: Async WebSocket handling prevents blocking on slow clients
* **Action Registry**: In-memory storage with O(1) action lookup

Integration Notes
-----------------

This module integrates with:

* ``neuro_api.api`` - Base API functionality
* ``neuro_api.command`` - Command definitions and validation
* ``neuro_api.client`` - Client interface definitions
* ``trio`` - Async runtime and structured concurrency
* ``trio-websocket`` - WebSocket protocol implementation

For production deployment, implement the abstract methods in ``AbstractTrioNeuroServer``
to integrate with your specific AI system and game infrastructure.
