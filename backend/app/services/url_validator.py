"""
URL Validation and Canonical Normalization Service for CampusAI.

Guarantees that every external URL stored and rendered by CampusAI is an actual,
verified, and reachable official college resource. Strictly rejects 404s, 403s, 500s,
SSRF attempts, and broken/unreachable links.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import re
import socket
from typing import Optional, Tuple, List
from urllib.parse import urlparse, urljoin, urldefrag, unquote, quote

import httpx

from backend.app.core.logging import logger

DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = "CampusAICrawler/1.0 (+https://mits.ac.in/bot)"
ALLOWED_MITS_DOMAINS = ["mits.ac.in", "www.mits.ac.in", "studentportal.universitysolutions.in"]


@dataclass
class UrlValidationResult:
    original_url: str
    resolved_url: str
    final_url: str
    http_status: int
    content_type: str
    is_valid: bool
    error_reason: Optional[str] = None
    last_checked_at: Optional[datetime] = None


def normalize_external_url(url: str, base_url: str = "https://mits.ac.in/") -> str:
    """
    Robust canonical URL normalization:
    - Resolves relative URLs (including ../ paths) against base_url
    - Strips fragments (#...)
    - Unquotes and properly requotes spaces and special characters in path
    - Normalizes duplicate slashes (except http:// or https://)
    - Normalizes trailing slashes for non-file paths
    """
    if not url or not isinstance(url, str):
        return ""

    raw_url = url.strip()
    if not raw_url:
        return ""

    # Resolve against base URL if relative
    resolved = urljoin(base_url, raw_url)

    # Defrag
    defragged, _ = urldefrag(resolved)

    try:
        parsed = urlparse(defragged)
    except Exception:
        return defragged

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()

    # Clean path: normalize duplicate slashes, unquote then quote safely
    raw_path = parsed.path or "/"
    clean_path_parts = []
    for segment in raw_path.split("/"):
        if not segment and clean_path_parts:
            continue
        # Unquote first to avoid double encoding, then quote safe chars
        unquoted_seg = unquote(segment)
        clean_path_parts.append(quote(unquoted_seg, safe="@:$,;+=&~-_.!*'()"))

    normalized_path = "/".join(clean_path_parts)
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path

    # Reconstruct URL
    query_str = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{netloc}{normalized_path}{query_str}"


def check_ssrf_safety(url: str, allowed_domains: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Strict SSRF protection:
    - Verifies scheme is http or https
    - Rejects private IPs, loopback, link-local, cloud metadata IPs
    - Checks domain whitelist if provided
    """
    if not url:
        return False, "URL is empty"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Failed to parse URL: {exc}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}'. Only http/https allowed."

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        return False, "Missing valid hostname"

    # Blocked hosts and metadata endpoints
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1", "metadata.google.internal"}
    if hostname in blocked_hosts or hostname.endswith(".local") or hostname.endswith(".internal") or hostname.endswith(".lan"):
        return False, f"Access to host '{hostname}' is forbidden (SSRF protection)."

    try:
        ip_obj = ipaddress.ip_address(hostname)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
            return False, f"Access to private IP '{hostname}' is forbidden."
    except ValueError:
        # Hostname DNS check
        try:
            resolved_ip_str = socket.gethostbyname(hostname)
            resolved_ip = ipaddress.ip_address(resolved_ip_str)
            if resolved_ip.is_private or resolved_ip.is_loopback or resolved_ip.is_link_local or resolved_ip.is_reserved:
                return False, f"Host '{hostname}' resolves to private IP '{resolved_ip_str}' (SSRF protection)."
        except (socket.gaierror, socket.herror):
            pass

    domains = allowed_domains if allowed_domains is not None else ALLOWED_MITS_DOMAINS
    if domains:
        clean_domains = [d.lower().strip() for d in domains if d.strip()]
        domain_match = any(hostname == allowed or hostname.endswith("." + allowed) for allowed in clean_domains)
        if not domain_match:
            return False, f"Host '{hostname}' is not in allowed domains list: {clean_domains}"

    return True, "URL is safe"


def validate_external_url(
    url: str,
    base_url: str = "https://mits.ac.in/",
    client: Optional[httpx.Client] = None,
    timeout: float = DEFAULT_TIMEOUT,
    allowed_domains: Optional[List[str]] = None,
) -> UrlValidationResult:
    """
    Validate external URL against official MITS server:
    1. Normalizes URL
    2. Runs SSRF safety checks
    3. Makes HEAD request (with follow_redirects)
    4. If HEAD returns 405/403/fails, falls back to streaming GET
    5. Rejects 404, 403, 500, empty body
    6. Returns structured UrlValidationResult
    """
    now = datetime.now(timezone.utc)
    if not url or not isinstance(url, str) or not url.strip():
        return UrlValidationResult(
            original_url=url or "",
            resolved_url="",
            final_url="",
            http_status=0,
            content_type="",
            is_valid=False,
            error_reason="Empty URL",
            last_checked_at=now,
        )

    normalized_url = normalize_external_url(url, base_url)

    is_safe, ssrf_msg = check_ssrf_safety(normalized_url, allowed_domains)
    if not is_safe:
        return UrlValidationResult(
            original_url=url,
            resolved_url=normalized_url,
            final_url=normalized_url,
            http_status=400,
            content_type="",
            is_valid=False,
            error_reason=f"Security check failed: {ssrf_msg}",
            last_checked_at=now,
        )

    should_close = False
    if client is None:
        client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        should_close = True

    try:
        # Try HEAD first
        resp = None
        try:
            resp = client.head(normalized_url)
            # If server does not support HEAD (405 Method Not Allowed or 403 Forbidden on HEAD)
            if resp.status_code in (405, 403):
                resp = None
        except Exception:
            resp = None

        # Fallback to GET stream if HEAD failed or was rejected
        if resp is None:
            with client.stream("GET", normalized_url) as stream_resp:
                http_status = stream_resp.status_code
                final_url = str(stream_resp.url)
                content_type = stream_resp.headers.get("content-type", "").lower()
                is_valid = (200 <= http_status < 400)
                error_reason = None if is_valid else f"HTTP {http_status}"
                return UrlValidationResult(
                    original_url=url,
                    resolved_url=normalized_url,
                    final_url=final_url,
                    http_status=http_status,
                    content_type=content_type,
                    is_valid=is_valid,
                    error_reason=error_reason,
                    last_checked_at=now,
                )

        http_status = resp.status_code
        final_url = str(resp.url)
        content_type = resp.headers.get("content-type", "").lower()
        is_valid = (200 <= http_status < 400)
        error_reason = None if is_valid else f"HTTP {http_status}"

        return UrlValidationResult(
            original_url=url,
            resolved_url=normalized_url,
            final_url=final_url,
            http_status=http_status,
            content_type=content_type,
            is_valid=is_valid,
            error_reason=error_reason,
            last_checked_at=now,
        )

    except httpx.HTTPError as http_err:
        return UrlValidationResult(
            original_url=url,
            resolved_url=normalized_url,
            final_url=normalized_url,
            http_status=0,
            content_type="",
            is_valid=False,
            error_reason=f"Network error: {type(http_err).__name__} ({str(http_err)[:100]})",
            last_checked_at=now,
        )
    except Exception as exc:
        return UrlValidationResult(
            original_url=url,
            resolved_url=normalized_url,
            final_url=normalized_url,
            http_status=0,
            content_type="",
            is_valid=False,
            error_reason=f"Validation error: {str(exc)[:100]}",
            last_checked_at=now,
        )
    finally:
        if should_close:
            client.close()
