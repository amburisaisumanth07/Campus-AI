"""
Unit tests for URL Validator and SSRF Protection.
"""
import pytest
from backend.app.services.url_validator import (
    normalize_external_url,
    check_ssrf_safety,
    validate_external_url,
    UrlValidationResult,
)


def test_normalize_external_url_basic():
    url = "https://mits.ac.in/assets/pdf/admin/General Holidays in 2026.pdf"
    normalized = normalize_external_url(url)
    assert "https://mits.ac.in" in normalized
    assert "%20" in normalized or " " not in normalized


def test_normalize_external_url_relative_path():
    base = "https://mits.ac.in/academic-calenders"
    relative = "public/uploads/ugc/B.Tech-1st Year.pdf"
    normalized = normalize_external_url(relative, base_url=base)
    assert normalized.startswith("https://mits.ac.in/public/uploads/ugc/")
    assert "B.Tech-1st%20Year.pdf" in normalized or "B.Tech-1st" in normalized


def test_normalize_external_url_strips_fragments():
    url = "https://mits.ac.in/departments#faculty"
    normalized = normalize_external_url(url)
    assert "#" not in normalized
    assert normalized == "https://mits.ac.in/departments"


def test_ssrf_blocks_private_ips():
    is_safe, msg = check_ssrf_safety("http://127.0.0.1:8000/admin")
    assert not is_safe
    assert "forbidden" in msg.lower() or "ssrf" in msg.lower()

    is_safe, msg = check_ssrf_safety("http://169.254.169.254/latest/meta-data/")
    assert not is_safe


def test_ssrf_blocks_unauthorized_domains():
    is_safe, msg = check_ssrf_safety("https://malicious-external-site.com/steal-data", allowed_domains=["mits.ac.in"])
    assert not is_safe
    assert "not in allowed domains" in msg.lower()


def test_ssrf_allows_valid_mits_subdomains():
    is_safe, _ = check_ssrf_safety("https://mits.ac.in/about-us", allowed_domains=["mits.ac.in", "www.mits.ac.in"])
    assert is_safe

    is_safe, _ = check_ssrf_safety("https://studentportal.universitysolutions.in/", allowed_domains=["studentportal.universitysolutions.in"])
    assert is_safe


def test_validate_external_url_rejects_nonexistent_path():
    """Verify that a 404 URL is strictly rejected and marked is_valid = False."""
    fake_url = "https://mits.ac.in/this-file-definitely-does-not-exist-at-all-404.pdf"
    result = validate_external_url(fake_url, timeout=10.0)
    assert isinstance(result, UrlValidationResult)
    assert not result.is_valid
    assert result.http_status in (404, 0, 403, 500)
