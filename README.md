# Home Assistant Config

This repository is gathering the part of home assistant configuration and appdaemon script I want to share with the community. The code available in this directory is under MIT License. <a href="LICENSE">![](images/license.svg)</a>

## Home automation architecture

My installation is composed by, solar panels, a weather station, an automover, ... all managed by Home Assistant. 
The architecture of my installation is detailed into [**Architecture page**](architecture/README.md).

## Appdaemon applications

<a href="https://xavierberger.github.io/homeassistant-config/">![](https://xavierberger.github.io/homeassistant-config/pylint.svg)</a>
<a href="https://xavierberger.github.io/homeassistant-config/">![](https://xavierberger.github.io/homeassistant-config/pytest.svg)</a>
<a href="https://xavierberger.github.io/homeassistant-config/">![code coverage](https://xavierberger.github.io/homeassistant-config/coverage.svg)</a>

AppDaemon directory is gathering the application I use to manage automower, garage door, shopping list, ... All details of theses applications are available into a [**Appdaemon** page](appdaemon/README.md).

* [multiple shopping list](appdaemon#multiple-shopping-list-manager) : Manage multiple shopping lists
* [Garage door](appdaemon#garage-door) : Send notification is garage dorr remain open at night
* [Automower](appdaemon#automower) : Advanced management of automower

A specific effort has been made on test. Detail of tests are explained into [**Appdaemon Test** page](appdaemon/test/README.md). Code coverage report is available [here](https://xavierberger.github.io/homeassistant-config/).

## Configuration

Configuration is organized into packages. Detail of tests are explained into [**Packages** page](packages/README.md).

* 