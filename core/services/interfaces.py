import abc
from datetime import date


class IFootballApi(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_league_by_id(self, league_id: int) -> dict | None: ...

    @classmethod
    @abc.abstractmethod
    def get_teams_of_league_by_season(self, league_id: int, season: int) -> dict | None: ...

    @classmethod
    @abc.abstractmethod
    def get_matches_of_league_by_season_and_date_period(
        cls,
        league_id: int,
        season: int,
        start_date: date,
        end_date: date,
    ) -> list[dict]: ...
