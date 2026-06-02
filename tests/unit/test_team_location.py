"""Unit tests for team city parsing."""

from sportsipy.team_location import city_for_team_name


def test_city_from_prefix():
    assert city_for_team_name('Denver Nuggets') == 'Denver'
    assert city_for_team_name('Boston Celtics') == 'Boston'


def test_multi_word_city():
    assert city_for_team_name('Los Angeles Lakers') == 'Los Angeles'
    assert city_for_team_name('Oklahoma City Thunder') == 'Oklahoma City'


def test_nickname_override():
    assert city_for_team_name('Utah Jazz') == 'Salt Lake City'
    assert city_for_team_name('Green Bay Packers') == 'Green Bay'
