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
from unittest import mock

import pytest
from apps.automower import Automower

from .appdaemon_testing.pytest import (  # pylint: disable=W0611
    automation_fixture,
    hass_driver,
)


@automation_fixture(
    Automower,
    args={
        "message_title": "Nono",
        "message_park_because_of_rain": "It starts raining, park until rain stops and lawn dries.",
        "message_end_of_session_soon": "End session is in less than 1 hour, stay parked.",
        "message_lawn_is_dry": "No rain during last 6h. Lawn should be dry now.",
        "message_activated": "Advanced automation is activated.",
        "message_deactivated": "Advanced automation is deactivated.",
    },
    initialize=False,
)
def automower() -> Automower:
    pass


@pytest.mark.automower
class TestAutomowerSession:
    # pylint: disable=W0621
    def test__callback_next_start_changed__session_completed(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the session is completed.
        """
        # GIVEN
        #   Robot is not parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "2023-08-04T18:30:00+00:00")
            hass_driver.set_state("calendar.nono", "2023-08-03 11:00:00", attribute_name="start_time")
            hass_driver.set_state("calendar.nono", "2023-08-03 19:00:00", attribute_name="end_time")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()
        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mock()

        # WHEN
        #   Next start is defined as tomorrow
        hass_driver.set_state("sensor.nono_next_start", "2023-08-04T09:00:00+00:00")

        # THEN
        #   Session is completed, wait until tomorrow.
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-04T18:30:00+00:00"),
                mock.call("\tnew=2023-08-04T09:00:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00 => 2023-08-03 17:00:00+00:00 UTC"),
                mock.call("\tNext start is planned at 2023-08-04 11:00:00+02:00 => 2023-08-04 09:00:00+00:00 UTC"),
                mock.call("\tThe number of hour before mowing session end is -16.0"),
                mock.call("\tSession completed. Lets restart tomorrow at 2023-08-04 11:00:00+02:00"),
                mock.call("Send notification"),
                mock.call("\tMessage: Session completed. Lets restart tomorrow at 2023-08-04 11:00:00+02:00"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Session completed. Lets restart tomorrow at 2023-08-04 11:00:00+02:00",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_next_start_changed__too_short_session(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the remaining session duration is too short.
        """
        # GIVEN
        #   Robot is not parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "2023-08-03T18:30:00+00:00")
            hass_driver.set_state("calendar.nono", "2023-08-03 11:00:00", attribute_name="start_time")
            hass_driver.set_state("calendar.nono", "2023-08-03 19:00:00", attribute_name="end_time")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Next start is 26 minutes before end of session
        hass_driver.set_state("sensor.nono_next_start", "2023-08-03T16:34:00+00:00")

        # THEN
        #   Stay parked for 3 hours (180min)
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-03T18:30:00+00:00"),
                mock.call("\tnew=2023-08-03T16:34:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00 => 2023-08-03 17:00:00+00:00 UTC"),
                mock.call("\tNext start is planned at 2023-08-03 18:34:00+02:00 => 2023-08-03 16:34:00+00:00 UTC"),
                mock.call("\tThe number of hour before mowing session end is 0.43333333333333335"),
                mock.call("\tEnd session is in less than 1 hour, stay parked."),
                mock.call("Call service"),
                mock.call("\tnumber/set_value ({'entity_id': 'number.nono_park_for', 'value': 180})"),
                mock.call("Send notification"),
                mock.call("\tMessage: End session is in less than 1 hour, stay parked."),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("number/set_value", entity_id="number.nono_park_for", value=180),
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="End session is in less than 1 hour, stay parked.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_next_start_changed__good_session(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the remaining session duration is sufficient.
        """
        # GIVEN
        #   Robot is not parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "2023-08-03T15:30:00+00:00")
            hass_driver.set_state("calendar.nono", "2023-08-03 11:00:00", attribute_name="start_time")
            hass_driver.set_state("calendar.nono", "2023-08-03 19:00:00", attribute_name="end_time")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mock()

        # WHEN
        #   Next start is 1h26min before end of session
        hass_driver.set_state("sensor.nono_next_start", "2023-08-03T13:34:00+00:00")

        # THEN
        #   Let mowing session continue
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-03T15:30:00+00:00"),
                mock.call("\tnew=2023-08-03T13:34:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00 => 2023-08-03 17:00:00+00:00 UTC"),
                mock.call("\tNext start is planned at 2023-08-03 15:34:00+02:00 => 2023-08-03 13:34:00+00:00 UTC"),
                mock.call("\tThe number of hour before mowing session end is 3.433333333333333"),
                mock.call(
                    "\tDuration between next start (2023-08-03 15:34:00+02:00) "
                    "and end of session is greater than 1 hour."
                ),
                mock.call("Send notification"),
                mock.call("\tMessage: Next start planned at 2023-08-03 15:34:00+02:00"),
            ]
        )

        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Next start planned at 2023-08-03 15:34:00+02:00",
                    disable_notification=True,
                )
            ]
        )

    def test__callback_next_start_changed__currently_mowing(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the robot is currently mowing.
        """
        # GIVEN
        #   Robot is not parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("calendar.nono", "2023-08-03 11:00:00", attribute_name="start_time")
            hass_driver.set_state("calendar.nono", "2023-08-03 19:00:00", attribute_name="end_time")
            hass_driver.set_state("sensor.nono_next_start", "2023-08-03T15:34:00+00:00")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Next start is 1h26min before end of session
        hass_driver.set_state("sensor.nono_next_start", "unknown")

        # THEN
        #   Let mowing session continue
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-03T15:34:00+00:00"),
                mock.call("\tnew=unknown"),
                mock.call("\tRobot is currently mowing, let it come back to base before checking."),
                mock.call("Send notification"),
                mock.call("\tMessage: Robot is currently mowing, let it come back to base before checking."),
            ]
        )
