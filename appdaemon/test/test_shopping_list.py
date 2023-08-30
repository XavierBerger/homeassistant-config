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
import json
from unittest import mock

import pytest
from apps.shopping_list import ShoppingList

from .appdaemon_testing.pytest import (  # pylint: disable=W0611
    automation_fixture,
    hass_driver,
)


@automation_fixture(
    ShoppingList,
    args={
        "shops": "input_select.shops",
        "notification_url": "/shopping-list-extended/",
        "notification_title": "Liste de course",
        "notification_message": "Afficher la liste de courses ",
        "persons": [
            {"name": "user1", "id": "person.user1"},
            {"name": "user2", "id": "person.user2"},
        ],
        "tempo": 0.5,
    },
)
def shopping_list() -> ShoppingList:
    pass


@pytest.fixture
def mock_open_files():
    """
    Fixture for mocking open files in unit tests.

    This fixture sets up a context for mocking the `open` function. It defines the expected contents
    for each file that might be opened during testing.

    Returns:
        tuple: A tuple containing the expected data dictionary and the mock file object.
    """
    # Define the expected contents for each file
    list_shop1 = [
        {"name": "Bread", "id": "1", "complete": False},
        {"name": "Cheese", "id": "2", "complete": True},
    ]
    list_shop2 = [
        {"name": "Pain", "id": "3", "complete": True},
        {"name": "Fromage", "id": "4", "complete": False},
    ]
    expected_data = {
        "/config/.shopping_list_shop1.json": json.dumps(list_shop1),
        "/config/.shopping_list_shop2.json": json.dumps(list_shop2),
    }

    def mock_open_side_effect(filename, mode):
        content = expected_data.get(filename, "")
        return mock.mock_open(read_data=content).return_value

    with mock.patch("builtins.open", mock_open_side_effect) as mock_file:
        yield expected_data, mock_file


