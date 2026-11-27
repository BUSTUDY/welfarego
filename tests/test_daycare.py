import io
import unittest
import zipfile
from xml.etree import ElementTree as ET

import welfare_app
from daycare_forms import DAYCARE_FORMS


class DaycareAndOfficeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        welfare_app.app.config.update(TESTING=True, SITE_BASE="https://welfarego.co.kr")
        cls.client = welfare_app.app.test_client()

    def test_backup_menu_and_assets_are_served_on_every_page(self):
        for path in ("/", "/tools", "/about"):
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn("data-backup-open", html)
            self.assertIn("js/backup.js", html)
            self.assertIn("vendor/xlsx.mini.min.js", html)
        for asset in ("/static/js/backup.js", "/static/vendor/xlsx.mini.min.js"):
            resp = self.client.get(asset)
            self.assertEqual(resp.status_code, 200, asset)
            resp.close()
        # 백업 스크립트는 사용자 자료를 서버로 보내는 네트워크 호출을 하지 않는다.
        src = self.client.get("/static/js/backup.js").get_data(as_text=True)
        for needle in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket"):
            self.assertNotIn(needle, src)

    def test_homepage_uses_gov_portal_design_and_links_to_subsites(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for path in ("/evaluation", "/operations", "/forms", "/office", "/about"):
            self.assertIn(f'href="{path}"', html)
        self.assertIn("site-header", html)
        self.assertIn("id=\"drawer\"", html)
        self.assertIn("hdrScore", html)
        self.assertIn('id="btnTheme"', html)
        # 기본은 밝은 화면: 서버가 어두운 테마를 미리 지정하지 않는다.
        self.assertNotIn('<html lang="ko" data-theme', html)
        self.assertIn("평가매뉴얼", html)
        self.assertIn("운영매뉴얼", html)
        self.assertIn("서식자료실", html)
        self.assertIn("무료 오피스", html)
        self.assertIn("48.6%", html)
        self.assertNotIn("복지시설 일자리", html)
        self.assertNotIn("우리 동네 복지혜택", html)

    def test_daycare_pages_render_latest_2026_content(self):
        ev = self.client.get("/evaluation")
        self.assertEqual(ev.status_code, 200)
        ev_html = ev.get_data(as_text=True)
        self.assertIn("급여제공 결과평가", ev_html)
        self.assertIn("기능회복훈련", ev_html)
        self.assertIn("dc-eval-data", ev_html)
        self.assertIn('id="tab-checklist"', ev_html)
        self.assertIn("36개 평가지표 준비완료 통합 자가점검표", ev_html)

        ops = self.client.get("/operations")
        self.assertEqual(ops.status_code, 200)
        ops_html = ops.get_data(as_text=True)
        self.assertIn("2,512,900원", ops_html)
        self.assertIn("69,730", ops_html)
        self.assertIn("81,270", ops_html)
        self.assertIn("제2026-189호", ops_html)
        self.assertIn("48.6%", ops_html)
        self.assertIn('id="stfActCareGen"', ops_html)
        self.assertIn('id="stfPresetBar"', ops_html)

        forms = self.client.get("/forms")
        self.assertEqual(forms.status_code, 200)
        forms_html = forms.get_data(as_text=True)
        self.assertEqual(len(DAYCARE_FORMS), 20)
        self.assertIn("별지 제15호서식", forms_html)
        self.assertIn("/forms/bundle.zip", forms_html)
        self.assertIn('href="/evaluation#indicator-8"', forms_html)
        self.assertNotIn('href="https://www.longtermcare.or.kr"', forms_html)

        home_html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('href="https://www.longtermcare.or.kr"', home_html)

        for form in DAYCARE_FORMS:
            self.assertRegex(form["eval_url"], r"^/evaluation#indicator-([1-9]|[12][0-9]|3[0-6])$")
            self.assertTrue(form["eval_label"])
            self.assertNotIn(
                form["gov_url"].rstrip("/"),
                {"https://www.longtermcare.or.kr", "https://www.nid.or.kr", "https://lst.go.kr"},
            )

    def test_all_20_forms_generate_valid_hwpx_docx_xlsx_and_print(self):
        from hwpx import HwpxDocument, validate_editor_open_safety, validate_package

        gov_hwp_count = 0
        for form in DAYCARE_FORMS:
            slug = form["slug"]
            with self.subTest(slug=slug):
                hwpx_resp = self.client.get(f"/forms/{slug}.hwpx?org=행복주야간센터&code=2-11000-12345")
                self.assertEqual(hwpx_resp.status_code, 200)
                self.assertTrue(validate_package(hwpx_resp.data).ok)
                self.assertTrue(validate_editor_open_safety(hwpx_resp.data).ok)
                hwpx_txt = HwpxDocument.open(hwpx_resp.data).text.plain()
                self.assertIn("행복주야간센터", hwpx_txt)
                self.assertIn("2-11000-12345", hwpx_txt)

                gov_resp = self.client.get(f"/forms/{slug}/gov.hwp")
                if form.get("gov_hwp_file"):
                    gov_hwp_count += 1
                    self.assertEqual(gov_resp.status_code, 200)
                    self.assertEqual(gov_resp.data[:8], b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
                else:
                    self.assertEqual(gov_resp.status_code, 404)

                docx = self.client.get(f"/forms/{slug}.docx?org=행복주야간센터&code=2-11000-12345")
                self.assertEqual(docx.status_code, 200)
                with zipfile.ZipFile(io.BytesIO(docx.data)) as zf:
                    doc_xml = zf.read("word/document.xml").decode("utf-8")
                    ET.fromstring(doc_xml)
                    self.assertIn("행복주야간센터", doc_xml)
                    self.assertIn("2-11000-12345", doc_xml)

                xlsx = self.client.get(f"/forms/{slug}.xlsx?org=행복주야간센터&code=2-11000-12345")
                self.assertEqual(xlsx.status_code, 200)
                with zipfile.ZipFile(io.BytesIO(xlsx.data)) as zf:
                    sheet_xml = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
                    ET.fromstring(sheet_xml)
                    self.assertIn("행복주야간센터", sheet_xml)

                pr = self.client.get(f"/forms/{slug}/print?org=행복주야간센터")
                self.assertEqual(pr.status_code, 200)
                self.assertIn("행복주야간센터", pr.get_data(as_text=True))

        self.assertEqual(gov_hwp_count, 4)
        self.assertEqual(self.client.get("/forms/nonexistent.hwpx").status_code, 404)
        self.assertEqual(self.client.get("/forms/nonexistent.docx").status_code, 404)
        self.assertEqual(self.client.get("/forms/nonexistent.xlsx").status_code, 404)
        self.assertEqual(self.client.get("/forms/nonexistent/print").status_code, 404)

    def test_forms_bundle_zip_contains_all_65_files_and_readme(self):
        resp = self.client.get("/forms/bundle.zip?org=샘플센터")
        self.assertEqual(resp.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 65)
            self.assertIn("00_서식목록_및_사용안내.txt", names)
            self.assertEqual(sum(1 for n in names if n.endswith(".hwpx")), 20)
            self.assertEqual(sum(1 for n in names if n.endswith(".docx")), 20)
            self.assertEqual(sum(1 for n in names if n.endswith(".xlsx")), 20)
            self.assertEqual(sum(1 for n in names if n.endswith(".hwp")), 4)

    def test_free_office_routes_assets_certificate_and_mpl2_zip(self):
        office = self.client.get("/office")
        self.assertEqual(office.status_code, 200)
        self.assertIn("Welfarego OFFICE", office.get_data(as_text=True))

        preview = self.client.get("/office/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("Fluent Ribbon UI", preview.get_data(as_text=True))

        cert = self.client.get("/office/license-certificate?org=사랑돌봄센터&rep=김복지&pcs=5대")
        self.assertEqual(cert.status_code, 200)
        cert_html = cert.get_data(as_text=True)
        self.assertIn("사랑돌봄센터", cert_html)
        self.assertIn("김복지", cert_html)
        self.assertIn("MPL-2.0", cert_html)

        setup = self.client.get("/office/download/setup")
        self.assertEqual(setup.status_code, 302)

        asset = self.client.get("/office/assets/writer_app.png")
        self.assertEqual(asset.status_code, 200)
        asset.close()
        self.assertEqual(self.client.get("/office/assets/../../welfare_app.py").status_code, 404)
        self.assertEqual(self.client.get("/office/assets/secret.png").status_code, 404)

        src = self.client.get("/office/download/mpl2-source.zip")
        self.assertEqual(src.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(src.data)) as zf:
            names = zf.namelist()
            self.assertTrue(any(n.endswith("/LICENSE") for n in names))
            self.assertTrue(any("0003-fluent-ribbon-rendering.patch" in n for n in names))

    def test_rate_limiting_and_bandwidth_guards(self):
        from rate_limit import reset_rate_limits

        css = self.client.get("/static/css/portal.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn("max-age=86400", css.headers.get("Cache-Control", ""))
        css.close()

        robots = self.client.get("/robots.txt")
        robots_txt = robots.get_data(as_text=True)
        robots.close()
        self.assertIn("Disallow: /forms/bundle.zip", robots_txt)

        reset_rate_limits()
        welfare_app.app.config["RATELIMIT_IN_TESTS"] = True
        try:
            headers_a = {"CF-Connecting-IP": "203.0.113.10"}
            headers_b = {"CF-Connecting-IP": "203.0.113.11"}

            for _ in range(6):
                r = self.client.get("/forms/bundle.zip", headers=headers_a)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers.get("X-Robots-Tag"), "noindex, nofollow")

            blocked_zip = self.client.get("/forms/bundle.zip", headers=headers_a)
            self.assertEqual(blocked_zip.status_code, 429)
            self.assertTrue(int(blocked_zip.headers.get("Retry-After", "0")) >= 1)
            self.assertIn("잠시 후 다시 시도해 주세요", blocked_zip.get_data(as_text=True))

            # 다른 IP는 영향받지 않음
            other_ip = self.client.get("/forms/bundle.zip", headers=headers_b)
            self.assertEqual(other_ip.status_code, 200)

            # 개별 서식 다운로드는 분당 45회까지 허용 후 46회째에 차단
            for _ in range(45):
                d = self.client.get("/forms/contract-notice-form11.docx", headers=headers_a)
                self.assertEqual(d.status_code, 200)
            blocked_dl = self.client.get("/forms/contract-notice-form11.docx", headers=headers_a)
            self.assertEqual(blocked_dl.status_code, 429)

            # 헬스체크는 속도 제한에서 항상 제외
            for _ in range(20):
                self.assertEqual(self.client.get("/healthz", headers=headers_a).status_code, 200)
        finally:
            welfare_app.app.config.pop("RATELIMIT_IN_TESTS", None)
            reset_rate_limits()

    def test_practical_tools_hub_and_2026_work_hours(self):
        from daycare_data import HOLIDAYS_2026_MAP, MONTHLY_WORK_HOURS_2026

        self.assertEqual(len(MONTHLY_WORK_HOURS_2026), 12)
        expected_hours = {
            1: 168,
            2: 136,
            3: 168,
            4: 176,
            5: 144,
            6: 168,
            7: 176,
            8: 160,
            9: 160,
            10: 160,
            11: 168,
            12: 176,
        }
        for row in MONTHLY_WORK_HOURS_2026:
            m = row["month"]
            self.assertEqual(row["std_hours"], expected_hours[m])
            self.assertEqual(row["std_hours"], row["work_days"] * 8)
            self.assertEqual(row["helper_half_hours"], row["std_hours"] // 2)

        # 2026 제헌절 공휴일 복원(+30% 수가 가산 대상) vs 5.1 노동절(기준시간 제외·공휴일 수가 가산 미적용)
        self.assertTrue(HOLIDAYS_2026_MAP["2026-07-17"]["fee_addon_30"])
        self.assertFalse(HOLIDAYS_2026_MAP["2026-05-01"]["fee_addon_30"])
        self.assertTrue(HOLIDAYS_2026_MAP["2026-06-03"]["fee_addon_30"])

        tools = self.client.get("/tools")
        self.assertEqual(tools.status_code, 200)
        html = tools.get_data(as_text=True)
        for panel_id in ("tooltab-worktime", "tooltab-record", "tooltab-calendar", "tooltab-shuttle"):
            self.assertIn(f'id="{panel_id}"', html)
        self.assertIn("현재 기기 브라우저에만 저장", html)
        self.assertIn("제헌절 공휴일 복원", html)
        self.assertIn("dc-tools-data", html)


if __name__ == "__main__":
    unittest.main()

