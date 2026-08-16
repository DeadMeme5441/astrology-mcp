"""FastMCP server exposing calculated Jyotisha evidence to agents."""

from __future__ import annotations

import argparse
import json
import os
from importlib.resources import files
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__
from .calculations import calculate_sidereal_chart
from .context import calculate_person_context
from .geocoding import resolve_birth_location
from .profiles import (
    calculate_profile_context,
    delete_birth_profile,
    list_birth_profiles,
    save_birth_profile,
)

_SERVER_INSTRUCTIONS = """
Normal conversation workflow:
1. When a human asks about themselves, call list_birth_profiles.
2. If the intended profile exists, call ask_astrology with their question. Do not ask them to repeat
   birth data and do not call the advanced get_person_context tool.
3. If no profile exists, conversationally obtain birth date, exact local clock time, and birthplace.
   Call resolve_birth_location, verify the address (ask only if genuinely ambiguous), then call
   save_birth_profile. It resolves the historical IANA timezone and UTC offset offline. The human
   should never need to supply coordinates, timezone syntax, JSON, or tool names.
4. After saving, answer through ask_astrology. Use profile name "me" unless the human requests another.
Never infer coordinates, choose an ambiguous place, or invent a clock-change occurrence. Read
astrology://reference/guide before interpretation. Calculated placements are facts; predictions are
tradition-dependent interpretations. Cite relevant natal factors, dashas, and transits; state
uncertainty; never replace medical, legal, financial, or safety advice.
""".strip()

