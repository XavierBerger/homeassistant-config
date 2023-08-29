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
from datetime import datetime, timezone

import appdaemon.plugins.hass.hassapi as hass

#
# Automower App
#
# Args:
#

#
# End session management:
#   If remaining duration of mowing after next start is less than 1 hour, stay parked
#
# Rain management:
#   When it starts raining, go to dock or stay parcked for 24h
#   When sun is at its top, if no rain occurs during the 6 previous hours, restart mowing
#   If no rain occurs during the 6 previous hours and sun is setting, restart mowing
#
# Automation management:
#   Only activate this automation when "automower_automation" boolean input is on
#   Disable automation if automower is parked unti next order from another application


class Automower(hass.Hass):
    def initialize(self):
        """
        Initialize the Automower Automation.

        This method sets up the necessary listeners and handles for the Automower Automation.
        It registers a callback for monitoring the Automower's sensors and initializes
        parameters for the automation.

        Returns:
            None
        """
        self.log("Starting Automower Automation")

        # Handles to register / unregister callbacks
        self.state_handles = []

        self.park_max_duration = self.get_state("number.nono_park_for", attribute="max")
        self.log(f"\tpark max duration : {self.park_max_duration}")

        self.listen_state(self.callback_automower_automation, "sensor.nono_problem_sensor", immediate=True)

    def log_parked_because_of_rain(self):
        """
        Log the status of the 'parked_because_of_rain' binary sensor.

        This method logs the current state of the 'parked_because_of_rain' binary sensor.

        Returns:
            None
        """
        self.log(f"\tbinary_sensor.parked_because_of_rain: {self.get_state('binary_sensor.parked_because_of_rain')}")

    def send_notification(self, **kwargs):
        """
        Send a notification.

        This method sends a notification with the specified title and message.

        Args:
            kwargs: Keyword arguments containing the notification title and message.

        Returns:
            None
        """
        self.log("Send notification")
        self.log(f"\ttitle: {kwargs['title']}")
        self.log(f"\tMessage: {kwargs['message']}")
        self.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title=kwargs["title"],
            message=kwargs["message"],
            icon="mdi-robot-mower-outline",
            color="deep-orange",
            tag="nono",
        )

    def service(self, message, command, **kwargs):
        """
        Call a service and send a notification.

        This method calls a specified service with given keyword arguments and sends a notification
        with a specified title and message.

        Args:
            message (str): The message for the notification.
            command (str): The service command to call.
            kwargs: Keyword arguments for the service call.

        Returns:
            None
        """
        self.log("Call service")
        self.log(f"\t{command} ({kwargs})")
        self.call_service(command, **kwargs)
        self.send_notification(title="Nono", message=message)

    def force_park(self, message, duration):
        """
        Force the Automower to park for a specific duration.

        This method triggers a service call to set the parking duration for the Automower.

        Args:
            message (str): The message for the notification.
            duration (float): The duration for which the Automower should be parked.

        Returns:
            None
        """
        self.service(
            message=message,
            command="number/set_value",
            entity_id="number.nono_park_for",
            value=duration,
        )

    def restart_after_rain(self):
        """
        Restart the Automower after a period of rain.

        This method triggers a service call to restart the Automower and updates the state of the
        'parked_because_of_rain' binary sensor.

        Returns:
            None
        """
        self.service(
            message="No rain during last 6h. Lawn should be dry now.",
            command="vacuum/start",
            entity_id="vacuum.nono",
        )
        self.set_state("binary_sensor.parked_because_of_rain", state="off")

    def callback_automower_automation(self, entity, attribute, old, new, kwargs):
        """
        Callback for automower automation activation.

        This method is called when the Automower automation activation is triggered.
        It handles different automation scenarios based on the new state value.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.log("Automower automation activation triggered")
        prefix = "de" if new == "parked_until_further_notice" else ""
        message = f"Advanced automation is {prefix}activated."
        self.log(f"\t{message}")

        if new == "parked_until_further_notice":
            # Deregister callbacks
            while len(self.state_handles) >= 1:
                handle = self.state_handles.pop()
                self.cancel_listen_state(handle)
        elif new == "week_schedule":
            self.log_parked_because_of_rain()

            # register callbacks
            # Listen for rain sensors
            self.state_handles.append(self.listen_state(self.callback_rain_changed, "sensor.rain_last_6h"))

            # Listen for sun start to decreass
            self.state_handles.append(
                self.listen_state(self.callback_sun_is_at_top, "sun.sun", attribute="rising", new=False)
            )

            # Listen next start
            self.state_handles.append(
                self.listen_state(self.callback_next_start_changed, "sensor.nono_next_start", immediate=True)
            )
        self.send_notification(title="Nono", message=message)

    def callback_rain_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling rain sensor changes.

        This method is called when the rain sensor state changes. It handles different scenarios based
        on the rain sensor values to control the Automower's behavior during rain.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.log("Rain event triggered")
        self.log(f"\told={old}")
        self.log(f"\tnew={new}")
        self.log_parked_because_of_rain()

        try:
            old_value = float(old)
        except Exception:
            # at startup: old is None
            # if old is unavailable :
            #   let's considere that no rain occured
            old_value = 0.0

        try:
            new_value = float(new)
        except Exception:
            # if new is unavailable, we can't do anything
            return

        if (old_value == 0.0) and (new_value > 0.0):
            # Rain is starting
            self.set_state("binary_sensor.parked_because_of_rain", state="on")
            self.force_park(
                message="It starts raining, park until rain stops and lawn dries.",
                duration=60480,
            )
        elif new_value == 0.0:
            # No rain occurs during last 6 hours and sun is setting
            if self.get_state("sun.sun", attribute="rising"):
                self.log("No rain during last 6h, waiting for noon to restart.")
            elif self.get_state("sun.sun") == "below_horizon":
                self.log("No rain during last 6h, sun is below horizon, waiting for tomorow noon to restart.")
            else:
                self.restart_after_rain()
        else:
            # It is raining
            self.log("\tRain occured during last 6h, lawn shouldn't be dry yet.")
        self.log_parked_because_of_rain()

    def callback_sun_is_at_top(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling sun position changes.

        This method is called when the sun's position changes. It checks the state of the
        'parked_because_of_rain' binary sensor and the rain sensor to determine the Automower's behavior.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.log("Sun event triggered")
        self.log_parked_because_of_rain()
        if self.get_state("binary_sensor.parked_because_of_rain") == "on":
            if self.get_state("sensor.rain_last_6h") == 0.0:
                self.restart_after_rain()
            else:
                self.log("\tLawn shouldn't be dry yt. Staying parked.")
        else:
            self.log("\tNot park because of rain. Nothing to do.")
        self.log_parked_because_of_rain()

    def callback_next_start_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling changes in the next start time.

        This method is called when the next start time changes. It calculates the time difference
        between the next start and the end of the mowing session to determine the appropriate action.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.log("Next start event triggered")
        if self.get_state("binary_sensor.parked_because_of_rain") == "on":
            self.log("\tRobot is parked because of rain. Nothing to check.")
            return

        self.log(f"\told={old}")
        self.log(f"\tnew={new}")

        # If robot is currently mowing, we don't have next start
        if new == "unknown":
            self.log("Robot is currently mowing, let it come back to base before checking.")
            return

        # Get next end of session
        mowing_session_end = datetime.strptime(
            self.get_state("calendar.nono", attribute="end_time"), "%Y-%m-%d %H:%M:%S"
        ).astimezone(tz=None)
        self.log(f"\tMowing session will end at {mowing_session_end}")

        # Get next start
        next_start = datetime.strptime(new, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=timezone.utc).astimezone(tz=None)

        # Check delta and decide action to perform
        delta = (mowing_session_end - next_start).total_seconds() / 3600
        self.log(f"\tNext start is planned at {next_start}")
        self.log(f"\tThe number of hour before mowing session end is {delta}")
        if delta < 0:
            self.log("\tSession completed. Lets restart tomorrow.")
        elif delta < 1:
            self.log("\tDuration between next start and end of session is less than 1 hour, stay parked.")
            self.force_park(
                message="End session is in less than 1 hour, stay parked.",
                duration=180,
            )
        else:  # delta >= 1
            self.log("Duration between next start and end of session is greater than 1 hour.")
