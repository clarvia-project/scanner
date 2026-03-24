"""API client for the Clarvia AEO Scanner."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import urllib.request
import urllib.error


@dataclass
class ScanResult:
    """Parsed scan result from the Clarvia API."""

    scan_id: str
    url: str
    service_name: str
    clarvia_score: int
    rating: str
    dimensions: dict[str, dict[str, Any]]
    onchain_bonus: dict[str, Any] = field(default_factory=dict)
    top_recommendations: list[str] = field(default_factory=list)
    scanned_at: str = ""
    scan_duration_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> ScanResult:
        return cls(
            scan_id=data.get("scan_id", ""),
            url=data.get("url", ""),
            service_name=data.get("service_name", ""),
            clarvia_score=data.get("clarvia_score", 0),
            rating=data.get("rating", "unknown"),
            dimensions=data.get("dimensions", {}),
            onchain_bonus=data.get("onchain_bonus", {}),
            top_recommendations=data.get("top_recommendations", []),
            scanned_at=data.get("scanned_at", ""),
            scan_duration_ms=data.get("scan_duration_ms", 0),
            raw=data,
        )


class ScanError(Exception):
    """Raised when a scan request fails."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ClarviaClient:
    """HTTP client for the Clarvia AEO Scanner API."""

    def __init__(
        self,
        api_url: str = "https://clarvia.art",
        timeout: int = 60,
        auth_header: tuple[str, str] | None = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.auth_header = auth_header

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "clarvia-cli/1.0.0",
        }
        if self.auth_header:
            headers[self.auth_header[0]] = self.auth_header[1]
        return headers

    def scan(self, url: str) -> ScanResult:
        """Submit a URL for scanning and return the result.

        Args:
            url: The URL to scan.

        Returns:
            ScanResult with score, dimensions, and recommendations.

        Raises:
            ScanError: If the API returns an error.
        """
        endpoint = f"{self.api_url}/api/scan"
        payload = json.dumps({"url": url}).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return ScanResult.from_api_response(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                err = json.loads(body)
                msg = (
                    err.get("detail", "")
                    or err.get("error", {}).get("message", "")
                    or body[:300]
                )
            except json.JSONDecodeError:
                msg = body[:300]
            raise ScanError(f"API error ({e.code}): {msg}", status_code=e.code) from e
        except urllib.error.URLError as e:
            raise ScanError(f"Connection error: {e.reason}") from e
        except TimeoutError:
            raise ScanError(f"Request timed out after {self.timeout}s")

    def badge_url(self, identifier: str) -> str:
        """Return the badge URL for a service.

        Args:
            identifier: Service name, scan_id, or URL.

        Returns:
            Full badge URL string.
        """
        encoded = quote(identifier, safe="")
        return f"{self.api_url}/api/badge/{encoded}"
