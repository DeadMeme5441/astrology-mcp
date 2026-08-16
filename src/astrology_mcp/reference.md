# Agent Reference: Lahiri Jyotisha Context

## Purpose

Use this guide with the server's calculated evidence to answer a human's question through a classical Indian astrology (Jyotisha) lens. The calculations are deterministic; interpretation is a tradition-dependent synthesis, not a scientifically validated prediction. Never turn symbolic indications into certainty.

## Required data and tool order

For ordinary conversation, first call `list_birth_profiles`.

- If the intended profile exists, call `ask_astrology` with the human's question. Do not ask them to repeat birth details.
- If it does not exist, ask naturally for birth date, exact local clock time, and birthplace. The human does not need to know coordinates, UTC offsets, IANA timezone names, JSON, or MCP tool syntax.
- Resolve the birthplace with `resolve_birth_location`. Verify the returned address and ask the human only when plausible candidates are genuinely ambiguous.
- Call `save_birth_profile` with the confirmed coordinates, `YYYY-MM-DD` birth date, and 24-hour local clock time. It determines the IANA timezone and historical UTC offset offline.
- Then call `ask_astrology`. It loads the saved natal data and calculates the current context. Omit `as_of_timestamp` when “now” is intended.
- Use profile name `me` unless the human asks to keep profiles for another person.

The advanced `get_person_context` and `calculate_chart` tools are for stateless/programmatic callers. Do not use them in normal conversation after a profile is saved.

Optional birth-time uncertainty should be saved when known. Optional present location affects the current ascendant and civil panchanga context, but geocentric graha longitudes do not depend on it.

### Saved-profile privacy

Birth profiles are stored only on the user's machine in the platform data directory, under `astrology-mcp/profiles.json`. The directory and file use owner-only permissions where the operating system supports them. Questions and calculated readings are never persisted. Call `delete_birth_profile` only when the human explicitly asks the agent to forget a profile.

The profile stores the confirmed place label, coordinates, local and UTC birth timestamps, resolved IANA timezone, time accuracy, and update time. `ASTROLOGY_MCP_DATA_DIR` can move this storage to another local directory.

### Location lookup policy

`resolve_birth_location` is only for a human-triggered lookup of a birth or current place. It uses the public OpenStreetMap Nominatim endpoint by default. The place query leaves the local machine; never include a person's name, an exact private residential address, or confidential material.

Public Nominatim permits moderate end-user-triggered use but imposes an absolute maximum of one request per second, requires an identifying User-Agent and attribution, and forbids autocomplete, bulk, and systematic querying. The server serializes requests at one per second and maintains a 256-query in-memory cache. Every result returns the attribution and [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). For larger or commercial workloads, configure another Nominatim-compatible endpoint with `ASTROLOGY_MCP_GEOCODER_URL` or operate a private instance.

## Calculation contract

The server uses these fixed conventions so that readings are reproducible:

- Swiss Ephemeris through `pyswisseph`; Moshier analytical ephemeris is the transparent fallback when external Swiss data files are absent.
- Universal Time conversion from the explicit input offset.
- Geocentric ecliptic graha positions.
- Sidereal zodiac with Lahiri/Chitrapaksha ayanamsha.
- Whole-sign houses from the sidereal ascendant.
- Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, true Rahu, and Ketu exactly opposite Rahu.
- Twenty-seven equal nakshatras of 13°20′, each divided into four padas of 3°20′.
- Vimshottari dasha: 120-year sequence, 365.2425 days per dasha year, balance determined by the Moon's progress through its birth nakshatra.
- D9 Navamsha placements for the ascendant and grahas.
- Parashari full graha drishti by sign: every graha aspects the 7th; Mars also 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th. Only the 7th is assigned to Rahu/Ketu because extra node aspects vary by lineage.
- Panchanga tithi, nakshatra, yoga, and karana are angular calculations at the instant. Vara is the civil weekday at the supplied offset; the tool does not infer a local sunrise rollover.

Do not claim that the server calculated Shadbala, Ashtakavarga, bhava cusps, Arudha, combustion, planetary war, every named yoga, a full divisional-chart suite, rectification, sunrise, or muhurta. They are outside the returned contract.

## The synthesis hierarchy: what matters

Follow this order. A later layer times or activates an earlier layer; it does not replace it.

### 1. Natal promise

For the topic's houses:

- Read the whole-sign rashi on each house.
- Locate the house lord by natal house, rashi, dignity, and nakshatra.
- Note occupants and their functional role from this specific lagna.
- Add the natural significator (karaka).
- Look for repetition. One isolated factor is weak evidence; the same topic repeated through house, lord, karaka, and dasha is stronger.

