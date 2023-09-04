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
from apps.notifier import Notifier

from .appdaemon_testing.pytest import (  # pylint: disable=W0611
    automation_fixture,
    hass_driver,
)


@automation_fixture(
    Notifier,
    args={
        "home_occupancy_sensor_id": "binary_sensor.home_occupied",
        "proximity_threshold": 500,
        "persons": [
            {
                "name": "user1",
                "id": "person.user1",
                "notification_service": "notify/user1_mobile",
                "proximity_id": "proximity.distance_user1_home",
            },
            {
                "name": "user2",
                "id": "person.user2",
                "notification_service": "notify/user2_mobile",
                "proximity_id": "proximity.distance_user2_home",
            },
        ],
    },
)
def notifier() -> Notifier:
    pass


@pytest.mark.notifier
class TestNotifier:
    # pylint: disable=W0621
    def _set_user_distance(self, hass_driver, notifier, user, distance):
        hass_driver.set_state(f"proximity.distance_{user}_home", distance)
        if distance <= notifier.args["proximity_threshold"]:
            hass_driver.set_state("binary_sensor.home_occupied", "on")
            hass_driver.set_state(f"person.{user}", "home")
        else:
            hass_driver.set_state(f"person.{user}", "not_home")

    def _initialize_presence(self, hass_driver, notifier, distance_user1_home, distance_user2_home):
        with hass_driver.setup():
            hass_driver.set_state("binary_sensor.home_occupied", "off")
            self._set_user_distance(hass_driver, notifier, "user1", distance_user1_home)
            self._set_user_distance(hass_driver, notifier, "user2", distance_user2_home)

    def test_initial_state(self, hass_driver, notifier: Notifier):
        """
        Test the initial state of the Notifier component.
        """
        # GIVEN
        #   notifier starts

        # WHEN
        #   notifier is initialized

        # THEN
        #   notifier is listening for events and states
        listen_event = hass_driver.get_mock("listen_event")
        listen_event.assert_has_calls(
            [
                mock.call(notifier.callback_notifier_event_received, "NOTIFIER"),
                mock.call(notifier.callback_notifier_discard_event_received, "NOTIFIER_DISCARD"),
                mock.call(notifier.callback_button_clicked, "mobile_app_notification_action"),
            ],
            any_order=True,
        )

        listen_state = hass_driver.get_mock("listen_state")
        listen_state.assert_has_calls(
            [mock.call(notifier.callback_home_occupied, "binary_sensor.home_occupied", old="off", new="on")],
            any_order=True,
        )

    @pytest.mark.parametrize("user", ["user1", "user2"])
    def test__callback_notifier_event_received__send_to_person(self, hass_driver, notifier: Notifier, user):
        """
        Test the callback function for sending notifications to specific users.
        """
        # GIVEN
        #   Notifier is initialized

        # WHEN
        #   notification is sent to user1
        notifier.fire_event(
            "NOTIFIER",
            action=f"send_to_{user}",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="#ffffff",
            tag="notification_tag",
        )

        # THEN
        #   Notifier is called
        #   Notification is sent to user
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.assert_called_once_with(
            f"notify/{user}_mobile",
            title="Notification Title",
            message="Notification message",
            data={"notification_icon": "mdi-bell", "color": "#ffffff", "tag": "notification_tag"},
        )

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call(f"Sending notification to {user}"),
            ]
        )

    @pytest.mark.parametrize("distance_user1_home", [1, 1000])
    @pytest.mark.parametrize("distance_user2_home", [1, 1000])
    def test__callback_notifier_event_received__send_to_present(
        self, hass_driver, notifier: Notifier, distance_user1_home, distance_user2_home
    ):
        """
        Test the callback function for sending notifications to present users.
        """
        # GIVEN
        #   user1 and user2 are present or not
        self._initialize_presence(hass_driver, notifier, distance_user1_home, distance_user2_home)

        # WHEN
        #   Notification is sent to present
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_present",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            image_url="image.jpg",
            color="deep-orange",
            tag="notification_tag",
            siri_shortcut_name="siri_shortcut",
        )

        # THEN
        #   Notification are sent to user present
        #   If nobody is present no notification is sent
        #   Log is written
        get_state = hass_driver.get_mock("get_state")
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        if get_state("proximity.distance_user1_home") == get_state("proximity.distance_user2_home") == 1:
            call_service.assert_has_calls(
                [
                    mock.call(
                        "notify/user1_mobile",
                        title="Notification Title",
                        message="Notification message",
                        data={
                            "image": "image.jpg",
                            "notification_icon": "mdi-bell",
                            "color": "#ff5722",
                            "tag": "notification_tag",
                            "shortcut": {"name": "siri_shortcut"},
                        },
                    ),
                    mock.call(
                        "notify/user2_mobile",
                        title="Notification Title",
                        message="Notification message",
                        data={
                            "image": "image.jpg",
                            "notification_icon": "mdi-bell",
                            "color": "#ff5722",
                            "tag": "notification_tag",
                            "shortcut": {"name": "siri_shortcut"},
                        },
                    ),
                ],
                any_order=True,
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                    mock.call("Sending notification to user2"),
                ]
            )
        elif get_state("proximity.distance_user1_home") == 1:
            call_service.assert_called_once_with(
                "notify/user1_mobile",
                title="Notification Title",
                message="Notification message",
                data={
                    "image": "image.jpg",
                    "notification_icon": "mdi-bell",
                    "color": "#ff5722",
                    "tag": "notification_tag",
                    "shortcut": {"name": "siri_shortcut"},
                },
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                ]
            )
        elif get_state("proximity.distance_user2_home") == 1:
            call_service.assert_called_once_with(
                "notify/user2_mobile",
                title="Notification Title",
                message="Notification message",
                data={
                    "image": "image.jpg",
                    "notification_icon": "mdi-bell",
                    "color": "#ff5722",
                    "tag": "notification_tag",
                    "shortcut": {"name": "siri_shortcut"},
                },
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user2"),
                ]
            )
        else:
            assert get_state("proximity.distance_user1_home") == get_state("proximity.distance_user2_home") == 1000
            assert call_service.call_count == 0

    @pytest.mark.parametrize("distance_user1_home", [1, 1000])
    @pytest.mark.parametrize("distance_user2_home", [1, 1000])
    def test__callback_notifier_event_received__send_to_absent(
        self, hass_driver, notifier: Notifier, distance_user1_home, distance_user2_home
    ):
        """
        Test the callback function for sending notifications to absent users.
        """
        # GIVEN
        #   user1 and user2 are present or not
        self._initialize_presence(hass_driver, notifier, distance_user1_home, distance_user2_home)

        # WHEN
        #   Notification is sent to absent
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_absent",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            timeout=60,
            tag="notification_tag",
            interuption_level=7,
        )

        #   Notification are sent to user absent
        #   If nobody is absent no notification is sent
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        get_state = hass_driver.get_mock("get_state")
        log = hass_driver.get_mock("log")

        if get_state("proximity.distance_user1_home") == get_state("proximity.distance_user2_home") == 1000:
            call_service.assert_has_calls(
                [
                    mock.call(
                        "notify/user1_mobile",
                        title="Notification Title",
                        message="Notification message",
                        data={
                            "timeout": 60,
                            "notification_icon": "mdi-bell",
                            "color": "#ff5722",
                            "tag": "notification_tag",
                            "push": {"interruption-level": 7},
                        },
                    ),
                    mock.call(
                        "notify/user2_mobile",
                        title="Notification Title",
                        message="Notification message",
                        data={
                            "timeout": 60,
                            "notification_icon": "mdi-bell",
                            "color": "#ff5722",
                            "tag": "notification_tag",
                            "push": {"interruption-level": 7},
                        },
                    ),
                ],
                any_order=True,
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                    mock.call("Sending notification to user2"),
                ]
            )
        elif get_state("proximity.distance_user1_home") == 1000:
            call_service.assert_called_once_with(
                "notify/user1_mobile",
                title="Notification Title",
                message="Notification message",
                data={
                    "timeout": 60,
                    "notification_icon": "mdi-bell",
                    "color": "#ff5722",
                    "tag": "notification_tag",
                    "push": {"interruption-level": 7},
                },
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                ]
            )
        elif get_state("proximity.distance_user2_home") == 1000:
            call_service.assert_called_once_with(
                "notify/user2_mobile",
                title="Notification Title",
                message="Notification message",
                data={
                    "timeout": 60,
                    "notification_icon": "mdi-bell",
                    "color": "#ff5722",
                    "tag": "notification_tag",
                    "push": {"interruption-level": 7},
                },
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user2"),
                ]
            )
        else:
            assert get_state("proximity.distance_user1_home") == get_state("proximity.distance_user2_home") == 1
            assert call_service.call_count == 0

    @pytest.mark.parametrize("distance_user1_home", [1, 1000])
    @pytest.mark.parametrize("distance_user2_home", [1, 1000])
    def test__callback_notifier_event_received__send_to_all(
        self, hass_driver, notifier: Notifier, distance_user1_home, distance_user2_home
    ):
        """
        Test the callback function for sending notifications to all users.
        """

        # GIVEN
        #   user1 and user2 are present or not
        self._initialize_presence(hass_driver, notifier, distance_user1_home, distance_user2_home)

        # WHEN
        #   Notification is sent to all
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            click_url="lovelace/vaccum",
            tag="notification_tag",
        )

        # THEN
        #   Notification is sent to all
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.assert_has_calls(
            [
                mock.call(
                    "notify/user1_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "url": "lovelace/vaccum",
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    },
                ),
                mock.call(
                    "notify/user2_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "url": "lovelace/vaccum",
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    },
                ),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
            ]
        )

    @pytest.mark.parametrize("distance_user1_home", [1, 1000])
    @pytest.mark.parametrize("distance_user2_home", [1, 1000])
    def test__callback_notifier_event_received__send_to_nearest(
        self, hass_driver, notifier: Notifier, distance_user1_home, distance_user2_home
    ):
        """
        Test case for handling NOTIFIER events with 'send_to_nearest' action.
        """
        # GIVEN
        #   user1 and user2 are present or not
        self._initialize_presence(hass_driver, notifier, distance_user1_home, distance_user2_home)

        # WHEN
        #   Notification is sent to nearest
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_nearest",
            title="Custom Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            tag="notification_tag",
        )

        # THEN
        #   Notification are sent to nearest user
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        get_state = hass_driver.get_mock("get_state")
        log = hass_driver.get_mock("log")

        if get_state("proximity.distance_user1_home") == get_state("proximity.distance_user2_home"):
            call_service.assert_has_calls(
                [
                    mock.call(
                        "notify/user1_mobile",
                        title="Custom Title",
                        message="Notification message",
                        data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
                    ),
                    mock.call(
                        "notify/user2_mobile",
                        title="Custom Title",
                        message="Notification message",
                        data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
                    ),
                ],
                any_order=True,
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                    mock.call("Sending notification to user2"),
                ]
            )
        elif get_state("proximity.distance_user1_home") < get_state("proximity.distance_user2_home"):
            call_service.assert_called_once_with(
                "notify/user1_mobile",
                title="Custom Title",
                message="Notification message",
                data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user1"),
                ]
            )
        elif get_state("proximity.distance_user2_home") < get_state("proximity.distance_user1_home"):
            call_service.assert_called_once_with(
                "notify/user2_mobile",
                title="Custom Title",
                message="Notification message",
                data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
            )
            log.assert_has_calls(
                [
                    mock.call("NOTIFIER event received"),
                    mock.call("Sending notification to user2"),
                ]
            )
        else:
            # Notification has to be sent. This case should never occurs
            assert False

    @pytest.mark.parametrize("active_users", [["user1", "user2"], ["user2", "user1"]])
    def test__callback_notifier_event_received__send_when_present__nobody_present(
        self, hass_driver, notifier: Notifier, active_users
    ):
        """
        Test the callback function for sending notifications to the nearest user.
        """

        # GIVEN
        #   user1 and user2 are not present
        self._initialize_presence(hass_driver, notifier, 1000, 1000)

        # WHEN
        #   Notification is sent when present
        notifier.fire_event(
            "NOTIFIER",
            action="send_when_present",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            tag="notification_tag",
        )

        # THEN
        #   Listen state is set to watch for home occupency
        #
        listen_state = hass_driver.get_mock("listen_state")
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        listen_state.assert_has_calls(
            [mock.call(notifier.callback_home_occupied, "binary_sensor.home_occupied", old="off", new="on")],
        )

        assert call_service.call_count == 0

        # WHEN
        #   first user arrive at home
        self._set_user_distance(hass_driver, notifier, active_users[0], 1)

        # THEN
        #   first user is notified
        call_service.assert_has_calls(
            [
                mock.call(
                    f"notify/{active_users[0]}_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
                )
            ],
        )

        # WHEN
        #   second user arrive at home
        call_service.reset_mock()
        self._set_user_distance(hass_driver, notifier, active_users[1], 1)

        # THEN
        #   second user is not notified
        assert call_service.call_count == 0

        #   Log is written
        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Staging notification for when home becomes occupied ..."),
                mock.call("Home is occupied ... Sending stagged notifications now ..."),
                mock.call(f"Sending notification to {active_users[0]}"),
            ]
        )

    def test__callback_notifier_event_received__send_when_present__with_present(self, hass_driver, notifier: Notifier):
        """
        Test the callback function for sending notifications when users are present and user are present.
        """
        # GIVEN
        #   user1 and user2 are present
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent when present
        notifier.fire_event(
            "NOTIFIER",
            action="send_when_present",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            tag="notification_tag",
        )

        # THEN
        #   Both user are notified
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.assert_has_calls(
            [
                mock.call(
                    "notify/user1_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
                ),
                mock.call(
                    "notify/user2_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={"notification_icon": "mdi-bell", "color": "#ff5722", "tag": "notification_tag"},
                ),
            ],
        )

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
            ]
        )

    @pytest.mark.parametrize("with_tag", [True, False])
    def test__callback_notifier_event_received__send_to_all__persistent(
        self, hass_driver, notifier: Notifier, with_tag
    ):
        """
        Test the callback function for sending persistent notifications to all users.
        """
        # GIVEN
        #   user1 and user2 are present
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent to all with persistence
        with mock.patch("appdaemon.adapi.ADAPI.get_now_ts", return_value=int(42)):
            if with_tag:
                notifier.fire_event(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Notification Title",
                    message="Notification message",
                    icon="mdi-bell",
                    color="deep-orange",
                    persistent=True,
                    tag="notification_tag",
                )
            else:
                notifier.fire_event(
                    "NOTIFIER",
                    action="send_to_all",
                    title="Notification Title",
                    message="Notification message",
                    icon="mdi-bell",
                    color="deep-orange",
                    persistent=True,
                )

        # THEN
        #   Both user are notified
        #   A notification is added to Home assistant
        #   Log is written
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.assert_has_calls(
            [
                mock.call(
                    "notify/user1_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    }
                    if with_tag
                    else {
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                    },
                ),
                mock.call(
                    "notify/user2_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    }
                    if with_tag
                    else {
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                    },
                ),
                mock.call(
                    "persistent_notification/create",
                    title="Notification Title",
                    message="Notification message",
                    notification_id="notification_tag" if with_tag else "42",
                ),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
                mock.call("Persisting the notification on Home Assistant Front-end ..."),
            ]
        )

    def test__callback_notifier_event_received__send_to_all__until_tag_initialization(
        self, hass_driver, notifier: Notifier
    ):
        """
        Test the callback function for sending notifications to all users until a certain condition is met.
        """
        # GIVEN
        #   user1 and user2 are present
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent until change and associated with a callback
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            callback=[
                {"title": "actuator.garage_door", "event": "close_door", "icon": "icon", "destructive": True},
            ],
            until=[
                {"entity_id": "sun.sun", "new_state": "above_horizon"},
            ],
            tag="notification_tag",
        )

        # THEN
        #   Notification are sent to all with callback parameter set action
        #   Listen state is added to watch until parameter
        #   Log is written
        listen_state = hass_driver.get_mock("listen_state")
        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.assert_has_calls(
            [
                mock.call(
                    "notify/user1_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "actions": [
                            {
                                "action": "close_door",
                                "title": "actuator.garage_door",
                                "icon": "sfsymbols:icon",
                                "destructive": True,
                            }
                        ],
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    },
                ),
                mock.call(
                    "notify/user2_mobile",
                    title="Notification Title",
                    message="Notification message",
                    data={
                        "actions": [
                            {
                                "action": "close_door",
                                "title": "actuator.garage_door",
                                "icon": "sfsymbols:icon",
                                "destructive": True,
                            }
                        ],
                        "notification_icon": "mdi-bell",
                        "color": "#ff5722",
                        "tag": "notification_tag",
                    },
                ),
            ],
            any_order=True,
        )

        listen_state.assert_has_calls(
            [
                mock.call(
                    notifier.callback_until_watcher,
                    "sun.sun",
                    new="above_horizon",
                    oneshot=True,
                    tag="notification_tag",
                ),
            ]
        )

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
                mock.call(
                    "All notifications with tag notification_tag will be cleared "
                    "if sun.sun transitions to above_horizon"
                ),
            ]
        )

    def test__callback_notifier_event_received__send_to_all__until_tag_state_new_changed(
        self, hass_driver, notifier: Notifier
    ):
        """
        Test the callback function for clearing notifications with a specific tag when a state condition on new is met.
        """
        # GIVEN
        #   user1 and user2 are present
        #   Notification has been sent with tag and until set
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent until change and associated with a callback
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            until=[
                {"entity_id": "sun.sun", "new_state": "above_horizon"},
            ],
            tag="notification_tag",
        )

        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
                mock.call(
                    "All notifications with tag notification_tag will be cleared "
                    "if sun.sun transitions to above_horizon"
                ),
            ]
        )

        call_service.reset_mock()
        log.reset_mock()

        # WHEN
        #   Until state is triggered
        hass_driver.set_state("sun.sun", "above_horizon")

        # THEN
        #   Notification cancellation is sent to both user
        #   Log is written
        call_service.assert_has_calls(
            [
                mock.call("notify/user1_mobile", message="clear_notification", data={"tag": "notification_tag"}),
                mock.call("notify/user2_mobile", message="clear_notification", data={"tag": "notification_tag"}),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Clearing notifications with tag notification_tag (if any) ..."),
                mock.call("Removing watchers with tag notification_tag (if any) ..."),
            ]
        )

    def test__callback_notifier_event_received__send_to_all__until_tag_state_old_changed(
        self, hass_driver, notifier: Notifier
    ):
        """
        Test the callback function for clearing notifications with a specific tag when a state condition on old is met.
        """
        # GIVEN
        #   user1 and user2 are present
        #   Sun is above horizon
        #   Notification has been sent with tag and until set
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "above_horizon")
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent until change and associated with a callback
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            until=[
                {"entity_id": "sun.sun", "old_state": "above_horizon"},
            ],
            tag="notification_tag",
        )

        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
                mock.call(
                    "All notifications with tag notification_tag will be cleared "
                    "if sun.sun transitions from above_horizon"
                ),
            ]
        )

        call_service.reset_mock()
        log.reset_mock()

        # WHEN
        #   Until state is triggered
        hass_driver.set_state("sun.sun", "below_horizon")

        # THEN
        #   Notification cancellation is sent to both user
        #   Log is written
        call_service.assert_has_calls(
            [
                mock.call("notify/user1_mobile", message="clear_notification", data={"tag": "notification_tag"}),
                mock.call("notify/user2_mobile", message="clear_notification", data={"tag": "notification_tag"}),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Clearing notifications with tag notification_tag (if any) ..."),
                mock.call("Removing watchers with tag notification_tag (if any) ..."),
            ]
        )

    def test__callback_notifier_event_received__send_to_all__until_tag_state_old_and_new_changed(
        self, hass_driver, notifier: Notifier
    ):
        """
        Test the callback function for clearing notifications with a specific tag when a certain external event
        is triggered.
        """
        # GIVEN
        #   Notification has been sent with tag and until set
        with hass_driver.setup():
            hass_driver.set_state("sun.sun", "above_horizon")
        self._initialize_presence(hass_driver, notifier, 1, 1)

        # WHEN
        #   Notification is sent until change and associated with a callback
        notifier.fire_event(
            "NOTIFIER",
            action="send_to_all",
            title="Notification Title",
            message="Notification message",
            icon="mdi-bell",
            color="deep-orange",
            until=[
                {"entity_id": "sun.sun", "old_state": "above_horizon", "new_state": "below_horizon"},
            ],
            tag="notification_tag",
        )

        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        log.assert_has_calls(
            [
                mock.call("NOTIFIER event received"),
                mock.call("Sending notification to user1"),
                mock.call("Sending notification to user2"),
                mock.call(
                    "All notifications with tag notification_tag will be cleared "
                    "if sun.sun transitions from above_horizon to below_horizon"
                ),
            ]
        )

        call_service.reset_mock()
        log.reset_mock()

        # WHEN
        #   Until state is triggered
        hass_driver.set_state("sun.sun", "below_horizon")

        # THEN
        #   Notification cancellation is sent to both user
        #   Log is written
        call_service.assert_has_calls(
            [
                mock.call("notify/user1_mobile", message="clear_notification", data={"tag": "notification_tag"}),
                mock.call("notify/user2_mobile", message="clear_notification", data={"tag": "notification_tag"}),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Clearing notifications with tag notification_tag (if any) ..."),
                mock.call("Removing watchers with tag notification_tag (if any) ..."),
            ]
        )

    @pytest.mark.parametrize("external_event", ["NOTIFIER_DISCARD", "mobile_app_notification_action"])
    def test__callback_notifier_event_received__send_to_all__until_tag_event_discard(
        self, hass_driver, notifier: Notifier, external_event
    ):
        """
        Test the callback function for clearing notifications with a specific tag when a certain external event
        is triggered.
        """
        # GIVEN
        #   Notification has been sent with tag and until set
        self.test__callback_notifier_event_received__send_to_all__until_tag_initialization(hass_driver, notifier)

        call_service = hass_driver.get_mock("call_service")
        log = hass_driver.get_mock("log")

        call_service.reset_mock()
        log.reset_mock()

        # WHEN
        #   Cancel event is triggered state is triggered
        notifier.fire_event(
            external_event,
            tag="notification_tag",
        )

        # THEN
        #   Notification cancellation is sent to both user
        #   Log is written
        call_service.assert_has_calls(
            [
                mock.call("notify/user1_mobile", message="clear_notification", data={"tag": "notification_tag"}),
                mock.call("notify/user2_mobile", message="clear_notification", data={"tag": "notification_tag"}),
            ],
            any_order=True,
        )

        log.assert_has_calls(
            [
                mock.call("Clearing notifications with tag notification_tag (if any) ..."),
                mock.call("Removing watchers with tag notification_tag (if any) ..."),
            ]
        )
