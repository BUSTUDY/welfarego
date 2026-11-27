# -*- coding: utf-8 -*-
"""웰페어고 주·야간보호시설 실무 포털 (메인·평가매뉴얼·운영매뉴얼·서식자료·무료 오피스)."""

import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from functools import lru_cache
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
    HOLIDAYS_2026_MAP,
    LABOR_RATIOS_2026,
    LONG_TERM_ALLOWANCE_2026,
    MONTHLY_LIMITS_2026,
    MONTHLY_WORK_HOURS_2026,
    OPS_CHAPTERS_2026,
    TRAINING_MATRIX_2026,
    load_eval_bundle,
)
from daycare_forms import (
    DAYCARE_FORMS,
    FORM_CATEGORIES,
    FORM_MAP,
    GOV_FORMS_DIR,
    build_all_forms_zip,
    build_form_docx,
    build_form_hwpx,
    build_form_xlsx,
)
from office_log import (
    record_license_certificate,
    record_office_download,
    validate_org_name,
    validate_user_count,
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

# Welfarego OFFICE 확장기능(.oxt) 및 리본 바로가기 전용 고정 리다이렉트 목적지
OFFICE_SHORTCUT_TARGETS = {
    "forms": "/forms",
    "tools": "/tools",
    "worktime": "/tools#worktime",
    "record": "/tools#record",
    "calendar": "/tools#calendar",
    "shuttle": "/tools#shuttle",
    "staffing": "/operations#staffing",
    "fees": "/operations#fees",
    "checklist": "/evaluation#checklist",
    "eval": "/evaluation#simulator",
}


def _compute_asset_ver():
    h = hashlib.sha256()
    for rel in ("static/css/portal.css", "static/js/portal.js", "static/js/backup.js"):
        p = ROOT / rel
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


ASSET_VER = _compute_asset_ver()


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
        "X-Robots-Tag": "noindex, nofollow",
    }
    return Response(payload_bytes, mimetype=mimetype, headers=headers)


