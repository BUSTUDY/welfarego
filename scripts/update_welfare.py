# -*- coding: utf-8 -*-
"""
웰페어고 복지서비스 조회 — 보조금24 API 수집기.

사용법
------
  export GOV24_KEY="발급받은_디코딩_인증키"

  python scripts/update_welfare.py --probe    # 실제 필드명/조건코드 확인 (최초 1회 필수)
  python scripts/update_welfare.py            # 전체 수집 -> data/services.json
  python scripts/update_welfare.py --dry-run  # 저장하지 않고 파싱 통계만 출력

두 번째 데이터 소스 (선택) — 한국사회보장정보원_지자체복지서비스
-----------------------------------------------------------
행정안전부(보조금24) 데이터에는 지자체가 아직 등록하지 않은 사업이 빠져 있을 수 있다.
복지로를 직접 운영하는 한국사회보장정보원의 지자체복지서비스 API를 더하면 그 틈을 메울 수 있다.

  1) https://www.data.go.kr/data/15108347/openapi.do 에서 활용신청
     (data.go.kr 계정의 일반 인증키는 여러 API에서 공용으로 쓰이는 경우가 많다.
      먼저 GOV24_KEY를 그대로 써보고, 401이 나면 그때 KOSSI_KEY를 따로 설정한다)
  2) export KOSSI_KEY="위에서 받은 키"   (생략하면 GOV24_KEY를 그대로 재사용)
  3) python scripts/update_welfare.py --probe-local   # 실제 필드명 확인 (최초 1회 필수)

KOSSI_KEY(또는 GOV24_KEY)가 없으면 이 소스는 그냥 건너뛰고 기존과 완전히 동일하게 동작한다.

두 소스는 서비스ID 체계가 서로 달라 같은 사업이 두 번 올라올 수 있다.
그래서 이름·기관·지역이 같으면 하나로 합친다(dedupe_cross_source 참고).
합칠 때 비어 있는 항목은 서로 채워 넣고, 지자체복지서비스 쪽에만 있는
새 사업만 그대로 추가한다.

트래픽 주의
-----------
개발계정은 일 10,000건 제한. 하루 1회만 돌리고 매칭·필터링은
저장된 JSON에서 처리한다. 사용자 요청마다 API를 부르면 한도가 터진다.
지자체복지서비스 API는 개발계정 트래픽이 더 낮을 수 있다(사이트에 명시된 값 확인).
계속 실패하면 data.go.kr에서 "활용사례 등록"으로 운영계정 트래픽 증설을 신청한다.
"""

import argparse
import re
from urllib.parse import quote, quote_plus, unquote
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests

import welfare_parsers as parsers
import welfare_regions as regions

BASE = "https://api.odcloud.kr/api/gov24/v3"
KEY = os.environ.get("GOV24_KEY", "")
PER_PAGE = 500
OUT = Path(__file__).resolve().parent.parent / "data" / "welfare_services.json"

# --- 두 번째 소스: 한국사회보장정보원_지자체복지서비스 (선택, 명시적 옵트인) ---
# --- 두 번째 소스: 한국사회보장정보원_지자체복지서비스 (선택, 명시적 옵트인) ---
# GOV24_KEY가 있다고 자동으로 이 소스를 켜지는 않는다. 활용신청을 아직 안 했는데
# 매일 401 오류만 쌓이는 걸 막기 위해서다. KOSSI_KEY를 따로(값은 같아도 되니
# 그대로 복사해도 된다) 설정해야만 이 소스를 시도한다.
KOSSI_KEY = os.environ.get("KOSSI_KEY", "")

# 포털 "개발계정 상세보기" 화면에 명시된 실제 End Point.
#   https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations
# 오퍼레이션명(LcgvWelfarelist)은 처음엔 문서를 못 봐서 여러 번 추측이 틀렸었다
# (LocalWelfarelistV001 등). 실제 코드표(.doc)에도 요청 URL은 안 나와 있어서,
# 후보를 자동으로 시도하는 --probe-local 로 직접 찾아 확정했다.
KOSSI_BASE = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"
KOSSI_LIST_OP = "LcgvWelfarelist"
KOSSI_DETAIL_OP = "LcgvWelfaredetailed"

# 수집 결과가 기존 대비 이 비율 미만이면 저장을 거부한다.
# API 장애 시 빈 파일로 덮어써서 사이트가 비는 사고를 막는다.
# 수집 건수가 기존의 이 비율보다 적으면 저장하지 않고 기존 파일을 지킨다.
# 예전 값 0.5 는 너무 헐거웠다. 2026-08-02 에 지자체 소스가 통째로 빠져
# 14,896 → 10,964건(73%)이 됐는데 50% 문턱을 통과해 그대로 저장됐다.
# 실제 일별 변동은 97~102% 범위라 0.9 로 잡아도 여유가 충분하다.
MIN_KEEP_RATIO = 0.9

