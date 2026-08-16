"""Deterministic Lahiri sidereal chart, panchanga, and Vimshottari calculations."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import swisseph as swe

from .constants import (
    DASHA_SEQUENCE,
    DASHA_YEARS,
    EXALTATION_SIGNS,
    NAKSHATRAS,
    OWN_SIGNS,
    RASHIS,
    TITHI_NAMES,
    WEEKDAYS,
    YOGA_NAMES,
)

NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0
VIMSHOTTARI_YEAR_DAYS = 365.2425

_GRAHA_IDS = (
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mars", swe.MARS),
    ("Mercury", swe.MERCURY),
    ("Jupiter", swe.JUPITER),
    ("Venus", swe.VENUS),
    ("Saturn", swe.SATURN),
    ("Rahu", swe.TRUE_NODE),
)

_ephemeris_path = os.environ.get("SE_EPHE_PATH")
swe.set_ephe_path(_ephemeris_path or None)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0.0, 0.0)


def parse_timestamp(value: str, field_name: str = "timestamp") -> datetime:
    """Parse an ISO-8601 timestamp and require an explicit UTC offset."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 string")
    normalized = value.strip()
    if normalized.endswith(("Z", "z")):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must be ISO-8601, for example 1990-05-17T14:30:00+05:30"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"{field_name} must include its UTC offset; a local time without an offset is ambiguous"
        )
    return parsed


def _validate_location(latitude: float, longitude: float) -> None:
    if not -89.999 <= latitude <= 89.999:
        raise ValueError("latitude must be between -89.999 and 89.999 degrees")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be between -180 and 180 degrees")


def _julian_day(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + (utc.second + utc.microsecond / 1_000_000.0) / 3600.0
    return swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)


def _rashi_details(sign_index: int) -> dict[str, Any]:
    rashi = RASHIS[sign_index]
    return {
        "index": sign_index + 1,
        "name": rashi["name"],
        "english": rashi["english"],
        "lord": rashi["lord"],
        "element": rashi["element"],
        "modality": rashi["modality"],
    }