mcp = FastMCP(
    "Indian Astrology (Jyotisha)",
    instructions=_SERVER_INSTRUCTIONS,
    host=os.environ.get("ASTROLOGY_MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("ASTROLOGY_MCP_PORT", "8000")),
)

_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

_READ_ONLY_NETWORK = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_READ_CURRENT_CONTEXT = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

_WRITE_LOCAL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

_DELETE_LOCAL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


@mcp.tool(
    name="resolve_birth_location",
    title="Resolve a birth or current place to coordinates",
    description=(
        "Convert a human-supplied birthplace or current place into up to five coordinate candidates "
        "using Nominatim/OpenStreetMap. This purpose-limited lookup is not for autocomplete or bulk "
        "geocoding. Inspect display_name and address; if candidates are ambiguous, ask the human. "
        "The query is sent to the configured external geocoder and must not contain private data."
    ),
    annotations=_READ_ONLY_NETWORK,
    structured_output=True,
)
def resolve_birth_location_tool(
    query: str,
    country_codes: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Args:
        query: Birth/current place name, preferably neighbourhood, city, state, and country.
            Do not include a person's name or exact private residential address.
        country_codes: Optional comma-separated ISO alpha-2 filter, such as ``in`` or ``gb,ie``.
        limit: Maximum candidates from 1 to 5. Results are not an autocomplete feed.
    """
    return resolve_birth_location(query, country_codes=country_codes, limit=limit)

@mcp.tool(
    name="list_birth_profiles",
    title="Check locally saved birth profiles",
    description=(
        "First tool for normal personal conversation. Lists local profile names and place labels. "
        "If the intended profile exists, immediately use ask_astrology; otherwise collect birth date, "
        "exact local time, and birthplace and complete onboarding."
    ),
    annotations=_READ_ONLY,
    structured_output=True,
)
def list_birth_profiles_tool() -> dict[str, Any]:
    return list_birth_profiles()


@mcp.tool(
    name="save_birth_profile",
    title="Save a private local birth profile",
    description=(
        "Save birth details once so the human never repeats them. Call resolve_birth_location first, "
        "then pass its confirmed coordinates with YYYY-MM-DD date and 24-hour local time. Historical "
        "timezone and UTC offset are resolved offline. Data stays in the user's local data directory."
    ),
    annotations=_WRITE_LOCAL,
    structured_output=True,
)
def save_birth_profile_tool(
    birth_date: str,
    birth_time: str,
    birth_place: str,
    latitude: float,
    longitude: float,
    profile_name: str = "me",
    birth_time_accuracy_minutes: float | None = None,
    fold: int | None = None,
) -> dict[str, Any]:
    """
    Args:
        birth_date: Calendar birth date in YYYY-MM-DD format.
        birth_time: Exact local 24-hour clock time as HH:MM or HH:MM:SS.
        birth_place: Confirmed human-readable place label from the location result.
        latitude: Confirmed birthplace latitude.
        longitude: Confirmed birthplace longitude.
        profile_name: Local profile name, normally ``me``.
        birth_time_accuracy_minutes: Optional plus/minus uncertainty in minutes.
        fold: For a repeated daylight-saving clock time only: 0 for first or 1 for second occurrence.
    """
    return save_birth_profile(
        profile_name,
        birth_date,
        birth_time,
        birth_place,
        latitude,
        longitude,
        birth_time_accuracy_minutes=birth_time_accuracy_minutes,
        fold=fold,
    )


@mcp.tool(
    name="ask_astrology",
    title="Answer a question using a saved birth profile",
    description=(
        "Primary tool after onboarding. Requires only the human's question; loads their private local "
        "birth profile and combines it with the current time, Vimshottari dasha, and transits. "
        "Omit as_of_timestamp for now."
    ),
    annotations=_READ_CURRENT_CONTEXT,
    structured_output=True,
)
def ask_astrology_tool(
    question: str,
    profile_name: str = "me",
    as_of_timestamp: str | None = None,
    current_latitude: float | None = None,
    current_longitude: float | None = None,
) -> dict[str, Any]:
    return calculate_profile_context(
        question,
        profile_name=profile_name,
        as_of_timestamp=as_of_timestamp,
        current_latitude=current_latitude,
        current_longitude=current_longitude,
    )


@mcp.tool(
    name="delete_birth_profile",
    title="Delete a private local birth profile",
    description=(
        "Permanently delete one saved birth profile. Use only when the human explicitly asks to "
        "forget or delete that profile."
    ),
    annotations=_DELETE_LOCAL,
    structured_output=True,
)
def delete_birth_profile_tool(profile_name: str = "me") -> dict[str, Any]:
    return delete_birth_profile(profile_name)


@mcp.tool(
    name="calculate_chart",
    title="Calculate a Lahiri sidereal chart",
    description=(
        "Calculate a standalone Indian astrology Rashi chart, D9 placements, and panchanga "
        "factors for an exact offset-aware time and Earth location. Use get_person_context "
        "instead for a person's time-specific question."
    ),
    annotations=_READ_ONLY,
    structured_output=True,
)
def calculate_chart_tool(
    timestamp: str,
    latitude: float,
    longitude: float,
    label: str = "Chart",
) -> dict[str, Any]:
    """
    Args:
        timestamp: ISO-8601 local time with explicit UTC offset, such as
            ``1990-05-17T14:30:00+05:30``. A naive local time is rejected.
        latitude: Decimal degrees, north positive and south negative.
        longitude: Decimal degrees, east positive and west negative.
        label: Human-readable chart label included in the result.
    """
    return calculate_sidereal_chart(timestamp, latitude, longitude, label=label)


@mcp.tool(
    name="get_person_context",
    title="Build question-aware Jyotisha context",
    description=(
        "Advanced stateless tool for callers that already manage exact birth data. Combines the natal "
        "chart, reading-time chart, Vimshottari dashas, gochara from natal lagna and Moon, Sade Sati, "
        "and question-specific houses. For ordinary conversation with a saved profile, always use "
        "ask_astrology instead."
    ),
    annotations=_READ_ONLY,
    structured_output=True,
)
def get_person_context_tool(
    birth_timestamp: str,
    birth_latitude: float,
    birth_longitude: float,
    question: str,
    as_of_timestamp: str | None = None,
    current_latitude: float | None = None,
    current_longitude: float | None = None,
    birth_time_accuracy_minutes: float | None = None,
) -> dict[str, Any]:
    """
    Args:
        birth_timestamp: Birth local time as ISO-8601 with the historical UTC offset.
        birth_latitude: Birthplace latitude in decimal degrees; north is positive.
        birth_longitude: Birthplace longitude in decimal degrees; east is positive.
        question: The human's actual question. It selects relevant houses and karakas.
        as_of_timestamp: Reading/transit time with UTC offset. Omit only when now is intended.
        current_latitude: Optional present latitude, supplied together with current_longitude.
        current_longitude: Optional present longitude, supplied together with current_latitude.
        birth_time_accuracy_minutes: Optional known plus/minus uncertainty of the birth time.
    """
    return calculate_person_context(
        birth_timestamp,
        birth_latitude,
        birth_longitude,
        question,
        as_of_timestamp=as_of_timestamp,
        current_latitude=current_latitude,
        current_longitude=current_longitude,
        birth_time_accuracy_minutes=birth_time_accuracy_minutes,
    )


@mcp.resource(
    "astrology://reference/guide",
    name="jyotisha-reference-guide",
    title="Agent reference for Lahiri Jyotisha readings",
    description=(
        "Calculation contract, interpretation hierarchy, graha/rashi/house/nakshatra references, "
        "question focus, data-quality rules, and safe answer protocol."
    ),
    mime_type="text/markdown",
)
def reference_guide() -> str:
    """Return the packaged agent interpretation guide."""
    return files("astrology_mcp").joinpath("reference.md").read_text(encoding="utf-8")


@mcp.prompt(
    name="personal_jyotisha_reading",
    title="Answer a personal question with calculated Jyotisha context",
    description=(
        "A complete agent workflow that requires exact birth data, current-time context, "
        "calculated evidence, calibrated interpretation, and practical safeguards."
    ),
)
def personal_jyotisha_reading_prompt(
    question: str,
    profile_name: str = "me",
    birth_date: str = "",
    birth_time: str = "",
    birth_location: str = "",
    as_of_timestamp: str = "now",
) -> str:
    """Construct a conversational onboarding-or-reading workflow."""
    supplied_birth_data = all(
        value.strip() for value in (birth_date, birth_time, birth_location)
    )
    if supplied_birth_data:
        onboarding = (
            f"Resolve {birth_location!r} with resolve_birth_location, verify the matching address, then "
            f"save profile {profile_name!r} with birth_date={birth_date!r}, birth_time={birth_time!r}, "
            "and the confirmed coordinates. The save tool resolves the historical timezone offline."
        )
    else:
        onboarding = (
            f"Call list_birth_profiles. If profile {profile_name!r} does not exist, ask conversationally "
            "for birth date, exact local clock time, and birthplace, then resolve and save it. Do not ask "
            "the human for coordinates, a UTC offset, JSON, or tool syntax."
        )
    as_of_instruction = (
        "Omit as_of_timestamp so ask_astrology uses the current instant."
        if as_of_timestamp.strip().casefold() == "now"
        else f"Pass as_of_timestamp={as_of_timestamp!r}."
    )
    return f"""Answer this human naturally through a calculated Jyotisha lens.

Question: {question}
Profile: {profile_name}

Workflow:
1. Read astrology://reference/guide.
2. {onboarding}
3. Call ask_astrology with question={question!r} and profile_name={profile_name!r}.
   {as_of_instruction}
4. Answer in plain language: direct answer; natal basis; active dasha/transit evidence; timing;
   practical agency and limits. Never expose raw tool mechanics unless the human asks.
5. Treat calculations as facts but astrology as a non-scientific interpretive tradition. Never invent
   missing factors or replace medical, legal, financial, or safety-critical judgment.
"""


def main() -> None:
    """Run the MCP server over stdio by default."""
    parser = argparse.ArgumentParser(description="Lahiri Jyotisha MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http", "sse"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="print a generic stdio MCP client configuration and exit",
    )
    parser.add_argument("--version", action="version", version=f"astrology-mcp {__version__}")
    args = parser.parse_args()
    if args.print_config:
        print(
            json.dumps(
                {
                    "mcpServers": {
                        "astrology": {
                            "command": "astrology-mcp",
                            "args": [],
                        }
                    }
                },
                indent=2,
            )
        )
        return
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
