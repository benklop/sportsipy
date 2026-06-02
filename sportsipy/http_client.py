"""
HTTP fetching for Sports Reference sites with rate limiting and retries.

Sports Reference blocks aggressive scrapers (403/429). All outbound requests
share one session, sliding-window rate limits, and per-domain circuit breakers.
"""

import logging
import os
import time
from collections import deque
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
DEFAULT_MIN_INTERVAL = float(os.environ.get('SPORTSIPY_REQUEST_INTERVAL', '3.0'))
DEFAULT_MAX_REQUESTS_PER_MINUTE = int(
    os.environ.get('SPORTSIPY_MAX_REQUESTS_PER_MINUTE', '20')
)
DEFAULT_CIRCUIT_COOLDOWN_SECONDS = int(
    os.environ.get('SPORTSIPY_CIRCUIT_COOLDOWN_SECONDS', '900')
)
DEFAULT_MAX_RETRIES = int(os.environ.get('SPORTSIPY_MAX_RETRIES', '2'))
RETRYABLE_SERVER_ERRORS = {500, 502, 503, 504}

DOMAIN_INTERVAL_OVERRIDES = {
    'pro-football-reference.com': 4.0,
    'www.pro-football-reference.com': 4.0,
    'sports-reference.com': 4.0,
    'www.sports-reference.com': 4.0,
    'fbref.com': 4.0,
    'www.fbref.com': 4.0,
}

_session = None
_last_request_at = 0.0
_request_timestamps: deque = deque()
_url_exists_cache: dict = {}

_domain_failures: dict = {}
_domain_circuit_open_until: dict = {}


class SportsReferenceBlockedError(HTTPError):
    """Raised when a domain circuit breaker is open or a block is not retried."""

    def __init__(self, url, code, msg, hdrs, fp, domain=None, retry_at=None):
        super().__init__(url, code, msg, hdrs, fp)
        self.domain = domain
        self.retry_at = retry_at


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


def _domain_for_url(url):
    return urlparse(url).netloc.lower()


def _domain_interval(domain):
    return max(
        DEFAULT_MIN_INTERVAL,
        DOMAIN_INTERVAL_OVERRIDES.get(domain, DEFAULT_MIN_INTERVAL),
    )


def _parse_retry_after(headers, default_seconds):
    retry_after = headers.get('Retry-After') if headers else None
    if not retry_after:
        return default_seconds
    try:
        return min(3600, max(1, int(retry_after)))
    except (TypeError, ValueError):
        try:
            retry_dt = parsedate_to_datetime(retry_after)
            return min(3600, max(1, int(retry_dt.timestamp() - time.time())))
        except (TypeError, ValueError, OverflowError):
            return default_seconds


def _open_circuit(domain, cooldown_seconds):
    until = time.monotonic() + cooldown_seconds
    _domain_circuit_open_until[domain] = until
    logger.warning(
        'Sports Reference circuit open for %s until cooldown (%ss)',
        domain,
        cooldown_seconds,
    )


def _check_circuit(domain):
    until = _domain_circuit_open_until.get(domain)
    if until is None:
        return
    now = time.monotonic()
    if now >= until:
        _domain_circuit_open_until.pop(domain, None)
        _domain_failures[domain] = 0
        return
    retry_at = time.time() + (until - now)
    raise SportsReferenceBlockedError(
        domain,
        403,
        f'circuit open for {domain}',
        {},
        None,
        domain=domain,
        retry_at=retry_at,
    )


def _record_success(domain):
    _domain_failures[domain] = 0
    _domain_circuit_open_until.pop(domain, None)


