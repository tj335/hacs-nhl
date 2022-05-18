# NHL game data in Home Assistant

This integration fetches data for an NHL team's current/future game, and creates a sensor with attributes for the details of the game. 

The integration is a shameless fork of the excellent [NFL](https://github.com/zacs/ha-nfl) custom component by @zacs.

## Sensor Data

### State
The sensor is pretty simple: the main state is `PRE`, `IN`, `POST`, or `NOT_FOUND`, but there are attributes for pretty much all aspects of the game, when available. State definitions are as you'd expect:
- `PRE`: The game is in pre-game state. 
- `IN`: The game is in progress.
- `POST`: The game has completed. It usually remains in this state until about 10:00 AM ET the following day when ESPN updates their scoreboard.
- `NOT_FOUND`: There is no game found for your team. This should only happen at the end of the season, and once your team is eliminated from postseason play. 

### Attributes
The attributes available will change based on the sensor's state, a small number are always available (team abbreviation, team name, and logo), but otherwise the attributes only populate when in the current state. The table below lists which attributes are available in which states. 

| Name | Value | Relevant States |
| --- | --- | --- |
| `detailed_state` | Containts a more detailed status of the game such as STATUS_SCHEDULED. | `PRE` `IN` `POST` |
| `game_length` | Length of the game | `POST` |
| `date` | Date and time that the game starts (or started) | `PRE` `IN` `POST` |
| `game_end_time` | Date and time that the game ended | `POST` |
| `attendance` | Number of fans in attendance | `POST` |
| `event_name` | Description of the event (eg. "New York Rangers at Carolina Hurricanes") | `PRE` `IN` `POST` |
| `event_short_name` | Shorter description of the event (eg. "NYR @ CAR") | `PRE` `IN` `POST` |
| `event_type` | Code indicating the type of event (eg. "STD", "RD16" or "QTR") | `PRE` `IN` `POST` |
| `game_notes` | Notes about the game (eg. "East 1st Round - Game 7") | `PRE` `IN` `POST` |
| `series_summary` | Current status of the series (eg. "Series Tied 3-3") | `PRE` `IN` `POST` |
| `venue_name` | The name of the stadium where the game is being played (eg. "PNC Arena") | `PRE` `IN` `POST` |
| `venue_city` | The city where the stadium is located (eg. "Raleigh") | `PRE` `IN` `POST` |
| `venue_state` | The state where the stadium is located (eg. "NC") | `PRE` `IN` `POST` |
| `venue_capacity` | The capacity of the venue (eg. "18,680") | `PRE` `IN` `POST` |
| `venue_indoor` | An indicator if the venue is indoors (true) or not (false)  | `PRE` `IN` `POST` |
| `period` | The current period of the game formatted as an integer (eg. "3") | `IN` |
| `period_description` | The current period of the game (eg. "13:33 - 3rd") | `IN` |
| `winning_goalie` | Name of the winning goalie | `POST` |
| `winning_goalie_saves` | An integer representing the number of saves for the winning goalie | `POST` |
| `winning_goalie_save_pct` | A float representing the save percentage for the winning goalie | `POST` |
| `losing_goalie` | Name of the losting goalie | `POST` |
| `losing_goalie_saves` | An integer representing the number of saves for the winning goalie | `POST` |
| `losing_goalie_save_pct` | A float representing the save percentage for the winning goalie | `POST` |
| `first_star` | Name of the game's 1st star | `POST` |
| `second_star` | Name of the game's 2nd star | `POST` |
| `third_star` | Name of the game's 3rd star | `POST` |
| `game_status` | Status of the current game | `IN` `POST` |
| `home_team_abbr` | The abbreviation of the home team (ie. `CAR` for the Carolina Hurricanes). | `PRE` `IN` `POST` |
| `home_team_id` | A numeric ID for the home team. | `PRE` `IN` `POST` |
| `home_team_city` | The home team's city (eg. "Carolina"). Note this does not include the team name. | `PRE` `IN` `POST` |
| `home_team_name` | The home team's name (eg. "Hurricanes"). Note this does not include the city name. | `PRE` `IN` `POST` |
| `home_team_logo` | A URL for a 500px wide PNG logo for the home team. | `PRE` `IN` `POST` |
| `home_team_goals` | The home team's score. An integer. | `IN` `POST` |
| `home_team_colors` | An array with two hex colors. The first is the home team's primary color, and the second is their secondary color. | `PRE` `IN` `POST` |
| `home_team_ls_1` | The home team's line score for the 1st period. An integer. | `IN` `POST` |
| `home_team_ls_2` | The home team's line score for the 2nd period. An integer. | `IN` `POST` |
| `home_team_ls_3` | The home team's line score for the 3rd period. An integer. | `IN` `POST` |
| `home_team_ls_ot` | The home team's line score for the OT period. An integer. | `IN` `POST` |
| `home_team_record` | The home team's current record (eg. "52-24-6"). | `PRE` `IN` `POST` |
| `away_team_abbr` | The abbreviation of the away team (ie. `NYR` for the New York Rangers). | `PRE` `IN` `POST` |
| `away_team_id` | A numeric ID for the away team. | `PRE` `IN` `POST` |
| `away_team_city` | The away team's city (eg. "New York"). Note this does not include the team name. | `PRE` `IN` `POST` |
| `away_team_name` | The away team's name (eg. "Rangers"). Note this does not include the city name. | `PRE` `IN` `POST` |
| `away_team_logo` | A URL for a 500px wide PNG logo for the away team. | `PRE` `IN` `POST` |
| `away_team_goals` | The away team's score. An integer. | `IN` `POST` |
| `away_team_colors` | An array with two hex colors. The first is the away team's primary color, and the second is their secondary color. | `PRE` `IN` `POST` |
| `away_team_ls_1` | The away team's line score for the 1st period. An integer. | `IN` `POST` |
| `away_team_ls_2` | The away team's line score for the 2nd period. An integer. | `IN` `POST` |
| `away_team_ls_3` | The away team's line score for the 3rd period. An integer. | `IN` `POST` |
| `away_team_ls_ot` | The away team's line score for the OT period. An integer. | `IN` `POST` |
| `away_team_record` | The away team's current record (eg. "54-20-8"). | `PRE` `IN` `POST` |
| `puck_drop_in` | Human-readable string for how far away the game is (eg. "in 30 minutes" or "tomorrow") |  `PRE` `IN` `POST` |
| `tv_network` | The TV network where you can watch the game (eg. "NBC" or "NFL"). Note that if there is a national feed, it will be listed here, otherwise the local affiliate will be listed. | `PRE` `IN` `POST` |
| `last_play` | Sentence describing the most recent play. Note this can be null between periods. | `IN` |
| `home_team_starting_goalie` | The probable starting goalie for the home team | `PRE` `IN` |
| `away_team_starting_goalie` | The probable starting goalie for the home team | `PRE` `IN` |
| `odds` | The betting odds for the game (eg. "PIT -5.0") | `PRE` |
| `overunder` | The over/under betting line for the total points scored in the game (eg. "42.5"). | `PRE` |
| `home_team_odds_win_pct` | The pre-game chance the home team has to win, according to ESPN.  A percentage, but presented as a float. | `IN` |
| `away_team_odds_win_pct` | The pre-game chance the away team has to win, according to ESPN.  A percentage, but presented as a float. | `IN` |
| `headlines` | A one sentence headline provided by ESPN. | `PRE` `IN` `POST` |
| `last_update` | A timestamp for the last time data was fetched for the game. If you watch this in real-time, you should notice it updating every 10 minutes, except for during the game (and for the ~20 minutes pre-game) when it updates every 5 seconds. | `PRE` `IN` `POST` |

## Installation

### Manually

Clone or download this repository and copy the "nhl" directory to your "custom_components" directory in your config directory

```<config directory>/custom_components/nhl/...```
  
### HACS

1. Open the HACS section of Home Assistant.
2. Click the "..." button in the top right corner and select "Custom Repositories."
3. In the window that opens paste this Github URL.
4. In the window that opens when you select it click om "Install This Repository in HACS"
  
## Configuration

You'll need to know your team ID, which is a 2- or 3-letter acronym (eg. "NYR" for New York Rangers). You can find yours at https://espn.com/nhl in the top scores UI. 

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
  name: Rangers
```

Using the configuration example above the sensor will then be called "sensor.rangers".
