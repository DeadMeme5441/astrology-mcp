"""Private local birth profiles and offline historical timezone resolution."""

from __future__ import annotations

import json
import os
import platform
import re
import tempfile
import threading
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from timezonefinder import TimezoneFinder

from .context import calculate_person_context

_PROFILE_NAME = re.compile(r"^[\w .'-]{1,50}$", re.UNICODE)
_store_lock = threading.RLock()
_thread_state = threading.local()


def _data_directory() -> Path:
    override = os.environ.get("ASTROLOGY_MCP_DATA_DIR")
    if override:
        return Path(override).expanduser()
    system = platform.system()
    if system == "Windows":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "astrology-mcp"


def _profile_path() -> Path:
    return _data_directory() / "profiles.json"


def _profile_key(profile_name: str) -> str:
    normalized = " ".join(profile_name.split())
    if not _PROFILE_NAME.fullmatch(normalized):
        raise ValueError("profile_name must be 1-50 letters, numbers, spaces, or simple punctuation")
    return normalized.casefold()


def _empty_store() -> dict[str, Any]:
    return {"schema_version": 1, "profiles": {}}


def _read_store() -> dict[str, Any]:
    path = _profile_path()
    if not path.exists():
        return _empty_store()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read the local birth-profile store: {exc}") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or not isinstance(payload.get("profiles"), dict)
    ):
        raise RuntimeError("The local birth-profile store has an unsupported or invalid format")
    return payload


def _write_store(store: dict[str, Any]) -> None:
    directory = _data_directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    descriptor, temporary_name = tempfile.mkstemp(prefix="profiles-", suffix=".tmp", dir=directory)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(0o600)
        os.replace(temporary_path, _profile_path())
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _timezone_finder() -> TimezoneFinder:
    finder = getattr(_thread_state, "timezone_finder", None)
    if finder is None:
        finder = TimezoneFinder(in_memory=False)
        _thread_state.timezone_finder = finder
    return finder


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be between -90 and 90 degrees")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be between -180 and 180 degrees")


def _parse_local_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("birth_date must use YYYY-MM-DD format") from exc


def _parse_local_time(value: str) -> time:
    try:
        parsed = time.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("birth_time must use 24-hour HH:MM or HH:MM:SS format") from exc
    if parsed.tzinfo is not None:
        raise ValueError("birth_time must be a local clock time without a UTC offset")
    return parsed


def _valid_local_candidate(local_naive: datetime, zone: ZoneInfo, fold: int) -> datetime | None:
    candidate = local_naive.replace(tzinfo=zone, fold=fold)
    round_trip = candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    return candidate if round_trip == local_naive else None


def resolve_local_birth_timestamp(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    *,
    fold: int | None = None,
) -> dict[str, Any]:
    """Resolve coordinates and local civil time to a historical offset-aware timestamp."""
    _validate_coordinates(latitude, longitude)
    local_naive = datetime.combine(_parse_local_date(birth_date), _parse_local_time(birth_time))
    timezone_name = _timezone_finder().timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("no IANA timezone could be resolved for those coordinates")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"timezone data for {timezone_name!r} is unavailable") from exc

    first = _valid_local_candidate(local_naive, zone, 0)
    second = _valid_local_candidate(local_naive, zone, 1)
    if first is None and second is None:
        raise ValueError(
            f"{birth_date} {birth_time} did not exist in {timezone_name} because of a clock change"
        )
    is_ambiguous = (
        first is not None
        and second is not None
        and first.utcoffset() != second.utcoffset()
    )
    if is_ambiguous and fold is None:
        assert first is not None and second is not None
        raise ValueError(
            "birth time is ambiguous because clocks moved backward; ask whether it was the first "
            f"({first.isoformat()}) or second ({second.isoformat()}) occurrence, then pass fold=0 or fold=1"
        )
    if fold not in (None, 0, 1):
        raise ValueError("fold must be 0, 1, or omitted")
    selected = (second if fold == 1 else first) or first or second
    assert selected is not None
    return {
        "birth_timestamp": selected.isoformat(),
        "birth_timestamp_utc": selected.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timezone": timezone_name,
        "utc_offset": selected.strftime("%z")[:3] + ":" + selected.strftime("%z")[3:],
        "fold": selected.fold,
    }