def _record_block(domain, status_code, headers):
    failures = _domain_failures.get(domain, 0) + 1
    _domain_failures[domain] = failures
    cooldown = _parse_retry_after(headers, DEFAULT_CIRCUIT_COOLDOWN_SECONDS)
    if status_code == 429:
        cooldown = max(cooldown, DEFAULT_CIRCUIT_COOLDOWN_SECONDS // 2)
    _open_circuit(domain, cooldown)


def _record_request():
    now = time.monotonic()
    _request_timestamps.append(now)
    cutoff = now - 60.0
    while _request_timestamps and _request_timestamps[0] < cutoff:
        _request_timestamps.popleft()


def _throttle(domain):
    """Enforce minimum spacing and sliding-window request cap."""
    global _last_request_at
    interval = _domain_interval(domain)
    if interval > 0:
        elapsed = time.monotonic() - _last_request_at
        if elapsed < interval:
            time.sleep(interval - elapsed)

    if DEFAULT_MAX_REQUESTS_PER_MINUTE > 0:
        while len(_request_timestamps) >= DEFAULT_MAX_REQUESTS_PER_MINUTE:
            oldest = _request_timestamps[0]
            wait = 60.0 - (time.monotonic() - oldest) + 0.01
            if wait > 0.01:
                logger.debug('Rate window full; sleeping %.1fs', wait)
                time.sleep(wait)
            cutoff = time.monotonic() - 60.0
            while _request_timestamps and _request_timestamps[0] <= cutoff:
                _request_timestamps.popleft()
            if len(_request_timestamps) >= DEFAULT_MAX_REQUESTS_PER_MINUTE:
                _request_timestamps.popleft()

    _last_request_at = time.monotonic()


def get_stats():
    """Return limiter and circuit breaker state for monitoring."""
    now = time.monotonic()
    circuits = {}
    for domain, until in _domain_circuit_open_until.items():
        circuits[domain] = {
            'open': until > now,
            'cooldown_remaining_seconds': max(0, round(until - now, 1)),
            'failures': _domain_failures.get(domain, 0),
        }
    cutoff = now - 60.0
    requests_last_minute = sum(1 for ts in _request_timestamps if ts >= cutoff)
    return {
        'requests_last_minute': requests_last_minute,
        'max_requests_per_minute': DEFAULT_MAX_REQUESTS_PER_MINUTE,
        'min_interval_seconds': DEFAULT_MIN_INTERVAL,
        'circuits': circuits,
    }


def fetch(url, method='get', timeout=60, **kwargs):
    """
    Fetch a URL with rate limiting, circuit breaker, and limited retries.

    Returns response body text. 403 opens the domain circuit immediately.
    429 may retry once after Retry-After.
    """
    domain = _domain_for_url(url)
    _check_circuit(domain)

    session = get_session()
    headers = dict(session.headers)
    headers.update(kwargs.pop('headers', {}))
    method = method.lower()
    last_error = None
    max_attempts = max(1, DEFAULT_MAX_RETRIES)

    for attempt in range(max_attempts):
        _throttle(domain)
        try:
            response = session.request(
                method,
                url,
                timeout=timeout,
                headers=headers,
                **kwargs,
            )
            _record_request()

            if response.status_code == 403:
                _record_block(domain, 403, response.headers)
                raise SportsReferenceBlockedError(
                    url,
                    403,
                    response.reason,
                    response.headers,
                    None,
                    domain=domain,
                    retry_at=time.time() + DEFAULT_CIRCUIT_COOLDOWN_SECONDS,
                )

            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers, 60)
                if attempt < max_attempts - 1:
                    logger.warning(
                        'HTTP 429 for %s; sleeping %ss (%s/%s)',
                        url,
                        retry_after,
                        attempt + 1,
                        max_attempts,
                    )
                    time.sleep(retry_after)
                    continue
                _record_block(domain, 429, response.headers)
                raise SportsReferenceBlockedError(
                    url,
                    429,
                    response.reason,
                    response.headers,
                    None,
                    domain=domain,
                    retry_at=time.time() + retry_after,
                )

            if (
                response.status_code in RETRYABLE_SERVER_ERRORS
                and attempt < max_attempts - 1
            ):
                backoff = min(60, (2 ** attempt) * 5)
                logger.warning(
                    'HTTP %s for %s; retrying in %ss (%s/%s)',
                    response.status_code,
                    url,
                    backoff,
                    attempt + 1,
                    max_attempts,
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

            _record_success(domain)
            return response.text

        except SportsReferenceBlockedError:
            raise
        except HTTPError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_attempts - 1:
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


def url_exists(url, timeout=30, cache_ttl=3600):
    """Return True if the URL responds with success. Uses one GET via fetch."""
    now = time.monotonic()
    cached = _url_exists_cache.get(url)
    if cached is not None:
        value, expires = cached
        if now < expires:
            return value

    try:
        session = get_session()
        domain = _domain_for_url(url)
        _check_circuit(domain)
        _throttle(domain)
        response = session.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            stream=True,
            headers=session.headers,
        )
        _record_request()
        ok = response.status_code < 400
        response.close()
        if ok:
            _record_success(domain)
        elif response.status_code in (403, 429):
            _record_block(domain, response.status_code, response.headers)
    except (requests.RequestException, SportsReferenceBlockedError):
        ok = False

    _url_exists_cache[url] = (ok, now + cache_ttl)
    return ok


def install_pyquery_opener():
    """Route pyquery URL loads through :func:`fetch`."""
    import pyquery.openers as openers

    if getattr(openers, '_sportsipy_patched', False):
        return

    def _sportsipy_requests(url, kwargs):
        method = kwargs.get('method', 'get')
        encoding = kwargs.get('encoding')
        html = fetch(
            url,
            method=method,
            timeout=kwargs.get('timeout', openers.DEFAULT_TIMEOUT),
        )
        if encoding:
            return html.encode(encoding).decode(encoding)
        return html

    openers._requests = _sportsipy_requests
    openers._sportsipy_patched = True


install_pyquery_opener()
