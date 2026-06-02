"""
HTTP fetching for Sports Reference sites with rate limiting and retries.

Sports Reference blocks aggressive scrapers (403/429). This module centralizes
requests so all pyquery page loads share one session, a browser-like User-Agent,
spacing between requests, and limited retries on transient blocks.
"""

import logging
import os
import time
from urllib.error import HTTPError

import requests

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
DEFAULT_MIN_INTERVAL = float(os.environ.get('SPORTSIPY_REQUEST_INTERVAL', '3.0'))
DEFAULT_MAX_RETRIES = int(os.environ.get('SPORTSIPY_MAX_RETRIES', '3'))
RETRY_STATUS_CODES = {403, 429, 500, 502, 503, 504}

_session = None
_last_request_at = 0.0


def get_session():
    """Return a shared requests session with default browser headers."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            'User-Agent': os.environ.get('SPORTSIPY_USER_AGENT', DEFAULT_USER_AGENT),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        })
    return _session


def _throttle():
    """Enforce minimum delay between HTTP requests."""
    global _last_request_at
    interval = DEFAULT_MIN_INTERVAL
    if interval <= 0:
        return
    elapsed = time.monotonic() - _last_request_at
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_request_at = time.monotonic()


def fetch(url, method='get', timeout=60, **kwargs):
    """
    Fetch a URL with rate limiting and retries on 403/429.

    Returns
    -------
    str
        Response body text.

    Raises
    ------
    HTTPError
        When the server returns a non-retryable error status.
    requests.RequestException
        On network failures after retries are exhausted.
    """
    session = get_session()
    headers = dict(session.headers)
    headers.update(kwargs.pop('headers', {}))
    method = method.lower()
    last_error = None

    for attempt in range(DEFAULT_MAX_RETRIES):
        _throttle()
        try:
            response = session.request(
                method,
                url,
                timeout=timeout,
                headers=headers,
                **kwargs,
            )
            if (
                response.status_code in RETRY_STATUS_CODES
                and attempt < DEFAULT_MAX_RETRIES - 1
            ):
                backoff = min(60, (2 ** attempt) * 5)
                logger.warning(
                    'HTTP %s for %s; retrying in %ss (%s/%s)',
                    response.status_code,
                    url,
                    backoff,
                    attempt + 1,
                    DEFAULT_MAX_RETRIES,
                )
                time.sleep(backoff)
                continue
            if not (200 <= response.status_code < 300):
                raise HTTPError(
                    url,
                    response.status_code,
                    response.reason,
                    response.headers,
                    None,
                )
            return response.text
        except HTTPError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1:
                backoff = min(60, (2 ** attempt) * 5)
                logger.warning(
                    'Request failed for %s: %s; retrying in %ss',
                    url,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
                continue
            raise

    if last_error:
        raise last_error
    raise HTTPError(url, 0, 'unknown', {}, None)


def url_exists(url, timeout=30):
    """Return True if the URL responds with a success status code."""
    session = get_session()
    try:
        _throttle()
        response = session.head(url, allow_redirects=True, timeout=timeout)
        if response.status_code in (405, 403) or response.status_code >= 400:
            _throttle()
            response = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
            response.close()
        return response.status_code < 400
    except requests.RequestException:
        return False


def install_pyquery_opener():
    """Route pyquery URL loads through :func:`fetch`."""
    import pyquery.openers as openers

    if getattr(openers, '_sportsipy_patched', False):
        return

    def _sportsipy_requests(url, kwargs):
        method = kwargs.get('method', 'get')
        encoding = kwargs.get('encoding')
        html = fetch(url, method=method, timeout=kwargs.get('timeout', openers.DEFAULT_TIMEOUT))
        if encoding:
            return html.encode(encoding).decode(encoding)
        return html

    openers._requests = _sportsipy_requests
    openers._sportsipy_patched = True


install_pyquery_opener()
