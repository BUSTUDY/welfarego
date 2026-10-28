# -*- coding: utf-8 -*-
"""
이미 받아둔 data/welfare_services.json 의 '해석된 값'만 다시 계산한다.

왜 필요한가
-----------
복지 데이터는 하루 한 번 GitHub Actions 가 정부 API 에서 새로 받아온다.
그래서 파서(welfare_parsers.py)를 고쳐도, 다음 수집이 돌기 전까지는
사이트가 옛날 해석 결과를 그대로 보여준다. 분류가 잘못돼서 받을 수 있는
사업이 안 보이는 상황이면 하루를 기다릴 이유가 없다. 이 스크립트는
API 를 다시 부르지 않고, 이미 저장된 원문(서비스명·지원대상·지원내용)만
가지고 태그·소득기준 같은 해석 값을 다시 매긴다.

조심해야 할 점 — 저장된 원문은 잘려 있다
------------------------------------------
update_welfare.py 는 파일 크기를 줄이려고 지원대상을 320자, 지원내용을
420자로 자른다(TRUNC). 게다가 '선정기준'은 아예 저장하지 않는다.
그래서 저장본만 보고 태그를 처음부터 다시 매기면, 잘려나간 뒷부분에
근거가 있던 태그가 통째로 사라진다. 실제로 그렇게 해보니 '노년' 99건,
'장애인' 84건이 사라졌다 — 규칙이 틀려서가 아니라 글자가 없어서다.
그 태그를 잃으면 노인·장애인이 자기 사업을 못 찾는다.

그래서 '전체 재계산'이 아니라 '이번 규칙 변경분만' 반영한다.
같은 저장본을 옛 파서와 새 파서에 각각 넣어보고, 두 결과의 차이만
적용한다. 잘림 때문에 생긴 손실은 두 파서 모두 똑같이 겪으므로
차이에 나타나지 않고, 따라서 기존 값이 그대로 보존된다.

옛 파서는 git 에서 가져온다(HEAD 기준). git 을 쓸 수 없으면 태그를
'추가'만 하고 '제거'는 건너뛴다 — 잘못 지우는 쪽이 더 위험하기 때문.

사용법
------
  python scripts/refresh_welfare_derived.py --dry-run   # 무엇이 바뀌는지만 출력
  python scripts/refresh_welfare_derived.py             # 실제로 파일을 고침
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import welfare_parsers as P  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "welfare_services.json"
BASELINE_REF = "HEAD:scripts/welfare_parsers.py"


def load_baseline_parser(ref=None):
    """데이터를 만든 시점의 파서를 git 에서 꺼내 임시 모듈로 읽는다.

    기본값은 HEAD 다. 다만 GitHub Actions 가 데이터를 새로 만든 뒤라면,
    그 데이터는 '그때의 파서'로 해석된 것이므로 기준도 그 커밋이어야 한다.
    HEAD 를 기준으로 삼으면 두 결과가 같아져서 아무 변화도 못 잡는다.
      예)  --baseline d88bce3:scripts/welfare_parsers.py
    실패하면 None (그 경우 태그를 지우지 않고 추가만 한다).
    """
    try:
        src = subprocess.run(
            ["git", "show", ref or BASELINE_REF],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout.decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"  [주의] 직전 파서를 git 에서 가져오지 못했습니다({e}).", file=sys.stderr)
        print("         태그 '추가'만 반영하고 '제거'는 건너뜁니다.", file=sys.stderr)
        return None

    tmp = Path(tempfile.mkdtemp()) / "welfare_parsers_baseline.py"
    tmp.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("welfare_parsers_baseline", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tag_args(s):
    return (s.get("name") or "", s.get("target") or "",
            s.get("field") or "", s.get("content") or "")


# 사람이 직접 받는 혜택임을 드러내는 말. 이 중 하나가 지원대상에 있어야
# '기업·단체' 표시를 풀어준다.
_PERSON_MARKERS = (
    "가구", "세대주", "수급자", "차상위", "본인", "주민등록", "자녀",
    "어르신", "노인", "아동", "영유아", "청년", "학생", "장애인",
    "임산부", "산모", "한부모", "국가유공자", "기초생활", "저소득층",
)
# 이름에 이런 말이 있으면 기관·사업자용으로 본다(그대로 둔다).
_ORG_NAME_MARKERS = (
    "시설", "센터", "기관", "법인", "단체", "사업자", "업체", "기업",
    "어선", "선박", "선원", "공동체", "조합", "협회", "농가", "어가",
    "학교", "어린이집 운영", "경영체", "점포", "상가", "공장", "매장",
    "운영비", "사업비", "육성", "인증", "수출", "출하", "가공",
)


def _looks_personal(name: str, target: str) -> bool:
    """개인이 신청하는 복지 혜택으로 보이는지(보수적으로 판단)."""
    if any(k in name for k in _ORG_NAME_MARKERS):
        return False
    if P.is_org_only(target, ""):
        return False
    return any(k in target for k in _PERSON_MARKERS)


def main(dry_run=False, baseline=None, legacy_fixups=False):
    if not DATA.exists():
        sys.exit(f"{DATA} 가 없습니다.")
    blob = json.loads(DATA.read_text(encoding="utf-8"))
    items = blob.get("items") or []
    print(f"대상 {len(items):,}건")

    base = load_baseline_parser(baseline)

    added = Counter()
    removed = Counter()
    stat = Counter()
    samples = {"biz": [], "special": [], "income": []}
    tag_samples = {}

    for s in items:
        name = s.get("name") or ""
        sprt = s.get("sprt_type") or ""
        stored = list(s.get("tags") or [])

        # ---- 태그: 옛 파서와 새 파서의 '차이'만 반영 ----
        t_new = set(P.parse_tags(*tag_args(s), sprt_type=sprt))
        if base is not None:
            t_old = set(base.parse_tags(*tag_args(s)))
            drop = t_old - t_new          # 이번 규칙 변경으로 걸러진 오탐
            gain = t_new - t_old          # 이번에 새로 생긴 분류
        else:
            drop = set()
            gain = t_new - set(stored)

        final = [t for t in stored if t not in drop]
        for t in gain:
            if t not in final:
                final.append(t)
        if final != stored:
            stat["태그 변경"] += 1
            for t in drop:
                if t in stored:
                    removed[t] += 1
            for t in gain:
                if t not in stored:
                    added[t] += 1
                    tag_samples.setdefault(t, [])
                    if len(tag_samples[t]) < 8:
                        tag_samples[t].append(name)
            s["tags"] = final

        # ---- 일자리 제공 사업 표시 ----
        job = P.is_job_program(name, sprt)
        if job != bool(s.get("job")):
            s["job"] = job
            if job:
                stat["일자리 사업 표시"] += 1

        # ---- 기업·단체 표시: 규칙이 바뀌어 판정이 뒤집힌 것만 고친다 ----
        # 이건 '다시 계산'이 아니라 '두 파서의 차이'라서 안전하다. 판정
        # 근거인 사용자구분이 저장본에 없어도, 지원대상만으로 내리던
        # 판단이 True -> False 로 바뀐 경우는 규칙 수정 때문이 분명하다.
        #   예) 생계급여의 "제외 - 노숙인 자활시설 거주자" 속 '시설'을
        #       근거로 기업 전용으로 찍혀 조건 검색에서 빠져 있었다.
        if base is not None and s.get("biz"):
            tgt = s.get("target") or ""
            if base.is_org_only(tgt, "") and not P.is_org_only(tgt, ""):
                s["biz"] = False
                stat["기업·단체 오판 해제"] += 1
                if len(samples["biz"]) < 6:
                    samples["biz"].append(name)

        # ---- 아래 세 가지는 옛 데이터를 되살리기 위한 일회성 보정 ----
        # 정부 API 에서 새로 받은 데이터는 '선정기준'과 잘리지 않은 원문까지
        # 보고 판정된 것이라, 잘린 저장본으로 다시 계산하면 오히려 나빠진다.
        # 그래서 --legacy-fixups 를 줄 때만 손댄다.
        if not legacy_fixups:
            continue

        # ---- 특수 대상: 지우기만 한다(새로 붙이지 않는다) ----
        # 저장본에는 '선정기준'이 없어서 새로 판정하면 근거가 모자란다.
        # 배제 문구 오탐을 걷어내는 쪽으로만 쓴다.
        if s.get("special"):
            if P.special_group(name, s.get("target") or "") is None:
                s["special"] = None
                stat["특수대상 해제"] += 1
                if len(samples["special"]) < 6:
                    samples["special"].append(name)

        # ---- 기업·단체 표시: 지우기만 한다 ----
        # 고쳐야 할 것은 옛 is_individual() 의 버그다. 사용자구분이 '가구'·
        # '국민'처럼 적혀 있으면 '개인'이라는 글자가 없다는 이유만으로
        # 기업 전용으로 찍혔고, 그 바람에 주거급여·생계급여가 조건 검색에서
        # 통째로 사라졌다. 그런데 판정 근거였던 사용자구분 자체가 저장본에
        # 없어서 어떤 항목이 그 버그의 피해자인지 가려낼 수가 없다.
        #
        # 지원대상 문구만으로 판단하면 '영유아 보육시설 지방세 감면'처럼
        # 진짜 기관 사업까지 풀려서 개인 결과에 어업·선박 사업이 섞인다.
        # 그래서 사람이 받는 혜택이라는 표시가 뚜렷하고, 기관을 가리키는
        # 말이 이름에 없을 때만 푼다. 애매하면 그대로 둔다 — 다음 수집이
        # 돌면 고쳐진 규칙으로 정확히 다시 매겨진다.
        if s.get("biz") and _looks_personal(name, s.get("target") or ""):
            s["biz"] = False
            stat["기업·단체 표시 해제"] += 1
            if len(samples["biz"]) < 6:
                samples["biz"].append(name)

        # ---- 소득 상한: 규칙 변경으로 사라진 잘못된 상한을 먼저 지운다 ----
        # 지원대상 문구만으로 옛 파서가 뽑던 값이 그대로 저장돼 있고,
        # 새 파서는 그 값을 안 뽑는다면 오탐이었다는 뜻이다.
        #   예) 아동수당의 "(의료급여 전산관리번호) ... 포함"을 자격으로 읽어
        #       전 국민 대상 수당에 중위소득 40% 상한이 붙어 있었다.
        # 저장값이 지원대상만으로 똑같이 재현될 때만 지운다 — 그래야
        # 저장하지 않는 '선정기준'에서 온 진짜 상한을 잘못 날리지 않는다.
        if base is not None and s.get("income_max_pct") is not None:
            tgt = s.get("target") or ""
            o_mx, _o = base.parse_income_pct(tgt)
            n_mx, _n = P.parse_income_pct(tgt)
            if o_mx is not None and n_mx is None and s["income_max_pct"] == o_mx:
                s["income_max_pct"] = None
                stat["잘못된 소득상한 해제"] += 1
                if len(samples["income"]) < 6:
                    samples["income"].append(f"{name} (상한 {o_mx}% 해제)")

        # ---- 소득 상한: 비어 있을 때만 이름에서 보충 ----
        if s.get("income_max_pct") is None:
            pct = P.income_pct_from_name(name)
            if pct is not None:
                s["income_max_pct"] = pct
                stat["소득상한 보충"] += 1
                if len(samples["income"]) < 6:
                    samples["income"].append(f"{name} -> {pct}%")

    print("\n=== 변경 요약 ===")
    for k, v in stat.most_common():
        print(f"  {k:20} {v:6,}")

    if removed:
        print("\n--- 제거된 태그(오탐) ---")
        for t, v in removed.most_common():
            print(f"  {t:12} -{v:,}")
    if added:
        print("\n--- 추가된 태그 ---")
        for t, v in added.most_common():
            print(f"  {t:12} +{v:,}")
            for x in tag_samples.get(t, [])[:6]:
                print(f"        · {x[:52]}")

    for label, key in (("특수대상 해제", "special"), ("기업·단체 해제", "biz"),
                       ("소득상한 보충", "income")):
        if samples[key]:
            print(f"\n[{label} 예시]")
            for x in samples[key]:
                print("   ", x)

    if dry_run:
        print("\n--dry-run: 파일을 고치지 않았습니다.")
        return

    tmp = DATA.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(blob, ensure_ascii=False), encoding="utf-8")
    tmp.replace(DATA)
    print(f"\n저장 완료: {DATA}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="바뀌는 내용만 출력")
    ap.add_argument("--legacy-fixups", action="store_true",
                    help="특수대상·기업표시·잘못된 소득상한까지 손본다"
                         " (옛 데이터 되살릴 때만)")
    ap.add_argument("--baseline",
                    help="데이터를 만든 시점의 파서 (예: d88bce3:scripts/welfare_parsers.py)")
    main(**vars(ap.parse_args()))
