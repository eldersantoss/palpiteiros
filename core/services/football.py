import abc
import logging
from datetime import date

import requests
from django.conf import settings
from django.utils import timezone

from core.models import Competition, Match, Team

logger = logging.getLogger(__name__)


class FootballApiInterface(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_league_by_id(self, league_id: int) -> dict | None:
        pass

    @classmethod
    @abc.abstractmethod
    def get_teams_of_league_by_season(self, league_id: int, season: int) -> dict | None:
        pass

    @classmethod
    @abc.abstractmethod
    def get_matches_of_league_by_season_and_date_period(
        cls, league_id: int, season: int, days_from: int, days_ahead: int
    ):
        pass

    @classmethod
    @abc.abstractmethod
    def create_and_update_matches(cls, competition: Competition, season: int, start_date: date, end_date: date):
        pass


class FootballApiService(FootballApiInterface):
    _API_URL = f"https://{settings.FOOTBALL_API_HOST}"
    _DEFAULT_HEADERS = {
        "x-rapidapi-key": settings.FOOTBALL_API_KEY,
        "x-rapidapi-host": settings.FOOTBALL_API_HOST,
    }

    @classmethod
    def get_league_by_id(cls, league_id: int) -> dict | None:
        resource = "/leagues"
        params = {"id": league_id}
        response = cls._send_request(resource, params)
        if response is not None:
            json_data = response.json()
            try:
                return json_data["response"][0]

            except IndexError:
                return None

    @classmethod
    def get_teams_of_league_by_season(cls, league_id: int, season: int) -> list[dict]:
        resource = "/teams"
        params = {"league": league_id, "season": season}
        response = cls._send_request(resource, params)

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

        response = cls._send_request(resource, params)

        return response.json()["response"] or []

    @classmethod
    def create_and_update_matches(cls, competition: Competition, season: int, start_date: date, end_date: date):
        matches = cls.get_matches_of_league_by_season_and_date_period(
            competition.data_source_id, season, start_date, end_date
        )

        created = []
        updated = []

        for match in matches:
            match_data = cls._parse_match_data(match)

            if match_data["home_team"] is None or match_data["away_team"] is None:
                logger.warning(f"Match {match_data['data_source_id']} skipped because teams are not registered.")
                continue

            match_instance, created_instance = Match.objects.update_or_create(
                data_source_id=match_data["data_source_id"],
                defaults=match_data,
            )

            if created_instance:
                created.append(match_instance)

            else:
                updated.append(match_instance)

        return created, updated

    @classmethod
    def _parse_match_data(cls, match_raw_data: dict) -> dict:
        return {
            "data_source_id": match_raw_data["fixture"]["id"],
            "competition": Competition.objects.filter(data_source_id=match_raw_data["league"]["id"]).first(),
            "date_time": timezone.datetime.fromisoformat(match_raw_data["fixture"]["date"]),
            "status": match_raw_data["fixture"]["status"]["short"],
            "home_team": Team.objects.filter(data_source_id=match_raw_data["teams"]["home"]["id"]).first(),
            "away_team": Team.objects.filter(data_source_id=match_raw_data["teams"]["away"]["id"]).first(),
            "home_goals": match_raw_data["goals"]["home"],
            "away_goals": match_raw_data["goals"]["away"],
        }

    @classmethod
    def _send_request(cls, resource: str, params: dict[str, any]) -> requests.Response | None:
        try:
            return requests.get(
                cls._API_URL + resource,
                headers=cls._DEFAULT_HEADERS,
                params=params,
            )

        except Exception:
            logger.exception(f"Error when requesting data from resource {resource} with params {params}.")
            return None
