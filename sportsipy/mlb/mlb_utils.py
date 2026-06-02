from .constants import PARSING_SCHEME, STANDINGS_URL, TEAM_STATS_URL
from pyquery import PyQuery as pq
from sportsipy import utils


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
        # Skip the league average row
        if 'class="league_average_table"' in str(team_data):
            continue
        abbr = utils._parse_field(PARSING_SCHEME, team_data, 'abbreviation')
        try:
            team_data_dict[abbr]['data'] += team_data
        except KeyError:
            team_data_dict[abbr] = {'data': team_data, 'rank': rank}
        rank += 1
    return team_data_dict


def _retrieve_all_teams(year, standings_file=None, teams_file=None):
    """
    Find and create Team instances for all teams in the given season.

    For a given season, parses the specified MLB stats table and finds all
    requested stats. Each team then has a Team instance created which includes
    all requested stats and a few identifiers, such as the team's name and
    abbreviation. All of the individual Team instances are added to a list.

    Parameters
    ----------
    year : string
        The requested year to pull stats from.
    standings_file : string (optional)
        Link with filename to the local standings page.
    teams_file : string (optional)
        Link with filename to the local teams page.

    Returns
    -------
    tuple
        Returns a ``tuple`` of the team_data_dict and year which represent all
        stats for all teams, and the given year that should be used to pull
        stats from, respectively.
    """
    team_data_dict = {}

    if not year:
        year = utils._resolve_season_year('mlb', STANDINGS_URL, year)
    doc = utils._pull_page(STANDINGS_URL % year, standings_file)
    div_prefix = 'div#all_expanded_standings_overall'
    standings = utils._get_stats_table(doc, div_prefix)
    doc = utils._pull_page(TEAM_STATS_URL % year, teams_file)
    div_prefix = 'div#all_teams_standard_%s'
    batting_stats = utils._get_stats_table(doc, div_prefix % 'batting')
    pitching_stats = utils._get_stats_table(doc, div_prefix % 'pitching')
    if not standings and not batting_stats and not pitching_stats:
        utils._no_data_found()
        return None, None
    for stats_list in [standings, batting_stats, pitching_stats]:
        team_data_dict = _add_stats_data(stats_list, team_data_dict)
    return team_data_dict, year
