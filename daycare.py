# -*- coding: utf-8 -*-
"""웰페어고 주·야간보호시설 실무 포털 (메인·평가매뉴얼·운영매뉴얼·서식자료·무료 오피스)."""

import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
)

from daycare_data import (
    AUDIT_CASES_2026,
    DEMENTIA_FEES_2026,
    GENERAL_FEES_2026,
    LABOR_RATIOS_2026,
    LONG_TERM_ALLOWANCE_2026,
    MONTHLY_LIMITS_2026,
    OPS_CHAPTERS_2026,
    TRAINING_MATRIX_2026,
    load_eval_bundle,
)
from daycare_forms import (
    DAYCARE_FORMS,
    FORM_CATEGORIES,
    FORM_MAP,
    build_all_forms_zip,
    build_form_docx,
    build_form_xlsx,
)

daycare_bp = Blueprint("daycare", __name__)

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
OFFICE_DIR = ROOT / "office"
ALLOWED_OFFICE_ASSETS = {
    "writer_app.png",
    "calc_app.png",
    "impress_app.png",
    "draw_app.png",
    "base_app.png",
    "math_app.png",
    "soffice.png",
    "logo.svg",
    "logo-sc.svg",
}


def korea_today():
    return datetime.now(KST).date()


def _load_office_brand():
    brand_path = OFFICE_DIR / "branding" / "brand.json"
    try:
        return json.loads(brand_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "product_name": "Welfarego OFFICE",
            "package_version": "26.2.7.3",
            "release_notes_url": "https://github.com/BUSTUDY/welfarego/releases",
        }


def _attachment_response(payload_bytes, filename, mimetype):
    encoded = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        "Cache-Control": "no-store",
    }
    return Response(payload_bytes, mimetype=mimetype, headers=headers)


@daycare_bp.app_context_processor
def portal_globals():
    bundle = load_eval_bundle()
    return {
        "today": korea_today(),
        "site_base": current_app.config["SITE_BASE"].rstrip("/"),
        "nav_items": [
            {"key": "home", "path": "/", "label": "포털 메인"},
            {"key": "evaluation", "path": "/evaluation", "label": "주·야간보호 평가매뉴얼 (36)"},
            {"key": "operations", "path": "/operations", "label": "주·야간보호 운영매뉴얼 (2026)"},
            {"key": "forms", "path": "/forms", "label": "최신 서식자료실 (20종)"},
            {"key": "office", "path": "/office", "label": "무료 오피스 다운로드"},
        ],
        "global_eval_summary_indicators": [
            {
                "id": ind["id"],
                "domain": ind["domain"],
                "criteria": [
                    {
                        "no": c["no"],
                        "maxScore": c["maxScore"],
                        "linkedTo": c.get("linkedTo"),
                        "options": [{"score": o["score"], "isNA": bool(o.get("isNA"))} for o in c["options"]],
                    }
                    for c in ind["criteria"]
                ],
                "docsCount": len(ind.get("docs", [])),
            }
            for ind in bundle["indicators"]
        ],
    }


@daycare_bp.route("/")
def home():
    bundle = load_eval_bundle()
    return render_template(
        "daycare/home.html",
        active="home",
        page_crumb_name="웰페어고 주·야간보호 실무 포털",
        eval_bundle=bundle,
        forms_count=len(DAYCARE_FORMS),
        featured_forms=DAYCARE_FORMS[:6],
        monthly_limits=MONTHLY_LIMITS_2026,
    )


@daycare_bp.route("/evaluation")
def evaluation():
    bundle = load_eval_bundle()
    forms_lite = [
        {"slug": f["slug"], "no": f["no"], "title": f["title"], "code_badge": f["code_badge"]}
        for f in DAYCARE_FORMS
    ]
    return render_template(
        "daycare/evaluation.html",
        active="evaluation",
        page_crumb_name="2026 주·야간보호 평가매뉴얼",
        eval_bundle=bundle,
        forms_lite=forms_lite,
    )


@daycare_bp.route("/operations")
def operations():
    return render_template(
        "daycare/operations.html",
        active="operations",
        page_crumb_name="2026 주·야간보호 운영매뉴얼",
        monthly_limits=MONTHLY_LIMITS_2026,
        general_fees=GENERAL_FEES_2026,
        dementia_fees=DEMENTIA_FEES_2026,
        labor_ratios=LABOR_RATIOS_2026,
        long_term_allowance=LONG_TERM_ALLOWANCE_2026,
        training_matrix=TRAINING_MATRIX_2026,
        ops_chapters=OPS_CHAPTERS_2026,
        audit_cases=AUDIT_CASES_2026,
    )


@daycare_bp.route("/forms")
def forms_library():
    return render_template(
        "daycare/forms.html",
        active="forms",
        page_crumb_name="2026 주·야간보호 최신 서식자료실",
        categories=FORM_CATEGORIES,
        forms=DAYCARE_FORMS,
    )


@daycare_bp.route("/forms/<slug>/print")
def form_print(slug):
    form = FORM_MAP.get(slug)
    if not form:
        abort(404)
    org = (request.args.get("org") or "").strip()[:80] or "○○주·야간보호센터"
    code = (request.args.get("code") or "").strip()[:40] or "장기요양기관기호 미입력"
    return render_template("daycare/form_print.html", form=form, org_name=org, org_code=code)


