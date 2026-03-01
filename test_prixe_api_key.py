"""
Unittest: verify Prixe.io API responds successfully with a given API key.

Run with a specific key (e.g. to verify a key before setting on EB):
  TEST_PRIXE_API_KEY=e9476293-d019-4190-a9f2-d263572b6afd python -m pytest test_prixe_api_key.py -v

Or use the key from config (app_secrets / .env):
  python -m pytest test_prixe_api_key.py -v
"""
import os
import unittest
import requests

PRIXE_BASE_URL = "https://api.prixe.io"
PRICE_ENDPOINT = "/api/price"


def get_test_key():
    """Key to use: TEST_PRIXE_API_KEY env var, or config."""
    key = os.getenv("TEST_PRIXE_API_KEY", "").strip()
    if key:
        return key
    try:
        from config import PRIXE_API_KEY
        return (PRIXE_API_KEY or "").strip()
    except Exception:
        return ""


class TestPrixeApiKey(unittest.TestCase):
    """Test Prixe.io /api/price with the configured or provided key."""

    @classmethod
    def setUpClass(cls):
        cls.api_key = get_test_key()

    def test_prixe_api_key_is_set(self):
        """Fail fast if no key is available."""
        self.assertTrue(
            bool(self.api_key),
            "No API key. Set TEST_PRIXE_API_KEY or PRIXE_API_KEY (e.g. in app_secrets.py / .env)."
        )

    def test_prixe_price_endpoint_returns_200_with_valid_key(self):
        """POST /api/price with Bearer key should return 200 and success=True."""
        self.assertTrue(bool(self.api_key), "Skipped: no API key set")
        url = f"{PRIXE_BASE_URL}{PRICE_ENDPOINT}"
        payload = {
            "ticker": "IBM",
            "start_date": "2025-12-15",
            "end_date": "2026-01-20",
            "interval": "1d",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        self.assertEqual(
            resp.status_code,
            200,
            f"Expected 200, got {resp.status_code}. Response: {resp.text[:300]}",
        )
        data = resp.json()
        self.assertTrue(
            data.get("success") is True,
            f"Expected success=True in response. Got: {data}",
        )
        self.assertIn("data", data, "Response should contain 'data'")

    def test_prixe_price_endpoint_returns_data_shape(self):
        """Response data should have timestamp and close arrays for chart use."""
        self.assertTrue(bool(self.api_key), "Skipped: no API key set")
        url = f"{PRIXE_BASE_URL}{PRICE_ENDPOINT}"
        payload = {
            "ticker": "IBM",
            "start_date": "2025-12-15",
            "end_date": "2026-01-20",
            "interval": "1d",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            self.skipTest(f"API returned {resp.status_code}; run test_prixe_price_endpoint_returns_200_with_valid_key first")
        data = resp.json()
        inner = data.get("data") or {}
        self.assertIn("timestamp", inner, "data should have 'timestamp'")
        self.assertIn("close", inner, "data should have 'close'")


if __name__ == "__main__":
    unittest.main()
