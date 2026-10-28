# -*- coding: utf-8 -*-
"""
복지 데이터 복구 — 예전 백업과 현재 파일을 합친다
================================================
수집이 일부만 성공한 채로 저장돼 항목이 사라졌을 때 쓴다.

2026-08-02 에 지자체복지서비스(KOSSI) 소스가 통째로 실패했는데
그때는 실패해도 그냥 넘어가고 저장해서, 3,951건이 사라진 파일이
5일간 서비스됐다. (update_welfare.py 에 방지 장치를 넣었지만
이미 사라진 데이터는 되살려야 한다.)

단순히 옛 파일로 되돌리면 그 사이 새로 생긴 항목이 날아간다.
그래서 합친다 — 같은 id 는 '현재' 것을 쓰고(최신), 현재에 없는 것만
백업에서 가져온다.

사용법
------
  # 백업 파일 준비 (git 에서 꺼내기)
  git show <커밋>:data/welfare_services.json > backup.json

  python scripts/restore_welfare_backup.py backup.json
  python scripts/restore_welfare_backup.py backup.json --dry-run
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CUR = os.path.join(BASE, "data", "welfare_services.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit(f"{path}: items 가 비어 있거나 형식이 다릅니다.")
    return doc, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("backup", help="예전 welfare_services.json 경로")
    ap.add_argument("--dry-run", action="store_true", help="저장하지 않고 결과만 보기")
    args = ap.parse_args()

    bdoc, bitems = load(args.backup)
    cdoc, citems = load(CUR)

    # 현재 것이 최신이므로 먼저 깔고, 백업에만 있는 것을 채운다.
    merged = {x.get("id") or x.get("name"): x for x in bitems}
    merged.update({x.get("id") or x.get("name"): x for x in citems})
    items = list(merged.values())

    added = len(items) - len(citems)
    print(f"  백업  {len(bitems):,}건  ({bdoc.get('updated')})")
    print(f"  현재  {len(citems):,}건  ({cdoc.get('updated')})")
    print(f"  합계  {len(items):,}건   (+{added:,} 복구)")

    if len(items) < len(citems):
        raise SystemExit("중단: 합친 결과가 현재보다 적습니다. 로직 확인 필요.")
    if added == 0:
        print("  복구할 항목이 없습니다. 파일을 건드리지 않습니다.")
        return 0

    if args.dry_run:
        print("\n  --dry-run: 저장하지 않았습니다.")
        return 0

    out = {
        "updated": cdoc.get("updated") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "count": len(items),
        "items": items,
        # 다음 수집이 정상적으로 덮어쓰면 이 표시는 사라진다.
        "restored_from": os.path.basename(args.backup),
        "restored_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    tmp = CUR + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, CUR)
    print(f"\n  저장 완료 → {CUR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
