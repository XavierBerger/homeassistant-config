# Package configuration
```
packages
├── addons
│   ├── proximity.yaml
│   ├── sun.yaml
│   └── telegram.yaml
└── sensors
    ├── home_occupation.yaml
    ├── meteo.yaml
    └── nono.yaml
```

## Addons

### proximity.yaml

[Proximity](https://www.home-assistant.io/integrations/proximity/) configuration used by  [Notifier](../appdaemon/README.md#notifier).

### sun.yaml

Activate [Sun](https://www.home-assistant.io/integrations/sun/) integration used by [Automower](../appdaemon/README.md#automower) and [Garage Door](../appdaemon/README.md#garage-door) appdaemon applications to have information about sun. 

### telegram.yaml

[Telegram](https://www.home-assistant.io/integrations/telegram/) configuration used by [Automower](../appdaemon/README.md#automower) appdaemon application to send notifications.

## Sensors

### home_occupation.yaml

Binary sensor `home_occupied` defining if home is currently occupied or not. This sensor is used by  [Notifier](../appdaemon/README.md#notifier).

### meteo.yaml

Add various sensor to have history of rain. Some of these sensors are uses by [Automower](../appdaemon/README.md#automower) appdaemon application to determine is lawn has to be considered as dry or not.

### nono.yaml

Binary sensor `parked_because_of_rain` used by [Automower](../appdaemon/README.md#automower) appdaemon application to make state of park reason persistent.