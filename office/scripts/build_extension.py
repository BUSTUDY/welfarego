#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the MPL-2.0 LibreOffice / Welfarego OFFICE extension (.oxt).

Generates clean original PNG icons (16x16, 26x26, 42x42), package descriptions,
and packs `office/extensions/welfarego-links.oxt` deterministically.
"""

from __future__ import annotations

from pathlib import Path
import zipfile
from PIL import Image, ImageDraw

OFFICE_ROOT = Path(__file__).resolve().parent.parent
EXT_SRC = OFFICE_ROOT / "extensions" / "welfarego-links"
OUT_OXT = OFFICE_ROOT / "extensions" / "welfarego-links.oxt"


def _draw_badge_icon(size: int, bg_rgb: tuple[int, int, int], glyph: str) -> Image.Image:
    scale = 4
    big = size * scale
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = max(2, big // 12)
    rad = max(6, big // 4)
    d.rounded_rectangle([pad, pad, big - pad, big - pad], radius=rad, fill=bg_rgb + (255,))
    lw = max(4, big // 11)
    m = big // 4
    if glyph == "forms":
        # Document lines
        d.line([(m, int(big * 0.34)), (big - m, int(big * 0.34))], fill=(255, 255, 255, 255), width=lw)
        d.line([(m, int(big * 0.52)), (big - m, int(big * 0.52))], fill=(255, 255, 255, 255), width=lw)
        d.line([(m, int(big * 0.70)), (int(big * 0.62), int(big * 0.70))], fill=(255, 255, 255, 255), width=lw)
    elif glyph == "calc":
        # Plus / grid
        mid = big // 2
        d.line([(mid, m), (mid, big - m)], fill=(255, 255, 255, 255), width=lw)
        d.line([(m, mid), (big - m, mid)], fill=(255, 255, 255, 255), width=lw)
    elif glyph == "cal":
        # Calendar header + dots
        d.rectangle([m, int(big * 0.30), big - m, int(big * 0.42)], fill=(255, 255, 255, 255))
        r = max(3, big // 14)
        for cx in (0.36, 0.50, 0.64):
            for cy in (0.56, 0.70):
                x, y = int(big * cx), int(big * cy)
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255))
    else:
        # Checkmark
        pts = [
            (int(big * 0.27), int(big * 0.53)),
            (int(big * 0.44), int(big * 0.70)),
            (int(big * 0.74), int(big * 0.34)),
        ]
        d.line(pts, fill=(255, 255, 255, 255), width=lw + 2, joint="curve")
    return im.resize((size, size), Image.Resampling.LANCZOS)


def build_oxt() -> Path:
    icons_dir = EXT_SRC / "icons"
    desc_dir = EXT_SRC / "pkg-desc"
    icons_dir.mkdir(parents=True, exist_ok=True)
    desc_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("forms", (33, 81, 200)),
        ("calc", (8, 119, 106)),
        ("cal", (217, 119, 6)),
        ("check", (31, 138, 76)),
    ]
    for name, rgb in specs:
        for sz in (16, 26):
            _draw_badge_icon(sz, rgb, name).save(icons_dir / f"{name}_{sz}.png", format="PNG")
    _draw_badge_icon(42, (8, 119, 106), "check").save(icons_dir / "ext_icon_42.png", format="PNG")

    (desc_dir / "desc_ko.txt").write_text(
        "주·야간보호시설 표준서식 20종 다운로드, 2026년 월 기준근무시간 계산기, "
        "월간 본인부담금 안내문 출력기, 36개 평가지표 자가점검표 바로가기 메뉴·툴바를 추가합니다. "
        "(사용자가 버튼을 직접 클릭했을 때만 기본 웹브라우저가 열립니다.)",
        encoding="utf-8",
    )
    (desc_dir / "desc_en.txt").write_text(
        "Adds voluntary-click menu and toolbar shortcuts to Welfarego Daycare Standard Forms "
        "and 2026 Practical Calculators in the user's default web browser (MPL-2.0).",
        encoding="utf-8",
    )

    lic_src = OFFICE_ROOT / "LICENSE"
    if lic_src.is_file():
        (EXT_SRC / "LICENSE.txt").write_text(lic_src.read_text(encoding="utf-8"), encoding="utf-8")

    with zipfile.ZipFile(OUT_OXT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(EXT_SRC.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                rel = path.relative_to(EXT_SRC).as_posix()
                zf.write(path, arcname=rel)
    return OUT_OXT


if __name__ == "__main__":
    out = build_oxt()
    print(f"[OK] Built {out} ({out.stat().st_size:,} bytes)")
