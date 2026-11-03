"""Read cached public data. Page views never call an upstream API."""
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
REGIONS = {
    "11": "서울특별시", "12": "전남광주통합특별시", "26": "부산광역시", "27": "대구광역시",
    "28": "인천광역시", "30": "대전광역시",
    "31": "울산광역시", "36": "세종특별자치시", "41": "경기도",
    "43": "충청북도", "44": "충청남도",
    "47": "경상북도", "48": "경상남도", "50": "제주특별자치도",
    "51": "강원특별자치도", "52": "전북특별자치도",
}
REGION_ALIASES = {"강원도": "강원특별자치도", "전라북도": "전북특별자치도",
                  "광주광역시": "전남광주통합특별시", "전라남도": "전남광주통합특별시"}
SERVICES = [
    {"key": "welfare", "path": "/welfare", "name": "복지서비스 검색", "short": "맞춤 복지검색",
     "icon": "search", "color": "green", "audience": "나와 가족을 위한",
     "description": "나이·지역·소득을 입력하고\n내 조건에 맞는 지원을 찾아보세요."},
    {"key": "jobs", "path": "/jobs", "name": "복지시설 일자리", "short": "복지 일자리",
     "icon": "briefcase", "color": "blue", "audience": "새로운 시작을 위한",
     "description": "우리 지역 사회복지시설의\n채용공고와 마감일을 확인하세요.",
     "source": "한국사회보장정보원", "spec": "https://www.data.go.kr/data/15001848/openapi.do",
     "official": "https://www.w4c.go.kr/", "official_name": "사회복지시설정보시스템"},
    {"key": "care", "path": "/care", "name": "부모님 돌봄기관", "short": "돌봄기관 찾기",
     "icon": "heart", "color": "rose", "audience": "부모님의 편안한 일상을 위한",
     "description": "요양시설·주야간보호·방문요양,\n가족에게 필요한 기관을 찾아보세요.",
     "source": "국민건강보험공단", "spec": "https://www.data.go.kr/data/15059029/openapi.do",
     "official": "https://www.longtermcare.or.kr/npbs/r/a/201/selectLtcoSrch.web?menuId=npe0000000650",
     "official_name": "노인장기요양보험 기관 검색"},
    {"key": "benefits", "path": "/benefits", "name": "우리 동네 복지혜택", "short": "동네 복지혜택",
     "icon": "pin", "color": "amber", "audience": "우리 동네의 든든한 생활을 위한",
     "description": "생활·주거·돌봄·교육까지,\n지역과 관심 분야로 살펴보세요.",
     "source": "정부24·한국사회보장정보원", "spec": "https://www.data.go.kr/data/15090532/openapi.do",
     "official": "https://www.bokjiro.go.kr/", "official_name": "복지로"},
    {"key": "grants", "path": "/grants", "name": "시설 공공 지원사업", "short": "시설 지원사업",
     "icon": "gift", "color": "violet", "audience": "더 나은 시설 운영을 위한",
     "description": "시설에서 신청할 공공 공모와\n지원사업의 접수 일정을 살펴보세요.",
     "source": "보조금 통합포털", "spec": "https://www.data.go.kr/data/15097584/openapi.do",
     "official": "https://www.bojo.go.kr/", "official_name": "보조금 통합포털"},
]
SERVICE_MAP = {s["key"]: s for s in SERVICES}
BENEFIT_TYPES = ["생활안정", "주거·자립", "보건·의료", "보호·돌봄", "보육·교육", "임신·출산", "고용·창업", "서민금융"]
BENEFIT_TAGS = ["청년", "노년", "장애인", "영유아", "한부모", "다자녀", "저소득", "1인가구"]
# Confirmed against NHIS's public service-type search on 2026-11-03.
# Keep unknown codes verbatim; never infer a type from the institution's name.
CARE_TYPES = {"A03": "노인요양시설", "A04": "노인요양공동생활가정", "S41": "노인요양공동생활가정",
              "B01": "방문요양", "C01": "방문요양", "B02": "방문목욕", "C02": "방문목욕",
              "B05": "방문간호", "C05": "방문간호", "B03": "주야간보호", "C03": "주야간보호",
              "B04": "단기보호", "C04": "단기보호", "B06": "복지용구", "C06": "복지용구"}