def save_birth_profile(
    profile_name: str,
    birth_date: str,
    birth_time: str,
    birth_place: str,
    latitude: float,
    longitude: float,
    *,
    birth_time_accuracy_minutes: float | None = None,
    fold: int | None = None,
) -> dict[str, Any]:
    """Create or replace a private local birth profile."""
    key = _profile_key(profile_name)
    place = " ".join(birth_place.split())
    if not place:
        raise ValueError("birth_place must not be empty")
    if len(place) > 300:
        raise ValueError("birth_place cannot exceed 300 characters")
    if birth_time_accuracy_minutes is not None and birth_time_accuracy_minutes < 0:
        raise ValueError("birth_time_accuracy_minutes cannot be negative")
    resolved = resolve_local_birth_timestamp(
        birth_date,
        birth_time,
        latitude,
        longitude,
        fold=fold,
    )
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "profile_name": " ".join(profile_name.split()),
        "birth_date": _parse_local_date(birth_date).isoformat(),
        "birth_time": _parse_local_time(birth_time).isoformat(),
        "birth_timestamp": resolved["birth_timestamp"],
        "birth_timestamp_utc": resolved["birth_timestamp_utc"],
        "birth_timezone": resolved["timezone"],
        "birth_place": place,
        "birth_latitude": latitude,
        "birth_longitude": longitude,
        "birth_time_accuracy_minutes": birth_time_accuracy_minutes,
        "updated_at": now,
    }
    with _store_lock:
        store = _read_store()
        store["profiles"][key] = profile
        _write_store(store)
    return {
        "saved": True,
        "profile": profile,
        "privacy": "Stored only in the local astrology-mcp data directory with owner-only permissions where supported.",
        "next_step": "For this profile's questions, call ask_astrology with only the question and profile_name.",
    }


def get_birth_profile(profile_name: str = "me") -> dict[str, Any]:
    """Load one private local birth profile."""
    key = _profile_key(profile_name)
    with _store_lock:
        profile = _read_store()["profiles"].get(key)
    if not isinstance(profile, dict):
        raise ValueError(
            f"birth profile {profile_name!r} does not exist; ask for birth date, exact local time, and place"
        )
    return profile


def list_birth_profiles() -> dict[str, Any]:
    """List profile names and non-sensitive place labels without full birth timestamps."""
    with _store_lock:
        profiles = _read_store()["profiles"].values()
        summaries = [
            {
                "profile_name": profile["profile_name"],
                "birth_place": profile["birth_place"],
                "birth_timezone": profile["birth_timezone"],
                "updated_at": profile["updated_at"],
            }
            for profile in profiles
            if isinstance(profile, dict)
        ]
    summaries.sort(key=lambda profile: str(profile["profile_name"]).casefold())
    return {
        "profiles": summaries,
        "default_profile": "me",
        "next_step": (
            "Call ask_astrology when the intended profile exists. Otherwise ask the human for birth date, "
            "exact local time, and birthplace, then resolve the place and save a profile."
        ),
    }


def delete_birth_profile(profile_name: str) -> dict[str, Any]:
    """Permanently delete one local birth profile."""
    key = _profile_key(profile_name)
    with _store_lock:
        store = _read_store()
        removed = store["profiles"].pop(key, None)
        if removed is not None:
            _write_store(store)
    return {"deleted": removed is not None, "profile_name": profile_name}


def calculate_profile_context(
    question: str,
    *,
    profile_name: str = "me",
    as_of_timestamp: str | None = None,
    current_latitude: float | None = None,
    current_longitude: float | None = None,
) -> dict[str, Any]:
    """Calculate current context using a saved profile; no birth data is repeated by the human."""
    profile = get_birth_profile(profile_name)
    context = calculate_person_context(
        str(profile["birth_timestamp"]),
        float(profile["birth_latitude"]),
        float(profile["birth_longitude"]),
        question,
        as_of_timestamp=as_of_timestamp,
        current_latitude=current_latitude,
        current_longitude=current_longitude,
        birth_time_accuracy_minutes=(
            float(profile["birth_time_accuracy_minutes"])
            if profile["birth_time_accuracy_minutes"] is not None
            else None
        ),
    )
    return {
        "profile": {
            "profile_name": profile["profile_name"],
            "birth_place": profile["birth_place"],
            "birth_timezone": profile["birth_timezone"],
        },
        "context": context,
    }
