import json
import re
import unittest
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

import welfare_app

FORBIDDEN = re.compile(
    r"adsbygoogle|ca-pub-|googletagmanager|google-analytics|gtag\s*\(|AW-9819325336|clarity\.ms|wphbg8gymg|bustudy\.kr|cdn\.tailwindcss\.com|fonts\.googleapis\.com",
    re.I,
)


class WelfareAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        welfare_app.app.config.update(TESTING=True, SITE_BASE="https://welfarego.co.kr")
        cls.client = welfare_app.app.test_client()

    def test_all_sitemap_pages_are_standalone_and_clean(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        root = ET.fromstring(sitemap.data)
        urls = [node.text for node in root.findall(".//{*}loc")]
        self.assertEqual(
            urls,
            [
                "https://welfarego.co.kr/",
                "https://welfarego.co.kr/evaluation",
                "https://welfarego.co.kr/operations",
                "https://welfarego.co.kr/tools",
                "https://welfarego.co.kr/forms",
                "https://welfarego.co.kr/office",
                "https://welfarego.co.kr/about",
            ],
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(urlsplit(url).hostname, "welfarego.co.kr")
                path = urlsplit(url).path
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIsNone(FORBIDDEN.search(html))
                self.assertIn('rel="canonical" href="https://welfarego.co.kr' + unquote(path) + '"', html)
                ld_match = re.search(r'<script type="application/ld\+json" id="ld">(.*?)</script>', html, re.S)
                self.assertIsNotNone(ld_match)
                ld = json.loads(ld_match.group(1))
                self.assertEqual(ld["@graph"][0]["url"], "https://welfarego.co.kr/")
                self.assertEqual(
                    ld["@graph"][-1]["itemListElement"][-1]["item"],
                    "https://welfarego.co.kr" + unquote(path),
                )

    def test_removed_legacy_welfare_routes_return_404(self):
        for path in ("/welfare", "/jobs", "/care", "/benefits", "/grants", "/saved", "/calculator", "/s/national-1"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_legacy_daycare_paths_redirect_permanently(self):
        expected = {
            "/daycare": "/",
            "/daycare/evaluation": "/evaluation",
            "/daycare/operations": "/operations",
            "/daycare/forms": "/forms",
        }
        for old_path, new_path in expected.items():
            with self.subTest(old_path=old_path):
                resp = self.client.get(old_path)
                self.assertEqual(resp.status_code, 301)
                self.assertEqual(resp.location, new_path)

    def test_metadata_ad_withdrawal_and_health(self):
        self.assertEqual(self.client.get("/ads.txt").status_code, 410)
        self.assertEqual(self.client.get("/healthz").json, {"ok": True})
        for path in ("/robots.txt", "/llms.txt"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            body = response.get_data(as_text=True)
            response.close()
            self.assertIsNone(FORBIDDEN.search(body))
        llms_resp = self.client.get("/llms.txt")
        llms = llms_resp.get_data(as_text=True)
        llms_resp.close()
        for required in ("/evaluation", "/operations", "/tools", "/forms", "/office"):
            self.assertIn(required, llms)
        for removed in (
            "welfarego.co.kr/welfare",
            "welfarego.co.kr/jobs",
            "welfarego.co.kr/benefits",
            "welfarego.co.kr/grants",
        ):
            self.assertNotIn(removed, llms)


if __name__ == "__main__":
    unittest.main()