@daycare_bp.app_context_processor
def portal_globals():
    from welfare_app import get_adsense_config

    bundle = load_eval_bundle()
    return {
        "today": korea_today(),
        "asset_ver": ASSET_VER,
        "site_base": current_app.config["SITE_BASE"].rstrip("/"),
        "adsense": get_adsense_config(),
        "nav_items": [
            {"key": "home", "path": "/", "label": "포털 메인"},
            {"key": "evaluation", "path": "/evaluation", "label": "주·야간보호 평가매뉴얼 (36)"},
            {"key": "operations", "path": "/operations", "label": "주·야간보호 운영매뉴얼 (2026)"},
            {"key": "tools", "path": "/tools", "label": "실무 자동화 도구"},
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
        {
            "slug": f["slug"],
            "no": f["no"],
            "title": f["title"],
            "code_badge": f["code_badge"],
            "has_gov_hwp": bool(f.get("gov_hwp_file")),
        }
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


@daycare_bp.route("/tools")
def practical_tools():
    today = korea_today()
    return render_template(
        "daycare/tools.html",
        active="tools",
        page_crumb_name="주·야간보호 실무 자동화 도구",
        default_month=today.month,
        monthly_work_hours=MONTHLY_WORK_HOURS_2026,
        holidays_map=HOLIDAYS_2026_MAP,
        monthly_limits=MONTHLY_LIMITS_2026,
        general_fees=GENERAL_FEES_2026,
        dementia_fees=DEMENTIA_FEES_2026,
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


@daycare_bp.route("/forms/<slug>.hwpx")
def download_form_hwpx(slug):
    form = FORM_MAP.get(slug)
    if not form:
        abort(404)
    org = request.args.get("org", "")
    code = request.args.get("code", "")
    data = build_form_hwpx(form, org_name=org, org_code=code)
    filename = f"2026_주야간보호_서식{form['no']}_{form['slug']}.hwpx"
    return _attachment_response(data, filename, "application/hwp+zip")


@daycare_bp.route("/forms/<slug>/gov.hwp")
def download_form_gov_hwp(slug):
    form = FORM_MAP.get(slug)
    if not form or not form.get("gov_hwp_file"):
        abort(404)
    gov_path = GOV_FORMS_DIR / form["gov_hwp_file"]
    if not gov_path.is_file():
        abort(404)
    filename = form.get("gov_hwp_name") or f"{form['slug']}_정부원본.hwp"
    return _attachment_response(gov_path.read_bytes(), filename, "application/x-hwp")


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


DEFAULT_OFFICE_EXE_URL = (
    "https://github.com/BUSTUDY/welfarego/releases/download/"
    "v26.2.7/WelfaregoOFFICE_26.2.7_Setup_x64.exe"
)


@daycare_bp.route("/office")
def free_office():
    brand = _load_office_brand()
    custom_exe_url = os.environ.get("WELFAREGO_OFFICE_EXE_URL", "").strip() or DEFAULT_OFFICE_EXE_URL
    custom_msi_url = os.environ.get("WELFAREGO_OFFICE_MSI_URL", "").strip()
    return render_template(
        "daycare/office.html",
        active="office",
        page_crumb_name="사회복지시설 무료 오피스 다운로드",
        brand=brand,
        has_custom_exe=bool(custom_exe_url),
        has_custom_msi=bool(custom_msi_url),
        dl_err=(request.args.get("dl_err") or "").strip()[:120],
        cert_err=(request.args.get("cert_err") or "").strip()[:120],
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
    ok_org, org_res = validate_org_name(request.args.get("org"))
    if not ok_org:
        return redirect(f"/office?cert_err={quote(org_res)}#officeCertSection")

    raw_users = request.args.get("users")
    if raw_users is None and request.args.get("pcs"):
        raw_users = request.args.get("pcs")
    ok_users, users_res = validate_user_count(raw_users)
    if not ok_users:
        return redirect(f"/office?cert_err={quote(str(users_res))}#officeCertSection")

    rep = (request.args.get("rep") or "").strip()[:40] or "시설장"
    user_count = int(users_res)

    if not current_app.config.get("TESTING"):
        record_license_certificate(
            org_name=org_res,
            rep_name=rep,
            user_count=user_count,
            version=brand.get("package_version", "26.2.7"),
        )

    return render_template(
        "daycare/office_certificate.html",
        brand=brand,
        org_name=org_res,
        rep_name=rep,
        user_count=user_count,
    )


@daycare_bp.route("/office/download/setup")
def download_office_setup():
    ok_org, org_res = validate_org_name(request.args.get("org"))
    if not ok_org:
        return redirect(f"/office?dl_err={quote(org_res)}#officeDownloadForm")

    ok_users, users_res = validate_user_count(request.args.get("users"))
    if not ok_users:
        return redirect(f"/office?dl_err={quote(str(users_res))}#officeDownloadForm")

    brand = _load_office_brand()
    target_kind = (request.args.get("format") or "exe").strip().lower()
    if target_kind not in ("exe", "msi"):
        target_kind = "exe"

    if not current_app.config.get("TESTING"):
        record_office_download(
            org_name=org_res,
            user_count=int(users_res),
            version=brand.get("package_version", "26.2.7"),
            fmt=target_kind,
        )

    if target_kind == "msi":
        custom = os.environ.get("WELFAREGO_OFFICE_MSI_URL", "").strip()
        if custom.startswith(("https://", "http://")):
            return redirect(custom)
        return redirect(DEFAULT_OFFICE_EXE_URL)

    custom = os.environ.get("WELFAREGO_OFFICE_EXE_URL", "").strip()
    if custom.startswith(("https://", "http://")):
        return redirect(custom)
    return redirect(DEFAULT_OFFICE_EXE_URL)


@lru_cache(maxsize=2)
def _build_mpl2_source_zip(ver):
    buf = io.BytesIO()
    include_roots = ["LICENSE", "NOTICE", "README.md", "legal", "patches", "config", "installer", "extensions"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in include_roots:
            p = OFFICE_DIR / item
            if p.is_file():
                zf.write(p, arcname=f"WelfaregoOFFICE_{ver}_MPL2/{item}")
            elif p.is_dir():
                for sub in sorted(p.rglob("*")):
                    if sub.is_file() and "__pycache__" not in sub.parts:
                        rel = sub.relative_to(OFFICE_DIR)
                        zf.write(sub, arcname=f"WelfaregoOFFICE_{ver}_MPL2/{rel.as_posix()}")
    return buf.getvalue()


@daycare_bp.route("/office/download/mpl2-source.zip")
def download_office_mpl2_source():
    brand = _load_office_brand()
    ver = brand.get("package_version", "26.2.7.3")
    return _attachment_response(
        _build_mpl2_source_zip(ver),
        f"WelfaregoOFFICE_{ver}_MPL2_Source_Patches.zip",
        "application/zip",
    )


@daycare_bp.route("/office/download/welfarego-links.oxt")
def download_office_links_oxt():
    oxt_path = OFFICE_DIR / "extensions" / "welfarego-links.oxt"
    if not oxt_path.is_file():
        abort(404)
    return _attachment_response(
        oxt_path.read_bytes(),
        "Welfarego_Office_Shortcuts_26.2.7.oxt",
        "application/vnd.openofficeorg.extension",
    )


@daycare_bp.route("/office/update.xml")
def office_extension_update_xml():
    site = current_app.config["SITE_BASE"].rstrip("/")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<description xmlns="http://openoffice.org/extensions/update/2006"\n'
        '  xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        '  <identifier value="kr.co.welfarego.office.links"/>\n'
        '  <version value="26.2.7"/>\n'
        '  <update-download>\n'
        f'    <src xlink:href="{site}/office/download/welfarego-links.oxt"/>\n'
        '  </update-download>\n'
        '  <release-notes>\n'
        f'    <src xlink:href="{site}/office" lang="ko"/>\n'
        '  </release-notes>\n'
        '</description>\n'
    )
    return Response(xml, mimetype="application/xml; charset=utf-8")


@daycare_bp.route("/go/<target>")
def office_shortcut_redirect(target):
    dest = OFFICE_SHORTCUT_TARGETS.get(target)
    if not dest:
        abort(404)
    resp = redirect(dest, code=302)
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Cache-Control"] = "no-store"
    return resp


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
