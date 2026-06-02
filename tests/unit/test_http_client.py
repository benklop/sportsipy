"""Unit tests for HTTP rate limiting and circuit breaker."""

import pytest
from urllib.error import HTTPError

from sportsipy import http_client


@pytest.fixture(autouse=True)
def reset_http_state():
    http_client._request_timestamps.clear()
    http_client._url_exists_cache.clear()
    http_client._domain_failures.clear()
    http_client._domain_circuit_open_until.clear()
    http_client.set_max_requests_per_run(None)
    http_client._run_request_count = 0
    yield


def test_set_max_requests_per_run_raises_budget():
    http_client.set_max_requests_per_run(1)
    http_client._run_request_count = 1
    with pytest.raises(http_client.SportsReferenceBudgetExhausted):
        http_client._check_run_budget()


def test_circuit_opens_after_block(monkeypatch):
    monkeypatch.setattr(http_client, 'DEFAULT_MIN_INTERVAL', 0)

    class FakeResponse:
        status_code = 403
        reason = 'Forbidden'
        headers = {}

        @property
        def text(self):
            return ''

    def fake_request(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(http_client.get_session(), 'request', fake_request)
    url = 'https://www.pro-football-reference.com/years/2024/'

    with pytest.raises(http_client.SportsReferenceBlockedError):
        http_client.fetch(url)

    stats = http_client.get_stats()
    assert stats['circuits']['www.pro-football-reference.com']['open'] is True

    with pytest.raises(http_client.SportsReferenceBlockedError):
        http_client.fetch(url)


def test_url_exists_uses_cache(monkeypatch):
    calls = {'n': 0}

    class FakeResponse:
        status_code = 200
        headers = {}

        def close(self):
            return None

    def fake_get(*args, **kwargs):
        calls['n'] += 1
        return FakeResponse()

    monkeypatch.setattr(http_client.get_session(), 'get', fake_get)
    url = 'https://www.basketball-reference.com/leagues/NBA_2024.html'
    assert http_client.url_exists(url) is True
    assert http_client.url_exists(url) is True
    assert calls['n'] == 1


def test_get_stats_tracks_requests(monkeypatch):
    class FakeResponse:
        status_code = 200
        reason = 'OK'
        headers = {}

        @property
        def text(self):
            return '<html></html>'

    monkeypatch.setattr(http_client.get_session(), 'request', lambda *a, **k: FakeResponse())
    monkeypatch.setattr(http_client, 'DEFAULT_MIN_INTERVAL', 0)

    http_client.fetch('https://example.com/1')
    stats = http_client.get_stats()
    assert stats['requests_this_run'] == 1
    assert stats['requests_last_minute'] == 1
