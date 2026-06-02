from pyquery import PyQuery as pq
from sportsipy import utils
from .constants import (DEFENSIVE_STATS_URL,
                        OFFENSIVE_STATS_URL,
                        PARSING_SCHEME,
                        SEASON_PAGE_URL)


def _add_stats_data(teams_list, team_data_dict):
    """
    Add a team's stats row to a dictionary.

    Pass table contents and a stats dictionary of all teams to accumulate all
    stats for each team in a single variable.

    Parameters
    ----------
    teams_list : generator
        A generator of all row items in a given table.
    team_data_dict : {str: {'data': str}} dictionary
        A dictionary where every key is the team's abbreviation and every value
        is another dictionary with a 'data' key which contains the string
        version of the row data for the matched team.

    Returns
    -------
    dictionary
        An updated version of the team_data_dict with the passed table row
        information included.
    """
    if not teams_list:
        return team_data_dict
    for team_data in teams_list:
        # Skip the sub-header rows
        if 'class="over_header thead"' in str(team_data) or \
           'class="thead"' in str(team_data):
            continue
        abbr = utils._parse_field(PARSING_SCHEME, team_data, 'abbreviation')
        try:
            team_data_dict[abbr]['data'] += team_data
        except KeyError:
            team_data_dict[abbr] = {'data': team_data}
    return team_data_dict


def _retrieve_all_teams(year, season_page, offensive_stats, defensive_stats):
    """
    Find and create Team instances for all teams in the given season.

    For a given season, parses the specified NCAAF stats table and finds
    all requested stats. Each team then has a Team instance created which
    includes all requested stats and a few identifiers, such as the team's
    name and abbreviation. All of the individual Team instances are added
    to a list.

    Note that this method is called directly once Teams is invoked and does
    not need to be called manually.

    Parameters
    ----------
    year : string
        The requested year to pull stats from.
    season_page : string (optional)
        Link with filename to the local season stats page.
    offensive_stats : string (optional)
        Link with filename to the local offensive stats page.
    defensive_stats : string (optional)
        Link with filename to the local defensive stats page.

    Returns
    -------
    tuple
        Returns a ``tuple`` of the team_data_dict and year which represent all
        stats for all teams, and the given year that should be used to pull
        stats from, respectively.
    """
    team_data_dict = {}

    if not year:
        year = utils._resolve_season_year('ncaaf', SEASON_PAGE_URL, year)
    doc = utils._pull_page(SEASON_PAGE_URL % year, season_page)
    teams_list = utils._get_stats_table(doc, 'div#div_standings')
    offense_doc = utils._pull_page(OFFENSIVE_STATS_URL % year, offensive_stats)
    offense_list = utils._get_stats_table(offense_doc, 'table#offense')
    defense_doc = utils._pull_page(DEFENSIVE_STATS_URL % year, defensive_stats)
    defense_list = utils._get_stats_table(defense_doc, 'table#defense')
    if not teams_list and not offense_list and not defense_list:
        utils._no_data_found()
    for stats_list in [teams_list, offense_list, defense_list]:
        team_data_dict = _add_stats_data(stats_list, team_data_dict)
    return team_data_dict, year


def _retrieve_lightweight_teams(year, season_page=None):
    """Load team identifiers from the season standings page only."""
    team_data_dict = {}
    year = utils._resolve_season_year('ncaaf', SEASON_PAGE_URL, year)
    doc = utils._pull_page(SEASON_PAGE_URL % year, season_page)
    teams_list = utils._get_stats_table(doc, 'div#div_standings')
    if not teams_list:
        utils._no_data_found()
        return None, None
    team_data_dict = _add_stats_data(teams_list, team_data_dict)
    return team_data_dict, year
