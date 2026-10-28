"""
복지 데이터 점검용 내보내기.

실제 정부 API 데이터가 어떻게 생겼고, 우리 코드가 그걸 어떻게 해석했는지를
엑셀로 뽑는다. 원문과 해석 결과를 나란히 놓아서 잘못 읽은 곳을 바로 찾을 수 있다.

  python scripts/export_welfare_check.py          # 전체 저장 (기본)
  python scripts/export_welfare_check.py --small  # 표본만 (업로드가 막힐 때)

만들어지는 파일 (data/ 폴더):
  welfare_check.csv          원문 + 해석 결과 + 의심 표시 (엑셀에서 바로 열림)
  welfare_check.csv.gz       위 파일의 압축본. 보통 1/8 크기라 올리기 편하다
  welfare_check_summary.txt  통계 요약

CSV 는 한글이 깨지지 않도록 BOM 을 넣어 저장한다.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import welfare_parsers as parsers          # noqa: E402
import welfare_regions as regions          # noqa: E402
import update_welfare as U                 # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = OUT_DIR / "welfare_check.csv"
GZ_PATH = OUT_DIR / "welfare_check.csv.gz"
SUM_PATH = OUT_DIR / "welfare_check_summary.txt"

# 원문에서 가져올 필드 (API 응답 키 후보)
RAW_FIELDS = [
    ("서비스ID", ["서비스ID", "서비스아이디"]),
    ("서비스명", ["서비스명"]),
    ("요약", ["서비스목적요약", "서비스목적"]),
    ("소관기관", ["소관기관명", "부서명"]),
    ("사용자구분", ["사용자구분", "사용자유형"]),
    ("지원대상", ["지원대상"]),
    ("선정기준", ["선정기준"]),
    ("지원내용", ["지원내용"]),
    ("지원유형", ["지원유형"]),
    ("서비스분야", ["서비스분야"]),
    ("신청기한", ["신청기한"]),
    ("신청방법", ["신청방법"]),
]

MAX_TEXT = 600          # 원문을 충분히 남긴다. 잘라내면 진단이 어렵다
SAMPLE_N = 400          # 정상 항목 중 무작위로 뽑을 개수
PER_FLAG_N = 120        # 의심 유형마다 뽑을 개수 (파일 크기 억제)


def cut(v, n=MAX_TEXT):
    v = "" if v is None else str(v).replace("\r", " ").replace("\n", " ").strip()
    return v if len(v) <= n else v[: n - 1] + "…"


def build_row(raw: dict, cond_by_id: dict, source: str = "GOV24"):
    """원문 한 건과, 우리 코드가 해석한 결과를 한 줄로 만든다.

    source 는 "GOV24"(행정안전부·보조금24) 또는 "KOSSI"(한국사회보장정보원_
    지자체복지서비스). 예전에는 여기서 필드 후보를 따로, 좁게 나열했는데
    그래서 KOSSI 원문(servNm, tgtrDtlCn 같은 영문 필드)을 넣으면 대부분
    못 찾고 빈 값이 됐다. update_welfare.py 의 FIELD_MAP 은 두 소스의
    필드명을 이미 다 후보로 갖고 있으므로 그걸 그대로 쓴다 — 후보 목록을
    두 곳에서 따로 관리하면 언젠가 또 어긋난다(전에 지역 자동완성 목록이
    그래서 몇 달간 안 맞았던 적이 있다).
    """
    get = lambda keys: U.pick(raw, keys)          # noqa: E731
    fm = U.FIELD_MAP

    name = get(fm["name"]) or ""
    org = get(fm["org"]) or ""
    target = get(fm["target"]) or ""
    criteria = get(fm["criteria"]) or ""
    content = get(fm["content"]) or ""
    field = get(fm["field"]) or ""
    deadline = get(fm["deadline"]) or ""
    usr = get(fm["usr_type"]) or ""

    age_text = f"{target} {criteria}"
    lo, hi = parsers.parse_age(age_text)
    child_age = parsers.is_child_age(age_text)
    tier, sido, sigungu = regions.classify_org(org, name, target)
    tags = parsers.parse_tags(name, target, field, content)
    pct, pct_min = parsers.parse_income_pct(target, criteria)
    months = parsers.parse_child_months(name)
    preg = parsers.is_pregnancy(name, target)
    kid = parsers.needs_child(name, target)
    biz = not U.is_individual(usr)

    # --- 의심 표시: 사람이 눈으로 확인해야 할 곳 ---
    flags = []
    if org and tier == "national" and any(
        w in org for w in ("시", "도", "군", "구")
    ) and not any(w in org for w in ("부", "청", "처", "원", "회", "공단", "공사")):
        flags.append("지역판별의심")
    if lo is not None and child_age:
        flags.append("아이나이로판정")
    if lo is not None and not child_age and hi is not None and hi <= 18:
        flags.append("상한18세이하인데본인나이")
    if not tags:
        flags.append("태그없음")
    if len(tags) >= 4:
        flags.append("태그과다")
    if deadline and not any(
        k in deadline
        for k in ("상시", "수시", "연중", "소진", "접수중", "공고", "해당 없음", "참고")
    ) and "20" not in deadline:
        flags.append("기한해석불가")
    if kid and months is None:
        flags.append("자녀필요인데개월수없음")
    if pct is not None and not (10 <= pct <= 300):
        flags.append("소득비율이상")

    return {
        "출처": source,
        "서비스ID": cut(get(fm["id"]), 40),
        "서비스명": cut(name, 120),
        "소관기관": cut(org, 80),
        "사용자구분": cut(usr, 40),
        "지원대상원문": cut(target),
        "선정기준원문": cut(criteria),
        "신청기한원문": cut(deadline, 160),
        "서비스분야": cut(field, 60),
        # --- 우리 코드의 해석 ---
        "해석_단계": tier,
        "해석_시도": sido,
        "해석_시군구": sigungu,
        "해석_나이하한": "" if lo is None else lo,
        "해석_나이상한": "" if hi is None else hi,
        "해석_아이나이인가": "Y" if child_age else "",
        "해석_소득상한%": "" if pct is None else pct,
        "해석_소득하한%(초과)": "" if pct_min is None else pct_min,
        "해석_자녀필요": "Y" if kid else "",
        "해석_자녀개월상한": "" if months is None else months,
        "해석_임신": "Y" if preg else "",
        "해석_기업단체": "Y" if biz else "",
        "해석_태그": ",".join(tags),
        "의심": ",".join(flags),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--small", action="store_true",
                    help="표본만 저장 (업로드 용량이 문제일 때)")
    args = ap.parse_args()

    if not os.environ.get("GOV24_KEY"):
        sys.exit("GOV24_KEY 환경변수가 없습니다. data.go.kr 의 '디코딩' 키를 넣어주세요.")

    print("서비스 목록 수집 중...", file=sys.stderr)
    services = U.fetch_all("serviceList")

    print("지원조건 수집 중...", file=sys.stderr)
    try:
        conds = U.fetch_all("supportConditions")
        cond_by_id = {U.pick(c, ["서비스ID", "서비스아이디"]): c for c in conds}
    except Exception as e:                                   # noqa: BLE001
        print(f"  지원조건 수집 실패({U.safe_error(e)}) — 없이 진행합니다", file=sys.stderr)
        cond_by_id = {}

    rows = [build_row(r, cond_by_id, source="GOV24") for r in services]
    rows = [r for r in rows if r["서비스명"]]

    # --- 두 번째 소스: 한국사회보장정보원_지자체복지서비스 (키가 있을 때만) ---
    # update_welfare.py 의 실제 운영 데이터에는 이미 이 소스가 합쳐지고 있지만,
    # 이 점검 파일은 지금까지 GOV24 만 봤다 — 그래서 KOSSI 쪽 원문·해석 결과를
    # 눈으로 확인할 방법이 없었다. 여기서는 합치지 않고 GOV24/KOSSI 를
    # '출처' 컬럼으로 나란히 남겨서, 어느 소스에서 뭐가 왔는지 그대로 보여준다.
    kossi_rows_raw = []
    kossi_status = "KOSSI_KEY 없음 — 건너뜀"
    if os.environ.get("KOSSI_KEY"):
        print("지자체복지서비스(한국사회보장정보원) 수집 중...", file=sys.stderr)
        try:
            kossi_rows_raw = U.fetch_all_kossi(U.KOSSI_LIST_OP)
            kossi_status = f"성공 — {len(kossi_rows_raw):,}건"
        except Exception as e:                                  # noqa: BLE001
            kossi_status = f"실패: {U.safe_error(e)}"
            print(f"  지자체복지서비스 수집 실패: {U.safe_error(e)}", file=sys.stderr)

    kossi_rows = [build_row(r, {}, source="KOSSI") for r in kossi_rows_raw]
    kossi_rows = [r for r in kossi_rows if r["서비스명"]]
    rows = rows + kossi_rows
    total_all = len(rows)

    # 지금 문의받은 사례를 이름으로 직접 찾아 요약에 바로 보여준다.
    # (매번 스크린샷을 주고받지 않아도 이 파일 하나로 답이 나오게)
    # '산후조리비 지원' 이라고 물어보셨지만 실제 서비스명은
    # '산모·신생아 건강관리 지원' 처럼 다르게 등록된 경우가 흔하다.
    # "산후조리" 글자만 찾으면 있어도 못 찾는다 — 관련 표현을 모두 받아준다.
    _NAMYANGJU_KW = ("산후조리", "산모", "신생아", "산후")
    namyangju_hit = [r for r in rows
                     if "남양주" in r["소관기관"]
                     and any(k in r["서비스명"] for k in _NAMYANGJU_KW)]

    # 요약은 항상 전체 기준으로 낸다
    summary_rows = rows

    # 저장할 행은 기본적으로 줄인다. 전부 담으면 10MB 를 넘어 주고받기 불편하다.
    if args.small:
        import random
        random.seed(0)
        # 의심 유형마다 골고루 뽑는다. 한 유형이 수천 건이어도 파일이 커지지 않고,
        # 유형별로 실제 사례를 충분히 볼 수 있다.
        by_flag = {}
        for r in rows:
            for f in r["의심"].split(","):
                if f:
                    by_flag.setdefault(f, []).append(r)
        picked_ids, suspect = set(), []
        for f, group in sorted(by_flag.items()):
            for r in random.sample(group, min(PER_FLAG_N, len(group))):
                key = id(r)
                if key not in picked_ids:
                    picked_ids.add(key)
                    suspect.append(r)
        normal = [r for r in rows if not r["의심"]]
        sample = random.sample(normal, min(SAMPLE_N, len(normal)))
        rows = suspect + sample
        print(f"\n저장 대상: 의심 {len(suspect):,}건(유형별 최대 {PER_FLAG_N})"
              f" + 정상 표본 {len(sample):,}건  / 전체 {total_all:,}건",
              file=sys.stderr)

    OUT_DIR.mkdir(exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 압축본도 같이 만든다. 텍스트라 보통 1/8 로 줄어서 올리기 편하다.
    import gzip
    import shutil
    with open(CSV_PATH, "rb") as src, gzip.open(GZ_PATH, "wb", 6) as dst:
        shutil.copyfileobj(src, dst)

    # --- 요약 (전체 기준) ---
    rows_for_sum = summary_rows
    n = len(rows_for_sum)
    tiers = Counter(r["해석_단계"] for r in rows_for_sum)
    flags = Counter(f for r in rows_for_sum for f in r["의심"].split(",") if f)
    tagc = Counter(t for r in rows_for_sum for t in r["해석_태그"].split(",") if t)
    have = lambda k: sum(1 for r in rows_for_sum if r[k] != "")   # noqa: E731

    src_ct = Counter(r["출처"] for r in rows_for_sum)
    lines = [
        f"총 {n:,}건 (CSV 에는 {len(rows):,}건 저장)",
        f"  GOV24(행안부·보조금24)  {src_ct.get('GOV24', 0):6,}건",
        f"  KOSSI(사회보장정보원)   {src_ct.get('KOSSI', 0):6,}건  — {kossi_status}",
        "",
        "[남양주 산후조리 관련 서비스 검색 결과]  ← 문의하신 사례를 직접 확인",
        *([f"  ✅ 발견: {r['서비스명']} (출처={r['출처']}, {r['소관기관']})"
           for r in namyangju_hit] if namyangju_hit else
          ["  ❌ 이번 수집 결과에서 찾지 못했습니다.",
           "     KOSSI 가 '실패' 라면 오퍼레이션명이 아직 안 맞는 것입니다.",
           "     KOSSI 가 '성공'인데도 없다면, 이 사업이 API 자체에 없을 가능성이 큽니다."]),
        "",
        "[지역 판별]",
        *[f"  {k or '(없음)':10} {v:6,}건 ({v*100//n if n else 0}%)"
          for k, v in tiers.most_common()],
        "",
        "[해석된 항목 비율]",
        f"  나이 조건      {have('해석_나이하한'):6,}건 ({have('해석_나이하한')*100//n if n else 0}%)",
        f"  소득 조건      {have('해석_소득상한%'):6,}건 ({have('해석_소득상한%')*100//n if n else 0}%)",
        f"  자녀 필요      {have('해석_자녀필요'):6,}건",
        f"  자녀 개월상한  {have('해석_자녀개월상한'):6,}건",
        f"  기업·단체      {have('해석_기업단체'):6,}건",
        "",
        "[태그 분포]",
        *[f"  {k:10} {v:6,}건" for k, v in tagc.most_common()],
        "",
        "[의심 항목]  ← 이 숫자가 크면 그 부분 해석이 잘못됐을 가능성이 큽니다",
        *[f"  {k:24} {v:6,}건" for k, v in flags.most_common()],
    ]
    SUM_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines), file=sys.stderr)
    mb = lambda p: os.path.getsize(p) / 1024 / 1024          # noqa: E731
    print(f"\n저장 완료", file=sys.stderr)
    print(f"  {CSV_PATH.name}     {mb(CSV_PATH):6.2f} MB", file=sys.stderr)
    print(f"  {GZ_PATH.name}  {mb(GZ_PATH):6.2f} MB  <- 이걸 올리면 가볍습니다",
          file=sys.stderr)
    print(f"  {SUM_PATH.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
