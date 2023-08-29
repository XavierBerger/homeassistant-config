# Home Asshstant Config

This repository is gathering the part of home assistant configuration and appdaemon script I want to share with the community.

## Appdaemon applications

### Multiple shopping list manager

[Shopping list](https://www.home-assistant.io/integrations/shopping_list/) integration is only able to mange one shopping list. This application add teh capability the manage multiple shopping lists. Shopping list can be selected and updated indpendently and notification can be send when entering in a shop zone. One list can be associated to multiple zone.

Read the comment on the to of the script to see how to install and configure it. 


### Notifier

[Notifier](https://github.com/jlpouffier/home-assistant-config/blob/master/appdaemon/apps/notifier.py) is a script originally written by jlpouffier. The version provided in this directory has been slightly updated for optimisation. I also created a test script which covers 100% of the code to be sure that modification I add doesn't change to original behavior.

### Appdaemon testing

[Appdaemon-testing](https://github.com/nickw444/appdaemon-testing) is a framework designed to create unit test of appdaemon scripts. Even if the original version doesn't provides all the tools I need to fully test my scripts, I dicide to use it since it is easy to understand and easy to update.

The version provided into this repository is an improved version with additionnal tests functions. 