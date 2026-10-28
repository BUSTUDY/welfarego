import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import update_welfare as collector

class ErrorRedactionTests(unittest.TestCase):
    def test_raw_and_encoded_api_keys_are_not_logged(self):
        key = "test+secret/value="
        with patch.object(collector, "KEY", key), patch.object(collector, "KOSSI_KEY", "other-secret"):
            for value in (key, quote(key, safe=""), "other-secret"):
                output = collector.safe_error("API failed: " + value)
                self.assertNotIn(value, output)
                self.assertIn("[redacted]", output)

    def test_service_key_query_is_redacted_even_if_not_configured(self):
        output = collector.safe_error("HTTP error https://api.example/?serviceKey=sample-token&x=1")
        self.assertNotIn("sample-token", output)
        self.assertIn("serviceKey=[redacted]&x=1", output)

if __name__ == "__main__":
    unittest.main()
