import logging
import uuid

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from . import AlertsDataUpdateCoordinator

from .const import (
    ATTRIBUTION,
    CONF_TIMEOUT,
    CONF_TEAM_ID,
    COORDINATOR,
    DEFAULT_ICON,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_TEAM_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configuration from yaml"""
    if DOMAIN not in hass.data.keys():
        hass.data.setdefault(DOMAIN, {})
        config.entry_id = slugify(f"{config.get(CONF_TEAM_ID)}")
        config.data = config
    else:
        config.entry_id = slugify(f"{config.get(CONF_TEAM_ID)}")
        config.data = config

    # Setup the data coordinator
    coordinator = AlertsDataUpdateCoordinator(
        hass,
        config,
        config[CONF_TIMEOUT],
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    hass.data[DOMAIN][config.entry_id] = {
        COORDINATOR: coordinator,
    }
    async_add_entities([NHLScoresSensor(hass, config)], True)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup the sensor platform."""
    async_add_entities([NHLScoresSensor(hass, entry)], True)


class NHLScoresSensor(CoordinatorEntity):
    """Representation of a Sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(hass.data[DOMAIN][entry.entry_id][COORDINATOR])
        self._config = entry
        self._name = entry.data[CONF_NAME]
        self._icon = DEFAULT_ICON
        self._state = "PRE"
        self._detailed_state = None
        self._game_length = None
        self._date = None
        self._game_end_time = None
        self._attendance = None
        self._event_name = None
        self._event_short_name = None
        self._event_type = None
        self._game_notes = None
        self._series_summary = None
        self._venue_name = None
        self._venue_city = None
        self._venue_state = None
        self._venue_capacity = None
        self._venue_indoor = None
        self._period = None
        self._period_description = None
        self._winning_goalie = None
        self._winning_goalie_saves = None
        self._winning_goalie_save_pct = None
        self._losing_goalie = None
        self._losing_goalie_saves = None
        self._losing_goalie_save_pct = None
        self._first_star = None
        self._second_star = None
        self._third_star = None
        self._game_status = None
        self._home_team_abbr = None
        self._home_team_id = None
        self._home_team_city = None
        self._home_team_name = None
        self._home_team_logo = None
        self._home_team_goals = None
        self._home_team_colors = None
        self._home_team_ls_1 = None
        self._home_team_ls_2 = None
        self._home_team_ls_3 = None
        self._home_team_ls_ot = None
        self._home_team_record = None
        self._away_team_abbr = None
        self._away_team_id = None
        self._away_team_city = None
        self._away_team_name = None
        self._away_team_logo = None
        self._away_team_goals = None
        self._away_team_colors = None
        self._away_team_ls_1 = None
        self._away_team_ls_2 = None
        self._away_team_ls_3 = None
        self._away_team_ls_ot = None
        self._away_team_record = None
        self._puck_drop_in = None
        self._tv_network = None
        self._last_play = None
        self._home_team_starting_goalie = None
        self._away_team_starting_goalie = None
        self._odds = None
        self._overunder = None
        self._home_team_odds_win_pct = None
        self._away_team_odds_win_pct = None
        self._headlines = None
        self._last_update = None
        self._team_id = entry.data[CONF_TEAM_ID]
        self.coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    @property
    def unique_id(self):
        """
        Return a unique, Home Assistant friendly identifier for this entity.
        """
        return f"{slugify(self._name)}_{self._config.entry_id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        elif "state" in self.coordinator.data.keys():
            return self.coordinator.data["state"]
        else:
            return None

    @property
    def extra_state_attributes(self):
        """Return the state message."""
        attrs = {}

        if self.coordinator.data is None:
            return attrs

        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
        attrs["detailed_state"] = self.coordinator.data["detailed_state"]
        attrs["game_length"] = self.coordinator.data["game_length"]
        attrs["date"] = self.coordinator.data["date"]
        attrs["game_end_time"] = self.coordinator.data["game_end_time"]
        attrs["attendance"] = self.coordinator.data["attendance"]
        attrs["event_name"] = self.coordinator.data["event_name"]
        attrs["event_short_name"] = self.coordinator.data["event_short_name"]
        attrs["event_type"] = self.coordinator.data["event_type"]
        attrs["game_notes"] = self.coordinator.data["game_notes"]
        attrs["series_summary"] = self.coordinator.data["series_summary"]
        attrs["venue_name"] = self.coordinator.data["venue_name"]
        attrs["venue_city"] = self.coordinator.data["venue_city"]
        attrs["venue_state"] = self.coordinator.data["venue_state"]
        attrs["venue_capacity"] = self.coordinator.data["venue_capacity"]
        attrs["venue_indoor"] = self.coordinator.data["venue_indoor"]
        attrs["period"] = self.coordinator.data["period"]
        attrs["period_description"] = self.coordinator.data["period_description"]
        attrs["winning_goalie"] = self.coordinator.data["winning_goalie"]
        attrs["winning_goalie_saves"] = self.coordinator.data["winning_goalie_saves"]
        attrs["winning_goalie_save_pct"] = self.coordinator.data["winning_goalie_save_pct"]
        attrs["losing_goalie"] = self.coordinator.data["losing_goalie"]
        attrs["losing_goalie_saves"] = self.coordinator.data["losing_goalie_saves"]
        attrs["losing_goalie_save_pct"] = self.coordinator.data["losing_goalie_save_pct"]
        attrs["first_star"] = self.coordinator.data["first_star"]
        attrs["second_star"] = self.coordinator.data["second_star"]
        attrs["third_star"] = self.coordinator.data["third_star"]
        attrs["game_status"] = self.coordinator.data["game_status"]
        attrs["home_team_abbr"] = self.coordinator.data["home_team_abbr"]
        attrs["home_team_id"] = self.coordinator.data["home_team_id"]
        attrs["home_team_city"] = self.coordinator.data["home_team_city"]
        attrs["home_team_name"] = self.coordinator.data["home_team_name"]
        attrs["home_team_logo"] = self.coordinator.data["home_team_logo"]
        attrs["home_team_goals"] = self.coordinator.data["home_team_goals"]
        attrs["home_team_colors"] = self.coordinator.data["home_team_colors"]
        attrs["home_team_ls_1"] = self.coordinator.data["home_team_ls_1"]
        attrs["home_team_ls_2"] = self.coordinator.data["home_team_ls_2"]
        attrs["home_team_ls_3"] = self.coordinator.data["home_team_ls_3"]
        attrs["home_team_ls_ot"] = self.coordinator.data["home_team_ls_ot"]
        attrs["home_team_record"] = self.coordinator.data["home_team_record"]
        attrs["away_team_abbr"] = self.coordinator.data["away_team_abbr"]
        attrs["away_team_id"] = self.coordinator.data["away_team_id"]
        attrs["away_team_city"] = self.coordinator.data["away_team_city"]
        attrs["away_team_name"] = self.coordinator.data["away_team_name"]
        attrs["away_team_logo"] = self.coordinator.data["away_team_logo"]
        attrs["away_team_goals"] = self.coordinator.data["away_team_goals"]
        attrs["away_team_colors"] = self.coordinator.data["away_team_colors"]
        attrs["away_team_ls_1"] = self.coordinator.data["away_team_ls_1"]
        attrs["away_team_ls_2"] = self.coordinator.data["away_team_ls_2"]
        attrs["away_team_ls_3"] = self.coordinator.data["away_team_ls_3"]
        attrs["away_team_ls_ot"] = self.coordinator.data["away_team_ls_ot"]
        attrs["away_team_record"] = self.coordinator.data["away_team_record"]
        attrs["puck_drop_in"] = self.coordinator.data["puck_drop_in"]
        attrs["tv_network"] = self.coordinator.data["tv_network"]
        attrs["last_play"] = self.coordinator.data["last_play"]
        attrs["home_team_starting_goalie"] = self.coordinator.data["home_team_starting_goalie"]
        attrs["away_team_starting_goalie"] = self.coordinator.data["away_team_starting_goalie"]
        attrs["odds"] = self.coordinator.data["odds"]
        attrs["overunder"] = self.coordinator.data["overunder"]
        attrs["home_team_odds_win_pct"] = self.coordinator.data["home_team_odds_win_pct"]
        attrs["away_team_odds_win_pct"] = self.coordinator.data["away_team_odds_win_pct"]
        attrs["headlines"] = self.coordinator.data["headlines"]
        attrs["last_update"] = self.coordinator.data["last_update"]
      
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
