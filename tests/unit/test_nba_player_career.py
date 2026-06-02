"""NBA Player career stats with modern basketball-reference table ids."""

from sportsipy.nba.roster import Player


def test_player_career_advanced_stats_from_fixture_html(monkeypatch):
    """Career row uses table footers; _season must not be overwritten by parsing."""
    html = """
    <h1>Test Player</h1>
    <table id="advanced">
      <tbody>
        <tr><th data-stat="year_id">2023-24</th>
            <td data-stat="per">20.0</td>
            <td data-stat="ws">5.0</td>
            <td data-stat="bpm">4.0</td>
            <td data-stat="vorp">2.0</td>
            <td data-stat="ts_pct">.550</td></tr>
      </tbody>
      <tfoot>
        <tr><th data-stat="year_id">Career</th>
            <td data-stat="per">22.5</td>
            <td data-stat="ws">12.0</td>
            <td data-stat="bpm">5.5</td>
            <td data-stat="vorp">6.0</td>
            <td data-stat="ts_pct">.575</td></tr>
      </tfoot>
    </table>
    <table id="totals_stats">
      <tbody>
        <tr><th data-stat="year_id">2023-24</th>
            <td data-stat="games">82</td>
            <td data-stat="pts">2000</td></tr>
      </tbody>
      <tfoot>
        <tr><th data-stat="year_id">3 Yrs</th>
            <td data-stat="games">246</td>
            <td data-stat="pts">6000</td></tr>
      </tfoot>
    </table>
  """

    def fake_retrieve(_self):
        from pyquery import PyQuery as pq
        from sportsipy import utils
        return pq(utils._remove_html_comment_tags(html))

    monkeypatch.setattr(Player, '_retrieve_html_page', fake_retrieve)
    player = Player('testpl01')
    assert player.name == 'Test Player'
    assert 'Career' in player._season
    assert player.player_efficiency_rating == 22.5
    assert player.win_shares == 12
    assert player.box_plus_minus == 5.5
    assert player.value_over_replacement_player == 6.0
