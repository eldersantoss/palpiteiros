"""Soccer Football Info (SFI) API service.

Provides typed request/response handling for the Soccer Football Info API
hosted on RapidAPI (soccer-football-info.p.rapidapi.com).
"""

import logging
from datetime import date
from typing import Any, Generic, TypedDict, TypeVar

import requests

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SFIPagination(TypedDict):
    """Single pagination object returned by paginated SFI endpoints."""

    page: int
    per_page: int
    items: int


SFIScore = TypedDict(
    "SFIScore",
    {
        "f": int | None,  # final score
        "1h": int | None,  # first-half score
        "2h": int | None,  # second-half score
        "o": int | None,  # overtime
        "p": int | None,  # penalties
    },
)


class SFITeamRef(TypedDict):
    """Lightweight team descriptor embedded inside a match payload."""

    id: str
    name: str
    score: SFIScore


class SFIChampionshipRef(TypedDict):
    """Lightweight championship descriptor embedded inside a match payload."""

    id: str
    name: str
    s_name: str


class SFIMatch(TypedDict):
    """A single match object as returned by the /matches/day/basic/ endpoint."""

    id: str
    date: str  # "YYYY-MM-DD HH:MM:SS"
    status: str  # e.g. "NOT_STARTED", "ENDED"
    championship: SFIChampionshipRef
    teamA: SFITeamRef
    teamB: SFITeamRef


class SFIResponse(TypedDict, Generic[T]):
    """Generic wrapper for all SFI API responses.

    The ``result`` field contains a list of objects whose shape depends on the
    specific endpoint called.  Use the concrete aliases below (e.g.
    ``SFIMatchesResponse``) to preserve typing through the call-sites.
    """

    status: int
    errors: list[Any]
    pagination: list[SFIPagination]
    result: list[T]


SFIMatchesResponse = SFIResponse[SFIMatch]


class SFITeamInTableEntry(TypedDict):
    """Team descriptor inside a table entry."""

    id: str
    name: str


class SFITableEntry(TypedDict):
    """A single team entry in a group's standings table."""

    team: SFITeamInTableEntry
    position: int
    win: int
    draw: int
    loss: int
    points: int
    goals_scored: int
    goals_conceded: int
    note: str | None


class SFIGroup(TypedDict):
    """A group (phase) within a season, containing a standings table."""

    name: str
    table: list[SFITableEntry]


SFISeason = TypedDict(
    "SFISeason",
    {
        "id": str,
        "name": str,
        "from": str,  # "YYYY-MM-DD"
        "to": str,  # "YYYY-MM-DD"
        "groups": list[SFIGroup],
    },
)


class SFIChampionshipView(TypedDict):
    """A championship with all its seasons and standings."""

    id: str
    name: str
    country: str
    has_image: bool
    important: bool
    seasons: list[SFISeason]


SFIChampionshipViewResponse = SFIResponse[SFIChampionshipView]


class SFITeamInfo(TypedDict):
    """Team information in championship teams response."""

    id: str
    name: str


class SFISeasonTeams(TypedDict):
    """Teams data for a specific season."""

    teams: list[SFITeamInfo]


class SFIChampionshipTeamsResponse(TypedDict):
    """Response from get_teams_of_championship method.

    Contains championship metadata and teams grouped by season year.
    """

    id: str
    name: str
    seasons: dict[str, SFISeasonTeams]


