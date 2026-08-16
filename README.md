# astrology-mcp

**Install once, share birth details once, then ask ordinary questions.**

`astrology-mcp` is a local Model Context Protocol server for Indian astrology (Jyotisha). It gives agents deterministic Lahiri sidereal calculations, question-aware natal context, Vimshottari dasha, and current gochara instead of a context-free horoscope.

The human speaks naturally. The agent resolves their birthplace, determines the historical timezone, stores a private local profile, and reuses it for future conversations across MCP clients. Calculated evidence is separated from tradition-dependent interpretation through a bundled agent reference guide.

> Astrology is an interpretive tradition, not a scientifically validated predictive method. This server makes the calculation and evidence trail reproducible; it does not make predictions certain.

## What it calculates

- Swiss Ephemeris geocentric graha longitudes, with the Moshier analytical ephemeris as the no-data-file fallback
- Lahiri/Chitrapaksha sidereal zodiac
- Whole-sign houses from the sidereal ascendant
- Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, true Rahu, and opposite Ketu
- Nakshatra, pada, sign dignity, motion, and D9 Navamsha placement
- Tithi, karana, nakshatra, yoga, and civil vara at the requested instant
- Vimshottari mahadasha, antardasha, pratyantardasha, birth balance, and period timeline
- Current placements from natal lagna and Moon, full sign-based Parashari graha drishti, and Sade Sati geometry
- A topic filter for career, relationships, finance, health, education, family/home, spirituality, or general questions
- Purpose-limited, free birth/current-place lookup through Nominatim/OpenStreetMap when coordinates are unknown

Calculation conventions and deliberate exclusions are documented in the MCP resource `astrology://reference/guide`.

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/) for the commands below, or another Python package installer

## Install once, then talk normally

Install the executable once on the machine:

```bash
uv tool install .
astrology-mcp --version
```

When distributed through a package index, the corresponding command is:

```bash
uv tool install astrology-mcp
```

Register that executable once in any stdio-capable MCP client. Generate the generic configuration:

```bash
astrology-mcp --print-config
```

It prints:

```json
{
  "mcpServers": {
    "astrology": {
      "command": "astrology-mcp",
      "args": []
    }
  }
}
```

Claude Desktop, Cursor, VS Code integrations, Codex-compatible clients, and other stdio MCP hosts use this same command even when their settings file or UI differs. MCP clients do not share a global server registry, so each host must be pointed at the executable once. The installed server and saved profiles are machine-wide for the user; birth details do not need to be re-entered in each client.

After registration, the human only talks:

```text
Human: I was born on 22 January 2000 at 9:30 PM in Jayanagar, Bangalore.
Agent:  [resolves the place, calculates the historical timezone, and saves profile “me”]

Human: What should I pay attention to in my career this year?
Agent:  [calls ask_astrology using the saved profile and current time]
```

The human never needs to write JSON, find coordinates, calculate a UTC offset, name an MCP tool, or paste birth details again.

For development without a persistent install:

```bash
uv sync
uv run astrology-mcp
```

The default transport is stdio. Streamable HTTP remains available for managed deployments:

```bash
ASTROLOGY_MCP_HOST=127.0.0.1 ASTROLOGY_MCP_PORT=8000 \
  astrology-mcp --transport streamable-http
```

## Agent contract

MCP clients receive these instructions from the server automatically. An integrating agent should follow the same contract:

1. Start a personal conversation with `list_birth_profiles`.
2. If the intended profile exists, call `ask_astrology` with the human's question. Never ask them to repeat saved birth details.
3. If it does not exist, ask only for birth date, exact local clock time, and ordinary birthplace. The human should not need coordinates, timezone syntax, JSON, or MCP vocabulary.
4. Resolve the place with `resolve_birth_location`; verify the returned address and ask only when candidates are genuinely ambiguous.
5. Save with `save_birth_profile`. Historical timezone and UTC offset resolution happen offline.
6. Read `astrology://reference/guide`, then interpret the structured context returned by `ask_astrology`.
7. Separate calculated facts from interpretation, state conflicting evidence and uncertainty, and never substitute astrology for medical, legal, financial, or safety-critical judgment.

Use `get_person_context` and `calculate_chart` only for advanced stateless integrations. Delete saved data only after an explicit human request.

