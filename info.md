# NHL Scores

## Description

This integration retrieves scores for your favorite NHL team.

## Installation:

### Manual
Clone or download this repository and copy the "nhl" directory to your "custom_components" directory in your config directory

<config directory>/custom_components/nhl/...

### HACS
Open the HACS section of Home Assistant.
Click the "..." button in the top right corner and select "Custom Repositories."
In the window that opens paste this Github URL.
In the window that opens when you select it click om "Install This Repository in HACS"

## Configuration:

Find your team ID, which is a 2- or 3-letter acronym (eg. "SEA" for Seattle or "NE" for New England). You can find yours at https://espn.com/nhl in the top scores UI. 

### Via the "Configuration->Integrations" section of the Home Assistant UI

Look for the integration labeled "NHL" and enter your team's acronym in the UI prompt. You can also enter a friendly name. If you keep the default, your sensor will be `sensor.nhl`, otherwise it will be `sensor.friendly_name_you_picked`. 

### Manually in your `configuration.yaml` file

To create a sensor instance add the following configuration to your sensor definitions using the team_id found above:

```
- platform: nhl
  team_id: 'NYR'
```

After you restart Home Assistant then you should have a new sensor called `sensor.nhl` in your system.

You can overide the sensor default name (`sensor.nhl`) to one of your choosing by setting the `name` option:

```
- platform: nhl
  team_id: 'NYR'
  name: New York Rangers
```

Using the configuration example above the sensor will then be called "sensor.new_york_rangers".
