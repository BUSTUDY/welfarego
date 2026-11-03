import importlib.util
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, quote, urlsplit

import requests

import portal_data as data
from welfare_app import app

spec = importlib.util.spec_from_file_location("update_portal", Path(__file__).resolve().parents[1] / "scripts/update_portal.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "data").mkdir()
        def save(kind, items):
            name = "welfare_services.json" if kind == "benefits" else "portal_" + kind + ".json"
            (root / "data" / name).write_text(json.dumps({"updated": "2026-11-03T05:30:00+09:00", "items": items}, ensure_ascii=False), encoding="utf-8")
        save("benefits", [
            {"id": "one", "name": "전국 주거지원", "org": "공공기관", "field": "주거·자립", "tags": ["청년"]},
            {"id": "two", "name": "서울 청년지원", "org": "서울특별시", "sido": "서울특별시", "field": "생활안정", "tags": ["청년"]},
            {"id": "three", "name": "부산 어르신 지원", "org": "부산광역시", "sido": "부산광역시", "tags": ["노년"]},
        ])
        save("jobs", [
            {"id": "open", "name": "사회복지사 채용", "region": "서울특별시", "start": "20261101", "end": "20261103", "posted": "20261103", "type": "사회복지사"},
            {"id": "old", "name": "이미 마감한 채용", "region": "서울특별시", "end": "20261102"},
            {"id": "future", "name": "예정 채용", "start": "20261106", "end": "20261110"},
            {"id": "unknown", "name": "일정 미제공 채용", "url": "javascript:alert(1)", "summary": '<img src=x onerror="alert(1)">공공 정보'},
        ])
        save("care", [{"id": str(i), "name": "기관 " + str(i), "region": "서울특별시", "type": "기관유형 C04"} for i in range(4)])
        self.patch_root = patch.object(data, "ROOT", root)
        self.patch_root.start()
        self.patch_today = patch.object(data, "today", return_value=date(2026, 11, 3))
        self.patch_today.start()
        data._read.cache_clear()
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        self.patch_today.stop()
        self.patch_root.stop()
        data._read.cache_clear()
        self.temp.cleanup()

    def test_home_has_five_services_and_preserved_search(self):
        html = self.client.get("/").get_data(as_text=True)
        for service in data.SERVICES:
            self.assertIn('href="' + service["path"] + '"', html)
        self.assertIn("우리 동네 복지혜택", html)
        self.assertEqual(self.client.get("/welfare").status_code, 200)
        self.assertEqual(self.client.get("/welfare/?x=1").location, "/welfare?x=1")

    def test_region_includes_national_benefits_but_not_unknown_jobs(self):
        _, items = data.select("benefits", {"region": "서울특별시", "tag": "청년"})
        self.assertEqual({s["id"] for s in items}, {"one", "two"})
        _, items = data.select("jobs", {"region": "서울특별시"})
        self.assertEqual([s["id"] for s in items], ["open"])

    def test_deadline_uses_korean_calendar_and_excludes_future(self):
        _, items = data.select("jobs", {"status": "deadline"})
        self.assertEqual([s["id"] for s in items], ["open"])
        self.assertEqual(data.present(items[0])["status_label"], "오늘 마감")
        _, items = data.select("jobs", {"status": "new"})
        self.assertEqual([s["id"] for s in items], ["open"])

    def test_application_closes_at_provided_time(self):
        item = data.normalize("grants", {"name": "공모", "end": "20261103", "end_time": "16:00"})
        with patch.object(data, "now", return_value=datetime(2026, 11, 3, 16, 1, tzinfo=data.KST)):
            self.assertEqual(data.status(item)[0], "closed")
        with patch.object(data, "now", return_value=datetime(2026, 11, 3, 15, 59, tzinfo=data.KST)):
            self.assertEqual(data.status(item)[0], "open")

    def test_unavailable_api_does_not_claim_zero_results_or_fabricate(self):
        html = self.client.get("/grants").get_data(as_text=True)
        self.assertIn("공식 데이터를 연결하고 있습니다", html)
        self.assertIn("보조금 통합포털", html)
        self.assertNotIn("샘플", html)

    def test_url_safety_and_query_escaping(self):
        html = self.client.get('/jobs?q=%3Cscript%3E').get_data(as_text=True)
        self.assertNotIn('value="<script>"', html)
        self.assertIn('&lt;script&gt;', html)
        html = self.client.get("/jobs").get_data(as_text=True)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn('<img src=x', html)
        self.assertEqual(data.safe_url("//evil.example"), "")
        self.assertEqual(data.safe_url("https://user:secret@example.com"), "")

    def test_saved_lookup_current_records_and_removed_records(self):
        response = self.client.get("/api/portal/saved?ids=jobs:old,benefits:one,jobs:gone")
        self.assertEqual({x["save_key"] for x in response.json["items"]}, {"jobs:old", "benefits:one"})
        old = next(x for x in response.json["items"] if x["save_key"] == "jobs:old")
        self.assertEqual(old["status"], "closed")
        self.assertEqual(response.json["missing"], ["jobs:gone"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(self.client.get("/api/portal/saved").json, {"items": [], "missing": []})

    def test_compare_bound_and_unknown_fields(self):
        html = self.client.get("/care/compare?ids=0,1,2,3").get_data(as_text=True)
        self.assertIn("기관 2", html)
        self.assertNotIn("기관 3", html)
        self.assertIn("API 미제공 · 기관 문의", html)
        self.assertIn("기관에 직접 확인", html)

    def test_invalid_and_out_of_range_page(self):
        for page in ("garbage", "-30", "999999999"):
            response = self.client.get("/benefits?page=" + page)
            self.assertEqual(response.status_code, 200)


class CollectorTests(unittest.TestCase):
    def test_parse_singleton_empty_and_auth_errors(self):
        body = '<response><header><resultCode>00</resultCode></header><body><totalCount>1</totalCount><items><item><title>공고</title></item></items></body></response>'
        self.assertEqual(collector.parse_response(body), ([{"title": "공고"}], 1))
        self.assertEqual(collector.parse_response('<response><body><totalCount>0</totalCount></body></response>'), ([], 0))
        for invalid in ('<error>bad</error>', '<response><resultCode>30</resultCode></response>', 'not XML'):
            with self.assertRaises(collector.CollectionError):
                collector.parse_response(invalid)

    def test_ssis_json_response_is_also_supported(self):
        body = json.dumps({"response": {"header": {"resultCode": "00"}, "body": {"totalCount": 1, "items": {"item": {"title": "채용"}}}}})
        self.assertEqual(collector.parse_response(body), ([{"title": "채용"}], 1))
        with self.assertRaises(collector.CollectionError):
            collector.parse_response('{"response":{"header":{"resultCode":"30"}}}')

    def test_xml_text_encoding_defects_are_repaired(self):
        body = '<response><totalCount>1</totalCount><items><item><title>A & B\x01</title></item></items></response>'
        self.assertEqual(collector.parse_response(body), ([{"title": "A & B"}], 1))

    def test_repeated_or_truncated_pages_do_not_publish(self):
        with patch.object(collector, "request_page", return_value=([{"id": "one"}], 2)):
            with self.assertRaises(collector.CollectionError):
                collector.pages("jobs", "secret", limit=1)

    def test_encoded_key_is_encoded_once_and_errors_do_not_leak(self):
        key = "test+secret/value=="
        response = type('Response', (), {"status_code": 200, "content": b'<response><totalCount>0</totalCount></response>'})()
        for supplied in (key, quote(key, safe=""), " " + key + "\n"):
            with patch.object(collector.requests, "get", return_value=response) as get:
                collector.request_page("jobs", supplied, {})
                args, kwargs = get.call_args
                url = requests.Request("GET", args[0], params=kwargs["params"]).prepare().url
                self.assertEqual(parse_qs(urlsplit(url).query)["serviceKey"], [key])
        with patch.object(collector.requests, "get", side_effect=requests.RequestException("serviceKey=" + key)), patch.object(collector.time, "sleep"):
            with self.assertRaises(collector.CollectionError) as error:
                collector.request_page("jobs", key, {})
            self.assertNotIn(key, str(error.exception))

    def test_grants_use_application_dates_not_project_dates(self):
        item = collector.grant({"PBLANC_NM": "복지 지원", "BSNS_BEGIN_DE": "20260101", "BSNS_END_DE": "20261231", "PBLANC_END_DE": "20261130", "RCEPT_END_DE": "20261105"})
        self.assertEqual(item["end"], "2026-11-05")
        self.assertEqual(item["start"], "")

    def test_failed_collection_preserves_snapshot(self):
        with patch.dict(collector.os.environ, {"WELFARE_API_KEY": "test-secret"}), patch.object(collector, "collect", side_effect=collector.CollectionError("API unavailable")), patch("sys.stderr"):
            self.assertEqual(collector.run("jobs"), 1)


if __name__ == "__main__":
    unittest.main()
