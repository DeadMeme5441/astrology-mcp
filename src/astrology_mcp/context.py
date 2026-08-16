"""Question-aware natal, dasha, and gochara context assembly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .calculations import calculate_sidereal_chart, calculate_vimshottari_dasha, parse_timestamp
from .constants import QUESTION_DOMAINS

_FULL_ASPECTS = {
    "Sun": (7,),
    "Moon": (7,),
    "Mars": (4, 7, 8),
    "Mercury": (7,),
    "Jupiter": (5, 7, 9),
    "Venus": (7,),
    "Saturn": (3, 7, 10),
    "Rahu": (7,),
    "Ketu": (7,),
}

_GENERAL_HOUSES = (1, 5, 9, 10)
_GENERAL_GRAHAS = ("Sun", "Moon", "Jupiter", "Saturn")


def _detect_domain(question: str) -> tuple[str, tuple[int, ...], tuple[str, ...]]:
    lowered = question.casefold()
    scores: dict[str, int] = {}
    for domain, definition in QUESTION_DOMAINS.items():
        keywords = (str(keyword) for keyword in definition["keywords"])
        scores[domain] = sum(keyword in lowered for keyword in keywords)
    domain = max(scores, key=lambda name: scores[name]) if scores and max(scores.values()) > 0 else "general"
    if domain == "general":
        return domain, _GENERAL_HOUSES, _GENERAL_GRAHAS
    definition = QUESTION_DOMAINS[domain]
    houses = tuple(int(number) for number in definition["houses"])
    grahas = tuple(str(graha) for graha in definition["grahas"])
    return domain, houses, grahas


def _house_from(sign_index: int, reference_sign_index: int) -> int:
    return ((sign_index - reference_sign_index) % 12) + 1


def _transit_evidence(
    natal: dict[str, Any],
    transit: dict[str, Any],
) -> dict[str, Any]:
    natal_asc_sign = natal["ascendant"]["rashi"]["index"] - 1
    natal_moon_sign = natal["grahas"]["Moon"]["rashi"]["index"] - 1
    snapshot: dict[str, dict[str, Any]] = {}
    contacts: list[dict[str, Any]] = []

    for graha, placement in transit["grahas"].items():
        transit_sign = placement["rashi"]["index"] - 1
        snapshot[graha] = {
            "rashi": placement["rashi"],
            "degree_in_sign": placement["degree_in_sign"],
            "motion": placement["motion"],
            "house_from_natal_lagna": _house_from(transit_sign, natal_asc_sign),
            "house_from_natal_moon": _house_from(transit_sign, natal_moon_sign),
        }
        for natal_graha, natal_placement in natal["grahas"].items():
            natal_sign = natal_placement["rashi"]["index"] - 1
            ordinal = _house_from(natal_sign, transit_sign)
            if ordinal == 1:
                contacts.append(
                    {
                        "transit_graha": graha,
                        "natal_graha": natal_graha,
                        "relationship": "same-sign conjunction",
                    }
                )
            elif ordinal in _FULL_ASPECTS[graha]:
                contacts.append(
                    {
                        "transit_graha": graha,
                        "natal_graha": natal_graha,
                        "relationship": f"full sign-based graha drishti ({ordinal} from transit)",
                    }
                )

    saturn_from_moon = snapshot["Saturn"]["house_from_natal_moon"]
    sade_sati_phase = {12: "rising", 1: "middle", 2: "setting"}.get(saturn_from_moon)
    return {
        "grahas": snapshot,
        "sign_based_contacts": contacts,
        "sade_sati": {
            "active": sade_sati_phase is not None,
            "phase": sade_sati_phase,
            "basis": "Saturn in the 12th, 1st, or 2nd sign from the natal Moon",
        },
        "aspect_method": (
            "Whole-sign conjunctions and Parashari full graha drishti: all grahas 7th; "
            "Mars also 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th. "
            "Only the 7th is used for Rahu/Ketu because additional node aspects are tradition-dependent."
        ),
    }


def _focus_evidence(
    natal: dict[str, Any],
    transit_evidence: dict[str, Any],
    dasha: dict[str, Any],
    focus_houses: tuple[int, ...],
    focus_grahas: tuple[str, ...],
) -> dict[str, Any]:
    house_records = []
    for number in focus_houses:
        house = natal["houses"][number - 1]
        lord = house["rashi"]["lord"]
        lord_placement = natal["grahas"][lord]
        house_records.append(
            {
                "house": number,
                "rashi": house["rashi"],
                "occupants": house["occupants"],
                "lord": lord,
                "lord_natal_house": lord_placement["house"],
                "lord_dignity": lord_placement["dignity"],
            }
        )

    active_lords = []
    for level in ("mahadasha", "antardasha", "pratyantardasha"):
        period = dasha["active"][level]
        lord = period["lord"]
        natal_placement = natal["grahas"][lord]
        active_lords.append(
            {
                "level": level,
                **period,
                "natal_house": natal_placement["house"],
                "natal_rashi": natal_placement["rashi"],
                "natal_dignity": natal_placement["dignity"],
                "transit": transit_evidence["grahas"][lord],
            }
        )

    relevant_transits = []
    for graha in ("Jupiter", "Saturn", "Rahu", "Ketu"):
        placement = transit_evidence["grahas"][graha]
        aspects_focus = [
            house
            for house in focus_houses
            if _house_from(
                (natal["ascendant"]["rashi"]["index"] - 1 + house - 1) % 12,
                placement["rashi"]["index"] - 1,
            )
            in _FULL_ASPECTS[graha]
        ]
        if placement["house_from_natal_lagna"] in focus_houses or aspects_focus:
            relevant_transits.append(
                {
                    "graha": graha,
                    **placement,
                    "focus_houses_aspected": aspects_focus,
                }
            )

    return {
        "houses": house_records,
        "natural_significators": [
            {
                "graha": graha,
                "natal_house": natal["grahas"][graha]["house"],
                "natal_rashi": natal["grahas"][graha]["rashi"],
                "dignity": natal["grahas"][graha]["dignity"],
            }
            for graha in focus_grahas
        ],
        "active_dasha_lords": active_lords,
        "slow_transits_touching_focus_houses": relevant_transits,
    }


def calculate_person_context(
    birth_timestamp: str,
    birth_latitude: float,
    birth_longitude: float,
    question: str,
    *,
    as_of_timestamp: str | None = None,
    current_latitude: float | None = None,
    current_longitude: float | None = None,
    birth_time_accuracy_minutes: float | None = None,
) -> dict[str, Any]:
    """Build the evidence an agent needs for a time-specific Jyotisha response."""
    if not question.strip():
        raise ValueError("question must not be empty")
    if birth_time_accuracy_minutes is not None and birth_time_accuracy_minutes < 0:
        raise ValueError("birth_time_accuracy_minutes cannot be negative")
    if (current_latitude is None) != (current_longitude is None):
        raise ValueError("current_latitude and current_longitude must be supplied together")

    birth_moment = parse_timestamp(birth_timestamp, "birth_timestamp")
    if as_of_timestamp is None:
        as_of_moment = datetime.now(timezone.utc)
        as_of_timestamp = as_of_moment.isoformat()
    else:
        as_of_moment = parse_timestamp(as_of_timestamp, "as_of_timestamp")
    if as_of_moment.astimezone(timezone.utc) < birth_moment.astimezone(timezone.utc):
        raise ValueError("as_of_timestamp must not be before birth_timestamp")

    transit_latitude = birth_latitude if current_latitude is None else current_latitude
    transit_longitude = birth_longitude if current_longitude is None else current_longitude
    natal = calculate_sidereal_chart(
        birth_timestamp,
        birth_latitude,
        birth_longitude,
        label="Natal chart",
    )
    transit = calculate_sidereal_chart(
        as_of_timestamp,
        transit_latitude,
        transit_longitude,
        label="Transit chart",
    )
    dasha = calculate_vimshottari_dasha(
        birth_timestamp,
        natal["grahas"]["Moon"]["longitude"],
        as_of_timestamp,
    )
    transits = _transit_evidence(natal, transit)
    domain, focus_houses, focus_grahas = _detect_domain(question)
    focus = _focus_evidence(natal, transits, dasha, focus_houses, focus_grahas)

    cautions = [
        "Astrology is an interpretive tradition, not a scientifically validated predictive method.",
        "Treat timing as a window and tendency, never as certainty or guaranteed causation.",
    ]
    if birth_time_accuracy_minutes is None:
        cautions.append(
            "Birth-time accuracy was not supplied; ascendant, houses, and divisional placements may be less reliable."
        )
    elif birth_time_accuracy_minutes > 15:
        cautions.append(
            "The stated birth-time uncertainty exceeds 15 minutes; prioritize Moon, dasha, and sign-level factors over exact houses."
        )
    if domain == "health":
        cautions.append("Do not use this context to diagnose, treat, or delay professional medical care.")
    if domain == "finance":
        cautions.append("Do not present this context as individualized financial or investment advice.")

    return {
        "question": question,
        "as_of": as_of_moment.isoformat(),
        "detected_domain": domain,
        "focus_houses": list(focus_houses),
        "natal_chart": natal,
        "current_chart": transit,
        "vimshottari_dasha": dasha,
        "transit_analysis": transits,
        "question_focus": focus,
        "agent_reading_order": [
            "Establish natal promise from the relevant houses, their lords, occupants, dignity, and natural significators.",
            "Use mahadasha, antardasha, and pratyantardasha to determine which natal promises are active.",
            "Use current Jupiter, Saturn, Rahu, and Ketu transits plus dasha-lord transits for timing; do not let a transit invent a natal promise.",
            "State corroborating and conflicting factors, identify the time window, and calibrate confidence to birth-time accuracy.",
            "Answer the human's actual question in plain language; separate calculated facts from interpretation and practical advice.",
        ],
        "cautions": cautions,
    }
