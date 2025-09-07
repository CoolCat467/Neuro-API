Client Module
=============

.. currentmodule:: neuro_api.client

The client module provides an abstract base class for implementing Neuro
API websocket clients. This module defines the core interface and
message handling functionality for communicating with the Neuro Game
Interaction API.

Overview
--------

The client module contains the foundational components needed to build a
websocket client that can communicate with the Neuro system. It provides
message parsing, validation, and abstract methods that must be
implemented by concrete client classes.

Classes
-------

NeuroMessage
~~~~~~~~~~~~

.. autoclass:: NeuroMessage
   :members:

   A TypedDict that defines the schema for incoming messages from both server and client connections.

   The message structure follows the Neuro Game SDK API specification:

   - **command** (str): Unique identifier for the websocket command
   - **game** (NotRequired[str]): Game name identifier (present in client messages, absent in server messages)
   - **data** (NotRequired[dict[str, object]]): Optional data associated with the command

   .. seealso::
      For complete specification details, see the `Neuro SDK API Specification <https://github.com/VedalAI/neuro-sdk/blob/main/API/SPECIFICATION.md#neuro-api-specification>`_.

AbstractNeuroAPIClient
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: AbstractNeuroAPIClient
   :members:

   Abstract base class providing the core interface for Neuro API websocket clients.

   This class defines the essential methods for websocket communication
   and message handling. Concrete implementations must provide the
   websocket I/O operations while inheriting the message parsing and
   command handling functionality.

Abstract Methods
~~~~~~~~~~~~~~~~

These methods must be implemented by subclasses:

.. automethod:: AbstractNeuroAPIClient.write_to_websocket
.. automethod:: AbstractNeuroAPIClient.read_from_websocket

Concrete Methods
~~~~~~~~~~~~~~~~

These methods are provided by the base class:

.. automethod:: AbstractNeuroAPIClient.send_command_data
.. automethod:: AbstractNeuroAPIClient.read_raw_full_message
.. automethod:: AbstractNeuroAPIClient.read_raw_server_message
.. automethod:: AbstractNeuroAPIClient.read_raw_client_message
.. automethod:: AbstractNeuroAPIClient.handle_unknown_command
.. automethod:: AbstractNeuroAPIClient.read_message

Usage Example
-------------

Here's a basic example of how to implement a concrete client:

.. code-block:: python

   import asyncio
   import websockets
   from neuro_api.client import AbstractNeuroAPIClient

   class MyNeuroClient(AbstractNeuroAPIClient):
       def __init__(self, websocket):
           self.websocket = websocket

       async def write_to_websocket(self, data: str) -> None:
           await self.websocket.send(data)

       async def read_from_websocket(self) -> str:
           return await self.websocket.recv()

       async def handle_unknown_command(self, command: str, data: dict | None) -> None:
           print(f"Received command: {command} with data: {data}")

   async def main():
       uri = "ws://localhost:8000"
       async with websockets.connect(uri) as websocket:
           client = MyNeuroClient(websocket)

           # Read messages in a loop
           while True:
               try:
                   await client.read_message()
               except websockets.exceptions.ConnectionClosed:
                   break

   asyncio.run(main())

Message Flow
------------

The client handles two types of message flows:

Server Messages
~~~~~~~~~~~~~~~

Messages received from the Neuro server contain:

- ``command``: The command identifier
- ``data`` (optional): Associated command data

Use ``read_raw_server_message()`` to parse these messages.

Client Messages
~~~~~~~~~~~~~~~

Messages from other game clients contain:

- ``command``: The command identifier
- ``game``: The source game identifier
- ``data`` (optional): Associated command data

Use ``read_raw_client_message()`` to parse these messages.