try:
    CARE_DISTRICTS = json.loads((ROOT / "data" / "care_districts.json").read_text(encoding="utf-8"))["regions"]
except (OSError, ValueError, KeyError):
    CARE_DISTRICTS = {}


def now():
    return datetime.now(KST)


def today():
    return now().date()


def text(value):
    """API descriptions sometimes contain HTML. Display them as plain text."""
    return html.unescape(re.sub(r"<[^>]*>", " ", str(value or ""))).strip()


def safe_url(value):
    value = str(value or "").strip()
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return ""


def iso_date(value):
    value = str(value or "").strip()
    match = re.match(r"^(\d{4})[-./]?(\d{2})[-./]?(\d{2})(?:$|[ T])", value)
    if match:
        try:
            return datetime(*map(int, match.groups())).date().isoformat()
        except ValueError:
            pass
    return ""


def normal_region(value):
    value = text(value)
    return REGION_ALIASES.get(value, value)


def region_from_address(address):
    for region in list(REGIONS.values()) + list(REGION_ALIASES):
        if region in address:
            return normal_region(region)
    for short, region in {"서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
                          "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
                          "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도",
                          "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
                          "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도",
                          "경남": "경상남도", "제주": "제주특별자치도"}.items():
        if address.startswith(short + " "):
            return normal_region(region)
    return ""


def normalize(kind, row):
    """Only persist public fields needed by the portal, never raw API records."""
    name = text(row.get("name"))
    identity = text(row.get("id")) or hashlib.sha256((name + str(row.get("org", ""))).encode()).hexdigest()[:20]
    region = normal_region(row.get("region"))
    if kind == "grants" and not region:
        region = region_from_address(text(row.get("org")))
    category = text(row.get("type"))
    district = text(row.get("district"))
    if kind == "care" and category.startswith("기관유형 "):
        category = CARE_TYPES.get(category.removeprefix("기관유형 "), category)
    if kind == "care" and district.startswith("시군구 코드 "):
        district = CARE_DISTRICTS.get(region, {}).get(district.removeprefix("시군구 코드 "), district)
    return {
        "id": identity, "kind": kind, "name": name, "org": text(row.get("org")),
        "summary": text(row.get("summary")), "region": region,
        "district": district, "address": text(row.get("address")),
        "type": category, "tags": [text(t) for t in row.get("tags", []) if t],
        "url": safe_url(row.get("url")), "phone": text(row.get("phone")),
        "posted": iso_date(row.get("posted")), "start": iso_date(row.get("start")),
        "end": iso_date(row.get("end")), "deadline": text(row.get("deadline")),
        "end_time": text(row.get("end_time")) if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(row.get("end_time", ""))) else "",
        "target": text(row.get("target")), "content": text(row.get("content")),
        "how": text(row.get("how")), "salary": text(row.get("salary")),
        "employment": text(row.get("employment")), "registered": iso_date(row.get("registered")),
    }


@lru_cache(maxsize=8)
def _read(path, mtime, size):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    kind = "benefits" if path.endswith("welfare_services.json") else Path(path).stem.removeprefix("portal_")
    rows = []
    for original in document.get("items", []):
        row = dict(original)
        if kind == "benefits":
            row.update(region=original.get("sido"), district=original.get("sigungu"),
                       type=original.get("field"), phone=original.get("tel"))
        item = normalize(kind, row)
        if item["name"]:
            rows.append(item)
    return {"items": rows, "updated": document.get("updated", ""), "available": True}


