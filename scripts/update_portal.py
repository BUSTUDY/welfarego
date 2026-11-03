"""Collect public jobs, care institutions and grant calls into atomic snapshots.

Keys are read from environment only. Errors never include URLs, response bodies
or credentials. A failed/incomplete refresh leaves the previous snapshot intact.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portal_data import KST, REGIONS, SERVICE_MAP, iso_date, normalize, region_from_address, text, today

ENDPOINTS = {
    "jobs": "https://apis.data.go.kr/B554287/sclWlfrFcltInfoInqirService2/getFcltByJoInfo2",
    "care": "https://apis.data.go.kr/B550928/searchLtcInsttService02/getLtcInsttSeachList02",
    "grants": "https://apis.data.go.kr/1051000/MoefOpenAPI/T_OPD_PBNS",
}
KEY_NAMES = {"jobs": "WELFARE_JOBS_KEY", "care": "LONGTERMCARE_KEY", "grants": "BOJO_KEY"}
RELEVANT = ("사회복지", "복지관", "요양", "장애인", "노인", "아동", "돌봄", "사회서비스",
            "비영리", "보육", "청소년", "노숙", "자활", "경로당", "사회적협동조합")


class CollectionError(Exception):
    pass


def parse_response(body):
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise CollectionError("XML 응답이 아닙니다. 제공기관의 서비스 상태를 확인하세요.") from None
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    code = next((node.text.strip() for name in ("resultCode", "returnReasonCode", "errCd")
                 for node in root.iter(name) if node.text), "")
    if code and code not in ("00", "0", "0000", "NORMAL_CODE", "INFO-000"):
        # Even malformed upstream codes must not be able to inject log content.
        safe_code = code if code.isalnum() and len(code) < 20 else "UNKNOWN"
        raise CollectionError("공공 API 오류 코드 " + safe_code + ". 활용 승인·인증키·호출 한도를 확인하세요.")
    rows = [{child.tag: child.text or "" for child in node} for node in root.iter("item")]
    total_node = root.find(".//totalCount")
    try:
        total = int(total_node.text) if total_node is not None else None
    except (TypeError, ValueError):
        raise CollectionError("전체 건수를 확인할 수 없습니다.") from None
    if not rows and total != 0:
        raise CollectionError("예상한 목록 필드를 찾지 못했습니다. 기존 데이터를 보존합니다.")
    return rows, total


def request_page(kind, key, params):
    for attempt in range(3):
        try:
            response = requests.get(ENDPOINTS[kind], params={"serviceKey": unquote(key.strip()), **params}, timeout=(10, 55))
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise CollectionError("공공 API에 연결하지 못했습니다. 기존 데이터를 보존합니다.") from None
        if (response.status_code == 429 or response.status_code >= 500) and attempt < 2:
            time.sleep(1 + attempt)
            continue
        if response.status_code != 200:
            raise CollectionError("공공 API HTTP " + str(response.status_code) + ". 기존 데이터를 보존합니다.")
        return parse_response(response.content)


def pages(kind, key, params=None, limit=500):
    records, fingerprints, expected = [], set(), None
    for page in range(1, 501):
        batch, total = request_page(kind, key, {**(params or {}), "pageNo": page, "numOfRows": limit})
        if expected is None:
            expected = total
        elif total != expected:
            raise CollectionError("수집 중 전체 건수가 변경되었습니다. 다음 수집에서 재시도합니다.")
        if total == 0:
            return []
        fingerprint = hashlib.sha256(json.dumps(batch, sort_keys=True).encode()).hexdigest()
        if fingerprint in fingerprints:
            raise CollectionError("API가 같은 페이지를 반복했습니다. 부분 데이터는 저장하지 않습니다.")
        fingerprints.add(fingerprint)
        records.extend(batch)
        if expected is not None and len(records) >= expected:
            if len(records) != expected:
                raise CollectionError("전체 건수와 수집 건수가 다릅니다.")
            return records
        if expected is None and len(batch) < limit:
            return records
        if not batch:
            raise CollectionError("전체 건수에 도달하기 전에 응답이 비었습니다.")
        time.sleep(.15)
    raise CollectionError("페이지 상한에 도달했습니다. 부분 데이터는 저장하지 않습니다.")


def job(row):
    address = " ".join(filter(None, [row.get("fcltAddr"), row.get("fcltDtl_1Addr")]))
    return normalize("jobs", {
        "id": str(row.get("fcltCd", "")) + "-" + str(row.get("seq", "")),
        "name": row.get("title"), "org": row.get("fcltNm"),
        "summary": row.get("dtyCntn"), "content": row.get("dtyCntn"),
        "region": region_from_address(address or text(row.get("wrkPrargRegn"))),
        "address": address, "type": row.get("rcrtFld") or row.get("relateJssfc"),
        "url": row.get("urllnk"), "phone": row.get("crgrTelNo") or row.get("fcltTelNo"),
        "target": row.get("applyQlfc"), "how": row.get("paperSbmtMth"),
        "salary": row.get("wageCond"), "employment": row.get("emplStle"),
        "posted": row.get("regDt"), "start": row.get("accpBgnDe"), "end": row.get("accpClseDe"),
    })


def care(row, region):
    code = text(row.get("adminPttnCd"))
    # The search API supplies the type code, not a service name, phone or street address.
    # Unverified codes are deliberately shown verbatim instead of guessed from the facility name.
    return normalize("care", {
        "id": text(row.get("longTermAdminSym")) + "-" + code,
        "name": row.get("adminNm"), "region": region,
        "district": "시군구 코드 " + text(row["siGunGuCd"]) if row.get("siGunGuCd") else "",
        "org": "국민건강보험공단", "type": row.get("adminPttnNm") or ("기관유형 " + code if code else "유형 원문 확인"),
        "registered": row.get("longTermPeribRgtDt"), "url": SERVICE_MAP["care"]["official"],
    })


def grant(row):
    identity = "|".join(text(row.get(k)) for k in ("BSNSYEAR", "PSSRP_INSTT_NM", "PBLANC_NM", "PBLANC_BEGIN_DE"))
    return normalize("grants", {
        "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
        "name": row.get("PBLANC_NM"), "org": row.get("PSSRP_INSTT_NM"),
        "summary": row.get("BSNS_SMRY"), "content": row.get("SPORT_CN"),
        "target": row.get("SPORT_TRGET_CN"), "how": row.get("REQST_RCEPT_MTH_CN"),
        "type": row.get("REALM_NM"), "phone": row.get("CHARGER_TELNO"),
        "posted": row.get("PBLANC_BEGIN_DE"),
        # Project and announcement periods are NOT application periods.
        "start": row.get("RCEPT_BEGIN_DE"), "end": row.get("RCEPT_END_DE"),
        "deadline": row.get("RCEPT_PD_DC"), "url": SERVICE_MAP["grants"]["official"],
        "region": row.get("CTPRVN_NM"), "district": row.get("SIGNGU_NM"),
    })


def collect(kind, key):
    if kind == "jobs":
        raw = pages(kind, key)
        rows = [job(row) for row in raw if str(row.get("useYn", "Y")).upper() != "N"]
    elif kind == "care":
        raw, rows = [], []
        for code, name in REGIONS.items():
            batch = pages(kind, key, {"siDoCd": code})
            raw.extend(batch)
            rows.extend(care(row, name) for row in batch)
    else:
        # Include next year's already-announced calls near year end.
        years = [today().year] + ([today().year + 1] if today().month >= 10 else [])
        raw = []
        for year in years:
            raw.extend(pages(kind, key, {"bsnsyear": str(year), "resultType": "xml"}))
        rows = [grant(row) for row in raw if any(word in " ".join(text(row.get(k)) for k in
                ("PBLANC_NM", "BSNS_SMRY", "SPORT_TRGET_CN", "SPORT_CN", "DDTLBZ_NM")) for word in RELEVANT)]
    cutoff = (today() - timedelta(days=30)).isoformat()
    if kind in ("jobs", "grants"):
        rows = [row for row in rows if not row["end"] or row["end"] >= cutoff]
    deduped = {row["id"]: row for row in rows if row["name"]}
    if raw and rows and not deduped:
        raise CollectionError("필수 필드를 확인할 수 없습니다.")
    return list(deduped.values()), len(raw)


def run(kind):
    key = next((os.environ.get(name, "").strip() for name in
               (KEY_NAMES[kind], "WELFARE_API_KEY", "GOV24_KEY", "KOSSI_KEY") if os.environ.get(name, "").strip()), "")
    if not key:
        print(kind + ": 인증키가 없습니다. " + KEY_NAMES[kind] + " 또는 WELFARE_API_KEY를 Actions Secrets에 등록하세요.", file=sys.stderr)
        return 1
    try:
        rows, raw_count = collect(kind, key)
        path = ROOT / "data" / ("portal_" + kind + ".json")
        document = {"updated": datetime.now(KST).isoformat(timespec="seconds"),
                    "source": SERVICE_MAP[kind]["source"], "source_url": SERVICE_MAP[kind]["spec"],
                    "raw_count": raw_count, "count": len(rows), "items": rows}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(path)
        print(kind + ": " + str(raw_count) + "개 조회, " + str(len(rows)) + "개 항목 저장 완료.")
        return 0
    except CollectionError as error:
        print(kind + ": " + str(error), file=sys.stderr)
        return 1
    except Exception:
        # Do not print a requests exception: it can contain the API key in the URL.
        print(kind + ": 수집 또는 저장 실패. 기존 스냅샷을 보존합니다.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=list(ENDPOINTS))
    sys.exit(run(parser.parse_args().kind))
