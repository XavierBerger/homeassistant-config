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
class TestAutomowerActivation:
    # pylint: disable=W0621
    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__initialize__automation_activated(self, hass_driver, automower: Automower, parked_because_of_rain):
        """
        Test the initialization of the Automower automation when the robot is parked due to rain.
        """
        # GIVEN
        #   next_start is planned to "unknown" (robot is mowing)
        with hass_driver.setup():
            hass_driver.set_state("number.nono_park_for", 60480, attribute_name="max")
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", parked_because_of_rain)
            hass_driver.set_state("sensor.nono_next_start", "unknown")

        # WHEN
        #   Application is starting
        automower.initialize()

        # THEN
        #   4 callback are set
        listen_state = hass_driver.get_mock("listen_state")
        assert listen_state.call_count == 4

        assert hass_driver.get_number_of_state_callbacks("sensor.nono_problem_sensor") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 1
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 1

        listen_state.assert_has_calls(
            [
                mock.call(automower.callback_automower_automation, "sensor.nono_problem_sensor", immediate=True),
                mock.call(automower.callback_rain_changed, "sensor.rain_last_6h"),
                mock.call(automower.callback_sun_is_at_top, "sun.sun", attribute="rising", new=False),
                mock.call(automower.callback_next_start_changed, "sensor.nono_next_start", immediate=True),
            ],
            any_order=True,
        )

        log = hass_driver.get_mock("log")
        call_service = hass_driver.get_mock("call_service")
        if parked_because_of_rain == "on":
            log.assert_has_calls(
                [
                    mock.call("Starting Automower Automation"),
                    mock.call("\tpark max duration : 60480"),
                    mock.call("Next start event triggered"),
                    mock.call("\tRobot is parked because of rain. Nothing to check."),
                    mock.call("Send notification"),
                    mock.call("\tMessage: Robot is parked because of rain. Nothing to check."),
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )
            call_service.assert_has_calls(
                [
                    mock.call(
                        service="telegram_bot/send_message",
                        title="🏡 Nono",
                        message="Advanced automation is activated.",
                    ),
                ]
            )
        else:
            log.assert_has_calls(
                [
                    mock.call("Starting Automower Automation"),
                    mock.call("\tpark max duration : 60480"),
                    mock.call("Next start event triggered"),
                    mock.call("\told=None"),
                    mock.call("\tnew=unknown"),
                    mock.call("\tRobot is currently mowing, let it come back to base before checking."),
                    mock.call("Send notification"),
                    mock.call("\tMessage: Robot is currently mowing, let it come back to base before checking."),
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )

            call_service.assert_has_calls(
                [
                    mock.call(
                        service="telegram_bot/send_message",
                        title="🏡 Nono",
                        message="Robot is currently mowing, let it come back to base before checking.",
                        disable_notification=True,
                    ),
                    mock.call(
                        service="telegram_bot/send_message",
                        title="🏡 Nono",
                        message="Advanced automation is activated.",
                    ),
                ]
            )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__initialize__automation_deactivated(self, hass_driver, automower: Automower, parked_because_of_rain):
        """
        Test the initialization of the Automower automation when the robot is parked until further notice.
        """
        # GIVEN
        #   next_start is planned to "unknown" (robot is mowing)
        with hass_driver.setup():
            hass_driver.set_state("number.nono_park_for", 60480, attribute_name="max")
            hass_driver.set_state("sensor.nono_problem_sensor", "parked_until_further_notice")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", parked_because_of_rain)
            hass_driver.set_state("sensor.nono_next_start", "unknown")

        # WHEN
        #   Application is starting
        automower.initialize()

        # THEN
        #   3 callback are unset
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 0
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 0
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 0

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Starting Automower Automation"),
                mock.call("\tpark max duration : 60480"),
                mock.call("Automower automation activation triggered"),
                mock.call("\tAdvanced automation is deactivated."),
                mock.call("Send notification"),
                mock.call("\tMessage: Advanced automation is deactivated."),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Advanced automation is deactivated.",
                ),
            ]
        )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__automation_deactivation(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation deactivation.
        """
        # GIVEN
        #   automation is activated
        self.test__initialize__automation_activated(hass_driver, automower, parked_because_of_rain)
        log = hass_driver.get_mock("log")
        log.reset_mock()

        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mock()

        # WHEN
        #   Automation is deactivated
        hass_driver.set_state("sensor.nono_problem_sensor", "parked_until_further_notice")

        # THEN
        #   3 callback are set
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 0
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 0
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 0

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Automower automation activation triggered"),
                mock.call("\tAdvanced automation is deactivated."),
                mock.call("Send notification"),
                mock.call("\tMessage: Advanced automation is deactivated."),
            ]
        )

        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Advanced automation is deactivated.",
                ),
            ]
        )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__automation_activation(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation activation.
        """
        # GIVEN
        #   automation is deactivated
        self.test__initialize__automation_deactivated(hass_driver, automower, parked_because_of_rain)

        log = hass_driver.get_mock("log")
        log.reset_mock()

        call_service = hass_driver.get_mock("call_service")
        call_service.reset_mock()

        # WHEN
        #   Automation is activated
        hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")

        # THEN
        #   3 callback are set
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 1
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 1

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(automower.callback_rain_changed, "sensor.rain_last_6h"),
                mock.call(automower.callback_sun_is_at_top, "sun.sun", attribute="rising", new=False),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Automower automation activation triggered"),
                mock.call("\tAdvanced automation is activated."),
                mock.call("Send notification"),
                mock.call("\tMessage: Advanced automation is activated."),
            ]
        )

        call_service.assert_has_calls(
            [
                mock.call(
                    service="telegram_bot/send_message",
                    title="🏡 Nono",
                    message="Advanced automation is activated.",
                ),
            ]
        )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__automation_reactivated(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation reactivation.
        """
        # GIVEN
        #   automation is activated
        self.test__callback_automower_automation__automation_activation(hass_driver, automower, parked_because_of_rain)

        hass_driver.set_state("sensor.nono_problem_sensor", "another_state")

        log = hass_driver.get_mock("log")
        log.reset_mock()

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.reset_mock()

        #   3 callback are set
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 1
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 1

        # WHEN
        #   Automation is activated
        hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")

        # THEN
        #   3 callback are set
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 1
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 1

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(automower.callback_rain_changed, "sensor.rain_last_6h"),
                mock.call(automower.callback_sun_is_at_top, "sun.sun", attribute="rising", new=False),
            ],
            any_order=True,
        )

        assert log.call_count == 0

        assert fire_event.call_count == 0

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__unmanaged_state(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation unmanaged state.
        """
        # GIVEN
        #   automation is activated
        self.test__initialize__automation_activated(hass_driver, automower, parked_because_of_rain)
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Automation is deactivated
        hass_driver.set_state("sensor.nono_problem_sensor", "unknown")

        # THEN
        #   3 callback are set
        assert hass_driver.get_number_of_state_callbacks("sensor.rain_last_6h") == 1
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 1
        assert hass_driver.get_number_of_state_callbacks("sensor.nono_next_start") == 1

        assert hass_driver.get_mock("log").call_count == 0

    def test__callback_next_start_changed__when_parked_because_of_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the robot is parked due to rain.
        """
        # GIVEN
        #   Robot is parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("binary_sensor.parked_because_of_rain", "on")
        automower.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Next start time changed
        hass_driver.set_state("sensor.nono_next_start", "2023-08-03T18:34:00+00:00")

        # THEN
        #   No action is performed
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\tRobot is parked because of rain. Nothing to check."),
            ]
        )
