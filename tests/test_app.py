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
        welfare_app.app.config.update(TESTING=True, SITE_BASE="https://welfarego.co.kr", ADSENSE_PUB_ID="")
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
                expected_og = (
                    "https://welfarego.co.kr/static/og/welfarego-office-2026.png"
                    if path == "/office"
                    else "https://welfarego.co.kr/static/og/welfarego-2026.png"
                )
                self.assertIn(f'property="og:image" content="{expected_og}"', html)
                self.assertIn('property="og:image:width" content="1200"', html)
                self.assertIn('property="og:image:height" content="630"', html)
                self.assertIn('name="twitter:card" content="summary_large_image"', html)
                self.assertNotIn("/static/og/welfare.png", html)
                ld_match = re.search(r'<script type="application/ld\+json" id="ld">(.*?)</script>', html, re.S)
                self.assertIsNotNone(ld_match)
                ld = json.loads(ld_match.group(1))
                self.assertEqual(ld["@graph"][0]["url"], "https://welfarego.co.kr/")
                self.assertEqual(
                    ld["@graph"][-1]["itemListElement"][-1]["item"],
                    "https://welfarego.co.kr" + unquote(path),
                )

        import struct

        for og_path in (
            "/static/og/welfarego-2026.png",
            "/static/og/welfarego-office-2026.png",
            "/static/og/welfare.png",
        ):
            with self.subTest(og_path=og_path):
                img_resp = self.client.get(og_path)
                self.assertEqual(img_resp.status_code, 200)
                self.assertTrue(img_resp.data.startswith(b"\x89PNG\r\n\x1a\n"))
                w, h = struct.unpack(">II", img_resp.data[16:24])
                self.assertEqual((w, h), (1200, 630))
                img_resp.close()

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

    def test_adsense_env_switch_and_cookie_disclosure(self):
        # 1) 잘못된 형식의 게시자 ID는 무시되어 410 유지
        welfare_app.app.config["ADSENSE_PUB_ID"] = "<script>bad</script>"
        try:
            self.assertEqual(self.client.get("/ads.txt").status_code, 410)
            self.assertNotIn("adsbygoogle", self.client.get("/").get_data(as_text=True))

            # 2) 정상 게시자 ID 설정 시 /ads.txt, 메타태그·스크립트, 개인정보 쿠키 고지 자동 활성화
            welfare_app.app.config["ADSENSE_PUB_ID"] = "pub-1234567890123456"
            welfare_app.app.config["ADSENSE_SLOT_BOTTOM"] = "9876543210"

            ads = self.client.get("/ads.txt")
            self.assertEqual(ads.status_code, 200)
            self.assertEqual(
                ads.get_data(as_text=True),
                "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n",
            )

            tools_html = self.client.get("/tools").get_data(as_text=True)
            self.assertIn('content="ca-pub-1234567890123456"', tools_html)
            self.assertIn("adsbygoogle.js?client=ca-pub-1234567890123456", tools_html)
            self.assertIn('data-ad-slot="9876543210"', tools_html)
            self.assertIn('class="ad-slot-box no-print"', tools_html)

            about_html = self.client.get("/about").get_data(as_text=True)
            self.assertIn("2. 개인정보 보호 및 쿠키·광고 운영 안내", about_html)
            self.assertIn("adssettings.google.com", about_html)
        finally:
            welfare_app.app.config["ADSENSE_PUB_ID"] = ""
            welfare_app.app.config.pop("ADSENSE_SLOT_BOTTOM", None)


if __name__ == "__main__":
    unittest.main()
