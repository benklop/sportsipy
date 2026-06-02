"""Public HTTP entry point for Sports Reference page loads."""

from sportsipy.http_client import fetch, get_stats, set_max_requests_per_run, url_exists


def get_html(url, method='get', timeout=60, **kwargs):
    """Fetch page HTML through the shared rate limiter and circuit breaker."""
    return fetch(url, method=method, timeout=timeout, **kwargs)
