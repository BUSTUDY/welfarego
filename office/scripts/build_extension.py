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
    rad = max(6, int(big * (8.0 / 36.0)))
    d.rounded_rectangle([pad, pad, big - pad, big - pad], radius=rad, fill=bg_rgb + (255,))
    lw = max(4, big // 11)
    m = big // 4
    if glyph == "forms":
        d.line([(m, int(big * 0.34)), (big - m, int(big * 0.34))], fill=(255, 255, 255, 255), width=lw)
        d.line([(m, int(big * 0.52)), (big - m, int(big * 0.52))], fill=(255, 255, 255, 255), width=lw)
        d.line([(m, int(big * 0.70)), (int(big * 0.62), int(big * 0.70))], fill=(255, 255, 255, 255), width=lw)
    elif glyph == "calc":
        # Clock / worktime circle + hands
        r_c = int(big * 0.27)
        cx, cy = big // 2, big // 2
        d.ellipse([cx - r_c, cy - r_c, cx + r_c, cy + r_c], outline=(255, 255, 255, 255), width=lw)
        d.line([(cx, cy), (cx, cy - int(r_c * 0.62))], fill=(255, 255, 255, 255), width=lw)
        d.line([(cx, cy), (cx + int(r_c * 0.55), cy)], fill=(255, 255, 255, 255), width=lw)
    elif glyph == "fees":
        # Won / Bar chart glyph for 2026 standard fee schedule
        w_bar = max(4, big // 9)
        y_bot = int(big * 0.74)
        for idx, h_frac in enumerate((0.46, 0.34, 0.24)):
            bx = int(big * (0.26 + idx * 0.19))
            d.rounded_rectangle([bx, int(big * h_frac), bx + w_bar, y_bot], radius=2, fill=(255, 255, 255, 255))
    elif glyph == "cal":
        d.rectangle([m, int(big * 0.29), big - m, int(big * 0.42)], fill=(255, 255, 255, 255))
        r = max(3, big // 14)
        for cx in (0.36, 0.50, 0.64):
            for cy in (0.56, 0.70):
                x, y = int(big * cx), int(big * cy)
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255))
    else:
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
        ("forms", (33, 81, 200)),     # #2151C8 portal royal blue
        ("calc", (13, 148, 136)),     # #0D9488 teal
        ("fees", (21, 128, 61)),      # #15803D emerald green
        ("cal", (217, 119, 6)),       # #D97706 amber
        ("check", (220, 38, 38)),     # #DC2626 crimson
    ]
    for name, rgb in specs:
        for sz in (16, 26):
            _draw_badge_icon(sz, rgb, name).save(icons_dir / f"{name}_{sz}.png", format="PNG")
    _draw_badge_icon(42, (33, 81, 200), "check").save(icons_dir / "ext_icon_42.png", format="PNG")

    (desc_dir / "desc_ko.txt").write_text(
        "주·야간보호시설 표준서식 20종 다운로드, 2026년 월 기준근무시간 계산기, "
        "2026 표준수가 계산기, 월간 본인부담금 안내문 출력기, 36개 평가지표 자가점검표 "
        "바로가기 리본 탭·홈 탭 버튼·메뉴를 추가합니다. "
        "(사용자가 버튼을 직접 클릭했을 때만 기본 웹브라우저가 열립니다.)",
        encoding="utf-8",
    )
    (desc_dir / "desc_en.txt").write_text(
        "Adds voluntary-click Ribbon & menu shortcuts to Welfarego Daycare Standard Forms, "
        "2026 Fee Schedule, and Practical Calculators in the user's default web browser (MPL-2.0).",
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
