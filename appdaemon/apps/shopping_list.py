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
import shutil
import time

import appdaemon.plugins.hass.hassapi as hass

# ----------------------------------------------------------------------------------------------------------------------
# Multiple shopping list manager
# ----------------------------------------------------------------------------------------------------------------------
#
#   Manage multiple shopping and notification based on Zone.
#   Notification gives an access to shopping list when entered into a shop.
#
# ----------------------------------------------------------------------------------------------------------------------
#
# To configure the application follow the instruction below:
#
# Create an input_select gathering the list of shops.
#    Options of this input_select are used to select the active list.
#
# Create zones
#    Zone are used to define shops area. These shop area are used to automatically select active list and trigger
#    notification. The beginning of zone's friendly_name has to match the shop name as defined into options of
#    input_select described upper.
#
#    Example:
#      Zone "zone.Biocoop_Grenoble" and "zone.Biocoop_Modane" will both use the shoppinglist named "Biocoop"
#
# Notifier is a dependency
#   Refer to notifier.py documentation activate notification
#
# Configure an AppDeamon application with:
#   shopping_list:
#     module: shopping_list
#     class : ShoppingList
#     shops: input_select gathering the shops to manage
#     tempo: delay ins seconds between list population and item complete update (recommended: 0.1)
#            if complete item are not set corectly, increase this value
#     notificationurl: url of shopping list's lovelace card used in notification
#     notification_title: title display in notification. This text will be prefixed by the zone name.
#     notification_message: message to display in notification
#     persons: List of person to notify when they enter into shop zone. At least one person has to be defined.
#         - name: username as defined in notifier application (used for notification)
#           id: a user as defined in notifier application (used for zone tracking)
#
#   Appdaemon configuration example:
#     shopping_list:
#       module: shopping_list
#       class: ShoppingList
#       log: shopping_list_log
#       shops: input_select.shoppinglist
#       tempo: 0.1
#       notification_url: "/shopping-list-extended/"
#       notification_title: "Shopping list"
#       notification_message: "Show shopping list"
#       persons:
#         - name: user1
#           id: person.user1
#
# Lovelace configuration
#   Create a new card with a vertical_layout and add the shops' input_select and shopping list card
#   as in the yaml example below:
#
#   title: Shopping list
#   views:
#     - cards:
#         - type: vertical-stack
#           cards:
#             - type: entities
#               entities:
#                 - entity: input_select.shops
#             - type: shopping-list
#


