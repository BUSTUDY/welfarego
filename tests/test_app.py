import gzip
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

import welfare_app
import welfare_site

FORBIDDEN = re.compile(r"adsbygoogle|ca-pub-|googletagmanager|google-analytics|gtag\s*\(|AW-9819325336|clarity\.ms|wphbg8gymg|bustudy\.kr", re.I)

class WelfareAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temporary.name) / "services.json"
        cls.data.write_text(json.dumps({
            "updated": "fixture", "count": 2,
            "items": [
                {"id": "national-1", "name": "전국 지원", "org": "테스트 기관", "sido": "", "tags": ["청년"]},
                {"id": "seoul-1", "name": "서울 지원", "org": "서울특별시", "sido": "서울특별시", "tags": ["청년"]},
            ]}, ensure_ascii=False), encoding="utf-8")
        cls.patch = patch.object(welfare_site, "_welfare_data_path", return_value=str(cls.data))
        cls.patch.start()
        welfare_app.app.config.update(TESTING=True, SITE_BASE="https://welfarego.co.kr")
        cls.client = welfare_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()
        cls.temporary.cleanup()

    def test_all_sitemap_pages_are_standalone(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        root = ET.fromstring(sitemap.data)
        urls = [node.text for node in root.findall(".//{*}loc")]
        self.assertEqual(len(urls), 252)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(urlsplit(url).hostname, "welfarego.co.kr")
                path = urlsplit(url).path
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIsNone(FORBIDDEN.search(html))
                self.assertIn('href="https://welfarego.co.kr' + unquote(path) + '"', html)
                ld = json.loads(re.search(r'<script type="application/ld\+json" id="ld">(.*?)</script>', html, re.S).group(1))
                self.assertEqual(ld["@graph"][0]["url"], "https://welfarego.co.kr/")
                self.assertEqual(ld["@graph"][-1]["itemListElement"][-1]["item"], "https://welfarego.co.kr" + unquote(path))

    def test_service_page_and_missing_service(self):
        response = self.client.get("/s/national-1")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('href="https://welfarego.co.kr/s/national-1"', html)
        self.assertIsNone(FORBIDDEN.search(html))
        self.assertEqual(self.client.get("/s/missing").status_code, 302)

    def test_json_delivery_cache_and_gzip(self):
        response = self.client.get("/data/welfare/national.json", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.status_code, 200)
        document = json.loads(gzip.decompress(response.data))
        self.assertEqual([x["id"] for x in document["items"]], ["national-1"])
        cached = self.client.get("/data/welfare/national.json", headers={"If-None-Match": response.headers["ETag"]})
        self.assertEqual(cached.status_code, 304)
        regional = self.client.get("/data/welfare/sido/서울특별시.json")
        self.assertEqual([x["id"] for x in regional.json["items"]], ["seoul-1"])

    def test_metadata_ad_withdrawal_and_health(self):
        self.assertEqual(self.client.get("/ads.txt").status_code, 410)
        self.assertEqual(self.client.get("/calculator").status_code, 404)
        self.assertEqual(self.client.get("/healthz").json, {"ok": True})
        for path in ("/robots.txt", "/llms.txt"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(FORBIDDEN.search(response.get_data(as_text=True)))

if __name__ == "__main__":
    unittest.main()