class SFIService:
    """Client for the Soccer Football Info (SFI) RapidAPI.

    Credentials are injected via the constructor so that tests can supply
    arbitrary values without touching Django settings or environment variables.

    Typical usage::

        service = SFIService(api_key=settings.SFI_API_KEY, api_host=settings.SFI_API_HOST)
        response = service.get_matches_by_day(date.today(), page=1)
    """

    _BASE_URL = "https://{host}"
    _MATCHES_BY_DAY_PATH = "/matches/day/basic/"
    _CHAMPIONSHIPS_VIEW_PATH = "/championships/view/"

    SFI_NOT_STARTED_STATUS = "NOT_STARTED"
    SFI_ENDED_STATUS = "ENDED"
    SFI_MATCH_STATUSES = [SFI_NOT_STARTED_STATUS, SFI_ENDED_STATUS]

    def __init__(self, api_key: str, api_host: str) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._base_url = self._BASE_URL.format(host=api_host)
        self._headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": api_host,
        }

    def get_matches_by_day(self, target_date: date, page: int = 1) -> SFIMatchesResponse:
        """Fetch matches for a specific calendar day.

        For **past** dates the API returns all matches in a single page
        (``pagination`` is an empty list).  For **present or future** dates the
        response is paginated (25 matches per page); iterate pages until all
        items are consumed.

        Args:
            target_date: The calendar day to fetch matches for.
            page: 1-based page number (only meaningful for present/future dates).

        Returns:
            The raw JSON response parsed into an ``SFIMatchesResponse`` dict.

        Raises:
            requests.HTTPError: If the HTTP response status is 4xx or 5xx.
            requests.RequestException: On network-level errors.
        """
        params = {
            "d": target_date.strftime("%Y%m%d"),
            "p": page,
        }

        logger.debug("SFI request: GET %s%s params=%s", self._base_url, self._MATCHES_BY_DAY_PATH, params)

        response = requests.get(
            self._base_url + self._MATCHES_BY_DAY_PATH,
            headers=self._headers,
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def get_teams_of_championship(self, championship_id: str, year: int) -> SFIChampionshipTeamsResponse:
        """Fetch teams from a specific championship season.

        Retrieves all teams from a championship season that matches the given year
        (extracted from the season's "from" field). Teams are deduplicated across
        all groups within the matched season.

        Args:
            championship_id: The SFI championship ID.
            year: The year to search for (e.g., 2026). Matched against the year
                extracted from each season's "from" field.

        Returns:
            A dict with championship metadata and teams grouped by season year:
            {
                "id": "57449cf280464d5c",
                "name": "Brazil Campeonato Carioca",
                "seasons": {
                    "2026": {
                        "teams": [
                            {"id": "74becc28c493fff8", "name": "Flamengo"},
                            ...
                        ]
                    }
                }
            }
            If no season matches the given year, the "teams" list will be empty.

        Raises:
            requests.HTTPError: If the HTTP response status is 4xx or 5xx.
            requests.RequestException: On network-level errors.
        """
        params = {"i": championship_id}

        logger.debug(
            "SFI request: GET %s%s params=%s",
            self._base_url,
            self._CHAMPIONSHIPS_VIEW_PATH,
            params,
        )

        response = requests.get(
            self._base_url + self._CHAMPIONSHIPS_VIEW_PATH,
            headers=self._headers,
            params=params,
        )
        response.raise_for_status()
        data: SFIChampionshipViewResponse = response.json()

        result = data.get("result", [])
        if not result:
            return {
                "id": championship_id,
                "name": "",
                "seasons": {str(year): {"teams": []}},
            }

        championship = result[0]
        championship_id_api = championship.get("id", "")
        championship_name = championship.get("name", "")
        seasons = championship.get("seasons", [])

        # Find season matching the given year
        target_season = None
        for season in seasons:
            season_from = season.get("from", "")
            if season_from:
                try:
                    season_year = date.fromisoformat(season_from).year
                    if season_year == year:
                        target_season = season
                        break
                except ValueError:
                    logger.warning("Could not parse season date: %s", season_from)

        # Extract teams, deduplicating by team ID
        teams: list[SFITeamInfo] = []
        if target_season:
            seen_ids: set = set()
            for group in target_season.get("groups", []):
                for entry in group.get("table", []):
                    team_data = entry.get("team", {})
                    team_id = team_data.get("id")
                    if team_id and team_id not in seen_ids:
                        seen_ids.add(team_id)
                        teams.append({"id": team_id, "name": team_data.get("name", "")})

        return {
            "id": championship_id_api,
            "name": championship_name,
            "seasons": {str(year): {"teams": teams}},
        }
