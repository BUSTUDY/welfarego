# -*- coding: utf-8 -*-
"""
분류가 엉뚱하게 붙은 곳을 찾아내는 점검 도구.

무엇을 보는가 — '단독 근거' 키워드
-----------------------------------
어떤 사업에 '의료비' 태그가 붙었는데 그 근거가 오직 '건강보험료' 한 단어뿐이라면,
그 단어가 다른 뜻으로 쓰였을 때(소득 심사 기준) 통째로 오분류가 된다.
반대로 '진료비·병원비·환자'가 두루 걸렸다면 웬만해선 진짜 의료 사업이다.

그래서 이 도구는 키워드마다 "이 단어 하나 때문에만 그 태그가 붙은 사업"이
몇 건인지 센다. 이 숫자가 크면서 서비스명이 그 태그와 안 어울려 보이면
거의 확실히 오분류다. 실제로 이 방법으로 아래를 찾아냈다.

  · 서비스분야 '고용·창업'의 '창업'  -> 일자리 사업 504건이 자영업자로
  · 서비스분야 '서민금융'            -> 출산지원금·장학금까지 금융·채무로
  · 급여 안내문의 '임금'             -> 일자리 사업이 근로자 사업으로
  · 성실상'환자'                     -> 채무조정 대출이 의료비로

사용법
------
  python scripts/audit_welfare_tags.py              # 상위 오탐 후보
  python scripts/audit_welfare_tags.py --tag 의료비  # 태그 하나만 자세히
  python scripts/audit_welfare_tags.py --special    # 특수 대상 판정 점검

특수 대상(special)과 자격요건 태그는 '고르지 않으면 결과에서 사라지는'
힘이 있어서 오분류의 대가가 특히 크다. 그래서 따로 표시해 준다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import welfare_parsers as P  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "welfare_services.json"


def columns(s):
    """태그 판정에 쓰이는 네 칸. parse_tags 와 순서를 맞춘다."""
    return [s.get("name") or "", s.get("target") or "",
            s.get("field") or "", s.get("content") or ""]


def source_text(tag, cols):
    """그 태그가 근거를 찾도록 허용된 칸만 이어 붙인다."""
    allowed = P._TAG_SOURCE_FIELDS.get(tag)
    if allowed is None:
        return " ".join(c for c in cols if c)
    return " ".join(cols[i] for i in allowed if cols[i])


def audit_tags(items, only_tag=None, top=6):
    # (태그, 키워드) -> 그 키워드가 유일한 근거였던 사업 수
    sole = Counter()
    samples = defaultdict(list)
    total = Counter()

    for s in items:
        cols = columns(s)
        for tag in (s.get("tags") or []):
            if only_tag and tag != only_tag:
                continue
            kws = P._TAG_RULES.get(tag)
            if not kws:
                continue
            blob = source_text(tag, cols)
            hit = [k for k in kws if P._kw_present(blob, k)]
            total[tag] += 1
            if len(hit) == 1:
                key = (tag, hit[0])
                sole[key] += 1
                if len(samples[key]) < 4:
                    samples[key].append(s.get("name") or "")

    print("=== 단독 근거 키워드 (숫자가 크고 이름이 안 어울리면 오탐 의심) ===\n")
    shown = set()
    for (tag, kw), n in sole.most_common():
        if only_tag is None and n < 25:
            continue
        if only_tag is None and tag in shown and n < 60:
            continue
        shown.add(tag)
        share = n * 100 // max(total[tag], 1)
        mark = "  <-- 자격요건(고르지 않으면 안 보임)" \
            if tag in P.EXCLUSIVE_TAGS else ""
        print(f"[{tag}] '{kw}' 단독 {n:,}건 (그 태그의 {share}%){mark}")
        for x in samples[(tag, kw)]:
            print(f"     · {x[:60]}")
        print()


def audit_special(items, top=14):
    sole = Counter()
    samples = defaultdict(list)
    for s in items:
        sp = s.get("special")
        if not sp:
            continue
        blob = " ".join(x for x in (s.get("name"), s.get("target")) if x)
        kws = P.SPECIAL_GROUPS.get(sp, ())
        hit = [k for k in kws if P._kw_present(blob, k)]
        if len(hit) == 1:
            sole[(sp, hit[0])] += 1
            if len(samples[(sp, hit[0])]) < 4:
                samples[(sp, hit[0])].append(s.get("name") or "")

    print("=== 특수 대상: 단독 근거 키워드 ===")
    print("(특수 대상은 사용자가 직접 고르지 않으면 결과에서 빠진다.")
    print(" 잘못 붙으면 그 사업이 사실상 사라지므로 특히 조심해야 한다)\n")
    for (sp, kw), n in sole.most_common(top):
        print(f"[{sp}] '{kw}' 단독 {n:,}건")
        for x in samples[(sp, kw)]:
            print(f"     · {x[:60]}")
        print()


def overview(items):
    n = len(items)
    tagged = sum(1 for s in items if s.get("tags"))
    print(f"전체 {n:,}건 / 태그 있음 {tagged:,}건 ({tagged * 100 // n}%)\n")
    c = Counter()
    for s in items:
        for t in (s.get("tags") or []):
            c[t] += 1
    print("--- 태그 분포 ---")
    for t, v in c.most_common():
        mark = " (자격요건)" if t in P.EXCLUSIVE_TAGS else ""
        print(f"  {t:12} {v:6,}{mark}")
    print()
    for key, label in (("special", "특수 대상"), ("biz", "기업·단체"),
                       ("job", "일자리 제공")):
        print(f"  {label:10} {sum(1 for s in items if s.get(key)):6,}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="이 태그만 자세히 본다")
    ap.add_argument("--special", action="store_true", help="특수 대상 판정 점검")
    a = ap.parse_args()

    items = json.loads(DATA.read_text(encoding="utf-8"))["items"]
    if a.special:
        audit_special(items)
        return
    if not a.tag:
        overview(items)
    audit_tags(items, only_tag=a.tag)


if __name__ == "__main__":
    main()
