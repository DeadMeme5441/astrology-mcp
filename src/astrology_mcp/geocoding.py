"""Policy-compliant, purpose-limited Nominatim lookup for birth/current places."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_DEFAULT_ENDPOINT = "https://nominatim.openstreetmap.org/search"
_POLICY_URL = "https://operations.osmfoundation.org/policies/nominatim/"
_ATTRIBUTION = "Search data © OpenStreetMap contributors, ODbL 1.0"
_COUNTRY_CODES = re.compile(r"^[a-z]{2}(?:,[a-z]{2})*$")
_REQUEST_INTERVAL_SECONDS = 1.0
_request_lock = threading.Lock()
_last_request_completed_at = 0.0


def _normalize_country_codes(country_codes: str | None) -> str:
    if country_codes is None or not country_codes.strip():
        return ""
    normalized = ",".join(part.strip().casefold() for part in country_codes.split(","))
    if not _COUNTRY_CODES.fullmatch(normalized):
        raise ValueError("country_codes must contain comma-separated ISO 3166-1 alpha-2 codes, such as 'in'")
    return normalized


def _float_field(candidate: dict[str, Any], field: str) -> float | None:
    value = candidate.get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    latitude = _float_field(candidate, "lat")
    longitude = _float_field(candidate, "lon")
    display_name = candidate.get("display_name")
    if latitude is None or longitude is None or not isinstance(display_name, str):
        return None
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        return None

    address_source = candidate.get("address")
    address = address_source if isinstance(address_source, dict) else {}
    selected_address = {
        key: value
        for key in (
            "neighbourhood",
            "suburb",
            "city_district",
            "city",
            "town",
            "village",
            "county",
            "state",
            "postcode",
            "country",
            "country_code",
        )
        if isinstance((value := address.get(key)), str)
    }
    bounding_box_source = candidate.get("boundingbox")
    bounding_box = None
    if isinstance(bounding_box_source, list) and len(bounding_box_source) == 4:
        try:
            bounding_box = [float(value) for value in bounding_box_source]
        except (TypeError, ValueError):
            bounding_box = None

    return {
        "display_name": display_name,
        "latitude": latitude,
        "longitude": longitude,
        "category": candidate.get("category") or candidate.get("class"),
        "type": candidate.get("type"),
        "importance": _float_field(candidate, "importance"),
        "address": selected_address,
        "bounding_box": bounding_box,
    }


def _request_json(query: str, country_codes: str, limit: int) -> list[dict[str, Any]]:
    global _last_request_completed_at

    endpoint = os.environ.get("ASTROLOGY_MCP_GEOCODER_URL", _DEFAULT_ENDPOINT).strip()
    if not endpoint.startswith(("https://", "http://")):
        raise ValueError("ASTROLOGY_MCP_GEOCODER_URL must be an HTTP or HTTPS URL")
    parameters = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": str(limit),
    }
    if country_codes:
        parameters["countrycodes"] = country_codes
    contact_email = os.environ.get("ASTROLOGY_MCP_GEOCODER_EMAIL", "").strip()
    if contact_email:
        parameters["email"] = contact_email

    user_agent = os.environ.get(
        "ASTROLOGY_MCP_GEOCODER_USER_AGENT",
        "astrology-mcp/0.1.0 birth-location-resolver",
    ).strip()
    if not user_agent:
        raise ValueError("ASTROLOGY_MCP_GEOCODER_USER_AGENT cannot be empty")
    request = Request(
        f"{endpoint}?{urlencode(parameters)}",
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )

    with _request_lock:
        remaining = _REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_completed_at)
        if remaining > 0:
            time.sleep(remaining)
        try:
            with urlopen(request, timeout=10.0) as response:
                raw_response = response.read()
        except HTTPError as exc:
            raise RuntimeError(f"Nominatim returned HTTP {exc.code}; try again later or configure another endpoint") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach the configured geocoder: {exc.reason}") from exc
        finally:
            _last_request_completed_at = time.monotonic()

    try:
        payload = json.loads(raw_response)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("The configured geocoder returned invalid JSON") from exc
    if not isinstance(payload, list):
        raise RuntimeError("The configured geocoder returned an unexpected response")
    return [candidate for candidate in payload if isinstance(candidate, dict)]


@lru_cache(maxsize=256)
def _cached_lookup(query: str, country_codes: str, limit: int) -> tuple[dict[str, Any], ...]:
    parsed = (_parse_candidate(candidate) for candidate in _request_json(query, country_codes, limit))
    return tuple(candidate for candidate in parsed if candidate is not None)


def resolve_birth_location(
    query: str,
    *,
    country_codes: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Resolve a user-supplied birthplace/current place into coordinate candidates."""
    normalized_query = " ".join(query.split())
    if len(normalized_query) < 2:
        raise ValueError("query must contain at least two non-whitespace characters")
    if len(normalized_query) > 200:
        raise ValueError("query cannot exceed 200 characters")
    if not 1 <= limit <= 5:
        raise ValueError("limit must be between 1 and 5")
    normalized_codes = _normalize_country_codes(country_codes)
    candidates = list(_cached_lookup(normalized_query, normalized_codes, limit))
    return {
        "query": normalized_query,
        "country_codes": normalized_codes or None,
        "candidates": candidates,
        "provider": "Nominatim / OpenStreetMap",
        "attribution": _ATTRIBUTION,
        "usage_policy": _POLICY_URL,
        "usage_notice": (
            "Public Nominatim is limited to one request per second, forbids autocomplete and bulk/systematic "
            "queries, and requires caching. This server uses serialized requests and an in-memory 256-query cache."
        ),
        "privacy_notice": (
            "The place query is sent to the configured geocoder. Do not include a person's name, exact private "
            "residential address, or other confidential information."
        ),
        "selection_rule": (
            "Use a candidate only when its display name and address match the human's intended place. "
            "If plausible candidates disagree, ask the human instead of guessing."
        ),
    }
