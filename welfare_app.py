# -*- coding: utf-8 -*-
"""
welfarego.co.kr 주·야간보호시설 실무 안내 포털 웹 앱.

실행: gunicorn welfare_app:app
2026년 주·야간보호 평가매뉴얼·운영매뉴얼·최신 서식자료·사회복지시설 무료 오피스를 제공하며
광고 및 방문 추적 코드는 사용하지 않는다.
"""

import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, send_from_directory

from daycare import daycare_bp

KST = timezone(timedelta(hours=9))

app = Flask(__name__)
app.config["SITE_BASE"] = os.environ.get("WELFARE_SITE_BASE", "https://welfarego.co.kr").rstrip("/")
app.register_blueprint(daycare_bp)


def korea_today():
    return datetime.now(KST).date()


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.root_path, "robots_welfare.txt", mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    return send_from_directory(app.root_path, "llms_welfare.txt", mimetype="text/plain")


@app.route("/ads.txt")
def ads_txt():
    # 이 도메인에서는 광고 판매자를 허용하지 않는다.
    return "", 410


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "portal"),
        "favicon.svg",
        mimetype="image/svg+xml",
    )


@app.route("/sitemap.xml")
def sitemap():
    from xml.sax.saxutils import escape as _xe

    site = app.config["SITE_BASE"]
    today = korea_today().isoformat()
    pages = [
        ("/", "1.0", "weekly"),
        ("/evaluation", "0.9", "weekly"),
        ("/operations", "0.9", "weekly"),
        ("/forms", "0.9", "weekly"),
        ("/office", "0.8", "monthly"),
        ("/about", "0.4", "monthly"),
    ]
    items = [
        f"<url><loc>{site}{_xe(path)}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for path, pri, freq in pages
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(items)
        + "</urlset>"
    )
    return app.response_class(xml, mimetype="application/xml")


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


@app.after_request
def response_policy(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=(os.environ.get("FLASK_ENV") == "development"))
