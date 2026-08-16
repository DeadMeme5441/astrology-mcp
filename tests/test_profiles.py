from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astrology_mcp.profiles import (
    calculate_profile_context,
    delete_birth_profile,
    get_birth_profile,
    list_birth_profiles,
    resolve_local_birth_timestamp,
    save_birth_profile,
)


class HistoricalTimezoneTests(unittest.TestCase):
    def test_bengaluru_local_time_resolves_without_user_offset(self) -> None:
        resolved = resolve_local_birth_timestamp(
            "2000-01-22",
            "21:30",
            12.9292731,
            77.5824229,
        )

        self.assertIn(resolved["timezone"], {"Asia/Kolkata", "Asia/Calcutta"})
        self.assertEqual(resolved["utc_offset"], "+05:30")
        self.assertEqual(resolved["birth_timestamp_utc"], "2000-01-22T16:00:00Z")

    def test_nonexistent_daylight_saving_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not exist"):
            resolve_local_birth_timestamp(
                "2024-03-10",
                "02:30",
                40.7128,
                -74.0060,
            )

    def test_repeated_daylight_saving_time_requires_occurrence(self) -> None:
        with self.assertRaisesRegex(ValueError, "first.*second"):
            resolve_local_birth_timestamp(
                "2024-11-03",
                "01:30",
                40.7128,
                -74.0060,
            )

        first = resolve_local_birth_timestamp(
            "2024-11-03",
            "01:30",
            40.7128,
            -74.0060,
            fold=0,
        )
        second = resolve_local_birth_timestamp(
            "2024-11-03",
            "01:30",
            40.7128,
            -74.0060,
            fold=1,
        )
        self.assertEqual(first["utc_offset"], "-04:00")
        self.assertEqual(second["utc_offset"], "-05:00")
        self.assertNotEqual(first["birth_timestamp_utc"], second["birth_timestamp_utc"])


class ProfileStoreTests(unittest.TestCase):
    def test_profile_persists_and_drives_question_only_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ASTROLOGY_MCP_DATA_DIR": directory}):
                saved = save_birth_profile(
                    "me",
                    "2000-01-22",
                    "21:30",
                    "Jayanagar, Bengaluru, Karnataka, India",
                    12.9292731,
                    77.5824229,
                    birth_time_accuracy_minutes=5,
                )
                self.assertTrue(saved["saved"])
                self.assertEqual(saved["profile"]["birth_timestamp"], "2000-01-22T21:30:00+05:30")

                profile_file = Path(directory) / "profiles.json"
                self.assertTrue(profile_file.is_file())
                if os.name == "posix":
                    self.assertEqual(profile_file.stat().st_mode & 0o777, 0o600)

                listed = list_birth_profiles()
                self.assertEqual(listed["profiles"][0]["profile_name"], "me")
                self.assertNotIn("birth_timestamp", listed["profiles"][0])
                self.assertEqual(get_birth_profile("ME")["birth_timezone"], "Asia/Kolkata")

                reading = calculate_profile_context(
                    "What should I pay attention to in my career?",
                    as_of_timestamp="2026-08-16T12:00:00+05:30",
                )
                self.assertEqual(reading["profile"]["profile_name"], "me")
                self.assertEqual(reading["context"]["detected_domain"], "career")
                self.assertEqual(
                    reading["context"]["natal_chart"]["input"]["timestamp"],
                    "2000-01-22T21:30:00+05:30",
                )

                deleted = delete_birth_profile("me")
                self.assertTrue(deleted["deleted"])
                with self.assertRaisesRegex(ValueError, "does not exist"):
                    get_birth_profile("me")


if __name__ == "__main__":
    unittest.main()
