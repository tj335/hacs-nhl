""" NHL Team Status """
import logging
from datetime import timedelta
from datetime import datetime
import arrow
import time

import aiohttp
from async_timeout import timeout
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_SCOREBOARD_ENDPOINT,
    API_TEAM_ENDPOINT,
    CONF_TIMEOUT,
    CONF_TEAM_ID,
    COORDINATOR,
    DEFAULT_TIMEOUT,
    DOMAIN,
    ISSUE_URL,
    PLATFORMS,
    USER_AGENT,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)

today = datetime.today().strftime('%Y-%m-%d')

def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    _LOGGER.info(offset)
    return utc_datetime + offset

_LOGGER.info(
        "Debugging todays date and time: %s",
        datetime.now(),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the saved entities."""
    # Print startup message
    _LOGGER.info(
        "NHL version %s is starting, if you have any issues please report them here: %s",
        VERSION,
        ISSUE_URL,
    )
    hass.data.setdefault(DOMAIN, {})

    if entry.unique_id is not None:
        hass.config_entries.async_update_entry(entry, unique_id=None)

        ent_reg = async_get(hass)
        for entity in async_entries_for_config_entry(ent_reg, entry.entry_id):
            ent_reg.async_update_entity(entity.entity_id, new_unique_id=entry.entry_id)

    # Setup the data coordinator
    coordinator = AlertsDataUpdateCoordinator(
        hass,
        entry.data,
        entry.data.get(CONF_TIMEOUT)
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, config_entry):
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        _LOGGER.info("Successfully removed sensor from the " + DOMAIN + " integration")
    except ValueError:
        pass
    return True


async def update_listener(hass, entry):
    """Update listener."""
    entry.data = entry.options
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, "sensor"))

async def async_migrate_entry(hass, config_entry):
     """Migrate an old config entry."""
     version = config_entry.version

     # 1-> 2: Migration format
     if version == 1:
         _LOGGER.debug("Migrating from version %s", version)
         updated_config = config_entry.data.copy()

         if CONF_TIMEOUT not in updated_config.keys():
             updated_config[CONF_TIMEOUT] = DEFAULT_TIMEOUT

         if updated_config != config_entry.data:
             hass.config_entries.async_update_entry(config_entry, data=updated_config)

         config_entry.version = 2
         _LOGGER.debug("Migration to version %s complete", config_entry.version)

     return True

class AlertsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching NHL data."""

    def __init__(self, hass, config, the_timeout: int):
        """Initialize."""
        self.interval = timedelta(minutes=20)
        self.name = config[CONF_NAME]
        self.timeout = the_timeout
        self.config = config
        self.hass = hass

        _LOGGER.debug("Data will be updated every %s", self.interval)

        super().__init__(hass, _LOGGER, name=self.name, update_interval=self.interval)

    async def _async_update_data(self):
        """Fetch data"""
        async with timeout(self.timeout):
            try:
                data = await update_game(self.config)
                # update the interval based on flag
                if data["private_fast_refresh"] == True:
                    self.update_interval = timedelta(seconds=5)
                else:
                    self.update_interval = timedelta(minutes=20)
            except Exception as error:
                raise UpdateFailed(error) from error
            return data
        


async def update_game(config) -> dict:
    """Fetch new state data for the sensor.
    This is the only method that should fetch new data for Home Assistant.
    """

    data = await async_get_state(config)
    return data

async def async_get_state(config) -> dict:
    """Query API for status."""

    values = {}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/ld+json"}
    data = None
    gameday_url = API_SCOREBOARD_ENDPOINT
    team_id = config[CONF_TEAM_ID]
    async with aiohttp.ClientSession() as session:
        async with session.get(gameday_url, headers=headers) as r:
            _LOGGER.debug("Getting state for %s from %s" % (team_id, gameday_url))
            if r.status == 200:
                data = await r.json()

    found_team = False
    if data is not None:
        for event in data["events"]:
            #_LOGGER.debug("Looking at this event: %s" % event)
            if team_id in event["shortName"]:
                _LOGGER.debug("Found team event for %s; parsing data." % (team_id))
                found_team = True
                # Determine whether our team is Competitor 0 or 1
                team_index = 0 if event["competitions"][0]["competitors"][0]["team"]["abbreviation"] == team_id else 1
                team_home_away = event["competitions"][0]["competitors"][team_index]["homeAway"]
                oppo_index = abs((team_index-1))
                
                try:
                    values["state"] = event["status"]["type"]["name"]
                except:
                    values["state"] = None
                
                # detailed_state will be one of: STATUS_SCHEDULED, STATUS_IN_PROGRESS, STATUS_FINAL
                try:
                    values["detailed_state"] = event["status"]["type"]["name"]
                except:
                    values["detailed_state"] = None
                
                # Attempt to calculate the length of the game
                #try:
                #    if prior_state in ['STATUS_IN_PROGRESS'] and values["state"] in ['STATUS_FINAL']:
                #        _LOGGER.debug("Calulating game time for %s" % (team_id))
                #        values["game_end_time"] = arrow.now().format(arrow.FORMAT_W3C)
                #        values["game_length"] = str(values["game_end_time"] - event["date"])
                #    elif values["state"] not in ['STATUS_FINAL']:
                #        values["game_end_time"] = None
                #        values["game_length"] = None
                #except:
                values["game_end_time"] = None
                values["game_length"] = None
                
                try:
                    values["date"] = event["date"]
                except:
                    values["date"] = None
                
                try:
                    values["attendance"] = event["competitions"][0]["attendance"]
                except:
                    values["attendance"] = None
                
                # Formatted as full team names like "Detroit Red Wings at New York Rangers"
                try:
                    values["event_name"] = event["name"]
                except:
                    values["event_name"] = None
                
                # Formatted as abbreviations like "DET @ NYR"
                try:
                    values["event_short_name"] = event["shortName"]
                except:
                    values["event_short_name"] = None

                # Formatted as "STD", "RD16", "QTR"
                try:
                    values["event_type"] = event["competitions"][0]["type"]["abbreviation"]
                except:
                    values["event_type"] = None
                
                # Formatted as "East 1st Round - Game 7", "East 2nd Round - Game 1"
                try:
                    values["game_notes"] = event["competitions"][0]["notes"][0]["headline"]
                except:
                    values["game_notes"] = None
                
                # Formatted as "Series Tied 3-3"
                try:
                    values["series_summary"] = event["competitions"][0]["series"]["summary"]
                except:
                    values["series_summary"] = None
                
                try:
                    values["venue_name"] = event["competitions"][0]["venue"]["fullName"]
                except:
                    values["venue_name"] = None
                
                try:
                    values["venue_city"] = event["competitions"][0]["venue"]["address"]["city"]
                except:
                    values["venue_city"] = None
                
                try:
                    values["venue_state"] = event["competitions"][0]["venue"]["address"]["state"]
                except:
                    values["venue_state"] = None
                
                try:
                    values["venue_capacity"] = event["competitions"][0]["venue"]["capacity"]
                except:
                    values["venue_capacity"] = None
                
                # Formatted as true/false
                try:
                    values["venue_indoor"] = event["competitions"][0]["venue"]["indoor"]
                except:
                    values["venue_indoor"] = None
                
                # Formatted as an integer like "3"
                try:
                    values["period"] = event["competitions"][0]["status"]["period"]
                except:
                    values["period"] = None
                
                # Formatted like "13:33 - 3rd"
                try:
                    values["period_description"] = event["competitions"][0]["status"]["type"]["shortDetail"]
                except:
                    values["period_description"] = None

                # featuredAthletes could be: winningGoalie, losingGoalie, firstStar, secondStar, thirdStar

                if values["state"] in ['STATUS_FINAL']:
                    try:
                        featuredAthlete_0_Type = event["competitions"][0]["status"]["featuredAthletes"][0]["name"]
                    except:
                        featuredAthlete_0_Type = None

                    try:
                        featuredAthlete_1_Type = event["competitions"][0]["status"]["featuredAthletes"][1]["name"]
                    except:
                        featuredAthlete_1_Type = None

                    try:
                        featuredAthlete_2_Type = event["competitions"][0]["status"]["featuredAthletes"][2]["name"]
                    except:
                        featuredAthlete_2_Type = None

                    try:
                        featuredAthlete_3_Type = event["competitions"][0]["status"]["featuredAthletes"][3]["name"]
                    except:
                        featuredAthlete_3_Type = None

                    try:
                        featuredAthlete_4_Type = event["competitions"][0]["status"]["featuredAthletes"][4]["name"]
                    except:
                        featuredAthlete_4_Type = None

                    if featuredAthlete_0_Type == 'winningGoalie':
                        wg_index = 0
                    elif featuredAthlete_1_Type == 'winningGoalie':
                        wg_index = 1
                    elif featuredAthlete_2_Type == 'winningGoalie':
                        wg_index = 2
                    elif featuredAthlete_3_Type == 'winningGoalie':
                        wg_index = 3
                    elif featuredAthlete_4_Type == 'winningGoalie':
                        wg_index = 4
                    else:
                        wg_index = -1

                    if featuredAthlete_0_Type == 'losingGoalie':
                        lg_index = 0
                    elif featuredAthlete_1_Type == 'losingGoalie':
                        lg_index = 1
                    elif featuredAthlete_2_Type == 'losingGoalie':
                        lg_index = 2
                    elif featuredAthlete_3_Type == 'losingGoalie':
                        lg_index = 3
                    elif featuredAthlete_4_Type == 'losingGoalie':
                        lg_index = 4
                    else:
                        lg_index = -1

                    if featuredAthlete_0_Type == 'firstStar':
                        fs_index = 0
                    elif featuredAthlete_1_Type == 'firstStar':
                        fs_index = 1
                    elif featuredAthlete_2_Type == 'firstStar':
                        fs_index = 2
                    elif featuredAthlete_3_Type == 'firstStar':
                        fs_index = 3
                    elif featuredAthlete_4_Type == 'firstStar':
                        fs_index = 4
                    else:
                        fs_index = -1

                    if featuredAthlete_0_Type == 'secondStar':
                        ss_index = 0
                    elif featuredAthlete_1_Type == 'secondStar':
                        ss_index = 1
                    elif featuredAthlete_2_Type == 'secondStar':
                        ss_index = 2
                    elif featuredAthlete_3_Type == 'secondStar':
                        ss_index = 3
                    elif featuredAthlete_4_Type == 'secondStar':
                        ss_index = 4
                    else:
                        ss_index = -1

                    if featuredAthlete_0_Type == 'thirdStar':
                        ts_index = 0
                    elif featuredAthlete_1_Type == 'thirdStar':
                        ts_index = 1
                    elif featuredAthlete_2_Type == 'thirdStar':
                        ts_index = 2
                    elif featuredAthlete_3_Type == 'thirdStar':
                        ts_index = 3
                    elif featuredAthlete_4_Type == 'thirdStar':
                        ts_index = 4
                    else:
                        ts_index = -1

                    if wg_index != -1:
                        try:
                            values["winning_goalie"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["athlete"]["fullName"]
                        except:
                            values["winning_goalie"] = None
                        
                        try:
                            if event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][0]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][0]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][1]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][1]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][2]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][2]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][3]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][3]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][4]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][4]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][5]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][5]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][6]["name"] == "saves":
                                values["winning_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][6]["displayValue"]
                            else:
                                values["winning_goalie_saves"] = None
                        except:
                            values["winning_goalie_saves"] = None
                    
                        try:
                            if event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][0]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][0]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][1]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][1]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][2]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][2]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][3]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][3]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][4]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][4]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][5]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][5]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][6]["name"] == "savePct":
                                values["winning_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][wg_index]["statistics"][6]["displayValue"]
                            else:
                                values["winning_goalie_save_pct"] = None
                        except:
                            values["winning_goalie_save_pct"] = None
                    else:
                        values["winning_goalie"] = None
                        values["winning_goalie_saves"] = None
                        values["winning_goalie_save_pct"] = None

                    if lg_index != -1:
                        try:
                            values["losing_goalie"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["athlete"]["fullName"]
                        except:
                            values["losing_goalie"] = None
                        
                        try:
                            if event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][0]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][0]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][1]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][1]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][2]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][2]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][3]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][3]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][4]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][4]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][5]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][5]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][6]["name"] == "saves":
                                values["losing_goalie_saves"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][6]["displayValue"]
                            else:
                                values["losing_goalie_saves"] = None
                        except:
                            values["losing_goalie_saves"] = None
                    
                        try:
                            if event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][0]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][0]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][1]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][1]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][2]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][2]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][3]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][3]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][4]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][4]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][5]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][5]["displayValue"]
                            elif event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][6]["name"] == "savePct":
                                values["losing_goalie_save_pct"] = event["competitions"][0]["status"]["featuredAthletes"][lg_index]["statistics"][6]["displayValue"]
                            else:
                                values["losing_goalie_save_pct"] = None
                        except:
                            values["losing_goalie_save_pct"] = None
                    else:
                        values["losing_goalie"] = None
                        values["losing_goalie_saves"] = None
                        values["losing_goalie_save_pct"] = None

                    if fs_index != -1:
                        try:
                            values["first_star"] = event["competitions"][0]["status"]["featuredAthletes"][fs_index]["athlete"]["fullName"]
                        except:
                            values["first_star"] = None
                    else:
                        values["first_star"] = None

                    if ss_index != -1:
                        try:
                            values["second_star"] = event["competitions"][0]["status"]["featuredAthletes"][ss_index]["athlete"]["fullName"]
                        except:
                            values["second_star"] = None
                    else:
                        values["second_star"] = None

                    if ts_index != -1:
                        try:
                            values["third_star"] = event["competitions"][0]["status"]["featuredAthletes"][ts_index]["athlete"]["fullName"]
                        except:
                            values["third_star"] = None
                    else:
                        values["third_star"] = None
                else:
                    values["winning_goalie"] = None
                    values["winning_goalie_saves"] = None
                    values["winning_goalie_save_pct"] = None
                    values["losing_goalie"] = None
                    values["losing_goalie_saves"] = None
                    values["losing_goalie_save_pct"] = None
                    values["first_star"] = None
                    values["second_star"] = None
                    values["third_star"] = None

                try:
                    values["game_status"] = event["status"]["type"]["shortDetail"]
                except:
                    values["game_status"] = None
                
                try:
                    values["home_team_abbr"] = event["competitions"][0]["competitors"][0]["team"]["abbreviation"]
                except:
                    values["home_team_abbr"] = None
                
                try:
                    values["home_team_id"] = event["competitions"][0]["competitors"][0]["team"]["id"]
                except:
                    values["home_team_id"] = None
                    
                try:
                    values["home_team_city"] = event["competitions"][0]["competitors"][0]["team"]["location"]
                except:
                    values["home_team_city"] = None
                
                try:
                    values["home_team_name"] = event["competitions"][0]["competitors"][0]["team"]["name"]
                except:
                    values["home_team_name"] = None
                
                try:
                    values["home_team_logo"] = event["competitions"][0]["competitors"][0]["team"]["logo"]
                except:
                    values["home_team_logo"] = None
                
                try:
                    values["home_team_goals"] = event["competitions"][0]["competitors"][0]["score"]
                except:
                    values["home_team_goals"] = None

                try:
                    values["home_team_colors"] = [''.join(('#',event["competitions"][0]["competitors"][0]["team"]["color"])), 
                        ''.join(('#',event["competitions"][0]["competitors"][0]["team"]["alternateColor"]))]
                except:
                    values["home_team_colors"] = ['#013369','#013369']
                
                try:
                    values["home_team_ls_1"] = event["competitions"][0]["competitors"][0]["linescores"][0]["value"]
                except:
                    values["home_team_ls_1"] = None

                try:
                    values["home_team_ls_2"] = event["competitions"][0]["competitors"][0]["linescores"][1]["value"]
                except:
                    values["home_team_ls_2"] = None

                try:
                    values["home_team_ls_3"] = event["competitions"][0]["competitors"][0]["linescores"][2]["value"]
                except:
                    values["home_team_ls_3"] = None
                
                try:
                    values["home_team_ls_ot"] = event["competitions"][0]["competitors"][0]["linescores"][3]["value"]
                except:
                    values["home_team_ls_ot"] = None
                
                try:
                    values["home_team_record"] = event["competitions"][0]["competitors"][0]["records"][0]["summary"]
                except:
                    values["home_team_record"] = None
                
                try:
                    values["away_team_abbr"] = event["competitions"][0]["competitors"][1]["team"]["abbreviation"]
                except:
                    values["away_team_abbr"] = None
                    
                try:
                    values["away_team_id"] = event["competitions"][0]["competitors"][1]["team"]["id"]
                except:
                    values["away_team_id"] = None
                
                try:
                    values["away_team_city"] = event["competitions"][0]["competitors"][1]["team"]["location"]
                except:
                    values["away_team_city"] = None
                
                try:
                    values["away_team_name"] = event["competitions"][0]["competitors"][1]["team"]["name"]
                except:
                    values["away_team_name"] = None
                
                try:
                    values["away_team_logo"] = event["competitions"][0]["competitors"][1]["team"]["logo"]
                except:
                    values["away_team_logo"] = None
                
                try:
                    values["away_team_goals"] = event["competitions"][0]["competitors"][1]["score"]
                except:
                    values["away_team_goals"] = None
                    
                try:
                    values["away_team_colors"] = [''.join(('#',event["competitions"][0]["competitors"][1]["team"]["color"])), 
                        ''.join(('#',event["competitions"][0]["competitors"][1]["team"]["alternateColor"]))]
                except:
                    values["away_team_colors"] = ['#D50A0A','#D50A0A']
                
                #if event["status"]["type"]["state"].lower() in ['in']:
                try:
                    values["away_team_ls_1"] = event["competitions"][0]["competitors"][1]["linescores"][0]["value"]
                except:
                    values["away_team_ls_1"] = None

                try:
                    values["away_team_ls_2"] = event["competitions"][0]["competitors"][1]["linescores"][1]["value"]
                except:
                    values["away_team_ls_2"] = None

                try:
                    values["away_team_ls_3"] = event["competitions"][0]["competitors"][1]["linescores"][2]["value"]
                except:
                    values["away_team_ls_3"] = None

                try:
                    values["away_team_ls_ot"] = event["competitions"][0]["competitors"][1]["linescores"][3]["value"]
                except:
                    values["away_team_ls_ot"] = None
                
                try:
                    values["away_team_record"] = event["competitions"][0]["competitors"][1]["records"][0]["summary"]
                except:
                    values["away_team_record"] = None
                
                try:
                    values["puck_drop_in"] = arrow.get(event["date"]).humanize()
                except:
                    values["puck_drop_in"] = None
                
                try:
                    values["tv_network"] = event["competitions"][0]["broadcasts"][0]["names"]
                except:
                    values["tv_network"] = None
                
                try:
                    values["last_play"] = event["competitions"][0]["situation"]["lastPlay"]["text"]
                except:
                    values["last_play"] = None
                
                # Starting Goalie
                try:
                    values["home_team_starting_goalie"] = event["competitions"][0]["competitors"][0]["probables"][0]["athlete"]["displayName"]
                except:
                    values["home_team_starting_goalie"] = None
                
                try:
                    values["away_team_starting_goalie"] = event["competitions"][0]["competitors"][1]["probables"][0]["athlete"]["displayName"]
                except:
                    values["away_team_starting_goalie"] = None
                
                try:
                    values["odds"] = event["competitions"][0]["odds"][0]["details"]
                except:
                    values["odds"] = None
                    
                try:
                    values["overunder"] = event["competitions"][0]["odds"][0]["overUnder"]
                except:
                    values["overunder"] = None
                
                try:
                    values["home_team_odds_win_pct"] = event["competitions"][0]["odds"][1]["homeTeamOdds"]["winPercentage"]
                except:
                    values["home_team_odds_win_pct"] = None
                
                try:
                    values["away_team_odds_win_pct"] = event["competitions"][0]["odds"][1]["awayTeamOdds"]["winPercentage"]
                except:
                    values["away_team_odds_win_pct"] = None
                
                try:
                    values["headlines"] = event["competitions"][0]["headlines"][0]["shortLinkText"]
                except:
                    values["headlines"] = None

                try:
                    if values["state"] in ['STATUS_FINAL']:
                        if values["home_team_abbr"] == team_id:
                            if values["home_team_goals"] > values["away_team_goals"]:
                                values["win_or_loss"] = "win"
                            else:
                                values["win_or_loss"] = "loss"
                        else:
                            if values["home_team_goals"] > values["away_team_goals"]:
                                values["win_or_loss"] = "loss"
                            else:
                                values["win_or_loss"] = "win"
                    else:
                        values["win_or_loss"] = None
                except:
                    values["win_or_loss"] = None

                    
                values["last_update"] = arrow.now().format(arrow.FORMAT_W3C)
                values["private_fast_refresh"] = False
        
        # Never found the team. Either off today or a post-season condition
        if not found_team:
            _LOGGER.info("Team not found on scoreboard feed.  Using team API.")

            team_url = API_TEAM_ENDPOINT + team_id
            _LOGGER.info(team_url)
            async with aiohttp.ClientSession() as session:
                async with session.get(team_url, headers=headers) as r:
                    if r.status == 200:
                        data = await r.json()
            team_data = data["team"]

            # Determine if our team is home or away.  hoome team is always index 0.
            try:
                team_index = 0 if team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["abbreviation"] == team_id else 1
            except:
                team_index = -1
            
            if team_index == -1:
                oppo_index = -1
            else:
                oppo_index = abs((team_index - 1))
            
            # Determine our opponents team id (abbreviation) so that we can lookup their information as well
            if oppo_index == -1:
                oppo_id = None
                oppo_url = None
                oppo_data = None
            else:
                oppo_id = team_data["nextEvent"][0]["competitions"][0]["competitors"][oppo_index]["team"]["abbreviation"]
                oppo_url = API_TEAM_ENDPOINT + oppo_id
                _LOGGER.info(oppo_url)
                async with aiohttp.ClientSession() as session:
                    async with session.get(oppo_url, headers=headers) as r:
                        if r.status == 200:
                            data = await r.json()
                oppo_data = data["team"]

            try:
                values["state"] = team_data["nextEvent"][0]["competitions"][0]["status"]["type"]["name"]
            except:
                values["state"] = None
                