def dataset(kind):
    filename = "welfare_services.json" if kind == "benefits" else "portal_" + kind + ".json"
    path = ROOT / "data" / filename
    try:
        stat = path.stat()
        result = dict(_read(str(path), stat.st_mtime_ns, stat.st_size))
    except (OSError, ValueError, TypeError):
        result = {"items": [], "updated": "", "available": False}
    updated = iso_date(result["updated"])
    result["stale"] = bool(updated and (today() - datetime.fromisoformat(updated).date()).days > 3)
    result["updated_label"] = str(result["updated"])[:16].replace("T", " ")
    return result


def status(item):
    current = today().isoformat()
    if item["end"] and item["end"] < current:
        return "closed", "마감"
    if item["end"] == current and item.get("end_time") and item["end_time"] < now().strftime("%H:%M"):
        return "closed", "마감"
    if item["start"] and item["start"] > current:
        return "scheduled", "접수 예정"
    if item["end"] and (not item["start"] or item["start"] <= current):
        days = (datetime.fromisoformat(item["end"]).date() - today()).days
        return "open", "오늘 마감" if days == 0 else "D-" + str(days)
    return "unknown", "일정 확인"


def present(item):
    item = dict(item)
    item["status"], item["status_label"] = status(item)
    item["location"] = " ".join(filter(None, [item["region"], item["district"]])) or "지역 원문 확인"
    item["save_key"] = item["kind"] + ":" + item["id"]
    item["detail_url"] = "/s/" + item["id"] if item["kind"] == "benefits" else ""
    if item["kind"] == "care":
        match = re.fullmatch(r"(\d{11})-([A-Z]\d{2})", item["id"])
        if match:
            item["url"] = ("https://www.longtermcare.or.kr/npbs/r/a/201/selectLtcoSrchDetail.web?ltcAdminSym="
                           + match.group(1) + "&adminPttnCd=" + match.group(2) + "&aTab=11")
    return item


def select(kind, filters):
    data = dataset(kind)
    items = data["items"]
    q = filters.get("q", "").strip().casefold()
    region, category, tag = filters.get("region", ""), filters.get("type", ""), filters.get("tag", "")
    state = filters.get("status", "all")
    if q:
        terms = q.split()
        items = [s for s in items if all(t in " ".join([s["name"], s["org"], s["summary"], s["target"], s["region"], s["district"], s["address"], s["type"], " ".join(s["tags"])]).casefold() for t in terms)]
    if region:
        # National benefits apply in every region. A missing facility region is unknown, not nationwide.
        items = [s for s in items if s["region"] == region or (kind == "benefits" and not s["region"])]
    if category:
        items = [s for s in items if category in s["type"]]
    if tag:
        items = [s for s in items if tag in s["tags"]]
    if kind in ("jobs", "grants"):
        if state == "open":
            items = [s for s in items if status(s)[0] == "open"]
        elif state == "deadline":
            items = [s for s in items if status(s)[0] == "open" and 0 <= (datetime.fromisoformat(s["end"]).date() - today()).days <= 7]
        elif state == "new":
            items = [s for s in items if s["posted"] == today().isoformat() and status(s)[0] != "closed"]
        elif state == "closed":
            items = [s for s in items if status(s)[0] == "closed"]
        else:
            items = [s for s in items if status(s)[0] != "closed"]
    sort = filters.get("sort") or ("relevance" if q else "name" if kind in ("care", "benefits") else "recent")
    if sort == "deadline":
        items = sorted(items, key=lambda s: (s["end"] or "9999", s["name"]))
    elif sort == "relevance":
        items = sorted(items, key=lambda s: -sum(
            8 * (term in s["name"].casefold()) + 4 * (term in s["type"].casefold())
            + 2 * (term in s["summary"].casefold()) + (term in s["org"].casefold()) for term in q.split()))
    elif kind == "benefits" or sort == "name":
        items = sorted(items, key=lambda s: ((s["region"] != region) if region and kind == "benefits" else bool(s["region"]), s["name"]))
    else:
        items = sorted(items, key=lambda s: (s["posted"], s["name"]), reverse=True)
    return data, items