@daycare_bp.route("/forms/<slug>.docx")
def download_form_docx(slug):
    form = FORM_MAP.get(slug)
    if not form:
        abort(404)
    org = request.args.get("org", "")
    code = request.args.get("code", "")
    data = build_form_docx(form, org_name=org, org_code=code)
    filename = f"2026_주야간보호_서식{form['no']}_{form['slug']}.docx"
    return _attachment_response(
        data,
        filename,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@daycare_bp.route("/forms/<slug>.xlsx")
def download_form_xlsx(slug):
    form = FORM_MAP.get(slug)
    if not form:
        abort(404)
    org = request.args.get("org", "")
    code = request.args.get("code", "")
    data = build_form_xlsx(form, org_name=org, org_code=code)
    filename = f"2026_주야간보호_서식{form['no']}_{form['slug']}.xlsx"
    return _attachment_response(
        data,
        filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@daycare_bp.route("/forms/bundle.zip")
def download_forms_bundle():
    org = request.args.get("org", "")
    code = request.args.get("code", "")
    data = build_all_forms_zip(org_name=org, org_code=code)
    return _attachment_response(
        data,
        "2026_주야간보호_최신표준서식_20종_전체패키지.zip",
        "application/zip",
    )


@daycare_bp.route("/office")
def free_office():
    brand = _load_office_brand()
    custom_exe_url = os.environ.get("WELFAREGO_OFFICE_EXE_URL", "").strip()
    custom_msi_url = os.environ.get("WELFAREGO_OFFICE_MSI_URL", "").strip()
    return render_template(
        "daycare/office.html",
        active="office",
        page_crumb_name="사회복지시설 무료 오피스 다운로드",
        brand=brand,
        has_custom_exe=bool(custom_exe_url),
        has_custom_msi=bool(custom_msi_url),
    )


@daycare_bp.route("/office/preview")
def free_office_preview():
    preview_file = OFFICE_DIR / "preview" / "ribbon-design-preview.html"
    if not preview_file.exists():
        abort(404)
    raw_html = preview_file.read_text(encoding="utf-8")
    back_bar = (
        '<div style="max-width:1080px;margin:0 auto 12px;display:flex;justify-content:space-between;'
        'align-items:center;gap:12px;font-size:13px;">'
        '<a href="/office" style="color:#003675;font-weight:700;text-decoration:none;">'
        '&larr; 웰페어고 무료 오피스 다운로드 페이지로 돌아가기</a>'
        '<a href="/forms" style="color:#334155;text-decoration:none;">'
        '주·야간보호 표준서식 20종 받기 &rarr;</a></div>'
    )
    injected = raw_html.replace('<div class="wrap">', back_bar + '<div class="wrap">', 1)
    return Response(injected, mimetype="text/html; charset=utf-8")


@daycare_bp.route("/office/license-certificate")
def office_license_certificate():
    brand = _load_office_brand()
    org = (request.args.get("org") or "").strip()[:80] or "○○사회복지시설 (주·야간보호센터)"
    rep = (request.args.get("rep") or "").strip()[:40] or "시설장"
    pcs = (request.args.get("pcs") or "").strip()[:20] or "시설 내 업무용 PC 전체"
    return render_template(
        "daycare/office_certificate.html",
        brand=brand,
        org_name=org,
        rep_name=rep,
        pc_scope=pcs,
    )


@daycare_bp.route("/office/download/setup")
def download_office_setup():
    target_kind = request.args.get("format", "exe")
    if target_kind == "msi":
        custom = os.environ.get("WELFAREGO_OFFICE_MSI_URL", "").strip()
        if custom.startswith(("https://", "http://")):
            return redirect(custom)
        return redirect("https://www.libreoffice.org/download/download-libreoffice/?type=win-x86_64&lang=ko")

    custom = os.environ.get("WELFAREGO_OFFICE_EXE_URL", "").strip()
    if custom.startswith(("https://", "http://")):
        return redirect(custom)
    return redirect("https://www.libreoffice.org/download/download-libreoffice/?type=win-x86_64&lang=ko")


@daycare_bp.route("/office/download/mpl2-source.zip")
def download_office_mpl2_source():
    brand = _load_office_brand()
    ver = brand.get("package_version", "26.2.7.3")
    buf = io.BytesIO()
    include_roots = ["LICENSE", "NOTICE", "README.md", "legal", "patches", "config", "installer"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in include_roots:
            p = OFFICE_DIR / item
            if p.is_file():
                zf.write(p, arcname=f"WelfaregoOFFICE_{ver}_MPL2/{item}")
            elif p.is_dir():
                for sub in sorted(p.rglob("*")):
                    if sub.is_file():
                        rel = sub.relative_to(OFFICE_DIR)
                        zf.write(sub, arcname=f"WelfaregoOFFICE_{ver}_MPL2/{rel.as_posix()}")
    return _attachment_response(
        buf.getvalue(),
        f"WelfaregoOFFICE_{ver}_MPL2_Source_Patches.zip",
        "application/zip",
    )


@daycare_bp.route("/office/assets/<path:filename>")
def office_asset(filename):
    if filename not in ALLOWED_OFFICE_ASSETS:
        abort(404)
    img_dir = OFFICE_DIR / "branding" / "images"
    return send_from_directory(img_dir, filename)


@daycare_bp.route("/about")
def about():
    return render_template(
        "daycare/about.html",
        active="about",
        page_crumb_name="포털 안내 · 공식 출처 · 개인정보",
    )


# 호환 리다이렉트 (/daycare* -> 루트 하위 경로)
@daycare_bp.route("/daycare")
def legacy_daycare():
    return redirect("/", code=301)


@daycare_bp.route("/daycare/evaluation")
def legacy_eval():
    return redirect("/evaluation", code=301)


@daycare_bp.route("/daycare/operations")
def legacy_ops():
    return redirect("/operations", code=301)


@daycare_bp.route("/daycare/forms")
def legacy_forms():
    return redirect("/forms", code=301)
