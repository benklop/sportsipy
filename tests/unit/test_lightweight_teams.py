"""Offline tests for lightweight Teams mode using saved HTML fixtures."""

from sportsipy.mlb.teams import Teams as MLBTeams
from sportsipy.nba.teams import Teams as NBATeams
from sportsipy.nfl.teams import Teams as NFLTeams


def test_nba_lightweight_local_fixture():
    teams = NBATeams(
        season_file='tests/integration/teams/nba_stats/NBA_2021.html',
        lightweight=True,
        year='2021',
    )
    assert len(teams) == 30
    lal = teams['LAL']
    assert lal.name
    assert lal.city == 'Los Angeles'


def test_mlb_lightweight_local_fixture():
    teams = MLBTeams(
        standings_file='tests/integration/teams/mlb_stats/2017_overall.html',
        lightweight=True,
    )
    assert len(teams) >= 28


def test_nfl_lightweight_local_fixture():
    teams = NFLTeams(
        season_page='tests/integration/teams/nfl_stats/2017.html',
        lightweight=True,
    )
    assert len(teams) >= 28
