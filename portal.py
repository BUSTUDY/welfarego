"""Five-service welfare portal, including the preserved eligibility search."""
import math
from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, render_template, request

from portal_data import (BENEFIT_TAGS, BENEFIT_TYPES, REGIONS, SERVICES, SERVICE_MAP,
                         dataset, present, select, today)

portal_bp = Blueprint("portal", __name__)


@portal_bp.app_context_processor
def portal_context():
    return {"services": SERVICES, "service_map": SERVICE_MAP,
            "regions": list(REGIONS.values()), "today": today(),
            "site_base": current_app.config["SITE_BASE"].rstrip("/")}


@portal_bp.route("/")
def home():
    region = request.args.get("region", "")
    if region not in REGIONS.values():
        region = ""
    feeds = {}
    for kind in ("jobs", "grants", "benefits"):
        filters = {"region": region, "sort": "recent"}
        data, rows = select(kind, filters)
        if kind == "benefits":
            featured = ("기초연금", "아동수당", "부모급여", "주거급여", "장애인연금", "긴급복지")
            rows = sorted(rows, key=lambda s: (
                bool(region and s["region"] != region),
                next((i for i, word in enumerate(featured) if word in s["name"]), len(featured)), s["name"]))
        feeds[kind] = {**data, "count": len(rows), "preview": [present(s) for s in rows[:3]]}
    closing = []
    for kind in ("jobs", "grants"):
        _, rows = select(kind, {"region": region, "status": "deadline", "sort": "deadline"})
        closing.extend(present(s) for s in rows)
    closing.sort(key=lambda s: s["end"])
    return render_template("portal/home.html", active="home", region=region,
                           feeds=feeds, closing=closing[:4], benefit_total=len(dataset("benefits")["items"]))


@portal_bp.route("/jobs")
@portal_bp.route("/care")
@portal_bp.route("/benefits")
@portal_bp.route("/grants")
def listing():
    kind = request.path.strip("/")
    service = SERVICE_MAP[kind]
    filters = {k: request.args.get(k, "")[:150] for k in ("q", "region", "type", "tag", "status", "sort")}
    data, rows = select(kind, filters)
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    total = len(rows)
    pages = max(1, math.ceil(total / 12))
    page = min(page, pages)
    categories = BENEFIT_TYPES if kind == "benefits" else sorted({s["type"] for s in data["items"] if s["type"]})
    if kind == "care":
        categories.sort(key=lambda value: (value.startswith("기관유형 "), value))
    def page_url(number):
        return service["path"] + "?" + urlencode({**{k: v for k, v in filters.items() if v}, "page": number})
    return render_template("portal/listing.html", active=kind, service=service, kind=kind,
                           filters=filters, data=data, rows=[present(s) for s in rows[(page-1)*12:page*12]],
                           total=total, page=page, pages=pages, page_url=page_url,
                           categories=categories, tags=BENEFIT_TAGS,
                           filtered=any(filters.get(k) for k in ("q", "region", "type", "tag", "status")))


@portal_bp.route("/saved")
def saved():
    return render_template("portal/saved.html", active="saved")


@portal_bp.route("/api/portal/saved")
def saved_records():
    ids = set(filter(None, request.args.get("ids", "").split(",")[:100]))
    records = []
    for kind in ("jobs", "grants", "care", "benefits"):
        records.extend(present(s) for s in dataset(kind)["items"] if kind + ":" + s["id"] in ids)
    response = jsonify({"items": records, "missing": sorted(ids - {s["save_key"] for s in records})})
    response.headers["Cache-Control"] = "private, no-store"
    return response


@portal_bp.route("/care/compare")
def compare():
    ids = set(request.args.get("ids", "").split(",")[:3])
    data = dataset("care")
    rows = [present(s) for s in data["items"] if s["id"] in ids]
    return render_template("portal/compare.html", active="care", rows=rows, data=data)


@portal_bp.route("/about")
def about():
    return render_template("portal/about.html", active="about")
