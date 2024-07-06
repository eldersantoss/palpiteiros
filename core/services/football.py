import abc
import logging
from time import sleep

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class FootballApiInterface(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_league_by_id(self, league_id: int) -> dict | None:
        pass


class FootballApiService(FootballApiInterface):
    _API_URL = f"https://{settings.FOOTBALL_API_HOST}"
    _DEFAULT_HEADERS = {
        "x-rapidapi-key": settings.FOOTBALL_API_KEY,
        "x-rapidapi-host": settings.FOOTBALL_API_HOST,
    }

    @classmethod
    def get_league_by_id(self, league_id: int) -> dict | None:
        resource_url = self._API_URL + "/leagues"
        params = {"id": league_id}

        try:
            response = requests.get(resource_url, headers=self._DEFAULT_HEADERS, params=params)
        except Exception:
            logger.exception(f"Error when requesting data for League with id {league_id}.")

        sleep(settings.FOOTBALL_API_RATE_LIMIT_TIME)

        json_data = response.json()

        try:
            return json_data["response"][0]

        except IndexError:
            logger.warning(f"League with id {league_id} not found.")
            return None
