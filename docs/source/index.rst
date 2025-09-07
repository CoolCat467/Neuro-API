Neuro-API Documentation
=======================

Welcome to the Neuro-API documentation. This library provides a comprehensive
Python interface for integrating games with the Neuro AI system through
WebSocket communication.

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   command
   api
   client
   event
   trio_ws
   server

Overview
========

The Neuro-API library enables real-time communication between games and the
Neuro AI system. It provides:

* **Command System**: Structured command definitions and validation
* **Client Interface**: Abstract and concrete client implementations
* **Event System**: Event-driven component architecture
* **Server Infrastructure**: WebSocket servers for hosting Neuro services
* **Trio Integration**: Async support using the Trio framework

Quick Start
===========

For game developers wanting to integrate with Neuro:

1. Use ``TrioNeuroAPIComponent`` for event-driven integration
2. Register actions that Neuro can perform in your game
3. Handle context updates and action requests
4. Connect to the Neuro WebSocket service

For developers building Neuro-compatible servers:

1. Extend ``AbstractTrioNeuroServer``
2. Implement AI decision-making logic
3. Handle multiple game client connections
4. Deploy with SSL/TLS for production

Module Overview
===============

Core Modules
------------

* **command**: Command definitions, validation, and protocol messages
* **api**: Abstract base classes for Neuro API communication
* **client**: WebSocket client abstractions and utilities

Integration Modules
-------------------

* **event**: Event-driven component system for game integration
* **trio_ws**: Trio-based WebSocket implementations
* **server**: WebSocket server infrastructure and implementations

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
