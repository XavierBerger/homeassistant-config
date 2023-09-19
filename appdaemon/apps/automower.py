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
from datetime import datetime

import appdaemon.plugins.hass.hassapi as hass
import pytz

#
# Automower App
#
# Args:
#  message_park_because_of_rain: "It starts raining, park until rain stops and lawn dries."
#  message_end_of_session_soon: "End session is in less than 1 hour, stay parked."
#  message_lawn_is_dry: "No rain during last 6h. Lawn should be dry now."
#  message_activated: "Advanced automation is activated."
#  message_deactivated: "Advanced automation is deactivated."

#
# End session management:
#   If remaining duration of mowing after next start is less than 1 hour, stay parked
#
# Rain management:
#   When it starts raining, go to dock or stay parcked for maximum possible duration (42 days)
#   When sun is at its top, if no rain occurs during the 6 previous hours, restart mowing
#   If no rain occurs during the 6 previous hours and sun is setting, restart mowing
#
# Automation management:
#   This automation is active only automower is not "parked until further notice"
#   This verification is designed to be sure that manual order will never be overwritten
#
# Notification:
#   Notification are sent to Telegram. This allow to have an history of what happen and when it happens.


class Automower(hass.Hass):
    def initialize(self):
        """
        Initialize the Automower Automation.
        """
        self.log("Starting Automower Automation")

        # Handles to register / unregister callbacks
        self.state_handles = []

        # Max duration time is used to park automover when it's raining (max = 42 days)
        self.park_max_duration = self.get_state("number.nono_park_for", attribute="max")
        self.log(f"\tpark max duration : {self.park_max_duration}")

        # This sensor tells if 'sheddule' or 'park until further notice' has been activated
        self.listen_state(self.callback_automower_automation, "sensor.nono_problem_sensor", immediate=True)

    ####################################################################################################################
    # UTILITIES
    ####################################################################################################################

    def log_parked_because_of_rain(self):
        """
        Log the status of the 'parked_because_of_rain' binary sensor.
        """
        self.log(f"\tbinary_sensor.parked_because_of_rain: {self.get_state('binary_sensor.parked_because_of_rain')}")

    def send_notification(self, **kwargs):
        """
        Send a notification.
        """
        self.log("Send notification")
        self.log(f"\tMessage: {kwargs['message']}")
        self.call_service(service="telegram_bot/send_message", title="🏡 Nono", **kwargs)

    def service(self, message, command, **kwargs):
        """
        Call a service and send a notification.
        """
        self.log("Call service")
        self.log(f"\t{command} ({kwargs})")
        self.call_service(command, **kwargs)
        self.send_notification(message=message, disable_notification=True)

    def force_park(self, message, duration):
        """
        Force the Automower to park for a specific duration.
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
        """
        self.service(
            message=self.args["message_lawn_is_dry"],
            command="vacuum/start",
            entity_id="vacuum.nono",
        )
        self.set_state("binary_sensor.parked_because_of_rain", state="off")

    ####################################################################################################################
    # APPLICATION MANAGEMENT
    ####################################################################################################################

    def callback_automower_automation(self, entity, attribute, old, new, kwargs):
        """
        Callback for automower automation activation.
        """
        # self.log(f"new={new}")
        if new == "parked_until_further_notice":
            # Deregister callbacks
            while len(self.state_handles) >= 1:
                handle = self.state_handles.pop()
                self.cancel_listen_state(handle)
            message = self.args["message_deactivated"]
        elif new in ["week_schedule", "charging"]:
            if len(self.state_handles) != 0:
                # callback are already registred. No need to register again
                return

            # register callbacks
            # Listen for rain sensors
            self.state_handles.append(self.listen_state(self.callback_rain_changed, "sensor.rain_last_6h"))

            # Listen for sun start to decrease
            self.state_handles.append(
                self.listen_state(self.callback_sun_is_at_top, "sun.sun", attribute="rising", new=False)
            )

            # Listen next start
            self.state_handles.append(
                self.listen_state(
                    self.callback_next_start_changed,
                    "sensor.nono_next_start",
                    immediate=True,
                )
            )
            message = self.args["message_activated"]
        else:
            # Robot is mowing or having an error
            return

        self.log("Automower automation activation triggered")
        self.log(f"\t{message}")
        self.send_notification(message=message)

    ####################################################################################################################
    # RAIN MANAGEMENT
    ####################################################################################################################

    def callback_rain_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling rain sensor changes.
        """
        self.log("Rain event triggered")
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
                message=self.args["message_park_because_of_rain"],
                duration=60480,
            )
        elif new_value == 0.0:
            # No rain occurs during last 6 hours and sun is setting
            if self.get_state("sun.sun", attribute="rising"):
                message = "No rain during last 6h, waiting for noon to restart."
                self.log(message)
                self.send_notification(message=message, disable_notification=True)
            elif self.get_state("sun.sun") == "below_horizon":
                message = "No rain during last 6h, sun is below horizon, waiting for tomorow noon to restart."
                self.log(f"\t{message}")
                self.send_notification(message=message, disable_notification=True)
            else:
                self.restart_after_rain()
        else:
            # It is still raining or rain has stopped recently
            self.log("\tRain occured during last 6h, lawn shouldn't be dry yet.")
        self.log_parked_because_of_rain()

    def callback_sun_is_at_top(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling sun position changes.
        """
        self.log("Sun event triggered")
        self.log_parked_because_of_rain()
        if self.get_state("binary_sensor.parked_because_of_rain") == "on":
            if self.get_state("sensor.rain_last_6h") == 0.0:
                self.restart_after_rain()
            else:
                message = "Lawn shouldn't be dry yet. Staying parked."
                self.log(f"\t{message}")
                self.send_notification(message=message, disable_notification=True)
        else:
            message = "Not park because of rain. Nothing to do."
            self.log(f"\t{message}")
        self.log_parked_because_of_rain()

    ####################################################################################################################
    # SESSION MANAGEMENT
    ####################################################################################################################

    def callback_next_start_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling changes in the next start time.
        """
        self.log("Next start event triggered")
        if self.get_state("binary_sensor.parked_because_of_rain") == "on":
            message = "Robot is parked because of rain. Nothing to check."
            self.log(f"\t{message}")
            self.send_notification(message=message, disable_notification=True)
            return

        self.log(f"\told={old}")
        self.log(f"\tnew={new}")

        # If robot is currently mowing, we don't have next start
        if new == "unknown":
            message = "Robot is currently mowing, let it come back to base before checking."
            self.log(f"\t{message}")
            self.send_notification(message=message, disable_notification=True)
            return

        # Get next end of session
        mowing_session_end = datetime.strptime(
            self.get_state("calendar.nono", attribute="end_time"), "%Y-%m-%d %H:%M:%S"
        )

        print(f"self.get_timezone() = {self.get_timezone()}")
        local = pytz.timezone(self.get_timezone())
        mowing_session_end_utc = local.localize(mowing_session_end, is_dst=None).astimezone(pytz.utc)

        self.log(f"\tMowing session will end at {mowing_session_end} => {mowing_session_end_utc} UTC")

        # Get next start
        next_start_utc = datetime.strptime(new, "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=pytz.utc)
        next_start = next_start_utc.astimezone(local)

        # Check delta and decide action to perform
        delta = (mowing_session_end_utc - next_start_utc).total_seconds() / 3600
        self.log(f"\tNext start is planned at {next_start} => {next_start_utc} UTC")
        self.log(f"\tThe number of hour before mowing session end is {delta}")
        if delta < 0:
            message = f"Session completed. Lets restart tomorrow at {next_start}"
            self.log(f"\t{message}")
            self.send_notification(message=message, disable_notification=True)
        elif delta < 1:
            self.log(f"\t{self.args['message_end_of_session_soon']}")
            self.force_park(
                message=self.args["message_end_of_session_soon"],
                duration=180,
            )
        else:  # delta >= 1
            message = f"Duration between next start ({next_start}) and end of session is greater than 1 hour."
            self.log(f"\t{message}")
            self.send_notification(message=f"Next start planned at {next_start}", disable_notification=True)