class ShoppingList(hass.Hass):
    def initialize(self):
        """
        Initialize the shopping list manager application.

        This method sets up the necessary listeners and event handlers for the shopping list manager.
        It initializes the active shop change callback, shopping list update callback, and zone change
        callbacks for each specified person.

        Returns:
            None
        """
        self.log("Starting multiple shopping list manager")

        self.listen_state(self.callback_active_shop_changed, self.args["shops"])
        self.listen_event(self.callback_shopping_list_changed, "shopping_list_updated")

        if "persons" in self.args:
            for person in self.args["persons"]:
                self.listen_state(
                    self.callback_zone_changed,
                    person["id"],
                    name=person["name"],
                )

        # Note: cancel_listen_event has no effect when executed within callback_active_shop_changed
        #       A workaround to avoid burst call to callback_shopping_list_changed is to manage
        #       a flag raised during update which deactivate the callback and clear this flag with a timer
        self.updating = False

    def update_completed(self, cb_args):
        """
        Update completed callback for the shopping list manager.

        This method is called when the shopping list update process is completed. It sets the 'updating'
        flag to False, indicating that the update process is finished.

        Args:
            cb_args: Callback arguments (not used in this method).

        Returns:
            None
        """
        self.updating = False
        self.log("Shopping list updated")

    def activate_shop(self, shop):
        """
        Activate a new shop and initialize its shopping list.

        This method is responsible for changing the active shop and initializing its shopping list.
        It first checks if the shopping list is currently being updated and returns early if so.
        Then, it performs shopping list update using call_service to homeassistant' shoppinglist plugin.

        Args:
            shop (str): The shop identifier to activate.

        Returns:
            bool: True if the shop's shopping list contains incomplete items, False otherwise.
        """
        if self.updating is True:
            # A shop change has just occurs lets ignore this call
            return

        self.log(f"Active shop has changed to {shop}")

        # Stop listen on shopping list change since all call_service bellow will add a callback_shopping_list_changed
        # call in a FIFO which will be processed once current callback will be completed
        self.updating = True

        # Clear current shopping list
        self.call_service("shopping_list/complete_all")
        self.call_service("shopping_list/clear_completed_items")

        has_incomplete = False

        # Open shop's sopping list backup
        with open(f"/config/.shopping_list_{shop}.json", "r") as file:
            data = json.load(file)
            for item in data:
                # Add items from backup
                self.call_service("shopping_list/add_item", name=item["name"])
            # Note: Complete is set in a second loop and after a tempo because I notice that sometime the list was not
            #       recreated correctly maybe because of too fast service calls
            #       /!\ sleep should be avoided in appdaemon application but it mandatory to make update works
            #       I prefer not using 'run_in' to have have to open the file a second time
            time.sleep(self.args["tempo"])
            for item in data:
                if item["complete"]:
                    # Set completion from backup
                    self.call_service("shopping_list/complete_item", name=item["name"])
                else:
                    has_incomplete = True

        # Reactivate listen on shopping list change in one second (when callback burst will be finished)
        self.run_in(self.update_completed, 1)
        return has_incomplete

    def callback_active_shop_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling changes in the active shop.

        This method is called when the active shop changes and triggers the activation of the new shop.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.activate_shop(new)

    def callback_shopping_list_changed(self, event_name, data, kwargs):
        """
        Callback for handling changes in the shopping list.

        This method is called when an itel of the shoppinglist is updated and triggers the creation or update of
        the backup shopping list for the active shop.

        Args:
            Arguments as define into Appdaemon event documentation.

        Returns:
            None
        """
        if self.updating is True:
            # A shop change has just occurs lets ignore this call
            return
        # Copy active shopping list to shop's backup
        shop = self.get_state(self.args["shops"])
        shutil.copyfile("/config/.shopping_list.json", f"/config/.shopping_list_{shop}.json")

    def callback_zone_changed(self, entity, attribute, old, new, kwargs):
        """
        Callback for handling changes in the zone of a person.

        This method is called when the zone of a person changes. It handles actions based on entering
        or leaving a zone, such as loading the appropriate shopping list and sending or clearing notifications.

        Args:
            Arguments as define into Appdaemon callback documentation.

        Returns:
            None
        """
        self.log(f"Zone changed to {new} for {entity}")
        if self.get_state(f"zone.{old}") is not None:
            # Leaving zone
            old_zone = self.get_state(f"zone.{old}", attribute="friendly_name")
            self.log(f"Leaving zone: {old_zone}")

            # Cancel notification
            self.fire_event("NOTIFIER_DISCARD", tag="shoppinglist")

        if self.get_state(f"zone.{new}") is not None:
            # Entering zone
            new_zone = self.get_state(f"zone.{new}", attribute="friendly_name")
            self.log(f"Entering zone: {new_zone}")
            for shop in self.get_state(self.args["shops"], attribute="options"):
                if new_zone.startswith(shop):
                    self.log(f"{shop} > loading shopping list")
                    has_incomplete = self.activate_shop(shop)
                    self.log(f"{shop} > shopping list loaded.")
                    self.select_option(self.args["shops"], shop)
                    self.log(f"{shop} > input_select updated.")
                    # Send notification only if incomplete item are present in the list
                    if has_incomplete:
                        self.log("Send notification")
                        self.fire_event(
                            "NOTIFIER",
                            action=f"send_to_{kwargs['name']}",
                            title=f"{new_zone}: {self.args['notification_title']}",
                            message=self.args["notification_message"],
                            icon="mdi-cart",
                            color="deep-orange",
                            tag="shoppinglist",
                            click_url=self.args["notification_url"],
                        )
