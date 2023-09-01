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
class TestAutomower:
    # pylint: disable=W0621
    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__initialize__automation_activated(self, hass_driver, automower: Automower, parked_because_of_rain):
        """
        Test the initialization of the Automower automation when the robot is parked due to rain.

        This test case simulates the scenario where the Automower automation is initialized when the robot is parked
        due to rain. It checks whether the correct callbacks are set based on the initial state of the application.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.
            parked_because_of_rain: The initial state of the binary sensor indicating if the robot is parked due to
            rain.

        Returns:
            None
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
                mock.call(automower.callback_next_start_changed, "sensor.nono_next_start"),
            ],
            any_order=True,
        )

        log = hass_driver.get_mock("log")
        if parked_because_of_rain == "on":
            log.assert_has_calls(
                [
                    mock.call("Starting Automower Automation"),
                    mock.call("\tpark max duration : 60480"),
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\ttitle: Nono"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )
        else:
            log.assert_has_calls(
                [
                    mock.call("Starting Automower Automation"),
                    mock.call("\tpark max duration : 60480"),
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\ttitle: Nono"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__initialize__automation_deactivated(self, hass_driver, automower: Automower, parked_because_of_rain):
        """
        Test the initialization of the Automower automation when the robot is parked until further notice.

        This test case simulates the scenario where the Automower automation is initialized when the robot is parked
        until further notice. It checks whether the correct callbacks are unset based on the initial state of the
        application.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.
            parked_because_of_rain: The initial state of the binary sensor indicating if the robot is parked due to
            rain.

        Returns:
            None
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

        # log = hass_driver.get_mock("log")
        # log.assert_has_calls(
        #     [
        #         mock.call("Starting Automower Automation"),
        #         mock.call("\tpark max duration : 60480"),
        #         mock.call("Automower automation activation triggered"),
        #         mock.call("\tAdvanced automation is deactivated."),
        #         mock.call("Send notification"),
        #         mock.call("\ttitle: Nono"),
        #         mock.call("\tMessage: Advanced automation is deactivated."),
        #     ]
        # )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__automation_deactivation(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation deactivation.

        This test case simulates the scenario where the callback for automower automation deactivation is triggered.
        It checks whether the correct callbacks are unset and whether the expected notifications are sent when the
        automation is deactivated.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.
            parked_because_of_rain: The initial state of the binary sensor indicating if the robot is parked due to
            rain.

        Returns:
            None
        """
        # GIVEN
        #   automation is activated
        self.test__initialize__automation_activated(hass_driver, automower, parked_because_of_rain)
        log = hass_driver.get_mock("log")
        log.reset_mock()

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
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: Advanced automation is deactivated."),
            ]
        )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="Advanced automation is deactivated.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__automation_activation(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation activation.

        This test case simulates the scenario where the callback for automower automation activation is triggered.
        It checks whether the correct callbacks are set and whether the expected notifications are sent when the
        automation is activated.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.
            parked_because_of_rain: The initial state of the binary sensor indicating if the robot is parked due to rain

        Returns:
            None
        """
        # GIVEN
        #   automation is deactivated
        self.test__initialize__automation_deactivated(hass_driver, automower, parked_because_of_rain)

        log = hass_driver.get_mock("log")
        log.reset_mock()

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.reset_mock()

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

        if parked_because_of_rain == "on":
            log.assert_has_calls(
                [
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\ttitle: Nono"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )
        else:
            log.assert_has_calls(
                [
                    mock.call("Automower automation activation triggered"),
                    mock.call("\tAdvanced automation is activated."),
                    mock.call("Send notification"),
                    mock.call("\ttitle: Nono"),
                    mock.call("\tMessage: Advanced automation is activated."),
                ]
            )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="Advanced automation is activated.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    @pytest.mark.parametrize("parked_because_of_rain", ["on", "off"])
    def test__callback_automower_automation__unmanaged_state(
        self, hass_driver, automower: Automower, parked_because_of_rain
    ):
        """
        Test the callback for automower automation unmanaged state.

        This test case simulates the scenario where the callback for automower automation is triggered with an
        unmanaged state.
        It checks that nothing is done is such a case

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.
            parked_because_of_rain: The initial state of the binary sensor indicating if the robot is parked due to
            rain.

        Returns:
            None
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

        This test case simulates the scenario where the callback for next start time change is triggered,
        but the robot is already parked due to rain, so no further actions should be performed.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
            [mock.call("Next start event triggered"), mock.call("\tRobot is parked because of rain. Nothing to check.")]
        )

    @pytest.mark.skip(reason="TODO: test with GMT clock")
    def test__callback_next_start_changed__session_completed(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the session is completed.

        This test case simulates the scenario where the callback for next start time change is triggered,
        but the current mowing session is already completed. Therefore, the automation should wait until
        tomorrow to restart the robot.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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

        # WHEN
        #   Next start is defined as tomorrow
        hass_driver.set_state("sensor.nono_next_start", "2023-08-04T11:00:00+00:00")

        # THEN
        #   Session is completed, wait until tomorrow.
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-04T18:30:00+00:00"),
                mock.call("\tnew=2023-08-04T11:00:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00+02:00"),
                mock.call("\tNext start is planned at 2023-08-04 13:00:00+02:00"),
                mock.call("\tThe number of hour before mowing session end is -18.0"),
                mock.call("\tSession completed. Lets restart tomorrow."),
            ]
        )

    @pytest.mark.skip(reason="TODO: test with GMT clock")
    def test__callback_next_start_changed__too_short_session(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the remaining session duration is too short.

        This test case simulates the scenario where the callback for next start time change is triggered,
        but the remaining time for the current mowing session is less than 1 hour. Therefore, the automation
        should stay parked and set a park duration of 3 hours (180 minutes).

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
        """
        # GIVEN
        #   Robot is not parked because of rain
        with hass_driver.setup():
            hass_driver.set_state("sensor.nono_problem_sensor", "week_schedule")
            hass_driver.set_state("sensor.nono_next_start", "2023-08-03T16:30:00+00:00")
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
                mock.call("\told=2023-08-03T16:30:00+00:00"),
                mock.call("\tnew=2023-08-03T16:34:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00+02:00"),
                mock.call("\tNext start is planned at 2023-08-03 18:34:00+02:00"),
                mock.call("\tThe number of hour before mowing session end is 0.43333333333333335"),
                mock.call("\tDuration between next start and end of session is less than 1 hour, stay parked."),
                mock.call("Call service"),
                mock.call("\tnumber/set_value ({'entity_id': 'number.nono_park_for', 'value': 180})"),
                mock.call("Send notification"),
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: End session is in less than 1 hour, stay parked."),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("number/set_value", entity_id="number.nono_park_for", value=180),
            ]
        )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="End session is in less than 1 hour, stay parked.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    @pytest.mark.skip(reason="TODO: test with GMT clock")
    def test__callback_next_start_changed__good_session(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the remaining session duration is sufficient.

        This test case simulates the scenario where the callback for next start time change is triggered,
        and the remaining time for the current mowing session is more than 1 hour. Therefore, the automation
        should continue without any park action.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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

        # WHEN
        #   Next start is 1h26min before end of session
        hass_driver.set_state("sensor.nono_next_start", "2023-08-03T15:34:00+00:00")

        # THEN
        #   Let mowing session continue
        log.assert_has_calls(
            [
                mock.call("Next start event triggered"),
                mock.call("\told=2023-08-03T15:30:00+00:00"),
                mock.call("\tnew=2023-08-03T15:34:00+00:00"),
                mock.call("\tMowing session will end at 2023-08-03 19:00:00+02:00"),
                mock.call("\tNext start is planned at 2023-08-03 17:34:00+02:00"),
                mock.call("\tThe number of hour before mowing session end is 1.4333333333333333"),
                mock.call("Duration between next start and end of session is greater than 1 hour."),
            ]
        )

    def test__callback_next_start_changed__currently_mowing(self, hass_driver, automower: Automower):
        """
        Test the callback for next start time change when the robot is currently mowing.

        This test case simulates the scenario where the callback for next start time change is triggered,
        but the robot is currently mowing. Therefore, the automation should not perform any action and
        wait for the robot to return to the base before further processing.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("Robot is currently mowing, let it come back to base before checking."),
            ]
        )

    def test__callback_rain_changed__rain_not_available(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain information is not available.

        This test case simulates the scenario where the callback for rain status change is triggered,
        but the rain information is not available. The automation should handle this case and not perform any action
        related to rain.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=None"),
                mock.call("\tnew=unknow"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

    def test__callback_rain_changed__no_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when there is no rain during the last 6 hours.

        This test case simulates the scenario where the callback for rain status change is triggered,
        and there has been no rain during the last 6 hours. The automation should start the automower
        to mow the lawn since it's expected to be dry.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=None"),
                mock.call("\tnew=0"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
                mock.call("Call service"),
                mock.call("\tvacuum/start ({'entity_id': 'vacuum.nono'})"),
                mock.call("Send notification"),
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
            ]
        )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    def test__callback_rain_changed__start_raining(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when it starts raining.

        This test case simulates the scenario where the callback for rain status change is triggered,
        and it starts raining. The automation should park the automower until the rain stops and the lawn dries.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=0"),
                mock.call("\tnew=1"),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
                mock.call("Call service"),
                mock.call("\tnumber/set_value ({'entity_id': 'number.nono_park_for', 'value': 60480})"),
                mock.call("Send notification"),
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: It starts raining, park until rain stops and lawn dries."),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls([mock.call("number/set_value", entity_id="number.nono_park_for", value=60480)])

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="It starts raining, park until rain stops and lawn dries.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    def test__callback_rain_changed__continue_raining(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when it continues raining.

        This test case simulates the scenario where the callback for rain status change is triggered,
        and it continues raining. The automation should keep the automower parked since the lawn shouldn't be dry yet.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=1"),
                mock.call("\tnew=2"),
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

        # WHEN
        # Application is initialised
        hass_driver.set_state("sensor.rain_last_6h", 0)

        # THEN

        log.assert_has_calls(
            [
                mock.call("Rain event triggered"),
                mock.call("\told=1"),
                mock.call("\tnew=0"),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
                mock.call("No rain during last 6h, waiting for noon to restart."),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
            ]
        )

    def test__callback_rain_changed__rain_has_stopped_6h_ago_after_noon(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain has stopped more than 6 hours ago before noon.

        This test case simulates the scenario where the callback for rain status change is triggered,
        and the rain has stopped more than 6 hours ago, before noon. The automation should keep the automower
        parked until noon before considering restarting it.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=1"),
                mock.call("\tnew=0"),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
                mock.call("Call service"),
                mock.call("\tvacuum/start ({'entity_id': 'vacuum.nono'})"),
                mock.call("Send notification"),
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
            ]
        )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    def test__callback_rain_changed__rain_has_stopped_6h_ago_sun_below_horizon(self, hass_driver, automower: Automower):
        """
        Test the callback for rain status change when rain has stopped more than 6 hours ago and the sun is below
        the horizon.

        This test case simulates the scenario where the callback for rain status change is triggered,
        and the rain has stopped more than 6 hours ago, and the sun is below the horizon. The automation should keep
        the automower parked until tomorrow noon before considering restarting it.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\told=1"),
                mock.call("\tnew=0"),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
                mock.call("No rain during last 6h, sun is below horizon, waiting for tomorow noon to restart."),
                mock.call("\tbinary_sensor.parked_because_of_rain: True"),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_no_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is no rain during the last 6 hours and the sun is at the top.

        This test case simulates the scenario where the callback for sun status change is triggered,
        and there is no rain during the last 6 hours and the sun is at the top. The automation should start the
        automower.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
                mock.call("\ttitle: Nono"),
                mock.call("\tMessage: No rain during last 6h. Lawn should be dry now."),
                mock.call("\tbinary_sensor.parked_because_of_rain: off"),
            ]
        )

        call_service = hass_driver.get_mock("call_service")
        call_service.assert_has_calls(
            [
                mock.call("vacuum/start", entity_id="vacuum.nono"),
            ]
        )

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Nono",
                    message="No rain during last 6h. Lawn should be dry now.",
                    icon="mdi-robot-mower-outline",
                    color="deep-orange",
                    tag="nono",
                ),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_still_rainning(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is rain during the last 6 hours and the sun is at the top.

        This test case simulates the scenario where the callback for sun status change is triggered,
        there is rain during the last 6 hours, and the sun is at the top. The automation should keep the automower
        parked.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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

        # WHEN
        # Application is initialised
        hass_driver.set_state("sun.sun", False, attribute_name="rising")

        # THEN
        log.assert_has_calls(
            [
                mock.call("Sun event triggered"),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
                mock.call("\tLawn shouldn't be dry yt. Staying parked."),
                mock.call("\tbinary_sensor.parked_because_of_rain: on"),
            ]
        )

    def test__callback_rain_changed__sun_is_at_top_not_parked_because_of_rain(self, hass_driver, automower: Automower):
        """
        Test the callback for sun status change when there is no rain during the last 6 hours and the sun is at the top,
        but the automower is not parked because of rain.

        This test case simulates the scenario where the callback for sun status change is triggered,
        there is no rain during the last 6 hours, the sun is at the top, but the automower is not parked because of
        rain.
        The automation should not take any action in this case.

        Args:
            hass_driver: Mocked Home Assistant driver.
            automower: Mocked Automower instance.

        Returns:
            None
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