## MCP interface

### Normal conversational flow

The server instructions teach any MCP-capable agent this sequence:

1. `list_birth_profiles` checks whether the person has already been onboarded.
2. `resolve_birth_location` converts their ordinary birthplace description into candidates. The agent verifies the address and asks only if the result is genuinely ambiguous.
3. `save_birth_profile` accepts a normal calendar date, local clock time, and confirmed coordinates. It resolves the IANA timezone and historical UTC offset offline, then persists the profile locally.
4. `ask_astrology` needs only the question and profile name. It loads birth data and uses the current instant automatically.
5. `delete_birth_profile` runs only when the human explicitly asks the agent to forget a profile.

`me` is the default profile. Other names allow explicitly requested profiles such as `partner`, without mixing charts.

### Free place lookup

`resolve_birth_location` uses the public OpenStreetMap Nominatim service by default. It returns full display names and address components; it never silently decides between ambiguous places. The server identifies itself, serializes requests to one per second, caches 256 queries in memory, returns attribution, and links the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). It is not an autocomplete or bulk-geocoding endpoint.

Override it for private or higher-volume operation:

```bash
export ASTROLOGY_MCP_GEOCODER_URL="https://nominatim.example.com/search"
export ASTROLOGY_MCP_GEOCODER_USER_AGENT="your-application/1.0 contact@example.com"
export ASTROLOGY_MCP_GEOCODER_EMAIL="contact@example.com"
```

### Offline timezone handling

`timezonefinder` maps the confirmed coordinates to an IANA timezone without sending birth data to a service. Python's `zoneinfo` and bundled `tzdata` determine the offset that applied on the birth date. Nonexistent daylight-saving times are rejected. Repeated clock times require the agent to ask whether the birth occurred during the first or second occurrence.

### Advanced/stateless tools

- `get_person_context` accepts complete offset-aware birth data directly for programmatic callers that manage their own profiles.
- `calculate_chart` computes one standalone Rashi/D9 chart and panchanga.

Ordinary agents should use `ask_astrology` after onboarding rather than repeatedly calling these tools.

### Resource and prompt

- `astrology://reference/guide` contains the calculation contract, synthesis hierarchy, interpretive reference, data-quality rules, and answer protocol.
- `personal_jyotisha_reading` handles either first-time conversational onboarding or an existing saved profile.

## Data rules

For saved profiles, the human supplies only a calendar birth date, exact local clock time, and ordinary birthplace description. Timezone and historical offset resolution happen locally after the place is confirmed. Advanced stateless calls still require an explicit offset-aware timestamp.

Profiles are stored in the user's platform data directory as `astrology-mcp/profiles.json`, with owner-only permissions where supported. Set `ASTROLOGY_MCP_DATA_DIR` to choose another local directory. Profiles contain birth data; questions and calculated readings are never persisted. Every client using the same operating-system account sees the same profiles.

Chart, dasha, and timezone calculations run locally. `resolve_birth_location` sends only its place query to the configured geocoder and caches the result in process memory; do not include a person's name, exact private residential address, or confidential information. No chart, timestamp, question, or saved profile is sent.

If `SE_EPHE_PATH` points to Swiss Ephemeris data files, they are used; otherwise each result transparently reports the Moshier analytical fallback.

## Scope and safety

Jyotisha is an interpretive tradition, not a scientifically validated predictive method. Results should be phrased as symbolic tendencies and timing windows, never certainties. The reference prompt prohibits deterministic claims and prohibits substituting astrology for medical, legal, financial, or safety-critical judgment.

The server does not claim to calculate Shadbala, Ashtakavarga, all named yogas, bhava cusps, rectification, sunrise-based vara, a full varga suite, or muhurta. Agents must not invent those factors.

## Dependency licensing

`pyswisseph` declares the GNU Affero General Public License v3 in its package metadata. Swiss Ephemeris is also offered under a commercial professional license. Review those terms before distributing this server or using it in a networked commercial product; this repository does not grant a separate Swiss Ephemeris license.

## Verification

Run the calculation and MCP protocol tests:

```bash
uv run python -m unittest discover -s tests -v
```

Build the installable wheel:

```bash
uv build
```
