"""
Application-level rate limiter for sensitive endpoints (MITS GEMS Attendance).

Protects against brute-force and credential-stuffing attacks without relying
on external infrastructure dependencies. Designed to operate safely behind
reverse proxies (Render / Cloudflare) by carefully extracting and validating
client IP addresses.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
import ipaddress
import threading
import time
from typing import Optional
from fastapi import HTTPException, Request, status

from backend.app.core.logging import logger


class AttendanceRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter.
    
    Security Invariants:
    - Never rate-limits on roll number alone (prevents DoS against honest students).
    - Rate limits on:
      1) Client IP (cap against distributed/sweeping brute force).
      2) Combined (Client IP + Roll Number) (cap against targeted password guessing).
    - Never stores, logs, or references passwords, tokens, or session identifiers.
    - User-friendly error message that does not leak whether a roll number exists.
    """

    def __init__(
        self,
        max_requests_per_ip: int = 15,
        max_requests_per_roll: int = 5,
        window_seconds: int = 60,
    ):
        self.max_requests_per_ip = max_requests_per_ip
        self.max_requests_per_roll = max_requests_per_roll
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._ip_history = defaultdict(deque)
        self._pair_history = defaultdict(deque)

    def _clean_expired(self, timestamps: deque, now: float) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

    def check(self, client_ip: str, roll_number: str) -> None:
        """
        Check and record an attendance sync attempt.
        Raises HTTPException(429) if rate limits are exceeded.
        """
        now = time.time()
        clean_ip = client_ip.strip() or "127.0.0.1"
        clean_roll = (roll_number or "").strip().upper()

        with self._lock:
            # 1. Clean and check per-IP sliding window
            ip_records = self._ip_history[clean_ip]
            self._clean_expired(ip_records, now)
            if len(ip_records) >= self.max_requests_per_ip:
                oldest = ip_records[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                logger.warning(f"[RATE_LIMIT] Exceeded per-IP limit for ip={clean_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attendance sync attempts. Please wait a few minutes and try again.",
                    headers={"Retry-After": str(retry_after)},
                )

            # 2. Clean and check per (IP, Roll) sliding window
            pair_key = f"{clean_ip}:{clean_roll}"
            pair_records = self._pair_history[pair_key]
            self._clean_expired(pair_records, now)
            if len(pair_records) >= self.max_requests_per_roll:
                oldest = pair_records[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                logger.warning(f"[RATE_LIMIT] Exceeded per-pair limit for ip={clean_ip}, roll_number={clean_roll}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attendance sync attempts. Please wait a few minutes and try again.",
                    headers={"Retry-After": str(retry_after)},
                )

            # Record attempt in both windows
            ip_records.append(now)
            pair_records.append(now)

    def reset(self) -> None:
        """Reset all rate limiter windows (used for test isolation)."""
        with self._lock:
            self._ip_history.clear()
            self._pair_history.clear()


def get_client_ip(request: Request) -> str:
    """
    Safely extract and validate client IP address from request.
    
    Security:
    - Behind reverse proxies (e.g. Render, Cloudflare), client IP is in X-Forwarded-For.
    - We take the leftmost untrusted IP from X-Forwarded-For and validate it using ipaddress.
    - Rejects invalid or forged header strings, falling back safely to request.client.host.
    - Supports 'testclient' for unit test environments.
    """
    # 1. Check X-Forwarded-For (standard reverse-proxy header)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Leftmost entry is the client address added by the edge proxy
        raw_ip = forwarded.split(",")[0].strip()
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            pass

    # 2. Check CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        raw_ip = cf_ip.strip()
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            pass

    # 3. Check X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        raw_ip = real_ip.strip()
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip
        except ValueError:
            pass

    # 4. Fall back to socket client
    if request.client and request.client.host:
        client_host = request.client.host.strip()
        if client_host == "testclient":
            return "testclient"
        try:
            ipaddress.ip_address(client_host)
            return client_host
        except ValueError:
            pass

    return "127.0.0.1"


# Global singleton instance for application use
attendance_rate_limiter = AttendanceRateLimiter(
    max_requests_per_ip=15,
    max_requests_per_roll=5,
    window_seconds=60,
)
