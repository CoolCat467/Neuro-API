Event Module
============

Overview
--------
Event Handling for Neuro API Components.

The event module provides abstractions for managing event-driven interactions
in the Neuro game automation system. It combines the functionality of
libcomponent's Component system with the Neuro API to create a seamless
interface for handling game actions and events.

Key Features
------------
* Event-driven action handling with libcomponent integration
* Automatic action registration and cleanup
* Temporary action groups with auto-unregistration
* Built-in result handling and error management
* Seamless integration between Component system and Neuro API

Dependencies
------------
This module builds upon:

* ``libcomponent.component`` - Provides the Component and Event system
* ``neuro_api.api`` - Core Neuro API functionality (AbstractNeuroAPI, NeuroAction)
* ``neuro_api.command`` - Action definitions

Classes
-------

AbstractNeuroAPIComponent
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: neuro_api.event.AbstractNeuroAPIComponent
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   This class serves as a base component for event-driven
   interactions with the Neuro API, handling action registration,
   event routing, and component management.

   **Inheritance:**

   * Inherits from ``libcomponent.component.Component`` for event system integration
   * Inherits from ``neuro_api.api.AbstractNeuroAPI`` for Neuro communication

   **Automatic Features:**

   * Action registration with Neuro
   * Event routing for received actions (prefixed with ``neuro_``)
   * Result sending back to Neuro
   * Cleanup of temporary actions on success
   * Component lifecycle management

Usage Examples
--------------

Basic Action Registration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from neuro_api.event import AbstractNeuroAPIComponent
   from neuro_api.command import Action

   class MyGameComponent(AbstractNeuroAPIComponent):
       def __init__(self):
           super().__init__("my_game", "My Game Title")

       async def setup_actions(self):
           async def move_handler(action):
               # Handle movement action
               print(f"Moving player with data: {action.data}")
               return True, "Moved successfully"

           await self.register_neuro_actions([
               (Action("move", "Move the player", {"type": "object"}), move_handler)
           ])

Temporary Action Groups
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Register actions that auto-cleanup when any succeeds
   action_group = await component.register_temporary_actions_group([
       (Action("option_a", "Choose option A"), handle_option_a),
       (Action("option_b", "Choose option B"), handle_option_b),
       (Action("option_c", "Choose option C"), handle_option_c),
   ])

   # Use the group in a forced action
   await component.send_force_action(
       "Choose an option",
       "Please select one of the available options",
       action_group
   )

Individual Temporary Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Register actions that self-unregister on success
   await component.register_temporary_actions([
       (Action("confirm", "Confirm action"), handle_confirm),
       (Action("cancel", "Cancel action"), handle_cancel),
   ])

Event Flow
----------

The typical event flow in the system:

1. **Registration Phase:**

   * Actions are registered with Neuro via ``register_neuro_actions()``
   * Handler functions are bound to component event system
   * Event names are prefixed with ``neuro_`` (e.g., ``move`` → ``neuro_move``)

2. **Action Processing:**

   * Neuro sends action requests to the component
   * ``handle_action()`` receives the NeuroAction
   * Component raises internal event using libcomponent's Event system
   * Registered handlers process the actions asynchronously

3. **Result Handling:**

   * Handler functions return ``(success: bool, message: str | None)``
   * Results are automatically sent back to Neuro
   * Temporary actions are cleaned up if successful

4. **Error Management:**

   * Failed actions can be retried by returning ``(False, error_message)``
   * Successful actions with warnings return ``(True, warning_message)``
   * Unhandled actions raise ``ValueError`` exceptions

Handler Function Signatures
----------------------------

Standard Handler
~~~~~~~~~~~~~~~~

.. code-block:: python

   async def action_handler(neuro_action: NeuroAction) -> tuple[bool, str | None]:
       """
       Args:
           neuro_action: The action received from Neuro

       Returns:
           tuple: (success_flag, optional_message)
               - success_flag: True if action succeeded, False otherwise
               - optional_message: Context message for success, error message for failure
       """
       # Process the action
       if success:
           return True, "Action completed successfully"
       else:
           return False, "Action failed: reason"

Raw Event Handler
~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def raw_event_handler(event: Event[NeuroAction]) -> None:
       """
       For use with register_neuro_actions_raw_handler()

       Args:
           event: libcomponent Event containing NeuroAction data
       """
       neuro_action = event.data
       # Handle action directly, manage results manually

Integration with Component System
----------------------------------

The AbstractNeuroAPIComponent leverages libcomponent's event system:

* **Event Names:** Neuro actions become component events with ``neuro_`` prefix
* **Component Manager:** Must be bound to a ComponentManager to function
* **Event Propagation:** Events can bubble up through component hierarchies
* **Handler Management:** Automatic cleanup when components are removed

Error Handling
--------------

The component provides comprehensive error handling:

* **Network Errors:** Connection issues propagate from the underlying client
* **Protocol Errors:** Invalid messages raise appropriate exceptions
* **Handler Errors:** Unhandled actions raise ``ValueError`` with context
* **Binding Errors:** ``AttributeError`` raised when component not bound to manager
* **Registration Errors:** ``ValueError`` for duplicate or invalid action names

Implementation Notes
--------------------

* Actions are automatically unregistered when components are removed from managers
* Temporary actions use wrapper functions to handle cleanup logic
* The ``_send_result_wrapper`` method bridges handler return values to Neuro responses
* Component binding is required before action registration can occur
