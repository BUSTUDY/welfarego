import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, quote, urlsplit

import requests

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import update_welfare as collector

class ErrorRedactionTests(unittest.TestCase):
    def test_kossi_accepts_raw_encoded_and_padded_general_keys(self):
        raw = "sample+key/value=="
        response = Mock(status_code=200, text='{"ok":true}')
        response.json.return_value = {"ok": True}
        for supplied in (raw, quote(raw, safe=""), "  " + raw + "\n"):
            with self.subTest(form=supplied), patch.object(collector, "KOSSI_KEY", supplied), \
                    patch.object(collector.requests, "get", return_value=response) as get:
                self.assertEqual(collector.call_kossi("LcgvWelfarelist", page=2, per_page=37, retries=1), {"ok": True})
                args, kwargs = get.call_args
                prepared = requests.Request("GET", args[0], params=kwargs["params"]).prepare()
                query = parse_qs(urlsplit(prepared.url).query)
                self.assertEqual(query["serviceKey"], [raw])
                self.assertEqual(query["pageNo"], ["2"])
                self.assertEqual(query["numOfRows"], ["37"])

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

