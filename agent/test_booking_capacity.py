"""
test_booking_capacity.py - Test suite verifying capacity boundary checks and overbooking prevention.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shelter-agent-backend")))

from toolbox.bigquery_tool import book_shelter_capacity
from main import find_shelters
from agent.mcp.toolbox_client import MCPToolboxClient


class MockHttpRequest:
    def __init__(self, json_data, method="POST"):
        self.method = method
        self._json_data = json_data
        self.headers = {"Content-Type": "application/json"}

    def get_json(self, silent=True):
        return self._json_data


class MockBigQueryRow:
    def __init__(self, shelter_id=367358, shelter_name="George Dupuis Rec", address_1="1212 E Pont Des Mouton", city="Lafayette", evacuation_capacity=100, available_capacity=10.0):
        self.shelter_id = shelter_id
        self.shelter_name = shelter_name
        self.address_1 = address_1
        self.city = city
        self.evacuation_capacity = evacuation_capacity
        self.available_capacity = available_capacity


class TestBookingCapacitySafety(unittest.TestCase):
    """Verifies that capacity limits cannot be breached by any booking request."""

    def test_overbooking_rejected_via_mocked_bigquery(self):
        """When available_capacity is 10, requesting 15 seats must be rejected."""
        mock_client = MagicMock()
        mock_fetch_job = MagicMock()
        mock_fetch_job.result.return_value = [MockBigQueryRow(available_capacity=10.0)]
        mock_client.query.return_value = mock_fetch_job

        with patch("google.cloud.bigquery.Client", return_value=mock_client):
            res = book_shelter_capacity(shelter_id=367358, count=15)
            self.assertFalse(res.get("success"), "Overbooking must fail")
            self.assertIn("error", res)
            self.assertIn("Cannot reserve 15", res["error"])
            self.assertEqual(res.get("available_capacity"), 10)

    def test_booking_when_shelter_is_full_rejected(self):
        """When available_capacity is 0, any booking request must be rejected."""
        mock_client = MagicMock()
        mock_fetch_job = MagicMock()
        mock_fetch_job.result.return_value = [MockBigQueryRow(available_capacity=0.0)]
        mock_client.query.return_value = mock_fetch_job

        with patch("google.cloud.bigquery.Client", return_value=mock_client):
            res = book_shelter_capacity(shelter_id=367358, count=1)
            self.assertFalse(res.get("success"))
            self.assertIn("already at full capacity", res.get("error", ""))

    def test_valid_booking_succeeds_and_updates_capacity(self):
        """When capacity is sufficient, booking succeeds and decrements capacity."""
        mock_client = MagicMock()
        mock_fetch_job = MagicMock()
        mock_fetch_job.result.return_value = [MockBigQueryRow(available_capacity=10.0)]
        mock_update_job = MagicMock()
        mock_update_job.num_dml_affected_rows = 1
        mock_client.query.side_effect = [mock_fetch_job, mock_update_job]

        with patch("google.cloud.bigquery.Client", return_value=mock_client):
            res = book_shelter_capacity(shelter_id=367358, count=3)
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("spots_reserved"), 3)
            self.assertEqual(res.get("available_capacity"), 7)

    def test_zero_or_negative_booking_rejected(self):
        """Party size <= 0 must be rejected immediately."""
        res_zero = book_shelter_capacity(shelter_id=367358, count=0)
        self.assertFalse(res_zero.get("success"))
        self.assertIn("must be at least 1", res_zero.get("error", ""))

        res_neg = book_shelter_capacity(shelter_id=367358, count=-5)
        self.assertFalse(res_neg.get("success"))

    def test_mcp_toolbox_client_overbooking_rejected(self):
        """MCP Toolbox client simulation must reject requests exceeding capacity."""
        client = MCPToolboxClient()
        # SHELTER-FL-4491 has 180 spots
        result = client.call_tool("book_shelter_capacity", {"shelter_id": "SHELTER-FL-4491", "count": 5000})
        self.assertFalse(result.get("success"))
        self.assertIn("Cannot reserve", result.get("error", ""))

    def test_http_endpoint_overbooking_returns_400(self):
        """Calling /book-shelter via HTTP handler returns 400 when overbooked."""
        mock_client = MagicMock()
        mock_fetch_job = MagicMock()
        mock_fetch_job.result.return_value = [MockBigQueryRow(available_capacity=4.0)]
        mock_client.query.return_value = mock_fetch_job

        with patch("google.cloud.bigquery.Client", return_value=mock_client):
            payload = {
                "action": "book",
                "shelter_id": 367358,
                "party_size": 10
            }
            req = MockHttpRequest(payload)
            res_body, status_code, headers = find_shelters(req)

            self.assertEqual(status_code, 400, "HTTP endpoint must return 400 on overbooking rejection")
            parsed = json.loads(res_body)
            self.assertFalse(parsed.get("success"))
            self.assertIn("Cannot reserve 10", parsed.get("error", ""))

    def test_http_endpoint_valid_booking_returns_200(self):
        """Calling /book-shelter via HTTP handler returns 200 when capacity is sufficient."""
        mock_client = MagicMock()
        mock_fetch_job = MagicMock()
        mock_fetch_job.result.return_value = [MockBigQueryRow(available_capacity=10.0)]
        mock_update_job = MagicMock()
        mock_update_job.num_dml_affected_rows = 1
        mock_client.query.side_effect = [mock_fetch_job, mock_update_job]

        with patch("google.cloud.bigquery.Client", return_value=mock_client):
            payload = {
                "action": "book",
                "shelter_id": 367358,
                "party_size": 2
            }
            req = MockHttpRequest(payload)
            res_body, status_code, headers = find_shelters(req)

            self.assertEqual(status_code, 200)
            parsed = json.loads(res_body)
            self.assertTrue(parsed.get("success"))
            self.assertEqual(parsed.get("spots_reserved"), 2)
            self.assertEqual(parsed.get("available_capacity"), 8)

    def test_live_bigquery_overbooking_rejected(self):
        """End-to-end integration test against live BigQuery verifying overbooking rejection."""
        # Requesting 999999 seats at shelter 367358 must be rejected
        res = book_shelter_capacity(367358, 999999)
        self.assertFalse(res.get("success"))
        self.assertIn("Cannot reserve 999999", res.get("error", ""))


if __name__ == "__main__":
    unittest.main()
