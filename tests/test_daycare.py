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

    def test_homepage_uses_gov_portal_design_and_links_to_subsites(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for path in ("/evaluation", "/operations", "/forms", "/office", "/about"):
            self.assertIn(f'href="{path}"', html)
        self.assertIn("site-header", html)
        self.assertIn("id=\"drawer\"", html)
        self.assertIn("hdrScore", html)
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

        ops = self.client.get("/operations")
        self.assertEqual(ops.status_code, 200)
        ops_html = ops.get_data(as_text=True)
        self.assertIn("2,512,900원", ops_html)
        self.assertIn("69,730", ops_html)
        self.assertIn("81,270", ops_html)
        self.assertIn("제2026-189호", ops_html)
        self.assertIn("48.6%", ops_html)

        forms = self.client.get("/forms")
        self.assertEqual(forms.status_code, 200)
        forms_html = forms.get_data(as_text=True)
        self.assertEqual(len(DAYCARE_FORMS), 20)
        self.assertIn("별지 제15호서식", forms_html)
        self.assertIn("/forms/bundle.zip", forms_html)

    def test_all_20_forms_generate_valid_docx_xlsx_and_print(self):
        for form in DAYCARE_FORMS:
            slug = form["slug"]
            with self.subTest(slug=slug):
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

        self.assertEqual(self.client.get("/forms/nonexistent.docx").status_code, 404)
        self.assertEqual(self.client.get("/forms/nonexistent.xlsx").status_code, 404)
        self.assertEqual(self.client.get("/forms/nonexistent/print").status_code, 404)

    def test_forms_bundle_zip_contains_all_40_files_and_readme(self):
        resp = self.client.get("/forms/bundle.zip?org=샘플센터")
        self.assertEqual(resp.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(resp.data)) as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 41)
            self.assertIn("00_서식목록_및_사용안내.txt", names)
            self.assertEqual(sum(1 for n in names if n.endswith(".docx")), 20)
            self.assertEqual(sum(1 for n in names if n.endswith(".xlsx")), 20)

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


if __name__ == "__main__":
    unittest.main()
