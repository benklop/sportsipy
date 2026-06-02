"""Derive team home city from display names."""

from __future__ import annotations

import re
from typing import Optional

# Nickname-only teams where the city is not a name prefix
_NICKNAME_CITY_OVERRIDES = {
    'utah jazz': 'Salt Lake City',
    'golden state warriors': 'San Francisco',
    'los angeles clippers': 'Los Angeles',
    'los angeles lakers': 'Los Angeles',
    'los angeles angels': 'Los Angeles',
    'los angeles dodgers': 'Los Angeles',
    'los angeles chargers': 'Los Angeles',
    'los angeles rams': 'Los Angeles',
    'new york knicks': 'New York',
    'new york nets': 'New York',
    'new york giants': 'New York',
    'new york jets': 'New York',
    'new york yankees': 'New York',
    'new york mets': 'New York',
    'new york rangers': 'New York',
    'new york islanders': 'New York',
    'brooklyn nets': 'Brooklyn',
    'tampa bay rays': 'Tampa',
    'tampa bay buccaneers': 'Tampa',
    'tampa bay lightning': 'Tampa',
    'green bay packers': 'Green Bay',
    'arizona cardinals': 'Phoenix',
    'arizona coyotes': 'Phoenix',
    'arizona diamondbacks': 'Phoenix',
    'dallas cowboys': 'Dallas',
    'dallas mavericks': 'Dallas',
    'dallas stars': 'Dallas',
    'minnesota timberwolves': 'Minneapolis',
    'minnesota vikings': 'Minneapolis',
    'minnesota twins': 'Minneapolis',
    'minnesota wild': 'Minneapolis',
    'new england patriots': 'Boston',
    'san antonio spurs': 'San Antonio',
    'oklahoma city thunder': 'Oklahoma City',
    'kansas city chiefs': 'Kansas City',
    'kansas city royals': 'Kansas City',
    'las vegas raiders': 'Las Vegas',
    'vegas golden knights': 'Las Vegas',
    'carolina panthers': 'Charlotte',
    'carolina hurricanes': 'Raleigh',
    'washington commanders': 'Washington',
    'washington wizards': 'Washington',
    'washington capitals': 'Washington',
    'washington nationals': 'Washington',
}

_MULTI_WORD_CITIES = (
    'Salt Lake City',
    'Oklahoma City',
    'Kansas City',
    'Las Vegas',
    'San Antonio',
    'San Diego',
    'San Francisco',
    'San Jose',
    'St. Louis',
    'St Louis',
    'New York',
    'New Orleans',
    'Los Angeles',
    'Fort Worth',
)


def city_for_team_name(name: Optional[str]) -> Optional[str]:
    """Best-effort city from a team display name such as 'Denver Nuggets'."""
    if not name or not str(name).strip():
        return None

    key = str(name).strip().lower()
    if key in _NICKNAME_CITY_OVERRIDES:
        return _NICKNAME_CITY_OVERRIDES[key]

    for city in _MULTI_WORD_CITIES:
        if key.startswith(city.lower() + ' '):
            return city.replace('St Louis', 'St. Louis')

    parts = str(name).strip().split()
    if len(parts) >= 2:
        return parts[0]
    return None


def city_property():
    """Descriptor-style helper for Team.city on classes with a name property."""

    class _CityProperty:
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            name = getattr(obj, 'name', None)
            return city_for_team_name(name)

    return _CityProperty()
