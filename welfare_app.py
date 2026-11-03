# -*- coding: utf-8 -*-
"""
welfarego.co.kr 전용 웹 앱.

실행: gunicorn welfare_app:app
복지 조회와 자체 검색 메타데이터만 제공하며 광고·추적 코드는 사용하지 않는다.
"""

import os

from flask import Flask, send_from_directory, jsonify

from welfare_site import welfare_bp, welfare_sitemap_urls
from portal import portal_bp
from portal_data import today as korea_today

app = Flask(__name__)

app.config["SITE_BASE"] = os.environ.get("WELFARE_SITE_BASE", "https://welfarego.co.kr").rstrip("/")

app.register_blueprint(portal_bp)
app.register_blueprint(welfare_bp)


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


@app.route("/sitemap.xml")
def sitemap():
    from xml.sax.saxutils import escape as _xe
    site = app.config["SITE_BASE"]
    today = korea_today().isoformat()

    items = []
    pages = welfare_sitemap_urls(site) + [
        ("/welfare", "0.9", "weekly"), ("/jobs", "0.8", "daily"),
        ("/care", "0.8", "weekly"), ("/benefits", "0.8", "daily"),
        ("/grants", "0.8", "daily"), ("/about", "0.3", "monthly"),
    ]
    for path, pri, freq in pages:
        items.append(f"<url><loc>{site}{_xe(path)}</loc><lastmod>{today}</lastmod>"
                     f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(items) + "</urlset>")
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