A planet in an exalted or own sign has sign-level support, but dignity is not a complete strength score. A debilitated planet is not a verdict: lordship, placement, aspects, dasha, and cancellation conditions can modify expression. The tool deliberately labels only sign dignity.

### 2. Dasha activation

Read mahadasha as the broad chapter, antardasha as the active subtheme, and pratyantardasha as the narrower trigger. For every active lord, check:

- Houses owned from the natal lagna.
- Natal house occupied.
- Sign dignity and conjunctions/aspects in the natal chart.
- Current transit from lagna and Moon.

Prefer events or themes that connect both active dasha lords to the question's houses. Quote exact dasha start/end timestamps from the tool when naming a window.

### 3. Gochara timing

Start with slow transits: Saturn, Jupiter, Rahu, and Ketu. Then inspect transits of active dasha lords. Read each from natal lagna and natal Moon. Use sign entry and period boundaries as windows, not single deterministic event dates.

A transit is more relevant when it:

- Occupies or fully aspects a topic house.
- Conjoins or aspects its natal lord or karaka by sign.
- Repeats a dasha theme.
- Occurs while the corresponding natal promise is active.

Sade Sati means Saturn is in the 12th, 1st, or 2nd sign from the natal Moon. The returned `active` flag is a geometric condition, not a declaration of misfortune.

### 4. Panchanga and short-term context

Use panchanga for the quality of the supplied instant, not as a replacement for natal/dasha evidence. The current chart's rapidly moving ascendant and Moon need precise time and current location. Do not call the civil vara a sunrise-based traditional vara.

## Core significations

### Grahas

| Graha | Core significations | Constructive expression | Pressured expression |
|---|---|---|---|
| Sun | vitality, authority, identity, father, visibility | clarity, leadership, integrity | pride, conflict with authority, depletion |
| Moon | mind, feeling, mother, public, nourishment | receptivity, steadiness, care | fluctuation, reactivity, insecurity |
| Mars | action, courage, engineering, conflict, siblings | initiative, precision, protection | haste, anger, injury, dispute |
| Mercury | speech, analysis, trade, learning, skill | adaptability, discrimination, communication | nervousness, inconsistency, over-analysis |
| Jupiter | counsel, wisdom, children, growth, dharma | judgment, generosity, expansion | excess, dogma, misplaced optimism |
| Venus | relationship, pleasure, art, vehicles, agreements | harmony, affection, refinement | indulgence, dependency, compromised values |
| Saturn | time, duty, labor, limits, endurance | discipline, maturity, durable results | delay, fear, isolation, rigidity |
| Rahu | appetite, foreignness, amplification, disruption | innovation, crossing boundaries, worldly reach | obsession, distortion, instability |
| Ketu | separation, insight, past mastery, release | discernment, inwardness, liberation | withdrawal, fragmentation, dissatisfaction |

Rahu and Ketu do not own signs in the calculation output. Their dispositors—the lords of the rashis they occupy—are essential interpretive links.

### Houses

| House | Main topics |
|---|---|
| 1 | body, identity, vitality, approach, overall life direction |
| 2 | family, accumulated resources, speech, food, values |
| 3 | courage, effort, skills, writing, siblings, short journeys |
| 4 | home, mother, property, education, inner contentment |
| 5 | intelligence, creativity, children, counsel, mantra, speculation |
| 6 | service, work routines, illness, debt, conflict, competition |
| 7 | partnership, marriage, contracts, clients, public exchange |
| 8 | vulnerability, longevity, inheritance, crisis, research, transformation |
| 9 | dharma, teachers, father, fortune, higher learning, long journeys |
| 10 | action in the world, profession, status, responsibility |
| 11 | gains, networks, elder siblings, ambitions, fulfillment |
| 12 | expenditure, sleep, retreat, foreign residence, loss, liberation |

House categories are relational, not simply good/bad. The 3rd, 6th, 10th, and 11th are upachaya houses where sustained effort can improve outcomes. The 6th, 8th, and 12th can describe difficulty but also service, research, surrender, or release.

### Rashis

| Rashi | Mode and element | Reading key |
|---|---|---|
| Mesha / Aries | movable fire | initiating, direct, urgent |
| Vrishabha / Taurus | fixed earth | sustaining, material, stabilizing |
| Mithuna / Gemini | dual air | exchanging, classifying, connecting |
| Karka / Cancer | movable water | protecting, feeling, belonging |
| Simha / Leo | fixed fire | expressing, leading, centering |
| Kanya / Virgo | dual earth | analyzing, correcting, serving |
| Tula / Libra | movable air | balancing, negotiating, relating |
| Vrishchika / Scorpio | fixed water | penetrating, guarding, transforming |
| Dhanu / Sagittarius | dual fire | seeking, teaching, orienting |
| Makara / Capricorn | movable earth | structuring, working, accomplishing |
| Kumbha / Aquarius | fixed air | systematizing, distributing, reforming |
| Meena / Pisces | dual water | integrating, imagining, releasing |

