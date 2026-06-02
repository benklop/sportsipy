from .constants import PARSING_SCHEME, SEASON_PAGE_URL
from pyquery import PyQuery as pq
from sportsipy import utils
from urllib.error import HTTPError


def _add_stats_data(teams_list, team_data_dict):
    """
    Add a team's stats row to a dictionary.

    Pass table contents and a stats dictionary of all teams to accumulate all
    stats for each team in a single variable.

    Parameters
    ----------
    teams_list : generator
        A generator of all row items in a given table.
    team_data_dict : {str: {'data': str, 'rank': int}} dictionary
        A dictionary where every key is the team's abbreviation and every value
        is another dictionary with a 'data' key which contains the string
        version of the row data for the matched team, and a 'rank' key which is
        the rank of the team.

    Returns
    -------
    dictionary
        An updated version of the team_data_dict with the passed table row
        information included.
    """
    # Teams are listed in terms of rank with the first team being #1
    rank = 1
    for team_data in teams_list:
        # Only try to pull data from the row if there's a team link, otherwise it
        # might be an embedded header row, like in the division standings
        if team_data('a').attr('href') is not None:
            abbr = utils._parse_field(PARSING_SCHEME, team_data, 'abbreviation')
            try:
                team_data_dict[abbr]['data'] += team_data
            except KeyError:
                team_data_dict[abbr] = {'data': team_data, 'rank': rank}
            rank += 1
    return team_data_dict


def _retrieve_all_teams(year, season_file=None):
    """
    Find and create Team instances for all teams in the given season.

    For a given season, parses the specified NBA stats table and finds all
    requested stats. Each team then has a Team instance created which includes
    all requested stats and a few identifiers, such as the team's name and
    abbreviation. All of the individual Team instances are added to a list.

    Parameters
    ----------
    year : string
        The requested year to pull stats from.
    season_file : string (optional)
        Link with filename to the local season page.

    Returns
    -------
    tuple
        Returns a ``tuple`` of the team_data_dict and year which represent all
        stats for all teams, and the given year that should be used to pull
        stats from, respectively.
    """
    team_data_dict = {}

    if not year:
        year = utils._find_year_for_season('nba')
        if year == 2021 and not utils._url_exists(SEASON_PAGE_URL % year):
            year = str(int(year) - 1)
        year = utils._resolve_season_year('nba', SEASON_PAGE_URL, year)
    doc = utils._pull_page(SEASON_PAGE_URL % year, season_file)
    teams_list = utils._get_stats_table(doc, 'div#div_totals-team')
    opp_teams_list = utils._get_stats_table(doc, 'div#div_totals-opponent')
    # Team wins, losses, and win % are in separate tables, and older years
    # do not have a conference standings table
    standings_list_E = utils._get_stats_table(doc, 'div#div_divs_standings_E')
    standings_list_W = utils._get_stats_table(doc, 'div#div_divs_standings_W')

    if not teams_list and not opp_teams_list and not standings_list_E and not standings_list_W:
        utils._no_data_found()
        return None, None
    for stats_list in [teams_list, opp_teams_list, standings_list_E, standings_list_W]:
        team_data_dict = _add_stats_data(stats_list, team_data_dict)
    return team_data_dict, year


def _retrieve_lightweight_teams(year, season_file=None):
    """Load team identifiers from a single season summary page."""
    team_data_dict = {}

    year = utils._resolve_season_year('nba', SEASON_PAGE_URL, year)
    doc = utils._pull_page(SEASON_PAGE_URL % year, season_file)
    teams_list = utils._get_stats_table(doc, 'div#div_totals-team')
    if not teams_list:
        utils._no_data_found()
        return None, None
    team_data_dict = _add_stats_data(teams_list, team_data_dict)
    return team_data_dict, year
