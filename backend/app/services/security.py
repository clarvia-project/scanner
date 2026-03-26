"""Security defense layer for Clarvia.

Provides:
1. Abuse detection — repeated failed requests, scan bombing, enumeration
2. IP reputation — track suspicious IPs, auto-ban after threshold
3. Request fingerprinting — detect bot patterns, scanner abuse
4. SSRF enhanced protection — expanded blocklist
5. Input sanitization — URL validation, injection prevention
6. Honeypot endpoints — detect malicious scanners

Designed to work alongside the existing rate limiter and security headers.
"""

import hashlib
import ipaddress
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSRF protection — expanded blocklist
# ---------------------------------------------------------------------------

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),   # shared address space
    ipaddress.ip_network("198.18.0.0/15"),   # benchmarking
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

_BLOCKED_HOSTNAMES = {
    "localhost", "metadata.google.internal", "metadata",
    "169.254.169.254",  # cloud metadata
    "metadata.google", "metadata.aws",
}

_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data", "javascript", "vbscript"}


def is_url_safe(url: str) -> tuple[bool, str]:
    """Validate URL is safe to scan (no SSRF, no injection)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Scheme check
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        return False, f"Blocked scheme: {scheme}"
    if scheme not in ("http", "https"):
        return False, f"Only http/https allowed, got: {scheme}"

    # Hostname check
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "No hostname in URL"
    if hostname in _BLOCKED_HOSTNAMES:
        return False, f"Blocked hostname: {hostname}"

    # IP check
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return False, f"Blocked IP range: {net}"
    except ValueError:
        pass  # Not an IP, it's a hostname — that's fine

    # Port check (block common internal ports)
    port = parsed.port
    if port and port in (22, 23, 25, 3306, 5432, 6379, 27017, 11211):
        return False, f"Blocked port: {port}"

    # Path injection check
    path = parsed.path or ""
    if ".." in path or "%2e%2e" in path.lower():
        return False, "Path traversal detected"

    # Length check
    if len(url) > 2000:
        return False, "URL too long (max 2000 chars)"

    return True, "OK"


# ---------------------------------------------------------------------------
# Abuse detection
# ---------------------------------------------------------------------------

class AbuseDetector:
    """Track and block abusive request patterns."""

    def __init__(self) -> None:
        # IP tracking
        self._ip_errors: dict[str, list[float]] = defaultdict(list)  # ip -> [timestamps of errors]
        self._ip_scans: dict[str, list[float]] = defaultdict(list)   # ip -> [scan timestamps]
        self._banned_ips: dict[str, float] = {}  # ip -> ban_expiry_timestamp

        # Thresholds (tuned for agent traffic — agents call fast)
        self.error_threshold = 50        # errors in window → ban
        self.scan_burst_threshold = 60   # scans in window → ban
        self.window_seconds = 300        # 5 minutes
        self.ban_duration = 600          # 10 minute ban (was 1 hour — too harsh for agents)

        # Stats
        self.total_blocked = 0
        self.total_bans = 0

    def is_banned(self, ip: str) -> bool:
        """Check if IP is currently banned."""
        expiry = self._banned_ips.get(ip)
        if expiry is None:
            return False
        if time.time() > expiry:
            del self._banned_ips[ip]
            return False
        return True

    def record_error(self, ip: str) -> bool:
        """Record an error from IP. Returns True if IP should be banned."""
        now = time.time()
        cutoff = now - self.window_seconds
        errors = self._ip_errors[ip]
        errors.append(now)
        # Trim old entries
        self._ip_errors[ip] = [t for t in errors if t > cutoff]

        if len(self._ip_errors[ip]) >= self.error_threshold:
            self._ban(ip, "excessive errors")
            return True
        return False

    def record_scan(self, ip: str) -> bool:
        """Record a scan from IP. Returns True if IP should be banned."""
        now = time.time()
        cutoff = now - self.window_seconds
        scans = self._ip_scans[ip]
        scans.append(now)
        self._ip_scans[ip] = [t for t in scans if t > cutoff]

        if len(self._ip_scans[ip]) >= self.scan_burst_threshold:
            self._ban(ip, "scan burst")
            return True
        return False

    def _ban(self, ip: str, reason: str) -> None:
        self._banned_ips[ip] = time.time() + self.ban_duration
        self.total_bans += 1
        logger.warning("IP banned: %s — reason: %s (total bans: %d)", ip, reason, self.total_bans)

    def get_stats(self) -> dict[str, Any]:
        """Get abuse detection stats for admin dashboard."""
        now = time.time()
        active_bans = {ip: exp for ip, exp in self._banned_ips.items() if exp > now}
        return {
            "active_bans": len(active_bans),
            "total_bans": self.total_bans,
            "total_blocked": self.total_blocked,
            "banned_ips": [
                {"ip": ip[:8] + "***", "expires_in": int(exp - now)}
                for ip, exp in active_bans.items()
            ],
        }

    def cleanup(self) -> int:
        """Remove expired bans and old tracking data."""
        now = time.time()
        expired = [ip for ip, exp in self._banned_ips.items() if exp < now]
        for ip in expired:
            del self._banned_ips[ip]

        cutoff = now - self.window_seconds * 2
        for store in (self._ip_errors, self._ip_scans):
            for ip in list(store.keys()):
                store[ip] = [t for t in store[ip] if t > cutoff]
                if not store[ip]:
                    del store[ip]

        return len(expired)


# Singleton
abuse_detector = AbuseDetector()


# ---------------------------------------------------------------------------
# Request fingerprinting — detect common attack patterns
# ---------------------------------------------------------------------------

_SUSPICIOUS_UA_PATTERNS = [
    r"sqlmap",
    r"nikto",
    r"nmap",
    r"masscan",
    r"dirbuster",
    r"gobuster",
    r"ffuf",
    r"wfuzz",
    r"hydra",
    r"nuclei",
    r"zgrab",
    r"pycurl",
    r"libwww-perl",
]

_SUSPICIOUS_PATH_PATTERNS = [
    r"\.env$",
    r"\.git/",
    r"wp-admin",
    r"wp-login",
    r"phpmyadmin",
    r"/admin\.php",
    r"\.\./",
    r"etc/passwd",
    r"\.sql$",
    r"\.bak$",
    r"\.backup$",
    r"/debug",
    r"/actuator",
    r"/console",
]


def is_suspicious_request(user_agent: str, path: str) -> tuple[bool, str | None]:
    """Check if request looks like an attack. Returns (suspicious, reason)."""
    ua_lower = user_agent.lower()
    for pattern in _SUSPICIOUS_UA_PATTERNS:
        if re.search(pattern, ua_lower):
            return True, f"Suspicious user-agent: {pattern}"

    path_lower = path.lower()
    for pattern in _SUSPICIOUS_PATH_PATTERNS:
        if re.search(pattern, path_lower):
            return True, f"Suspicious path pattern: {pattern}"

    return False, None
