from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from astrology_mcp.calculations import (
    VIMSHOTTARI_YEAR_DAYS,
    calculate_sidereal_chart,
    calculate_vimshottari_dasha,
)
from astrology_mcp.context import calculate_person_context


class SiderealChartTests(unittest.TestCase):
    def test_j2000_lahiri_reference_positions(self) -> None:
        chart = calculate_sidereal_chart(
            "2000-01-01T12:00:00+00:00",
            51.5078,
            -0.1275,
            label="J2000 London",
        )

        self.assertAlmostEqual(chart["julian_day_ut"], 2451545.0, places=7)
        self.assertAlmostEqual(chart["ayanamsha"]["degrees"], 23.857092, places=5)
        self.assertAlmostEqual(chart["grahas"]["Sun"]["longitude"], 256.515697, places=5)
        self.assertEqual(chart["grahas"]["Sun"]["rashi"]["english"], "Sagittarius")
        self.assertEqual(chart["grahas"]["Sun"]["nakshatra"]["name"], "Purva Ashadha")
        self.assertAlmostEqual(chart["ascendant"]["longitude"], 0.162405, places=5)
        self.assertEqual(chart["ascendant"]["rashi"]["english"], "Aries")
        self.assertEqual(chart["calculation"]["ayanamsha"], "Lahiri")
        self.assertIn("ephemeris", chart["calculation"])

    def test_same_instant_with_different_offsets_is_same_chart(self) -> None:
        utc_chart = calculate_sidereal_chart("2000-01-01T12:00:00Z", 28.6139, 77.209)
        offset_chart = calculate_sidereal_chart("2000-01-01T17:30:00+05:30", 28.6139, 77.209)

        self.assertEqual(utc_chart["julian_day_ut"], offset_chart["julian_day_ut"])
        self.assertEqual(utc_chart["ascendant"]["longitude"], offset_chart["ascendant"]["longitude"])
        for graha in utc_chart["grahas"]:
            self.assertEqual(
                utc_chart["grahas"][graha]["longitude"],
                offset_chart["grahas"][graha]["longitude"],
            )

    def test_whole_sign_houses_and_nodes_preserve_invariants(self) -> None:
        chart = calculate_sidereal_chart("1990-05-17T14:30:00+05:30", 28.6139, 77.209)
        ascendant_sign = chart["ascendant"]["rashi"]["index"]

        self.assertEqual(len(chart["houses"]), 12)
        self.assertEqual(chart["houses"][0]["rashi"]["index"], ascendant_sign)
        self.assertEqual(
            (chart["grahas"]["Ketu"]["longitude"] - chart["grahas"]["Rahu"]["longitude"])
            % 360.0,
            180.0,
        )
        for house in chart["houses"]:
            for occupant in house["occupants"]:
                self.assertEqual(chart["grahas"][occupant]["house"], house["number"])

    def test_naive_time_and_invalid_coordinates_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            calculate_sidereal_chart("2000-01-01T12:00:00", 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "latitude"):
            calculate_sidereal_chart("2000-01-01T12:00:00Z", 90.0, 0.0)
        with self.assertRaisesRegex(ValueError, "longitude"):
            calculate_sidereal_chart("2000-01-01T12:00:00Z", 0.0, 181.0)


class VimshottariTests(unittest.TestCase):
    def test_ashwini_zero_degrees_starts_full_ketu_period(self) -> None:
        birth = "2000-01-01T00:00:00+00:00"
        dasha = calculate_vimshottari_dasha(birth, 0.0, birth)

        self.assertEqual(dasha["birth_nakshatra"], "Ashwini")
        self.assertEqual(dasha["birth_balance"]["lord"], "Ketu")
        self.assertAlmostEqual(dasha["birth_balance"]["remaining_years"], 7.0, places=6)
        self.assertEqual(dasha["active"]["mahadasha"]["lord"], "Ketu")
        self.assertEqual(dasha["active"]["antardasha"]["lord"], "Ketu")
        self.assertEqual(dasha["active"]["pratyantardasha"]["lord"], "Ketu")

    def test_half_elapsed_nakshatra_leaves_half_birth_balance(self) -> None:
        birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
        as_of = birth + timedelta(days=4 * VIMSHOTTARI_YEAR_DAYS)
        dasha = calculate_vimshottari_dasha(
            birth.isoformat(),
            360.0 / 27.0 / 2.0,
            as_of.isoformat(),
        )

        self.assertAlmostEqual(dasha["birth_balance"]["remaining_years"], 3.5, places=5)
        self.assertEqual(dasha["active"]["mahadasha"]["lord"], "Venus")


class PersonContextTests(unittest.TestCase):
    def test_context_combines_question_dasha_and_transit_evidence(self) -> None:
        context = calculate_person_context(
            "1990-05-17T14:30:00+05:30",
            28.6139,
            77.209,
            "What should I pay attention to in my career?",
            as_of_timestamp="2026-08-16T12:00:00+05:30",
            birth_time_accuracy_minutes=5,
        )

        self.assertEqual(context["detected_domain"], "career")
        self.assertEqual(context["focus_houses"], [2, 6, 10, 11])
        self.assertEqual(context["vimshottari_dasha"]["active"]["mahadasha"]["lord"], "Jupiter")
        self.assertEqual(context["vimshottari_dasha"]["active"]["antardasha"]["lord"], "Mars")
        self.assertEqual(len(context["question_focus"]["houses"]), 4)
        self.assertIn("Saturn", context["transit_analysis"]["grahas"])
        self.assertFalse(
            any("Birth-time accuracy was not supplied" in caution for caution in context["cautions"])
        )

    def test_context_rejects_partial_current_location(self) -> None:
        with self.assertRaisesRegex(ValueError, "supplied together"):
            calculate_person_context(
                "1990-05-17T14:30:00+05:30",
                28.6139,
                77.209,
                "General reading",
                as_of_timestamp="2026-08-16T12:00:00Z",
                current_latitude=40.7128,
            )


if __name__ == "__main__":
    unittest.main()