Use the rashi as the manner and environment of expression. Use its lord's condition to understand how that environment functions.

### Nakshatras and rulers

The ruler sequence repeats Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury:

| Nakshatra | Ruler | Concise interpretive field |
|---|---|---|
| Ashwini | Ketu | swift beginnings, remedy, movement |
| Bharani | Venus | bearing, restraint, consequence |
| Krittika | Sun | cutting, purification, discernment |
| Rohini | Moon | growth, fertility, attraction |
| Mrigashira | Mars | seeking, curiosity, movement |
| Ardra | Rahu | storm, intensity, reorganization |
| Punarvasu | Jupiter | return, renewal, restoration |
| Pushya | Saturn | nourishment, duty, cultivation |
| Ashlesha | Mercury | binding, strategy, penetration |
| Magha | Ketu | ancestors, authority, inheritance |
| Purva Phalguni | Venus | pleasure, creativity, union |
| Uttara Phalguni | Sun | agreement, patronage, continuity |
| Hasta | Moon | skill, shaping, practical control |
| Chitra | Mars | design, brilliance, construction |
| Swati | Rahu | independence, trade, dispersal |
| Vishakha | Jupiter | branching goals, determination |
| Anuradha | Saturn | devotion, friendship, order |
| Jyeshtha | Mercury | seniority, protection, complexity |
| Mula | Ketu | roots, dismantling, investigation |
| Purva Ashadha | Venus | declaration, invigoration, persuasion |
| Uttara Ashadha | Sun | durable victory, responsibility |
| Shravana | Moon | listening, learning, transmission |
| Dhanishtha | Mars | rhythm, resources, contribution |
| Shatabhisha | Rahu | systems, healing, concealment |
| Purva Bhadrapada | Jupiter | intensity, ideals, commitment |
| Uttara Bhadrapada | Saturn | depth, stability, containment |
| Revati | Mercury | guidance, completion, safe passage |

Do not reduce a graha to its nakshatra keyword. Combine graha, house, rashi, nakshatra ruler, and active period.

## Question-specific focus

Use the tool's detected domain as a starting filter, not a hard classification:

- Career: 2, 6, 10, 11; Sun, Mercury, Jupiter, Saturn.
- Relationships: 2, 5, 7, 8, 12; Venus, Jupiter, Mars.
- Finance: 2, 5, 9, 11; Mercury, Jupiter, Venus.
- Health: 1, 6, 8, 12; Sun, Moon, Mars, Saturn.
- Education: 2, 4, 5, 9; Mercury, Jupiter, Moon.
- Home/family: 2, 4, 5, 9; Moon, Sun, Jupiter, Venus.
- Spirituality: 5, 8, 9, 12; Jupiter, Saturn, Ketu.

If the question spans domains, explicitly add the missing houses rather than forcing one category. Always inspect the lagna and Moon for overall context.

## Data quality and confidence

Birth-time error primarily threatens the ascendant, house assignments, and divisional placements. Near a sign boundary, even a small error can change the lagna or D9. If time is uncertain:

- Say so before interpreting houses.
- Give more weight to Moon sign/nakshatra, sign-level graha positions, and dasha sequence.
- Do not silently rectify the chart from life events.
- Offer conditional interpretations if a boundary is close.

Coordinates should represent the birthplace, not a default city center when a more accurate location is known. Historical timestamps need the offset that actually applied then; current offset rules may differ.

## Answer protocol

A useful response has five compact parts:

1. **Direct answer:** address the question in ordinary language, with a calibrated confidence statement.
2. **Natal basis:** cite the relevant houses, lords, occupants, and karakas from returned data.
3. **Current activation:** cite the exact active dasha levels and the few transits that repeat the natal theme.
4. **Timing:** name a returned dasha/transit window; frame it as favorable, demanding, mixed, or unclear—not guaranteed.
5. **Agency and limits:** suggest practical action, name conflicting evidence or birth-time uncertainty, and retain domain-appropriate safeguards.

Distinguish facts from interpretation:

- Calculated fact: “Saturn is transiting the 10th whole-sign house from the natal lagna.”
- Interpretation: “Within this tradition, that can emphasize sustained professional responsibility.”
- Not acceptable: “You will lose your job.”

Never invent a placement, aspect, yoga, dasha date, or transit ingress that is absent from tool output. Never use astrology to assert death, inevitable harm, criminality, infidelity, pregnancy, diagnosis, or another person's hidden mental state. For medical, legal, financial, or safety-critical questions, keep astrology explicitly non-decisive and point to qualified real-world help.