def _longitude_details(longitude: float) -> dict[str, Any]:
    normalized = longitude % 360.0
    sign_index = int(normalized // 30.0)
    degree_in_sign = normalized % 30.0
    nakshatra_index = min(int(normalized // NAKSHATRA_SPAN), 26)
    degree_in_nakshatra = normalized - nakshatra_index * NAKSHATRA_SPAN
    pada = min(int(degree_in_nakshatra // PADA_SPAN) + 1, 4)
    return {
        "longitude": round(normalized, 6),
        "degree_in_sign": round(degree_in_sign, 6),
        "rashi": _rashi_details(sign_index),
        "nakshatra": {
            "index": nakshatra_index + 1,
            "name": NAKSHATRAS[nakshatra_index],
            "lord": DASHA_SEQUENCE[nakshatra_index % 9],
            "pada": pada,
            "degree_in_nakshatra": round(degree_in_nakshatra, 6),
        },
    }


def _navamsha(longitude: float) -> dict[str, Any]:
    normalized = longitude % 360.0
    natal_sign = int(normalized // 30.0)
    division = min(int((normalized % 30.0) // (30.0 / 9.0)), 8)
    modality = RASHIS[natal_sign]["modality"]
    start_offset = 0 if modality == "Movable" else 8 if modality == "Fixed" else 4
    navamsha_sign = (natal_sign + start_offset + division) % 12
    return {"division": division + 1, "rashi": _rashi_details(navamsha_sign)}


def _dignity(graha: str, sign_index: int) -> str:
    if graha not in EXALTATION_SIGNS:
        return "not_assigned"
    if EXALTATION_SIGNS[graha] == sign_index:
        return "exalted_sign"
    if (EXALTATION_SIGNS[graha] + 6) % 12 == sign_index:
        return "debilitated_sign"
    if sign_index in OWN_SIGNS[graha]:
        return "own_sign"
    return "neutral_sign"


def _ephemeris_name(return_flags: list[int]) -> str:
    if any(flags & swe.FLG_JPLEPH for flags in return_flags):
        return "JPL ephemeris through Swiss Ephemeris"
    if any(flags & swe.FLG_SWIEPH for flags in return_flags):
        return "Swiss Ephemeris data files"
    return "Swiss Ephemeris Moshier analytical ephemeris"


def _panchanga(local_moment: datetime, sun_longitude: float, moon_longitude: float) -> dict[str, Any]:
    elongation = (moon_longitude - sun_longitude) % 360.0
    tithi_index = min(int(elongation // 12.0), 29)
    paksha_index = tithi_index % 15
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_name = TITHI_NAMES[paksha_index]
    if tithi_index == 29:
        tithi_name = "Amavasya"

    half_tithi_index = min(int(elongation // 6.0), 59)
    repeating_karanas = ("Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti")
    if half_tithi_index == 0:
        karana = "Kimstughna"
    elif half_tithi_index <= 56:
        karana = repeating_karanas[(half_tithi_index - 1) % 7]
    else:
        karana = ("Shakuni", "Chatushpada", "Naga")[half_tithi_index - 57]

    yoga_index = min(int(((sun_longitude + moon_longitude) % 360.0) // NAKSHATRA_SPAN), 26)
    moon_details = _longitude_details(moon_longitude)
    weekday_name, weekday_lord = WEEKDAYS[local_moment.weekday()]
    return {
        "tithi": {
            "number": tithi_index + 1,
            "paksha": paksha,
            "name": tithi_name,
            "completion_percent": round((elongation % 12.0) / 12.0 * 100.0, 3),
        },
        "karana": {"half_tithi_number": half_tithi_index + 1, "name": karana},
        "nakshatra": moon_details["nakshatra"],
        "yoga": {"number": yoga_index + 1, "name": YOGA_NAMES[yoga_index]},
        "vara": {
            "name": weekday_name,
            "lord": weekday_lord,
            "basis": "civil weekday at the supplied UTC offset; sunrise rollover is not inferred",
        },
    }


def calculate_sidereal_chart(
    timestamp: str,
    latitude: float,
    longitude: float,
    *,
    label: str = "Chart",
) -> dict[str, Any]:
    """Calculate a geocentric Lahiri sidereal Rashi chart and core panchanga factors."""
    _validate_location(latitude, longitude)
    local_moment = parse_timestamp(timestamp)
    utc_moment = local_moment.astimezone(timezone.utc)
    jd_ut = _julian_day(local_moment)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    positions: dict[str, dict[str, Any]] = {}
    return_flags: list[int] = []
    raw_positions: dict[str, tuple[float, float, float]] = {}
    for graha, body_id in _GRAHA_IDS:
        try:
            values, actual_flags = swe.calc_ut(jd_ut, body_id, flags)
        except swe.Error as exc:
            raise ValueError(f"Swiss Ephemeris could not calculate {graha}: {exc}") from exc
        raw_positions[graha] = (values[0] % 360.0, values[1], values[3])
        return_flags.append(actual_flags)

    try:
        _, ascmc = swe.houses_ex(
            jd_ut,
            latitude,
            longitude,
            b"W",
            swe.FLG_SIDEREAL,
        )
    except swe.Error as exc:
        raise ValueError(f"Swiss Ephemeris could not calculate the ascendant: {exc}") from exc
    ascendant_longitude = ascmc[swe.ASC] % 360.0
    ascendant_sign = int(ascendant_longitude // 30.0)

    for graha, (body_longitude, body_latitude, speed) in raw_positions.items():
        details = _longitude_details(body_longitude)
        sign_index = details["rashi"]["index"] - 1
        details.update(
            {
                "latitude": round(body_latitude, 6),
                "speed_degrees_per_day": round(speed, 6),
                "motion": "retrograde" if speed < 0.0 else "direct",
                "house": ((sign_index - ascendant_sign) % 12) + 1,
                "dignity": _dignity(graha, sign_index),
                "navamsha": _navamsha(body_longitude),
            }
        )
        positions[graha] = details

    rahu = positions["Rahu"]
    ketu_longitude = (float(rahu["longitude"]) + 180.0) % 360.0
    ketu = _longitude_details(ketu_longitude)
    ketu_sign = ketu["rashi"]["index"] - 1
    ketu.update(
        {
            "latitude": round(-float(rahu["latitude"]), 6),
            "speed_degrees_per_day": rahu["speed_degrees_per_day"],
            "motion": rahu["motion"],
            "house": ((ketu_sign - ascendant_sign) % 12) + 1,
            "dignity": "not_assigned",
            "navamsha": _navamsha(ketu_longitude),
        }
    )
    positions["Ketu"] = ketu

    houses = []
    for house_number in range(1, 13):
        sign_index = (ascendant_sign + house_number - 1) % 12
        houses.append(
            {
                "number": house_number,
                "rashi": _rashi_details(sign_index),
                "occupants": [
                    graha for graha, placement in positions.items() if placement["house"] == house_number
                ],
            }
        )

    ascendant = _longitude_details(ascendant_longitude)
    ascendant["navamsha"] = _navamsha(ascendant_longitude)
    return {
        "label": label,
        "input": {
            "timestamp": local_moment.isoformat(),
            "timestamp_utc": utc_moment.isoformat().replace("+00:00", "Z"),
            "latitude": latitude,
            "longitude": longitude,
        },
        "julian_day_ut": round(jd_ut, 8),
        "ayanamsha": {
            "name": "Lahiri (Chitrapaksha)",
            "degrees": round(swe.get_ayanamsa_ut(jd_ut), 6),
        },
        "ascendant": ascendant,
        "grahas": positions,
        "houses": houses,
        "panchanga": _panchanga(
            local_moment,
            raw_positions["Sun"][0],
            raw_positions["Moon"][0],
        ),
        "calculation": {
            "zodiac": "sidereal",
            "ayanamsha": "Lahiri",
            "house_system": "whole sign",
            "node": "true lunar node; Ketu exactly opposite",
            "planet_frame": "geocentric ecliptic",
            "ephemeris": _ephemeris_name(return_flags),
            "ephemeris_path": _ephemeris_path or "automatic (Moshier fallback when data files are absent)",
        },
    }


def _period_record(lord: str, start: datetime, end: datetime, as_of: datetime) -> dict[str, Any]:
    duration = (end - start).total_seconds()
    progress = (as_of - start).total_seconds() / duration * 100.0
    return {
        "lord": lord,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "progress_percent": round(max(0.0, min(progress, 100.0)), 3),
    }


def _find_subperiod(
    parent_lord: str,
    parent_start: datetime,
    parent_end: datetime,
    as_of: datetime,
) -> tuple[dict[str, Any], datetime, datetime]:
    start_index = DASHA_SEQUENCE.index(parent_lord)
    cursor = parent_start
    parent_duration = parent_end - parent_start
    for offset in range(9):
        lord = DASHA_SEQUENCE[(start_index + offset) % 9]
        end = cursor + parent_duration * (DASHA_YEARS[lord] / 120.0)
        if as_of < end or offset == 8:
            return _period_record(lord, cursor, end, as_of), cursor, end
        cursor = end
    raise RuntimeError("unreachable Vimshottari subperiod state")


def calculate_vimshottari_dasha(
    birth_timestamp: str,
    moon_longitude: float,
    as_of_timestamp: str,
) -> dict[str, Any]:
    """Calculate active Vimshottari maha, antar, and pratyantar dashas."""
    birth = parse_timestamp(birth_timestamp, "birth_timestamp").astimezone(timezone.utc)
    as_of = parse_timestamp(as_of_timestamp, "as_of_timestamp").astimezone(timezone.utc)
    if as_of < birth:
        raise ValueError("as_of_timestamp must not be before birth_timestamp")

    moon = moon_longitude % 360.0
    nakshatra_index = min(int(moon // NAKSHATRA_SPAN), 26)
    birth_lord = DASHA_SEQUENCE[nakshatra_index % 9]
    fraction_elapsed = (moon % NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    birth_lord_days = DASHA_YEARS[birth_lord] * VIMSHOTTARI_YEAR_DAYS
    first_start = birth - timedelta(days=birth_lord_days * fraction_elapsed)

    cursor = first_start
    lord_index = DASHA_SEQUENCE.index(birth_lord)
    major_lord = birth_lord
    major_start = cursor
    major_end = cursor
    sequence: list[dict[str, Any]] = []
    for offset in range(36):
        lord = DASHA_SEQUENCE[(lord_index + offset) % 9]
        end = cursor + timedelta(days=DASHA_YEARS[lord] * VIMSHOTTARI_YEAR_DAYS)
        if end > birth and len(sequence) < 12:
            sequence.append({"lord": lord, "start": cursor.isoformat(), "end": end.isoformat()})
        if cursor <= as_of < end:
            major_lord, major_start, major_end = lord, cursor, end
            break
        cursor = end
    else:
        raise ValueError("as_of_timestamp is outside the supported 360-year dasha window")

    antar, antar_start, antar_end = _find_subperiod(major_lord, major_start, major_end, as_of)
    pratyantar, _, _ = _find_subperiod(antar["lord"], antar_start, antar_end, as_of)
    birth_balance_end = first_start + timedelta(days=birth_lord_days)
    return {
        "system": "Vimshottari, 120-year cycle",
        "year_length_days": VIMSHOTTARI_YEAR_DAYS,
        "birth_nakshatra": NAKSHATRAS[nakshatra_index],
        "birth_balance": {
            "lord": birth_lord,
            "remaining_years": round((birth_balance_end - birth).total_seconds() / 86400.0 / VIMSHOTTARI_YEAR_DAYS, 6),
            "ends": birth_balance_end.isoformat(),
        },
        "active": {
            "mahadasha": _period_record(major_lord, major_start, major_end, as_of),
            "antardasha": antar,
            "pratyantardasha": pratyantar,
        },
        "major_period_timeline": sequence,
    }
