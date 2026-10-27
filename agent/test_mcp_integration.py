"""
test_mcp_integration.py - Verification suite for Google MCP Toolbox for Databases
and Google Maps Grounding Lite MCP integrations.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yaml
import unittest
from agent.mcp.toolbox_client import MCPToolboxClient, default_toolbox_client
from agent.mcp.maps_mcp_client import MapsGroundingMCPClient, default_maps_mcp_client

class TestMCPIntegration(unittest.TestCase):
    """Test suite verifying MCP tool definitions, client routing, and compliance."""

    def test_mcp_toolbox_config_validity(self):
        """Verifies that mcp-toolbox/tools.yaml is valid YAML and defines required tools."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "mcp-toolbox", "tools.yaml")
        self.assertTrue(os.path.exists(config_path), f"tools.yaml missing at {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        self.assertIn("sources", data)
        self.assertIn("tools", data)
        tool_names = [t["name"] for t in data["tools"]]

        expected_tools = [
            "search_shelters_spatial",
            "book_shelter_capacity",
            "query_care_facilities",
            "query_vulnerability_tracts",
            "query_hazard_tracts",
            "query_candidate_medical_shelters"
        ]
        for et in expected_tools:
            self.assertIn(et, tool_names, f"Expected tool {et} not found in tools.yaml")

    def test_toolbox_client_search_shelters_spatial(self):
        """Verifies spatial shelter search via MCP Toolbox client."""
        client = MCPToolboxClient()
        results = client.call_tool(
            "search_shelters_spatial",
            {"lat": 25.7617, "lon": -80.1918, "limit": 3}
        )
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        first = results[0]
        self.assertIn("shelter_name", first)
        self.assertIn("distance_meters", first)

    def test_toolbox_client_book_capacity(self):
        """Verifies atomic capacity booking via MCP Toolbox client."""
        client = MCPToolboxClient()
        booking = client.call_tool(
            "book_shelter_capacity",
            {"shelter_id": "SHELTER-FL-4491", "count": 2}
        )
        self.assertTrue(booking.get("success"))
        self.assertEqual(booking.get("reserved_spots"), 2)

    def test_toolbox_client_book_capacity_exceeds_available_rejected(self):
        """Verifies that requesting more seats than available capacity is rejected."""
        client = MCPToolboxClient()
        booking = client.call_tool(
            "book_shelter_capacity",
            {"shelter_id": "SHELTER-FL-4491", "count": 5000}
        )
        self.assertFalse(booking.get("success"), "Booking exceeding capacity must fail")
        self.assertIn("error", booking)
        self.assertIn("Cannot reserve", booking["error"])

    def test_toolbox_client_book_capacity_zero_or_negative_rejected(self):
        """Verifies that non-positive party sizes are rejected."""
        client = MCPToolboxClient()
        booking_zero = client.call_tool(
            "book_shelter_capacity",
            {"shelter_id": "SHELTER-FL-4491", "count": 0}
        )
        self.assertFalse(booking_zero.get("success"))

        booking_neg = client.call_tool(
            "book_shelter_capacity",
            {"shelter_id": "SHELTER-FL-4491", "count": -3}
        )
        self.assertFalse(booking_neg.get("success"))

    def test_toolbox_client_query_care_facilities(self):
        """Verifies healthcare facility query via MCP Toolbox."""
        client = MCPToolboxClient()
        facilities = client.call_tool("query_care_facilities", {"min_beds": 100, "limit": 2})
        self.assertIsInstance(facilities, list)
        self.assertGreater(len(facilities), 0)
        self.assertGreaterEqual(facilities[0]["bed_capacity"], 100)

    def test_maps_mcp_client_search_places(self):
        """Verifies place grounding and attribution on Maps MCP client."""
        client = MapsGroundingMCPClient()
        places = client.search_places("Northside Community Medical Point")
        self.assertIsInstance(places, list)
        self.assertGreater(len(places), 0)
        self.assertEqual(places[0]["businessStatus"], "CLOSED_PERMANENTLY")
        self.assertEqual(places[0]["attribution"], "Google Maps")

    def test_maps_mcp_client_compute_routes_modes(self):
        """Verifies both DRIVE and WALK routing via Maps MCP compute_routes."""
        client = MapsGroundingMCPClient()
        
        # Test DRIVE mode
        drive = client.compute_routes(
            origin_lat=25.7617, origin_lon=-80.1918,
            dest_lat=25.8451, dest_lon=-80.2215,
            travel_mode="DRIVE"
        )
        self.assertEqual(drive["travelMode"], "DRIVE")
        self.assertIn("durationMinutes", drive)
        self.assertIn("Google Maps", drive["attribution"])

        # Test WALK mode (for last-mile transit equity)
        walk = client.compute_routes(
            origin_lat=25.7617, origin_lon=-80.1918,
            dest_lat=25.8451, dest_lon=-80.2215,
            travel_mode="WALK"
        )
        self.assertEqual(walk["travelMode"], "WALK")
        self.assertGreater(walk["durationMinutes"], drive["durationMinutes"])

    def test_maps_mcp_lookup_weather(self):
        """Verifies weather lookup tool on Maps MCP client."""
        client = MapsGroundingMCPClient()
        weather = client.lookup_weather(25.7617, -80.1918)
        self.assertIn("temperature_f", weather)
        self.assertIn("condition", weather)

if __name__ == "__main__":
    unittest.main()
