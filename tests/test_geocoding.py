from __future__ import annotations

import unittest
from unittest.mock import patch

from astrology_mcp.geocoding import _cached_lookup, resolve_birth_location


class BirthLocationResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        _cached_lookup.cache_clear()

    def test_candidates_are_normalized_and_repeated_queries_are_cached(self) -> None:
        provider_response = [
            {
                "place_id": 123,
                "lat": "12.9308000",
                "lon": "77.5830000",
                "display_name": "Jayanagar, Bengaluru South, Karnataka, India",
                "category": "boundary",
                "type": "administrative",
                "importance": 0.42,
                "boundingbox": ["12.90", "12.96", "77.55", "77.61"],
                "address": {
                    "suburb": "Jayanagar",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "country": "India",
                    "country_code": "in",
                },
            },
            {"display_name": "missing coordinates"},
        ]
        with patch("astrology_mcp.geocoding._request_json", return_value=provider_response) as request:
            first = resolve_birth_location("  Jayanagar,   Bengaluru, India ", country_codes=" IN ", limit=3)
            second = resolve_birth_location("Jayanagar, Bengaluru, India", country_codes="in", limit=3)

        request.assert_called_once_with("Jayanagar, Bengaluru, India", "in", 3)
        self.assertEqual(first, second)
        self.assertEqual(len(first["candidates"]), 1)
        candidate = first["candidates"][0]
        self.assertEqual(candidate["latitude"], 12.9308)
        self.assertEqual(candidate["longitude"], 77.583)
        self.assertEqual(candidate["address"]["city"], "Bengaluru")
        self.assertEqual(candidate["bounding_box"], [12.9, 12.96, 77.55, 77.61])
        self.assertIn("OpenStreetMap", first["attribution"])
        self.assertIn("one request per second", first["usage_notice"])
        self.assertIn("ask the human", first["selection_rule"])

    def test_invalid_inputs_are_rejected_before_network_access(self) -> None:
        with patch("astrology_mcp.geocoding._request_json") as request:
            with self.assertRaisesRegex(ValueError, "at least two"):
                resolve_birth_location("x")
            with self.assertRaisesRegex(ValueError, "between 1 and 5"):
                resolve_birth_location("Bengaluru", limit=6)
            with self.assertRaisesRegex(ValueError, "ISO 3166"):
                resolve_birth_location("Bengaluru", country_codes="india")
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
