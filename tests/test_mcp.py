from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyUrl

from astrology_mcp.server import mcp

_TOOL_NAMES = {
    "ask_astrology",
    "calculate_chart",
    "delete_birth_profile",
    "get_person_context",
    "list_birth_profiles",
    "resolve_birth_location",
    "save_birth_profile",
}


class McpProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_resource_prompt_and_person_context_round_trip(self) -> None:
        async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as client:
            tools = await client.list_tools()
            self.assertEqual({tool.name for tool in tools.tools}, _TOOL_NAMES)
            person_tool = next(tool for tool in tools.tools if tool.name == "get_person_context")
            self.assertIn("birth_timestamp", person_tool.inputSchema["required"])
            assert person_tool.annotations is not None
            self.assertTrue(person_tool.annotations.readOnlyHint)
            location_tool = next(tool for tool in tools.tools if tool.name == "resolve_birth_location")
            assert location_tool.annotations is not None
            self.assertTrue(location_tool.annotations.openWorldHint)

            resources = await client.list_resources()
            self.assertEqual(
                [str(resource.uri) for resource in resources.resources],
                ["astrology://reference/guide"],
            )
            guide = await client.read_resource(AnyUrl("astrology://reference/guide"))
            guide_content = guide.contents[0]
            assert isinstance(guide_content, TextResourceContents)
            self.assertIn("The synthesis hierarchy", guide_content.text)
            self.assertIn("not a scientifically validated prediction", guide_content.text)

            prompts = await client.list_prompts()
            self.assertEqual([prompt.name for prompt in prompts.prompts], ["personal_jyotisha_reading"])
            prompt = await client.get_prompt(
                "personal_jyotisha_reading",
                {
                    "question": "What matters in my career now?",
                    "birth_date": "2000-01-22",
                    "birth_time": "21:30",
                    "birth_location": "Jayanagar, Bengaluru, Karnataka, India",
                    "as_of_timestamp": "2026-08-16T12:00:00+05:30",
                },
            )
            prompt_content = prompt.messages[0].content
            assert isinstance(prompt_content, TextContent)
            self.assertIn("ask_astrology", prompt_content.text)
            self.assertIn("resolve_birth_location", prompt_content.text)
            self.assertIn("save profile", prompt_content.text)

            result = await client.call_tool(
                "get_person_context",
                {
                    "birth_timestamp": "1990-05-17T14:30:00+05:30",
                    "birth_latitude": 28.6139,
                    "birth_longitude": 77.209,
                    "question": "What matters in my career now?",
                    "as_of_timestamp": "2026-08-16T12:00:00+05:30",
                    "birth_time_accuracy_minutes": 5,
                },
            )
            self.assertFalse(result.isError)
            self.assertIsNotNone(result.structuredContent)
            assert result.structuredContent is not None
            self.assertEqual(result.structuredContent["detected_domain"], "career")
            self.assertEqual(
                result.structuredContent["vimshottari_dasha"]["active"]["mahadasha"]["lord"],
                "Jupiter",
            )
            self.assertIn("current_chart", result.structuredContent)
            self.assertIn("transit_analysis", result.structuredContent)

    async def test_profile_onboarding_then_question_only_reading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"ASTROLOGY_MCP_DATA_DIR": directory}):
                async with create_connected_server_and_client_session(
                    mcp,
                    raise_exceptions=True,
                ) as client:
                    initial = await client.call_tool("list_birth_profiles")
                    assert initial.structuredContent is not None
                    self.assertEqual(initial.structuredContent["profiles"], [])

                    saved = await client.call_tool(
                        "save_birth_profile",
                        {
                            "profile_name": "me",
                            "birth_date": "2000-01-22",
                            "birth_time": "21:30",
                            "birth_place": "Jayanagar, Bengaluru, Karnataka, India",
                            "latitude": 12.9292731,
                            "longitude": 77.5824229,
                            "birth_time_accuracy_minutes": 5,
                        },
                    )
                    self.assertFalse(saved.isError)
                    assert saved.structuredContent is not None
                    self.assertEqual(
                        saved.structuredContent["profile"]["birth_timestamp"],
                        "2000-01-22T21:30:00+05:30",
                    )

                    reading = await client.call_tool(
                        "ask_astrology",
                        {
                            "question": "What matters in my career now?",
                            "as_of_timestamp": "2026-08-16T12:00:00+05:30",
                        },
                    )
                    self.assertFalse(reading.isError)
                    assert reading.structuredContent is not None
                    self.assertEqual(
                        reading.structuredContent["context"]["detected_domain"],
                        "career",
                    )
                    self.assertEqual(reading.structuredContent["profile"]["profile_name"], "me")

    async def test_installed_server_over_stdio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "astrology_mcp.server"],
                env={**os.environ, "ASTROLOGY_MCP_DATA_DIR": directory},
            )
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()
                    tools = await client.list_tools()
                    self.assertEqual({tool.name for tool in tools.tools}, _TOOL_NAMES)
                    saved = await client.call_tool(
                        "save_birth_profile",
                        {
                            "birth_date": "2000-01-22",
                            "birth_time": "21:30",
                            "birth_place": "Jayanagar, Bengaluru, Karnataka, India",
                            "latitude": 12.9292731,
                            "longitude": 77.5824229,
                        },
                    )
                    self.assertFalse(saved.isError)
                    reading = await client.call_tool(
                        "ask_astrology",
                        {
                            "question": "What matters in my career now?",
                            "as_of_timestamp": "2026-08-16T12:00:00+05:30",
                        },
                    )
                    self.assertFalse(reading.isError)
                    assert reading.structuredContent is not None
                    self.assertEqual(
                        reading.structuredContent["context"]["detected_domain"],
                        "career",
                    )


if __name__ == "__main__":
    unittest.main()
