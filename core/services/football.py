import logging
from datetime import date

import requests
from django.conf import settings

from .interfaces import IFootballApi

logger = logging.getLogger(__name__)


class FootballApi(IFootballApi):
    _API_URL = f"https://{settings.FOOTBALL_API_HOST}"
    _DEFAULT_HEADERS = {
        "x-rapidapi-key": settings.FOOTBALL_API_KEY,
        "x-rapidapi-host": settings.FOOTBALL_API_HOST,
    }

    @classmethod
    def get_league_by_id(cls, league_id: int) -> dict | None:
        resource = "/leagues"
        params = {
            "id": league_id,
        }
        response = cls._fetch_data(resource, params)

        if response is not None:
            json_data = response.json()
            try:
                return json_data["response"][0]
            except IndexError:
                return None

        return None

    @classmethod
    def get_teams_of_league_by_season(cls, league_id: int, season: int) -> list[dict]:
        resource = "/teams"
        params = {
            "league": league_id,
            "season": season,
        }
        response = cls._fetch_data(resource, params)

        return response.json()["response"] or []

    @classmethod
    def get_matches_of_league_by_season_and_date_period(
        cls,
        league_id: int,
        season: int,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        resource = "/fixtures"
        params = {
            "timezone": settings.TIME_ZONE,
            "league": league_id,
            "season": season,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        }
        response = cls._fetch_data(resource, params)

        return response.json()["response"] or []

    @classmethod
    def _fetch_data(cls, resource: str, params: dict[str, any]) -> requests.Response | None:
        try:
            return requests.get(
                cls._API_URL + resource,
                headers=cls._DEFAULT_HEADERS,
                params=params,
            )

        except Exception:
            logger.exception(f"Error when requesting data from resource {resource} with params {params}.")
            return None
