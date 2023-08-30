# The MIT License (MIT)
#
# Copyright © 2023 Xavier Berger
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the “Software”), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import appdaemon.plugins.hass.hassapi as hass

#
# Garage door App
#
# Args:
#    sun: sun.sun
#    notification_delay: 600
#    door_state: binary_sensor.porte_garage_opening

#
# Send a notification when sun is below horizon and garage door is style open
# based on following conditions:
#   - When door is open when sun is passing below horizon
#   - When door is open during the night and not closed after 10 minutes
#


class GarageDoor(hass.Hass):
    def initialize(self):
        """
        Initialize the GarageDoor application.

        This method sets up the necessary listeners and handles for the GarageDoor application.
        It registers callbacks for starting and stopping automation based on sun position.

        Returns:
            None
        """
        self.log("Starting GarageDoor")

        # Handles to register / unregister callbacks
        self.state_handles = []
        self.delayed_notification_handle = None

        # Activate/deactivate automation based on sun
        self.listen_state(
            self.callback_start_automation,
            self.args["sun"],
            new="below_horizon",
            immediate=True,
        )
        self.listen_state(
            self.callback_stop_automation,
            self.args["sun"],
            new="above_horizon",
            immediate=True,
        )

    def callback_start_automation(self, entity, attribute, old, new, kwargs):
        """
        Callback for starting the garage door automation.

        This method is called when conditions are met to start the garage door automation.
        It sets up listeners for garage door state changes.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        # Start automation
        self.log("Garage door Automation is started")
        # Start listening for garage states
        self.state_handles.append(
            self.listen_state(
                self.callback_garage_door_open,
                self.args["door_state"],
                new="on",
                immediate=True,
            )
        )
        self.state_handles.append(
            self.listen_state(
                self.callback_garage_door_close,
                self.args["door_state"],
                new="off",
                immediate=True,
            )
        )

    def callback_stop_automation(self, entity, attribute, old, new, kwargs):
        """
        Callback for stopping the garage door automation.

        This method is called when conditions are met to stop the garage door automation.
        It deregisters all the garage door state change callbacks.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        # Deregister garage door state change callbacks
        while len(self.state_handles) >= 1:
            handle = self.state_handles.pop()
            self.cancel_listen_state(handle)
        self.log("Garage door Automation is stopped")

    def callback_garage_door_open(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling the garage door opening.

        This method is called when the garage door opens. It determines whether to send an immediate
        notification or schedule a delayed notification based on the sun's position.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        # Automation is triggered only when sun is below horizon and door is open (new = on)
        if old in ["on", None]:
            # Door is open during sunset
            self.log("Door is open during sunset => send notification")
            self.send_notification(None)
        else:
            # Door was closed and is opening.
            self.log("Door is open while sun is below horizon => trigger delayed notification")
            self.delayed_notification_handle = self.run_in(self.send_notification, self.args["notification_delay"])

    def callback_garage_door_close(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling the garage door closing.

        This method is called when the garage door closes. If there is a pending delayed notification,
        it cancels the notification timer.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        # Automation is triggered only when sun is below horizon and door is closed (new = off)
        if self.delayed_notification_handle is not None:
            self.log("Cancel delayed notification")
            self.cancel_timer(self.delayed_notification_handle)
            self.delayed_notification_handle = None

    def send_notification(self, kwargs):
        """
        Send a notification about the open garage door.

        This method sends a notification saying tha the garage door is open during nighttime.

        Args:
            kwargs: Additional keyword arguments (not used in this method).

        Returns:
            None
        """
        # Send notification
        self.log("Send notification")
        self.fire_event(
            "NOTIFIER",
            action="send_to_present",
            title=self.args["notification_title"],
            message=self.args["notification_message"],
            icon="mdi-garage-open",
            color="deep-orange",
            tag="garage_open",
            until=[
                {"entity_id": self.args["door_state"], "new_state": "off"},
                {"entity_id": self.args["sun"], "new_state": "above_horizon"},
            ],
        )
        self.delayed_notification_handle = None