@mock.patch("time.sleep", mock.Mock)
@pytest.mark.usefixtures("mock_open_files")
@pytest.mark.shopping_list
class TestShoppingList:
    # pylint: disable=W0621
    def test_initialization(self, hass_driver, shopping_list: ShoppingList):
        """
        Test case for initializing the shopping list manager application.

        This test case covers the initialization of the shopping list manager application
        and verifies that necessary listeners and event handlers are properly set up.

        Args:
            hass_driver (HassDriver): An instance of the Home Assistant driver.
            shopping_list (ShoppingList): An instance of the ShoppingList class.

        Returns:
            None
        """
        # GIVEN
        #   Application is starting

        # WHEN
        #   Application is initialized
        # THEN
        listen_state = hass_driver.get_mock("listen_state")
        assert listen_state.call_count == 3
        listen_state.assert_has_calls(
            [
                mock.call(shopping_list.callback_active_shop_changed, "input_select.shops"),
                mock.call(shopping_list.callback_zone_changed, "person.user1", name="user1"),
                mock.call(shopping_list.callback_zone_changed, "person.user2", name="user2"),
            ],
        )

        listen_event = hass_driver.get_mock("listen_event")
        assert listen_event.call_count == 1
        listen_event.assert_has_calls(
            [
                mock.call(shopping_list.callback_shopping_list_changed, "shopping_list_updated"),
            ],
        )

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Starting multiple shopping list manager"),
            ]
        )

    @pytest.mark.parametrize("shop", ["shop1", "shop2"])
    def test_shop_change(self, hass_driver, shopping_list: ShoppingList, shop):
        """
        Test case for simulating a change of active shop and its effects.

        This test case simulates a change of the active shop and verifies the resulting
        behaviors, such as making shopping list modifications and sending notifications.

        Args:
            hass_driver (HassDriver): An instance of the Home Assistant driver.
            shopping_list (ShoppingList): An instance of the ShoppingList class.
            shop (str): The shop identifier for parameterized testing.

        Returns:
            None
        """
        hass_driver.set_state("input_select.shops", shop)
        hass_driver.set_state("input_select.shops", "do_not_trigger_twice")

        call_service = hass_driver.get_mock("call_service")
        match shop:
            case "shop1":
                call_service.assert_has_calls(
                    [
                        mock.call("shopping_list/complete_all"),
                        mock.call("shopping_list/clear_completed_items"),
                        mock.call("shopping_list/add_item", name="Bread"),
                        mock.call("shopping_list/add_item", name="Cheese"),
                        mock.call("shopping_list/complete_item", name="Cheese"),
                    ]
                )
            case "shop2":
                call_service.assert_has_calls(
                    [
                        mock.call("shopping_list/complete_all"),
                        mock.call("shopping_list/clear_completed_items"),
                        mock.call("shopping_list/add_item", name="Pain"),
                        mock.call("shopping_list/add_item", name="Fromage"),
                        mock.call("shopping_list/complete_item", name="Pain"),
                    ]
                )

        assert len(hass_driver.get_run_in_simulations()) == 1
        hass_driver.advance_time(1)
        assert len(hass_driver.get_run_in_simulations()) == 0

        log = hass_driver.get_mock("log")
        log.assert_has_calls(
            [
                mock.call("Starting multiple shopping list manager"),
                mock.call(f"Active shop has changed to {shop}"),
                mock.call("Shopping list updated"),
            ]
        )

    @pytest.mark.parametrize("zone", ["shop1", "shop2", "shop10", "shop20"])
    @pytest.mark.parametrize("user", ["user1", "user2"])
    def test_user_enter_zone(self, hass_driver, shopping_list: ShoppingList, zone, user):
        """
        Test case for simulating user entry into a specified zone and its effects.

        This test case simulates a user entering a specific zone and verifies the resulting
        behaviors, such as making shopping list modifications and sending notifications.

        Args:
            hass_driver (HassDriver): An instance of the Home Assistant driver.
            shopping_list (ShoppingList): An instance of the ShoppingList class.
            zone (str): The zone identifier for parameterized testing.
            user (str): The user identifier for parameterized testing.

        Returns:
            None
        """
        hass_driver.set_state("input_select.shops", ["shop1", "shop2"], attribute_name="options")
        hass_driver.set_state(f"zone.{zone}", zone)
        hass_driver.set_state(f"zone.{zone}", zone, attribute_name="friendly_name")
        shop = ""

        log = hass_driver.get_mock("log")
        log.reset_mock()

        hass_driver.set_state(f"person.{user}", zone)

        call_service = hass_driver.get_mock("call_service")
        match zone:
            case "shop1" | "shop10":
                call_service.assert_has_calls(
                    [
                        mock.call("shopping_list/complete_all"),
                        mock.call("shopping_list/clear_completed_items"),
                        mock.call("shopping_list/add_item", name="Bread"),
                        mock.call("shopping_list/add_item", name="Cheese"),
                        mock.call("shopping_list/complete_item", name="Cheese"),
                    ]
                )
                shop = "shop1"
            case "shop2" | "shop20":
                call_service.assert_has_calls(
                    [
                        mock.call("shopping_list/complete_all"),
                        mock.call("shopping_list/clear_completed_items"),
                        mock.call("shopping_list/add_item", name="Pain"),
                        mock.call("shopping_list/add_item", name="Fromage"),
                        mock.call("shopping_list/complete_item", name="Pain"),
                    ]
                )
                shop = "shop2"

        assert len(hass_driver.get_run_in_simulations()) == 1
        hass_driver.advance_time(1)
        assert len(hass_driver.get_run_in_simulations()) == 0

        fire_event = hass_driver.get_mock("fire_event")
        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER",
                    action=f"send_to_{user}",
                    title=f"{zone}: Liste de course",
                    message="Afficher la liste de courses ",
                    icon="mdi-cart",
                    color="deep-orange",
                    tag="shoppinglist",
                    click_url="/shopping-list-extended/",
                ),
            ]
        )

        log.assert_has_calls(
            [
                mock.call(f"Zone changed to {zone} for person.{user}"),
                mock.call(f"Entering zone: {zone}"),
                mock.call(f"{shop} > loading shopping list"),
                mock.call(f"Active shop has changed to {shop}"),
                mock.call(f"{shop} > shopping list loaded."),
                mock.call(f"{shop} > input_select updated."),
                mock.call("Send notification"),
                mock.call("Shopping list updated"),
            ]
        )

        log.reset_mock()
        fire_event.reset_mock()

        hass_driver.set_state(f"person.{user}", "home")

        fire_event.assert_has_calls(
            [
                mock.call(
                    "NOTIFIER_DISCARD",
                    tag="shoppinglist",
                ),
            ]
        )

        log.assert_has_calls(
            [
                mock.call(f"Zone changed to home for person.{user}"),
                mock.call(f"Leaving zone: {zone}"),
            ]
        )

    @pytest.mark.parametrize("shop", ["shop1", "shop2"])
    def test_item_change(self, hass_driver, shopping_list: ShoppingList, shop):
        """
        Test case for verifying the behavior of item changes in the shopping list.

        This test case simulates changes to the shopping list and checks whether the
        expected behavior is observed. It verifies that the shopping list update events
        trigger the appropriate actions and that file copying is performed as expected.

        Args:
            hass_driver (HassDriver): An instance of the Home Assistant driver.
            shopping_list (ShoppingList): An instance of the ShoppingList class.
            shop (str): The shop identifier for parameterized testing.

        Returns:
            None
        """
        with mock.patch("shutil.copyfile", autospec=True, create=True) as mock_copyfile:
            hass_driver.set_state("input_select.shops", shop)

            assert shopping_list.updating

            shopping_list.fire_event("shopping_list_updated")

            assert mock_copyfile.call_count == 0

            shopping_list.updating = False
            shopping_list.fire_event("shopping_list_updated")

            mock_copyfile.assert_called_once_with("/config/.shopping_list.json", f"/config/.shopping_list_{shop}.json")