# 소스별 수집 실패를 모아 둔다. 하나라도 실패하면 저장하지 않는다.
SOURCE_FAILURES = []

# API 필드명이 문서와 다를 수 있어 후보를 여러 개 둔다. --probe로 확인 후 확정.
# 두 소스(보조금24 / 한국사회보장정보원)가 같은 개념을 다른 이름으로 부른다.
# pick()이 후보를 순서대로 찾으므로, 후보를 넉넉히 둬도 먼저 있는 값을 쓸 뿐
# 잘못될 위험이 없다. --probe / --probe-local 로 실제 이름을 확인해 다듬는다.
FIELD_MAP = {
    "id":        ["서비스ID", "서비스아이디", "servId", "wlfareInfoId"],
    "name":      ["서비스명", "servNm", "wlfareInfoNm"],
    "summary":   ["서비스목적요약", "서비스목적", "servDgst", "wlfareInfoOutlCn"],
    "org":       ["소관기관명", "소관기관", "jurMnofNm", "jurOrgNm", "bizChrDeptNm",
                  "sprtInstNm"],
    "dept":      ["부서명", "소관부서명", "sprtInstCd"],
    "target":    ["지원대상", "sprtTrgtCn", "tgtrDtlCn"],
    "criteria":  ["선정기준", "slctCritCn"],
    "content":   ["지원내용", "alwServCn"],
    "sprt_type": ["지원유형", "지원형태", "sprtCycNm", "srvPvsnNm"],
    "field":     ["서비스분야", "servDvcd", "intrsThemaNmArray", "lifeNmArray"],
    "usr_type":  ["사용자구분", "사용자유형"],
    "deadline":  ["신청기한", "신청기간", "aplyPrdCn"],
    "how":       ["신청방법", "aplyMtdCn", "aplyMtdNm"],
    "docs":      ["구비서류", "제출서류"],
    "reception": ["접수기관", "접수기관명", "rcptInstNm"],
    "tel":       ["전화문의", "문의처", "문의", "rprsCtadr"],
    "url":       ["상세조회URL", "온라인신청사이트URL", "servDtlLink"],
    "updated":   ["수정일시", "등록일시", "lastModYmd"],
    # 지자체복지서비스 API는 시도/시군구를 필드로 직접 준다.
    # regions.classify_org() 는 기관명 문자열만 보므로, 이 필드가 있으면
    # 기관명 파싱보다 더 믿을 만하다(값이 있을 때만 활용).
    "sido_hint":    ["시도명", "ctpvNm"],
    "sigungu_hint": ["시군구명", "sggNm"],
}

GENDER_CODES = {"남성": ["JA0101", "남성"], "여성": ["JA0102", "여성"]}
MARITAL_CODES = {
    "single":        ["JA0201", "미혼"],
    "married":       ["JA0202", "기혼"],
    "single_parent": ["JA0311", "JA0312", "한부모", "조손"],
}

# UI로 내보낼 필드. 파싱·분류에만 쓰인 필드(criteria/docs/dept/reception 등)는
# 브라우저로 보내지 않는다 — 9천 건이면 파일이 수 MB 커지기 때문.
KEEP_FIELDS = (
    "id name summary org target content sprt_type field deadline how "
    "tel url tier sido sigungu gender marital needs_child preg "
    "child_age_max_months child_age_max_years age_min age_max income_max_pct income_min_pct tags special job"
).split()

# 긴 텍스트는 잘라서 내보낸다 (상세는 어차피 신청 페이지 링크로 확인)
TRUNC = {"name": 120, "summary": 220, "org": 60, "target": 320, "content": 420,
         "sprt_type": 60, "field": 60, "deadline": 140, "how": 220, "tel": 90}



# 사용자구분 필드가 "개인"이 아니라 "가구"·"세대주"·"국민" 처럼 적혀 있는
# 경우가 많다. 예전에는 "개인"이라는 글자가 없으면 전부 기업 전용으로
# 판정해서, 주거급여처럼 국민 누구나 받는 사업까지 '기업·단체 대상'으로
# 잘못 표시되어 일반 조건 검색에서 통째로 빠지는 사고가 있었다.
# 그래서 방향을 바꿔, 명시적으로 법인·단체를 가리키는 말이 있을 때만
# 기업 전용으로 본다.
_ORG_USR_TYPE_KW = ("법인", "단체", "기관", "사업자", "기업", "협회", "조합")


