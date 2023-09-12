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
class TestAutomowerRain:
    # pylint: disable=W0621
    def test__callback_rain_changed__rain_not_available(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain information is not available.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", "unknow")

        # THEN
        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

    def test__callback_rain_changed__no_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when there is no rain during the last 6 hours.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 0)

        # THEN
        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
                mock.call("Call service"),
                mock.call("\tvacuum/start ({'entity_id': 'vacuum.nono'})"),
                mock.call("Send notification"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__start_raining(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when it starts raining.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 0)
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            automower.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 1)

        # THEN
        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
                mock.call("Call service"),
                mock.call("\tnumber/set_value ({'entity_id': 'number.nono_park_for', 'value': 60480})"),
                mock.call("Send notification"),
                mock.call("\tMessage: It starts raining, park until rain stops and lawn dries."),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("number/set_value", entity_id="number.nono_park_for", value=60480),
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="It starts raining, park until rain stops and lawn dries.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__continue_raining(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when it continues raining.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 1)
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            automower.set_state("binary_sensor.parked_because_of_rain", True)
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 2)

        # THEN

        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
                mock.call("\tRain occured during last 6h, lawn shouldn't be dry yet."),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
            ]
        )

    def test__callback_rain_changed__rain_has_stopped_6h_ago_before_noon(self, hass_driver, automower: Automower):
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 1)
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("sun.sun", True, attribute_name="rising")
            automower.set_state("binary_sensor.parked_because_of_rain", True)
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()
        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 0)

        # THEN
        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
                mock.call("No rain during last 6h, waiting for noon to restart."),
                mock.call("Send notification"),
                mock.call("\tMessage: No rain during last 6h, waiting for noon to restart."),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="No rain during last 6h, waiting for noon to restart.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__rain_has_stopped_6h_ago_after_noon(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain has stopped more than 6 hours ago before noon.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 1)
            hass_driver.set_state("sun.sun", "above_horizon")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("sun.sun", False, attribute_name="rising")
            automower.set_state("binary_sensor.parked_because_of_rain", "on")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 0)

        # THEN

        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
                mock.call("Call service"),
                mock.call("\tvacuum/start ({'entity_id': 'vacuum.nono'})"),
                mock.call("Send notification"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__rain_has_stopped_6h_ago_sun_below_horizon(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain has stopped more than 6 hours ago and the sun is below
        the horizon.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 1)
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("sun.sun", False, attribute_name="rising")
            hass_driver.set_state("sun.sun", "below_horizon")
            automower.set_state("binary_sensor.parked_because_of_rain", True)
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 0)

        # THEN
        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
                mock.call("\tNo rain during last 6h, sun is below horizon, waiting for tomorow noon to restart."),
                mock.call("Send notification"),
                mock.call(
                    "\tMessage: No rain during last 6h, sun is below horizon, waiting for tomorow noon to restart."
                ),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="No rain during last 6h, sun is below horizon, waiting for tomorow noon to restart.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_no_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is no rain during the last 6 hours and the sun is at the top.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 0)
            hass_driver.set_state("sun.sun", "above_horizon")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("sun.sun", True, attribute_name="rising")
            automower.set_state("binary_sensor.parked_because_of_rain", "on")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sun.sun", False, attribute_name="rising")

        # THEN
        log.assert_has_calls(
            [
                mock.call("Sun event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
                mock.call("Call service"),
                mock.call("\tvacuum/start ({'entity_id': 'vacuum.nono'})"),
                mock.call("Send notification"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_still_rainning(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is rain during the last 6 hours and the sun is at the top.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.rain_last_6h", 1)
            hass_driver.set_state("sun.sun", "above_horizon")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            hass_driver.set_state("sun.sun", True, attribute_name="rising")
            automower.set_state("binary_sensor.parked_because_of_rain", "on")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()
        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mosk()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sun.sun", False, attribute_name="rising")

        # THEN
        log.assert_has_calls(
            [
                mock.call("Sun event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
                mock.call("\tLawn shouldn't be dry yet. Staying parked."),
                mock.call("Send notification"),
                mock.call("\tMessage: Lawn shouldn't be dry yet. Staying parked."),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
            ]
        )

        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Lawn shouldn't be dry yet. Staying parked.",
                    disable_notification=True,
                ),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_not_parked_because_of_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is no rain during the last 6 hours and the sun is at the top,
        but the automower is not parked because of rain.
        """
        # GIVEN
        #   no rain occurs during last 6h
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "unknown")
            automower.set_state("binary_sensor.parked_because_of_rain", "off")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        # Application is initialised
        hass_driver.set_state("sun.sun", False, attribute_name="rising")

        # THEN
        log.assert_has_calls(
            [
                mock.call("Sun event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
                mock.call("\tNot park because of rain. Nothing to do."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )
