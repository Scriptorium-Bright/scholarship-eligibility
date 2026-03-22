from __future__ import annotations

import httpx


class HttpTextFetcher:
    """Fetch HTML text over HTTP for production collector runs."""

    def __init__(self, timeout_seconds: float = 10.0):
        """Prepare a reusable HTTP client with redirect handling enabled."""

        self._client = httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
        )

    def fetch(self, url: str) -> str:
        """Return the response body for one notice list or detail URL."""

        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        """Release the underlying HTTP client when the service owns it."""

        self._client.close()
