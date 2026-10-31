"""Shared HTTP helpers for the northbound travel project."""

import time
from typing import Any

import requests

TIMEOUT_SECONDS = 30
RETRY_DELAYS = (2, 4, 6)


def get_json(url: str, params: dict | None = None, timeout: int = TIMEOUT_SECONDS) -> Any | None:
    """GET JSON data; retry request/HTTP/JSON failures, then return None.

    There are three attempts, waiting 2 seconds and 4 seconds between them.
    The final 6-second delay follows the course specification and is retained
    before returning None, making the complete retry schedule 2/4/6 seconds.
    """
    """the enumerate function is used to iterate over the RETRY_DELAYS tuple,
       providing both the attempt number and the corresponding delay time for each retry.
       The start=1 argument ensures that the attempt count starts from 1 instead of the default 0.
    """
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            # Raise an exception for HTTP errors (4xx or 5xx)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"JSON request failed (attempt {attempt}/3): {error}")
            time.sleep(delay)
    return None


def get_text(url: str, params: dict | None = None, timeout: int = TIMEOUT_SECONDS) -> str | None:
    """GET text data; retry request failures, then return None."""
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as error:
            print(f"Text request failed (attempt {attempt}/3): {error}")
            time.sleep(delay)
    return None


# Layer 1: test the request functions with small, hand-written fake responses.
class _FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _check_fetch_functions():
    """Exercise success, retry, and final-failure paths without network waits."""
    original_get = requests.get
    original_sleep = time.sleep
    sleep_calls = []

    def no_wait(seconds):
        sleep_calls.append(seconds)

    try:
        # JSON: first HTTP 503, then a successful response. This must call the
        # real get_json function twice and wait 2 seconds between attempts.
        json_responses = [
            _FakeResponse(503),
            _FakeResponse(200, {"date": "2026-10-29", "rates": {"CNY": 0.92}}),
        ]
        json_calls = []

        def fake_json_get(url, params=None, timeout=None):
            json_calls.append((url, params, timeout))
            return json_responses.pop(0)

        requests.get = fake_json_get
        time.sleep = no_wait
        result = get_json("https://example.test/rates", {"base": "HKD"})
        assert result == {"date": "2026-10-29", "rates": {"CNY": 0.92}}
        assert len(json_calls) == 2
        assert json_calls[0] == ("https://example.test/rates", {"base": "HKD"}, TIMEOUT_SECONDS)
        assert sleep_calls == [2]

        # Text: a successful response is returned unchanged.
        sleep_calls.clear()
        text_calls = []

        def fake_text_get(url, params=None, timeout=None):
            text_calls.append((url, params, timeout))
            return _FakeResponse(200, text="<html>sample</html>")

        requests.get = fake_text_get
        text_result = get_text("https://example.test/page")
        assert text_result == "<html>sample</html>"
        assert len(text_calls) == 1
        assert sleep_calls == []

        # JSON: malformed JSON raises ValueError, is retried, then returns None
        # after all three failed attempts. The waits are captured, not performed.
        sleep_calls.clear()
        failures = []

        def fake_failed_json_get(url, params=None, timeout=None):
            failures.append(url)
            return _FakeResponse(200, ValueError("invalid JSON"))

        requests.get = fake_failed_json_get
        assert get_json("https://example.test/bad-json") is None
        assert len(failures) == 3
        assert sleep_calls == list(RETRY_DELAYS)

        # Text: HTTP errors are retried and end as None after three attempts.
        sleep_calls.clear()
        failures.clear()

        def fake_failed_text_get(url, params=None, timeout=None):
            failures.append(url)
            return _FakeResponse(503)

        requests.get = fake_failed_text_get
        assert get_text("https://example.test/unavailable") is None
        assert len(failures) == 3
        assert sleep_calls == list(RETRY_DELAYS)
    finally:
        requests.get = original_get
        time.sleep = original_sleep


if __name__ == "__main__":
    _check_fetch_functions()
    print("Layer 1 checks passed: get_json/get_text success, retries, and final failure.")
    print("Run a live request from a notebook for layers 2 and 3.")
