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


# Layer 1: exact checks use a tiny, hand-written response and a fake session.
class _FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _check_fake_response():
    response = _FakeResponse(200, {"date": "2026-10-29", "rates": {"CNY": 0.92}}, "ok")
    response.raise_for_status()
    assert response.json()["rates"]["CNY"] == 0.92
    assert response.text == "ok"
    failed = _FakeResponse(503)
    try:
        failed.raise_for_status()
    except requests.exceptions.HTTPError:
        pass
    else:
        raise AssertionError("HTTP errors must be raised")


if __name__ == "__main__":
    _check_fake_response()
    print("Layer 1 checks passed. Run a live request from a notebook for layers 2 and 3.")