#            if values["state"] in ['STATUS_FINAL']:
#                _LOGGER.info("Game State is STATUS_FINAL")
#                if team_data["nextEvent"][0]["competitions"][0]["status"]["type"]["description"] == "Postponed":
#                    _LOGGER.info("Game is Postponed, set state")
#                    values["state"] = "STATUS_POSTPONED"
            try:
                values["detailed_state"] = team_data["nextEvent"][0]["competitions"][0]["status"]["type"]["name"]
            except:
                values["detailed_state"] = None
            
            try:
                values["date"] = team_data["nextEvent"][0]["date"]
            except:
                values["date"] = None

            values["last_update"] = arrow.now().format(arrow.FORMAT_W3C)

            values["attendance"] = None
            
            try:
                values["event_name"] = team_data["nextEvent"][0]["name"]
            except:
                values["event_name"] = None
            
            try:
                values["event_short_name"] = team_data["nextEvent"][0]["shortName"]
            except:
                values["event_short_name"] = None
            
            try:
                values["event_type"] = team_data["nextEvent"][0]["competitions"][0]["type"]["abbreviation"]
            except:
                values["event_type"] = None
            
            try:
                values["game_notes"] = team_data["nextEvent"][0]["competitions"][0]["notes"][0]["headline"]
            except:
                values["game_notes"] = None

            try:
                values["series_summary"] = team_data["nextEvent"][0]["competitions"][0]["series"]["summary"]
            except:
                values["series_summary"] = None
            
            try:
                values["venue_name"] = team_data["nextEvent"][0]["competitions"][0]["venue"]["fullName"]
            except:
                values["venue_name"] = None
            
            try:
                values["venue_city"] = team_data["nextEvent"][0]["competitions"][0]["venue"]["address"]["city"]
            except:
                values["venue_city"] = None
            
            try:
                values["venue_state"] = team_data["nextEvent"][0]["competitions"][0]["venue"]["address"]["state"]
            except:
                values["venue_state"] = None
                

            if team_index == 0:
                try:
                    values["venue_capacity"] = team_data["franchise"]["venue"]["capacity"]
                except:
                    values["venue_capacity"] = None
                
                # Formatted as true/false
                try:
                    values["venue_indoor"] = team_data["franchise"]["venue"]["indoor"]
                except:
                    values["venue_indoor"] = None
            else:
                try:
                    values["venue_capacity"] = oppo_data["franchise"]["venue"]["capacity"]
                except:
                    values["venue_capacity"] = None
                
                # Formatted as true/false
                try:
                    values["venue_indoor"] = oppo_data["franchise"]["venue"]["indoor"]
                except:
                    values["venue_indoor"] = None
                
            values["period"] = None
            values["period_description"] = None

            # featuredAthletes could be: winningGoalie, losingGoalie, firstStar, secondStar, thirdStar
            values["winning_goalie"] = None
            values["winning_goalie_saves"] = None
            values["winning_goalie_save_pct"] = None
            values["losing_goalie"] = None
            values["losing_goalie_saves"] = None
            values["losing_goalie_save_pct"] = None
            values["first_star"] = None
            values["second_star"] = None
            values["third_star"] = None
            values["game_status"] = None          
            
            try:
                values["home_team_abbr"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["abbreviation"]
            except:
                values["home_team_abbr"] = None
            
            try:
                values["home_team_id"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["id"]
            except:
                values["home_team_id"] = None
            
            try:
                values["home_team_city"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["location"]
            except:
                values["home_team_city"] = None
            
            try:
                values["home_team_name"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["shortDisplayName"]
            except:
                values["home_team_name"] = None

            if team_index == 0:
                try:
                    values["home_team_colors"] = [''.join(('#',team_data["color"])), 
                            ''.join(('#',team_data["alternateColor"]))]
                except:
                    values["home_team_colors"] = None
                
                try:
                    values["home_team_record"] = team_data["record"]["items"][0]["summary"]
                except:
                    values["home_team_record"] = None
            else:
                try:
                    values["home_team_colors"] = [''.join(('#',oppo_data["color"])), 
                            ''.join(('#',oppo_data["alternateColor"]))]
                except:
                    values["home_team_colors"] = None
                
                try:
                    values["home_team_record"] = oppo_data["record"]["items"][0]["summary"]
                except:
                    values["home_team_record"] = None

            try:
                values["home_team_logo"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["team"]["logos"][2]["href"]
            except:
                values["home_team_logo"] = None
                
            values["home_team_goals"] = None
            values["home_team_ls_1"] = None
            values["home_team_ls_2"] = None
            values["home_team_ls_3"] = None                
            values["home_team_ls_ot"] = None
            
            try:
                values["away_team_abbr"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["team"]["abbreviation"]
            except:
                values["away_team_abbr"] = None
            
            try:
                values["away_team_id"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["team"]["id"]
            except:
                values["away_team_id"] = None
                
            try:
                values["away_team_city"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["team"]["location"]
            except:
                values["away_team_city"] = None
                
            try:
                values["away_team_name"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["team"]["shortDisplayName"]
            except:
                values["away_team_name"] = None

            if team_index == 1:
                try:
                    values["away_team_colors"] = [''.join(('#',team_data["color"])), 
                            ''.join(('#',team_data["alternateColor"]))]
                except:
                    values["away_team_colors"] = None
                
                try:
                    values["away_team_record"] = team_data["record"]["items"][0]["summary"]
                except:
                    values["away_team_record"] = None
            else:
                try:
                    values["away_team_colors"] = [''.join(('#',oppo_data["color"])), 
                            ''.join(('#',oppo_data["alternateColor"]))]
                except:
                    values["away_team_colors"] = None
                
                try:
                    values["away_team_record"] = oppo_data["record"]["items"][0]["summary"]
                except:
                    values["away_team_record"] = None

            try:
                values["away_team_logo"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["team"]["logos"][2]["href"]
            except:
                values["away_team_logo"] = None
                
            values["away_team_goals"] = None
            values["away_team_ls_1"] = None
            values["away_team_ls_2"] = None
            values["away_team_ls_3"] = None
            values["away_team_ls_ot"] = None
            
            try:
                values["puck_drop_in"] = arrow.get(team_data["nextEvent"][0]["date"]).humanize()       
            except:
                values["puck_drop_in"] = None
                
            try:
                values["tv_network"] = team_data["nextEvent"][0]["competitions"][0]["broadcasts"][0]["media"]["shortName"]
            except:
                values["tv_network"] = None
                
            values["last_play"] = None
                
            # Starting Goalie
            try:
                values["home_team_starting_goalie"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][0]["probables"][0]["athlete"]["displayName"]
            except:
                values["home_team_starting_goalie"] = None
            
            try:
                values["away_team_starting_goalie"] = team_data["nextEvent"][0]["competitions"][0]["competitors"][1]["probables"][0]["athlete"]["displayName"]
            except:
                values["away_team_starting_goalie"] = None

            values["odds"] = None
            values["overunder"] = None
            values["home_team_odds_win_pct"] = None
            values["away_team_odds_win_pct"] = None
            
            try:
                values["headlines"] = team_data["nextEvent"][0]["competitions"][0]["notes"][0]["headline"]
            except:
                values["headlines"] = None

            values["win_or_loss"] = None
            
            values["last_update"] = arrow.now().format(arrow.FORMAT_W3C)
            values["game_length"] = None
            values["game_end_time"] = None

            if ((arrow.get(values["date"])-arrow.now()).total_seconds() < 172800):
                _LOGGER.debug("Next event for %s is 2 or more days ago, so this is likely a post-season scenario.", team_id) 
                values["state"] = 'STATUS_NO_GAME'
                values["detailed_state"] = 'STATUS_NO_GAME'
                values["date"] = None
                values["event_name"] = None
                values["event_short_name"] = None
                values["event_type"] = None
                values["game_notes"] = None
                values["venue_name"] = None
                values["venue_city"] = None
                values["venue_state"] = None
                values["venue_capacity"] = None
                values["venue_indoor"] = None
                values["home_team_abbr"] = None
                if values["home_team_abbr"] != team_id:
                    values["home_team_abbr"] = values["away_team_abbr"]
                    values["home_team_id"] = values["away_team_id"]
                    values["home_team_city"] = values["away_team_city"]
                    values["home_team_name"] = values["away_team_name"]
                    values["home_team_logo"] = values["away_team_logo"]
                    values["home_team_colors"] = values["away_team_colors"]
                    values["home_team_record"] = values["away_team_record"]
                
                values["away_team_abbr"] = None
                values["away_team_id"] = None
                values["away_team_city"] = None
                values["away_team_name"] = None
                values["away_team_logo"] = None
                values["away_team_colors"] = None
                values["away_team_record"] = None
                
                values["tv_network"] = None
                values["headlines"] = None
                values["win_or_loss"] = None

        if values["state"] == 'STATUS_SCHEDULED' and ((arrow.get(values["date"])-arrow.now()).total_seconds() < 1200):
            _LOGGER.debug("Event for %s is within 20 minutes, setting refresh rate to 5 seconds." % (team_id))
            values["private_fast_refresh"] = True
        elif values["state"] == 'STATUS_IN_PROGRESS':
            _LOGGER.debug("Event for %s is in progress, setting refresh rate to 5 seconds." % (team_id))
            values["private_fast_refresh"] = True
        elif values["state"] in ['STATUS_FINAL', 'OFF']: 
            _LOGGER.debug("Event for %s is over, setting refresh back to 10 minutes." % (team_id))
            values["private_fast_refresh"] = False
        else:
            _LOGGER.debug("Event for %s is other state, setting refresh to 10 minutes." % (team_id))
            values["private_fast_refresh"] = False


    return values

async def async_clear_states(config) -> dict:
    """Clear all state attributes"""
    
    values = {}
    # Reset values
    values = {
        "detailed_state": None,
        "game_length": None,
        "date": None,
        "game_end_time": None,
        "attendance": None,
        "event_name": None,
        "event_short_name": None,
        "event_type": None,
        "game_notes": None,
        "series_summary": None,
        "venue_name": None,
        "venue_city": None,
        "venue_state": None,
        "venue_capacity": None,
        "venue_indoor": None,
        "period": None,
        "period_description": None,
        "winning_goalie": None,
        "winning_goalie_saves": None,
        "winning_goalie_save_pct": None,
        "losing_goalie": None,
        "losing_goalie_saves": None,
        "losing_goalie_save_pct": None,
        "first_star": None,
        "second_star": None,
        "third_star": None,
        "game_status": None,
        "home_team_abbr": None,
        "home_team_id": None,
        "home_team_city": None,
        "home_team_name": None,
        "home_team_logo": None,
        "home_team_goals": None,
        "home_team_colors": None,
        "home_team_ls_1": None,
        "home_team_ls_2": None,
        "home_team_ls_3": None,
        "home_team_ls_ot": None,
        "home_team_record": None,
        "away_team_abbr": None,
        "away_team_id": None,
        "away_team_city": None,
        "away_team_name": None,
        "away_team_logo": None,
        "away_team_goals": None,
        "away_team_colors": None,
        "away_team_ls_1": None,
        "away_team_ls_2": None,
        "away_team_ls_3": None,
        "away_team_ls_ot": None,
        "away_team_record": None,
        "puck_drop_in": None,
        "tv_network": None,
        "last_play": None,
        "home_team_starting_goalie": None,
        "away_team_starting_goalie": None,
        "odds": None,
        "overunder": None,
        "home_team_odds_win_pct": None,
        "away_team_odds_win_pct": None,
        "headlines": None,
        "win_or_loss": None,
        "last_update": None,
        "team_id": None,
        "private_fast_refresh": False
    }

    return values