def is_individual(usr_type: str) -> bool:
    """개인 대상 서비스인지. '기업/법인/단체 전용'을 걸러낸다.

    이 필터가 없으면 원양선사 승선경비 지원 같은 기업 대상 사업까지
    개인 사용자 결과에 쏟아진다. 판단 불가(빈 값)거나 애매하면
    보수적으로 통과시킨다(개인으로 본다) — 놓치는 것보다 낫다.
    """
    if not usr_type:
        return True
    if "개인" in usr_type:
        return True
    return not any(k in usr_type for k in _ORG_USR_TYPE_KW)


def pick(row: dict, keys):
    for k in keys:
        v = row.get(k)
        if v not in (None, "", "null"):
            return str(v).strip()
    return ""


def safe_error(error):
    """API 인증키가 공개 Actions 로그의 오류 URL에 노출되지 않게 한다."""
    message = str(error)
    for secret in (KEY, KOSSI_KEY):
        if secret:
            for token in {secret, quote(secret, safe=""), quote_plus(secret), unquote(secret)}:
                if token:
                    message = message.replace(token, "[redacted]")
    return re.sub(r"(?i)(servicekey=)[^&\s]+", r"\1[redacted]", message)


def call(path, page=1, per_page=PER_PAGE, retries=3):
    if not KEY:
        sys.exit("GOV24_KEY 환경변수가 없습니다. data.go.kr에서 발급받은 '디코딩' 키를 넣어주세요.")
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(
                f"{BASE}/{path}",
                params={"page": page, "perPage": per_page,
                        "serviceKey": KEY, "returnType": "JSON"},
                timeout=30,
            )
            if r.status_code == 401:
                sys.exit(f"인증 실패: {r.text}\n키가 '인코딩'된 값이면 '디코딩' 키로 바꿔보세요.")
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** attempt
            print(f"  재시도 {attempt + 1}/{retries} ({safe_error(e)}) {wait}초 대기", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{path} 호출 실패: {last}")


def probe():
    """실제 응답의 필드명과 조건 코드를 확인한다. 매핑 확정 전 1회 실행."""
    for path in ("serviceList", "serviceDetail", "supportConditions"):
        try:
            data = call(path, page=1, per_page=3, retries=1)
        except Exception as e:  # noqa: BLE001
            print(f"[{path}] 호출 실패: {safe_error(e)}\n")
            continue
        rows = data.get("data") or []
        print(f"=== {path} ===  총 {data.get('totalCount', '?')}건")
        if rows:
            for k, v in rows[0].items():
                print(f"  {k:<24} : {str(v)[:60]}")
            if path == "supportConditions":
                codes = sorted({k for r in rows for k, v in r.items()
                                if str(v).upper() == "Y"})
                print(f"\n  [Y로 표시된 조건 코드 예시] {codes[:30]}")
                print("  -> 이 코드를 GENDER_CODES / MARITAL_CODES와 대조하세요.")
        print()


def fetch_all(path):
    out, page = [], 1
    while True:
        data = call(path, page=page)
        rows = data.get("data") or []
        out.extend(rows)
        total = data.get("totalCount", 0)
        print(f"  {path} {len(out)}/{total}", file=sys.stderr)
        if len(out) >= total or not rows:
            break
        page += 1
        time.sleep(0.3)
    return out


# 오퍼레이션 이름 후보. LcgvWelfarelist 가 정답으로 확인됐지만(--probe-local 로
# 직접 찾음), 혹시 API가 나중에 바뀌거나 다른 서비스를 붙일 때도 재사용할 수
# 있게 후보 탐색 방식은 그대로 남겨둔다.
KOSSI_OP_CANDIDATES = [
    "LcgvWelfarelist",
    "LcgvWelfaredetailed",
    "lcgvWelfarelist",
    "getLcgvWelfarelist",
    "LocalGovernmentWelfareInformations",
    "",            # End Point 자체가 완성형이라 뒤에 아무것도 안 붙는 경우
]


def probe_local():
    """지자체복지서비스 API 의 실제 오퍼레이션 경로와 필드명을 찾는다.

    오퍼레이션 이름 후보를 차례로 시도한다. 성공하는 것이 나오면 그 이름과
    필드 목록을 함께 출력한다.
    """
    if not KOSSI_KEY:
        print("KOSSI_KEY 가 없습니다. 먼저 GitHub Secrets 에 등록해 주세요.",
              file=sys.stderr)
        return

    print(f"기준 End Point: {KOSSI_BASE}")
    print(f"시도할 오퍼레이션 후보: {len(KOSSI_OP_CANDIDATES)}개")
    print()

    found = []
    for op in KOSSI_OP_CANDIDATES:
        label = op if op else "(오퍼레이션 없음 — End Point 직접 호출)"
        try:
            data = call_kossi(op, page=1, per_page=3, retries=1)
        except Exception as e:  # noqa: BLE001
            print(f"[실패] {label}")
            print(f"        {safe_error(e)[:200]}")
            continue

        rows, total = _kossi_rows(data)
        if rows:
            found.append(op)
            print(f"[성공] {label}  —  총 {total}건")
            print("        응답 필드:")
            for k, v in rows[0].items():
                print(f"          {k:<22} : {str(v)[:55]}")
        else:
            print(f"[응답은 옴] {label}  —  행이 비어 있음")
            print(f"        원본 앞부분: {str(data)[:250]}")
        print()

    print("=" * 60)
    if found:
        print(f"✅ 성공한 오퍼레이션: {found}")
        print("   이 이름을 KOSSI_LIST_OP 에 넣으면 됩니다.")
    else:
        print("❌ 모든 후보가 실패했습니다.")


def call_kossi(op, page=1, per_page=PER_PAGE, retries=3):
    """apis.data.go.kr 계열(한국사회보장정보원) 호출. 보조금24와 파라미터 관례가 다르다.

    공공데이터포털은 "인코딩(Encoding)" 키와 "디코딩(Decoding)" 키를 따로 낸다.
    인코딩 키에는 %2B, %2F 같은 문자가 이미 들어 있는 경우가 많은데, 이걸 그냥
    requests의 params= 에 넣으면 requests가 또 한 번 인코딩해서(%2B -> %252B)
    서비스키 자체가 깨진다. 그래서 serviceKey 는 URL 문자열에 직접 붙여
    재인코딩을 피하고, 나머지 파라미터만 params= 로 넘긴다.

    type=json 파라미터는 일부러 안 보낸다 — 이 API는 원래 XML 전용이라
    (포털 화면 "데이터포맷: XML"), type=json 을 붙이면 게이트웨이가
    오히려 응답 파싱에서 항목을 누락시키는 경우가 있었다. 그냥 XML 그대로
    받아 _xml_to_dict() 로 변환하는 편이 안정적이다.
    """
    if not KOSSI_KEY:
        return {}
    last = None
    path = f"{KOSSI_BASE}/{op}" if op else KOSSI_BASE
    url = f"{path}?serviceKey={KOSSI_KEY}"
    for attempt in range(retries):
        try:
            r = requests.get(
                url,
                params={"pageNo": page, "numOfRows": per_page},
                timeout=30,
            )
            if r.status_code in (401, 500):
                raise RuntimeError(f"호출 실패({r.status_code}): {r.text[:300]}")
            r.raise_for_status()

            text = r.text.strip()
            if text.startswith("<"):
                return _xml_to_dict(text)
            try:
                return r.json()
            except ValueError:
                return _xml_to_dict(text)
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** attempt
            print(f"  [KOSSI] 재시도 {attempt + 1}/{retries} ({safe_error(e)}) {wait}초 대기",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{op} 호출 실패: {last}")


def _xml_to_dict(text):
    """공공데이터포털 XML 응답을 _kossi_rows() 가 읽을 수 있는 모양으로 바꾼다.

    이 API는 개별 항목을 <item> 이 아니라 <servList> 태그로 감싼다
    (--probe-local 로 실제 응답을 받아보고서야 확인된 사실 — 흔한 관례와
    달라서 처음엔 계속 "행이 없습니다"로만 나왔었다). <item> 도 다른 API와의
    호환을 위해 폴백으로 남겨둔다.
    """
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise RuntimeError(f"응답을 JSON 으로도 XML 로도 읽지 못했습니다: {safe_error(e)} / "
                           f"원문 앞부분: {text[:200]}")

    items = []
    # 지자체복지서비스 API 모델 명세상 개별 항목 태그명은 <servList> 입니다.
    # <servList> 노드를 우선 탐색하고, 호환성을 위해 <item> 노드도 fallback 탐색합니다.
    target_nodes = list(root.iter("servList")) or list(root.iter("item"))
    for item in target_nodes:
        row = {}
        for child in item:
            row[child.tag] = (child.text or "").strip() if len(child) == 0 else \
                " ".join((g.text or "").strip() for g in child)
        if row:
            items.append(row)

    total_el = root.find(".//totalCount")
    total = int(total_el.text) if total_el is not None and (total_el.text or "").strip().isdigit() \
        else len(items)

    # 오류 응답이면 알려준다. items 가 이미 채워졌으면(=성공) 이 검사를
    # 건너뛴다 — 굳이 결과코드까지 따지면, 이 API가 실제로 쓰는 성공
    # 문자열을 전부 알지 못하는 이상(화이트리스트에 없는 표현이면 성공
    # 응답도 오류로 잘못 판정하게 된다) 오히려 위험이 더 크다.
    #
    # ElementTree 함정 주의: `elem or other`처럼 Element 를 불리언으로 쓰면
    # 자식이 없는(리프) 엘리먼트가 False 로 취급돼 있어도 없는 것처럼 사라진다
    # (파이썬이 향후 버전에서 아예 예외로 막겠다고 경고하는 알려진 함정이다).
    # 그래서 각 후보를 `is not None` 으로 하나씩 순서대로 확인한다.
    if not items:
        def first(*tags):
            for t in tags:
                el = root.find(f".//{t}")
                if el is not None:
                    return (el.text or "").strip()
            return ""
        msg_text = first("returnAuthMsg", "resultMsg", "resultMessage")
        reason_text = first("returnReasonCode", "resultCode")
        if msg_text or reason_text:
            raise RuntimeError(f"API 오류 응답: {msg_text} (코드 {reason_text or '?'})")

    return {"response": {"body": {"items": {"item": items}, "totalCount": total}}}


def _kossi_rows(data):
    """data.go.kr 계열 API는 응답 포장이 제각각이라 여러 모양을 다 시도한다.

    흔한 형태: response.body.items.item (list 또는 단일 dict) / response.body.items
    JSON 네이티브인 경우: data / items 같은 단순한 키일 수도 있다.
    """
    if not isinstance(data, dict):
        return [], 0
    body = (data.get("response") or {}).get("body") or data.get("body") or data
    items = body.get("items") if isinstance(body, dict) else None
    if isinstance(items, dict):
        items = items.get("item", items)
    if items is None:
        items = body.get("data") if isinstance(body, dict) else None
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []
    total = 0
    if isinstance(body, dict):
        total = body.get("totalCount") or body.get("total_count") or len(items)
    return items, total


def fetch_all_kossi(op):
    """지자체복지서비스 목록/상세를 전부 받는다.

    다 못 받았으면 반드시 예외를 던진다. 예전에는 중간 페이지가 빈 응답을
    주면 조용히 break 하고 거기까지만 돌려줬는데, 그러면 호출부는 그게
    '전부'인 줄 알고 저장해 버린다. 2026-08-02 에 지자체 사업 3,932건이
    이렇게 사라졌다(229개 시군구 중 200곳이 절반씩 줄어든 채로 저장됨).
    """
    out, page, total = [], 1, 0
    while True:
        data = call_kossi(op, page=page)
        rows, total = _kossi_rows(data)
        out.extend(rows)
        print(f"  [KOSSI] {op} {len(out)}/{total}", file=sys.stderr)
        if len(out) >= total:
            break
        if not rows:
            # 아직 남았는데 빈 페이지가 왔다 = 중간에 끊긴 것
            raise RuntimeError(
                f"{op} 페이지 {page} 가 비어 있습니다. "
                f"{len(out)}/{total}건만 받았습니다(불완전).")
        page += 1
        time.sleep(0.3)
    if total and len(out) < total:
        raise RuntimeError(f"{op} {len(out)}/{total}건만 받았습니다(불완전).")
    return out


# --- 이름/기관명을 아주 살짝만 다듬어 두 소스의 표기 차이를 흡수한다.
# 괄호 안 내용은 지우지 않는다 — "달성 장학금(대학교)"처럼 괄호가
# 서로 다른 사업을 구분하는 경우가 있어서, 지우면 다른 사업이 하나로
# 뭉개질 수 있다. 그래서 여기서는 공백·특수문자 차이만 없앤다.
def _norm(text):
    import re as _re
    if not text:
        return ""
    t = _re.sub(r"[\s·‧∙•\-_/]+", "", str(text))
    return t.strip()


def dedupe_cross_source(base_items, extra_items):
    """두 소스를 합치되 같은 사업을 두 번 보여주지 않는다.

    판단 기준(둘 다 만족해야 같은 사업으로 본다):
      1) 이름이 같다 (공백 등만 다듬은 뒤 비교)
      2) 행정 계층·지역이 같다 (tier/sido/sigungu)

    기관명은 일부러 기준에서 뺐다. 같은 사업인데 GOV24는 "경기도",
    KOSSI는 "경기도 보건건강국 건강증진과"처럼 부서명까지 붙여 서로
    다르게 적는 경우가 흔해서, 기관명까지 요구하면 실제로는 같은 사업이
    두 카드로 중복 노출된다
    (실사례: "경기도산후조리비지원" / "경기도 산후조리비 지원").

    이름만 같고 지역이 다르면(예: 여러 시군구가 똑같이 쓰는
    "교통약자 이동지원") 서로 다른 사업으로 남겨둔다 — 지역이 다르면
    실제로 받는 사람도, 문의처도 다른 별개의 사업이기 때문이다.

    일치하면 base_items(GOV24) 쪽을 유지하고, 비어 있는 항목만
    extra_items(KOSSI) 값으로 채운다. 일치하지 않으면 extra_items 의
    그 사업을 새 항목으로 추가한다.
    """
    def key(s):
        return (_norm(s.get("name")), s.get("tier"), s.get("sido"), s.get("sigungu"))

    index = {}
    for s in base_items:
        index.setdefault(key(s), s)

    merged = list(base_items)
    added = 0
    filled = 0
    for extra in extra_items:
        k = key(extra)
        hit = index.get(k)
        if hit is None:
            # KOSSI 고유 id가 GOV24 쪽 id와 우연히 겹치는 사고를 막기 위해
            # 접두어를 붙인다. 공유 링크(/welfare/s/<id>)가 엉뚱한 사업으로
            # 열리는 것을 방지한다.
            if extra.get("id") and not str(extra["id"]).startswith("K-"):
                extra["id"] = "K-" + str(extra["id"])
            merged.append(extra)
            added += 1
            continue
        # 겹치는 사업: 비어 있는 필드만 채운다. 이미 값이 있으면 덮지 않는다
        # (두 소스가 미묘하게 다르게 적었을 때 무엇이 더 정확한지 알 수 없으므로,
        # 먼저 확보한 값을 신뢰하고 빈 곳만 보강하는 쪽이 안전하다).
        for fk, fv in extra.items():
            if fv and not hit.get(fk):
                hit[fk] = fv
                filled += 1

    print(f"  [교차중복] 지자체복지서비스 신규 {added:,}건 추가 / "
          f"기존 항목 보강 {filled:,}건 / 중복 제거 {len(extra_items) - added:,}건",
          file=sys.stderr)
    return merged


def read_code(cond: dict, table: dict):
    for key, codes in table.items():
        if any(c in cond for c in codes):
            return key
    return None


def read_gender(cond: dict):
    """남녀 모두 Y이거나 둘 다 없으면 무관(None)."""
    if not cond:
        return None
    male = any(c in cond for c in GENDER_CODES["남성"])
    female = any(c in cond for c in GENDER_CODES["여성"])
    if male == female:
        return None
    return "남성" if male else "여성"


def read_marital(cond: dict):
    """혼인 상태 제한. 미혼·기혼이 모두 허용이면 제한 없음(None).

    read_code() 로 첫 일치만 보면 안 된다. 대부분의 사업은 미혼도 기혼도
    받을 수 있어서 두 코드가 함께 Y 인데, 표에서 '미혼'이 앞에 있다는
    이유만으로 전부 '미혼 전용'이 됐다 — 실데이터 9,877건(66%)이 그랬다.
    성별을 읽는 read_gender 와 같은 방식으로 '둘 다면 제한 없음'으로 본다.
    """
    if not cond:
        return None
    single = any(c in cond for c in MARITAL_CODES["single"])
    married = any(c in cond for c in MARITAL_CODES["married"])
    parent = any(c in cond for c in MARITAL_CODES["single_parent"])
    # 한부모만 표시돼 있으면 한부모 전용 사업이다.
    if parent and not (single and married):
        return "single_parent"
    if single == married:          # 둘 다 되거나, 둘 다 표시가 없음
        return None
    return "single" if single else "married"


def normalize(row, cond_by_id):
    svc = {key: pick(row, keys) for key, keys in FIELD_MAP.items()}
    cond = cond_by_id.get(svc["id"], {})

    # --- 계층 (동명 시군구는 부서명·접수기관으로 해소) ---
    regions.tier_of(svc)
    # 지자체복지서비스 API처럼 시도/시군구를 필드로 직접 주는 경우,
    # 기관명 문자열 파싱보다 이 값이 더 믿을 만하므로 있으면 우선한다.
    sido_hint = regions.normalize_sido(svc.get("sido_hint", ""))
    if sido_hint:
        svc["sido"] = sido_hint
        sg_hint = (svc.get("sigungu_hint") or "").strip()
        if sg_hint and sg_hint in regions.SIDO.get(sido_hint, []):
            svc["sigungu"] = sg_hint
            svc["tier"] = "local"
        else:
            svc["tier"] = "regional"

    # --- 조건 코드에서 ---
    svc["gender"] = read_gender(cond)
    svc["marital"] = read_marital(cond)

    # --- 자연어 텍스트에서 (이게 없으면 나이·소득 필터가 무효가 된다) ---
    target, criteria, name = svc["target"], svc["criteria"], svc["name"]
    # 지원대상에 적힌 나이가 '아이 나이'인 경우가 많다.
    #   예) "0~5세 아동에게 보육료 지원" -> 신청자는 30~40대 부모
    # 이걸 신청자 나이로 넣으면 정작 부모가 결과에서 통째로 사라진다.
    age_text = f"{target} {criteria}"
    lo, hi = parsers.parse_age(age_text, name)
    if lo is not None and parsers.is_child_age(age_text):
        svc["age_min"], svc["age_max"] = None, None
        svc["child_age_max_years"] = hi
        svc["needs_child"] = True
    else:
        svc["age_min"], svc["age_max"] = lo, hi
        svc["child_age_max_years"] = None
    svc["income_max_pct"], svc["income_min_pct"] = parsers.parse_income_pct(target, criteria)
    # 지원대상·선정기준 칸이 비어 있는 지자체 사업이 많다. 그럴 때는
    # 서비스명에 적힌 '차상위이하' 같은 말이라도 살려야, 소득이 넘는
    # 사람에게 저소득 전용 사업이 뜨는 일을 막을 수 있다.
    if svc["income_max_pct"] is None:
        svc["income_max_pct"] = parsers.income_pct_from_name(name)
    svc["job"] = parsers.is_job_program(name, svc.get("sprt_type", ""))
    svc["tags"] = parsers.parse_tags(name, target, svc["field"], svc["content"],
                                     sprt_type=svc.get("sprt_type", ""))
    if not svc.get("needs_child"):
        svc["needs_child"] = parsers.needs_child(name, target)
    svc["preg"] = parsers.is_pregnancy(name, target)
    svc["child_age_max_months"] = parsers.parse_child_months(name)

    svc["special"] = parsers.special_group(name, target, criteria)
    if not svc["marital"]:
        svc["marital"] = parsers.parse_marital(name, target)

    out = {k: svc.get(k) for k in KEEP_FIELDS}
    if not is_individual(svc.get("usr_type", "")) or \
            parsers.is_org_only(svc.get("target", ""), svc.get("usr_type", "")):
        out["biz"] = True
    for k, n in TRUNC.items():
        if out.get(k) and len(out[k]) > n:
            out[k] = out[k][:n - 1] + "…"
    return out


def report(items):
    c = Counter()
    for s in items:
        c["전체"] += 1
        c[f"계층:{s['tier']}"] += 1
        if s["age_min"] is not None:
            c["나이 파싱됨"] += 1
        if s["income_max_pct"] is not None:
            c["소득 파싱됨"] += 1
        if s["tags"]:
            c["태그 있음"] += 1
        if s["gender"]:
            c["성별 전용"] += 1
        if s["child_age_max_months"] is not None:
            c["개월수 보정"] += 1
        if s["tier"] == "local" and not s["sido"]:
            c["!! 시도 미특정(표시 안 됨)"] += 1

    print("\n=== 수집 리포트 ===", file=sys.stderr)
    for k, v in c.most_common():
        pct = f"{v / max(c['전체'], 1) * 100:5.1f}%"
        print(f"  {k:26} {v:6,}  {pct}", file=sys.stderr)

    if c["!! 시도 미특정(표시 안 됨)"]:
        print("\n  ⚠ 시도를 특정하지 못한 기초지자체 서비스가 있습니다.", file=sys.stderr)
        print("    parsers/regions의 힌트 필드(dept, reception)를 확인하세요.", file=sys.stderr)
    if c["나이 파싱됨"] / max(c["전체"], 1) < 0.2:
        print("\n  ⚠ 나이 파싱률이 낮습니다. --probe로 '지원대상' 필드명을 확인하세요.", file=sys.stderr)


def main(dry_run=False):
    print("서비스 목록 수집 중...", file=sys.stderr)
    services = fetch_all("serviceList")

    print("지원조건 수집 중...", file=sys.stderr)
    try:
        conds = fetch_all("supportConditions")
    except Exception as e:  # noqa: BLE001
        print(f"  지원조건 수집 실패(건너뜀): {safe_error(e)}", file=sys.stderr)
        conds = []

    cond_by_id = {}
    for c in conds:
        sid = pick(c, FIELD_MAP["id"])
        if sid:
            cond_by_id[sid] = {k: v for k, v in c.items() if str(v).upper() == "Y"}

    items = [normalize(r, cond_by_id) for r in services]
    items = [s for s in items if s["name"]]
    n_biz = sum(1 for s in items if s.get("biz"))
    print(f"  기업·단체 전용 표시: {n_biz:,}건 (조건 검색에서 제외, 키워드 검색에는 포함)",
          file=sys.stderr)

    if KOSSI_KEY:
        print("\n지자체복지서비스(한국사회보장정보원) 수집 중...", file=sys.stderr)
        try:
            kossi_rows = fetch_all_kossi(KOSSI_LIST_OP)
            kossi_items = [normalize(r, {}) for r in kossi_rows]
            kossi_items = [s for s in kossi_items if s["name"]]
            items = dedupe_cross_source(items, kossi_items)
        except Exception as e:  # noqa: BLE001
            # 예전에는 '건너뜀'으로 넘어가 나머지 소스만 저장했다. 그 결과
            # 2026-08-02 에 지자체 사업 3,932건이 통째로 빠진 파일이 5일간
            # 서비스됐다. 소스 하나가 통째로 빠지면 그건 갱신이 아니라 손실이다.
            SOURCE_FAILURES.append(f"지자체복지서비스(KOSSI): {safe_error(e)}")
            print(f"  지자체복지서비스 수집 실패: {safe_error(e)}", file=sys.stderr)
            print("  --probe-local 로 KOSSI_LIST_OP 오퍼레이션명을 확인해 보세요.",
                  file=sys.stderr)
    else:
        print("\nKOSSI_KEY 없음 — 지자체복지서비스 소스는 건너뜁니다.", file=sys.stderr)

    seen = {}
    for s in items:
        seen[s["id"] or s["name"]] = s
    items = list(seen.values())

    report(items)

    if dry_run:
        print("\n--dry-run: 저장하지 않았습니다.", file=sys.stderr)
        return

    # 소스 하나라도 실패했으면 저장하지 않는다.
    # 여러 소스를 합쳐 만드는 파일이라, 일부만 성공한 결과를 덮어쓰면
    # '갱신'이 아니라 '손실'이 된다.
    if SOURCE_FAILURES and OUT.exists():
        sys.exit("\n중단: 아래 소스를 받지 못해 데이터가 불완전합니다. "
                 "기존 파일을 유지합니다.\n  - " + "\n  - ".join(SOURCE_FAILURES))

    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("count", 0)
            if prev and len(items) < prev * MIN_KEEP_RATIO:
                sys.exit(f"\n중단: 수집 {len(items)}건이 기존 {prev}건의 "
                         f"{MIN_KEEP_RATIO:.0%} 미만입니다. API 장애 가능성이 있어 "
                         f"기존 파일을 유지합니다.")
        except (json.JSONDecodeError, OSError):
            pass

    if not items:
        sys.exit("중단: 수집 결과가 0건입니다. 기존 파일을 유지합니다.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(
        {"updated": time.strftime("%Y-%m-%d"), "count": len(items), "items": items},
        ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"\n저장 완료: {OUT}  {len(items):,}건", file=sys.stderr)

    n = len(items)
    def pct(k):
        c = sum(1 for s_ in items if s_.get(k) not in (None, "", []))
        return c, (c * 100 // n if n else 0)

    print("\n--- 파싱 진단 ---", file=sys.stderr)
    for key, label, warn_below in [
        ("tier", "계층 판별", 100), ("age_min", "나이 조건", 5),
        ("income_max_pct", "소득 조건", 3), ("tags", "상황 태그", 20),
        ("deadline", "신청기한", 30), ("url", "신청 링크", 20),
    ]:
        c, r = pct(key)
        flag = "  <-- 확인 필요" if r < warn_below else ""
        print(f"  {label:10} {c:6,}건 ({r:3d}%){flag}", file=sys.stderr)

    tier_n = sum(1 for s_ in items if s_.get("tier") == "national")
    print(f"  전국 사업    {tier_n:6,}건 ({tier_n*100//n if n else 0:3d}%)"
          + ("  <-- 지역 판별 실패 의심" if n and tier_n * 100 // n > 70 else ""),
          file=sys.stderr)
    n_biz = sum(1 for s_ in items if s_.get("biz"))
    print(f"  기업·단체    {n_biz:6,}건", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="응답 필드명·조건코드 출력")
    ap.add_argument("--probe-local", action="store_true",
                    help="지자체복지서비스(한국사회보장정보원) 필드명 출력")
    ap.add_argument("--dry-run", action="store_true", help="저장 없이 파싱 통계만")
    args = ap.parse_args()
    try:
        if args.probe:
            probe()
        elif args.probe_local:
            probe_local()
        else:
            main(dry_run=args.dry_run)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ 예상치 못한 오류로 중단: {type(e).__name__}: {safe_error(e)}",
              file=sys.stderr)
        print("   이 줄을 그대로 캡처해서 알려주시면 원인을 바로 찾을 수 있습니다.",
              file=sys.stderr)
        sys.exit(1)