# benklop/sportsipy fork

Maintained fork of [davidjkrause/sportsipy](https://github.com/davidjkrause/sportsipy) (itself a fork of the unmaintained roclark/sportsipy).

## Changes on top of davidjkrause/master

- **NHL schedules** (#14): hockey-reference renamed the gamelog table (`table#team_games`) and updated `data-stat` column names; schedule parsing works again.
- **NCAAB boxscores** (PR #18 from seang1121): updated CSS selectors for sports-reference HTML changes.
- **NFL boxscores** (#16): swapped home/away score indices in `BOXSCORE_ELEMENT_INDEX`.
- **NFL player stats** (PR #15): updated `PLAYER_SCHEME` `data-stat` attributes.

## Not merged (intentionally)

- PR #13 (type hints only): large diff, no functional benefit for consumers.
- PR #8 (NCAAF Coaches Poll): feature addition, not required for schedule/team scraping.
- PR #19 (big update): closed; massive unrelated refactor.

## Install

```bash
pip install git+https://github.com/benklop/sportsipy@master
```
