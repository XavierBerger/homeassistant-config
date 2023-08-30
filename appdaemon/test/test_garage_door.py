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
from apps.garage_door import GarageDoor

from .appdaemon_testing.pytest import (  # pylint: disable=W0611
    automation_fixture,
    hass_driver,
)


@automation_fixture(
    GarageDoor,
    args={
        "sun": "sun.sun",
        "notification_delay": 600,
        "door_state": "binary_sensor.porte_garage_opening",
        "notification_title": "Porte du garage",
        "notification_message": "Il fait nuit et la porte du garage est toujours ouverte",
    },
    initialize=False,
)
def garage_door() -> GarageDoor:
    pass


@pytest.mark.garage_door
class TestGarageDoor:
    # pylint: disable=W0621
    @pytest.mark.parametrize("garage_door_state", ["on", "off"])
    def test_initial_listen_state_with_sun_above_horizon(self, hass_driver, garage_door: GarageDoor, garage_door_state):
        """
        Test the initial state of listeners when the sun is above the horizon.

        This test case checks the behavior of the GarageDoor application's listeners when the sun is
        above the horizon during initialization.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.
            garage_door_state (str): The initial state of the garage door.

        Returns:
            None
        """
        # GIVEN
        #   Sun is below horizon
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "above_horizon")
            hass_driver.set_state("binary_sensor.porte_garage_opening", garage_door_state)

        # WHEN
        #   Application is starting
        garage_door.initialize()

        # THEN
        #   2 callback are set for sun
        #   0 callback are set for garage door
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 2
        assert hass_driver.get_number_of_state_callbacks("binary_sensor.porte_garage_opening") == 0

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(garage_door.callback_start_automation, "sun.sun", new="below_horizon", immediate=True),
                mock.call(garage_door.callback_stop_automation, "sun.sun", new="above_horizon", immediate=True),
            ],
            any_order=True,
        )

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Garage door Automation is stopped"),
            ]
        )

    @pytest.mark.parametrize("garage_door_state", ["on", "off"])
    def test_initial_listen_state_with_sun_below_horizon(self, hass_driver, garage_door: GarageDoor, garage_door_state):
        """
        Test the initial state of listeners when the sun is below the horizon.

        This test case checks the behavior of the GarageDoor application's listeners when the sun is
        below the horizon during initialization.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.
            garage_door_state (str): The initial state of the garage door.

        Returns:
            None
        """
        # GIVEN
        #   Sun is below horizon
        #   Garage door is closed
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "below_horizon")
            hass_driver.set_state("binary_sensor.porte_garage_opening", garage_door_state)

        # WHEN
        #   Application is starting
        garage_door.initialize()

        # THEN
        #   4 callback are set :
        #      2 for sun
        #      2 for garage door
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 2
        assert hass_driver.get_number_of_state_callbacks("binary_sensor.porte_garage_opening") == 2

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(garage_door.callback_start_automation, "sun.sun", new="below_horizon", immediate=True),
                mock.call(garage_door.callback_stop_automation, "sun.sun", new="above_horizon", immediate=True),
                mock.call(
                    garage_door.callback_garage_door_close,
                    "binary_sensor.porte_garage_opening",
                    new="off",
                    immediate=True,
                ),
                mock.call(
                    garage_door.callback_garage_door_open,
                    "binary_sensor.porte_garage_opening",
                    new="on",
                    immediate=True,
                ),
            ],
            any_order=True,
        )

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Garage door Automation is started"),
            ]
        )

    @pytest.mark.parametrize("garage_door_state", ["on", "off"])
    def test_change_listen_state_at_sunset(self, hass_driver, garage_door: GarageDoor, garage_door_state):
        """
        Test changing the state of listeners when the sun goes below the horizon.

        This test case simulates the transition from the sun being above the horizon to being below the horizon.
        It checks the behavior of the GarageDoor application's listeners during this transition.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.
            garage_door_state (str): The initial state of the garage door.

        Returns:
            None
        """
        # GIVEN
        #   Sun is above horizon and only callback for sun are set
        self.test_initial_listen_state_with_sun_above_horizon(hass_driver, garage_door, garage_door_state)
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Sun is going below horizon
        hass_driver.set_state("sun.sun", "below_horizon")

        # THEN
        #   Sun callback remain unchanged
        #   2 callbacks are added for the garage door
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 2
        assert hass_driver.get_number_of_state_callbacks("binary_sensor.porte_garage_opening") == 2

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(garage_door.callback_start_automation, "sun.sun", new="below_horizon", immediate=True),
                mock.call(garage_door.callback_stop_automation, "sun.sun", new="above_horizon", immediate=True),
                mock.call(
                    garage_door.callback_garage_door_close,
                    "binary_sensor.porte_garage_opening",
                    new="off",
                    immediate=True,
                ),
                mock.call(
                    garage_door.callback_garage_door_open,
                    "binary_sensor.porte_garage_opening",
                    new="on",
                    immediate=True,
                ),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Garage door Automation is started"),
            ]
        )

    @pytest.mark.parametrize("garage_door_state", ["on", "off"])
    def test_change_listen_state_at_sunrise(self, hass_driver, garage_door: GarageDoor, garage_door_state):
        # GIVEN
        #   sun is below horizon and 4 callback are set for sun and garage door
        self.test_initial_listen_state_with_sun_below_horizon(hass_driver, garage_door, garage_door_state)
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   sun is going above horizon
        hass_driver.set_state("sun.sun", "above_horizon")

        # THEN
        #    2 sun callback remain present
        #    2 callbacks of garage door are removed
        assert hass_driver.get_number_of_state_callbacks("sun.sun") == 2
        assert hass_driver.get_number_of_state_callbacks("binary_sensor.porte_garage_opening") == 0

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [
                mock.call(garage_door.callback_start_automation, "sun.sun", new="below_horizon", immediate=True),
                mock.call(garage_door.callback_stop_automation, "sun.sun", new="above_horizon", immediate=True),
            ],
            any_order=True,
        )

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Garage door Automation is stopped"),
            ]
        )

    def test_callback_garage_door_open_initial(self, hass_driver, garage_door: GarageDoor):
        """
        Test changing the state of listeners when the sun goes above the horizon.

        This test case simulates the transition from the sun being below the horizon to being above the horizon.
        It checks the behavior of the GarageDoor application's listeners during this transition.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.
            garage_door_state (str): The initial state of the garage door.

        Returns:
            None
        """
        # GIVEN
        #   Sun is below horizon
        #   Garage door is open
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "above_horizon")
            hass_driver.set_state("binary_sensor.porte_garage_opening", "on")
        garage_door.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   Sun passed below horizon
        hass_driver.set_state("sun.sun", "below_horizon")

        # THEN
        #   notification is sent
        fire_event = hass_driver.get_mock("fire_event")
        assert fire_event.call_count == 1
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_present",
                    title="Porte du garage",
                    message="Il fait nuit et la porte du garage est toujours ouverte",
                    icon="mdi-garage-open",
                    color="deep-orange",
                    tag="garage_open",
                    until=[
                        {"entity_id": "binary_sensor.porte_garage_opening", "new_state": "off"},
                        {"entity_id": "sun.sun", "new_state": "above_horizon"},
                    ],
                )
            ]
        )

        log.assert_has_calls(
            [
                mock.call("Garage door Automation is started"),
                mock.call("Door is open during sunset => send notification"),
                mock.call("Send notification"),
            ]
        )

    def test_callback_garage_door_open_at_night(self, hass_driver, garage_door: GarageDoor):
        """
        Test the callback when the garage door is opened at night.

        This test case simulates the scenario when the garage door is opened while the sun is below the horizon.
        It checks whether the delayed notification is planned correctly.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.

        Returns:
            None
        """
        # GIVEN
        #   Sun is below horizon
        #   door is closed
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "below_horizon")
            hass_driver.set_state("binary_sensor.porte_garage_opening", "off")
        garage_door.initialize()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   callback_garage_door_open is trigger
        hass_driver.set_state("binary_sensor.porte_garage_opening", "on")

        # THEN
        #   Delayed notification is planned
        run_in = hass_driver.get_mock("run_in")
        assert run_in.call_count == 1
        run_in.assert_has_calls([mock.call(garage_door.send_notification, 600)])

        log.assert_has_calls(
            [
                mock.call("Door is open while sun is below horizon => trigger delayed notification"),
            ]
        )

    def test_callback_garage_door_open_then_closed_at_night(self, hass_driver, garage_door: GarageDoor):
        """
        Test the callback when the garage door is opened at night and then closed.

        This test case simulates the scenario when the garage door is opened while the sun is below the horizon,
        and then it is closed. It checks whether the delayed notification is canceled when the garage door is closed.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.

        Returns:
            None
        """
        # GIVEN
        #   Garage door has been open at night
        self.test_callback_garage_door_open_at_night(hass_driver, garage_door)
        run_in = hass_driver.get_mock("run_in")
        run_in.reset_mock()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   closing garage door
        hass_driver.set_state("binary_sensor.porte_garage_opening", "off")

        # THEN
        #   Delayed notification has been canceled planned
        log.assert_has_calls(
            [
                mock.call("Cancel delayed notification"),
            ]
        )

    def test_callback_garage_door_remain_open_at_night(self, hass_driver, garage_door: GarageDoor):
        """
        Test the callback when the garage door remains open at night.

        This test case simulates the scenario when the garage door is opened while the sun is below the horizon,
        and it remains open for the duration of the delayed notification. It checks whether the delayed notification
        is triggered and includes the correct conditions for cancellation.

        Args:
            hass_driver: Mocked Home Assistant driver.
            garage_door: Mocked GarageDoor instance.

        Returns:
            None
        """
        # GIVEN
        #   Garage door has been open at night
        self.test_callback_garage_door_open_at_night(hass_driver, garage_door)
        run_in = hass_driver.get_mock("run_in")
        run_in.reset_mock()
        log = hass_driver.get_mock("log")
        log.reset_mock()

        # WHEN
        #   garage door remain open
        hass_driver.advance_time(600)
        assert run_in.call_count == 0

        # THEN
        #   Delayed notification has been canceled planned
        fire_event = hass_driver.get_mock("fire_event")
        assert fire_event.call_count == 1
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action="send_to_present",
                    title="Porte du garage",
                    message="Il fait nuit et la porte du garage est toujours ouverte",
                    icon="mdi-garage-open",
                    color="deep-orange",
                    tag="garage_open",
                    until=[
                        {"entity_id": "binary_sensor.porte_garage_opening", "new_state": "off"},
                        {"entity_id": "sun.sun", "new_state": "above_horizon"},
                    ],
                )
            ]
        )

        log.assert_has_calls(
            [
                mock.call("Send notification"),
            ]
        )
