#!/usr/bin/env python3
"""
Generate all original branding assets for Welfarego OFFICE, matching the exact
Welfarego portal emblem (static/portal/favicon.svg: #2151C8 rounded square + white house + heart).

All generated graphics are 100% original geometric artwork created for Welfarego OFFICE.
No The Document Foundation (TDF) or LibreOffice logos, icons, or trademarked imagery are used.

Outputs:
- branding/images/intro.png (644x199)
- branding/images/intro-highres.png (990x254)
- branding/images/progress.conf
- branding/images/logo.svg
- branding/images/logo_inverted.svg
- branding/images/logo-sc.svg
- branding/images/logo-sc_inverted.svg
- branding/images/about.svg
- branding/images/*_app.png & soffice.png (256x256 visual previews)
- branding/msi/Banner.bmp (632x57)
- branding/msi/Image.bmp (162x312)
- branding/msi/Image_2.bmp (493x312)
- branding/msi/WizardImage.bmp (164x314)
- branding/msi/WizardSmall.bmp (55x58)
- branding/icons/*.ico (all 31 Windows application & document icons, 13 resolutions 16..256px)
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = ROOT / "branding"
IMAGES_DIR = BRAND_DIR / "images"
ICONS_DIR = BRAND_DIR / "icons"
MSI_DIR = BRAND_DIR / "msi"

ICO_SIZES = [16, 20, 24, 30, 32, 36, 48, 60, 64, 72, 96, 128, 256]

FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
]

FONT_CANDIDATES_MEDIUM = [
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf",
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]


def load_brand() -> dict:
    return json.loads((BRAND_DIR / "brand.json").read_text(encoding="utf-8"))


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def hex_to_rgba(h: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = hex_to_rgb(h)
    return (r, g, b, alpha)


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def create_diagonal_gradient(
    width: int, height: int, c1: tuple[int, int, int], c2: tuple[int, int, int]
) -> Image.Image:
    base = Image.new("RGBA", (width, height))
    px = base.load()
    denom = float(max(1.0, width * 0.65 + height * 0.35))
    for y in range(height):
        for x in range(width):
            t = (x * 0.65 + y * 0.35) / denom
            r, g, b = lerp_color(c1, c2, t)
            px[x, y] = (r, g, b, 255)
    return base


def _cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 32,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        pts.append((x, y))
    return pts


def _draw_round_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    width: float,
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    round_caps: bool = True,
) -> None:
    """Draw anti-aliased polyline with exact round joins and optional round caps."""
    w_int = max(1, int(round(width)))
    r = width / 2.0
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color, width=w_int)
    for idx, (px, py) in enumerate(points):
        if not round_caps and (idx == 0 or idx == len(points) - 1):
            continue
        draw.ellipse((px - r, py - r, px + r, py + r), fill=color)


def draw_portal_house_heart_glyph(
    draw: ImageDraw.ImageDraw,
    x0: float,
    y0: float,
    size: float,
    fg: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> None:
    """
    Draw the exact white house + heart glyph from static/portal/favicon.svg (viewBox 0 0 36 36):
      <path d="M7.5 17.2 18 8l10.5 9.2" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M10.5 16v11.5h15V16" stroke-width="2.6" stroke-linejoin="round"/>
      <path d="M18 24.2c-3.4-2.2-4.6-3.6-4.6-5.1 0-1.3 1-2.2 2.2-2.2.9 0 1.9.5 2.4 1.5
               .5-1 1.5-1.5 2.4-1.5 1.2 0 2.2.9 2.2 2.2 0 1.5-1.2 2.9-4.6 5.1Z" fill="#fff"/>
    """
    u = size / 36.0
    sw = 2.6 * u

    # 1. Roof: M7.5 17.2 -> 18 8 -> 28.5 17.2 (round cap + round join)
    roof = [
        (x0 + 7.5 * u, y0 + 17.2 * u),
        (x0 + 18.0 * u, y0 + 8.0 * u),
        (x0 + 28.5 * u, y0 + 17.2 * u),
    ]
    _draw_round_polyline(draw, roof, sw, fg, round_caps=True)

    # 2. House walls: M10.5 16 -> 10.5 27.5 -> 25.5 27.5 -> 25.5 16 (round join at bottom corners)
    walls = [
        (x0 + 10.5 * u, y0 + 16.0 * u),
        (x0 + 10.5 * u, y0 + 27.5 * u),
        (x0 + 25.5 * u, y0 + 27.5 * u),
        (x0 + 25.5 * u, y0 + 16.0 * u),
    ]
    _draw_round_polyline(draw, walls, sw, fg, round_caps=False)

    # 3. Exact SVG cubic Bezier heart inside house
    def pt(vx: float, vy: float) -> tuple[float, float]:
        return (x0 + vx * u, y0 + vy * u)

    heart_poly: list[tuple[float, float]] = [pt(18.0, 24.2)]
    heart_poly.extend(_cubic_bezier(pt(18.0, 24.2), pt(14.6, 22.0), pt(13.4, 20.6), pt(13.4, 19.1)))
    heart_poly.extend(_cubic_bezier(pt(13.4, 19.1), pt(13.4, 17.8), pt(14.4, 16.9), pt(15.6, 16.9)))
    heart_poly.extend(_cubic_bezier(pt(15.6, 16.9), pt(16.5, 16.9), pt(17.5, 17.4), pt(18.0, 18.4)))
    heart_poly.extend(_cubic_bezier(pt(18.0, 18.4), pt(18.5, 17.4), pt(19.5, 16.9), pt(20.4, 16.9)))
    heart_poly.extend(_cubic_bezier(pt(20.4, 16.9), pt(21.6, 16.9), pt(22.6, 17.8), pt(22.6, 19.1)))
    heart_poly.extend(_cubic_bezier(pt(22.6, 19.1), pt(22.6, 20.6), pt(21.4, 22.0), pt(18.0, 24.2)))
    draw.polygon(heart_poly, fill=fg)


def render_portal_emblem_tile(
    out_size: int = 512,
    pad_ratio: float = 0.04,
    bg_hex: str = "#2151C8",
) -> Image.Image:
    """
    Render the exact Welfarego site icon (static/portal/favicon.svg / image.png)
    supersampled at 4x for razor-sharp edges at every Windows ICO size (16..256px).
    """
    ss = max(1024, out_size * 2)
    canvas = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")

    pad = int(round(ss * pad_ratio))
    tile_sz = ss - pad * 2
    rad = int(round(tile_sz * (8.0 / 36.0)))
    draw.rounded_rectangle(
        (pad, pad, pad + tile_sz - 1, pad + tile_sz - 1),
        radius=rad,
        fill=hex_to_rgba(bg_hex, 255),
    )
    draw_portal_house_heart_glyph(draw, float(pad), float(pad), float(tile_sz))
    return canvas.resize((out_size, out_size), Image.Resampling.LANCZOS)


def make_wordmark_svg(brand: dict, dark_mode: bool = False) -> str:
    """
    Create crisp SVG wordmark for Start Center & About Dialog (360x72),
    featuring the exact portal #2151C8 house + heart icon + Welfarego OFFICE.
    """
    text_primary = "#FFFFFF" if dark_mode else "#14213D"
    tile_fill = "#3B82F6" if dark_mode else "#2151C8"
    badge_bg = "#1E3A8A" if dark_mode else "#EEF2FB"
    badge_fg = "#93C5FD" if dark_mode else "#2151C8"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="360" height="72" viewBox="0 0 360 72">
  <g transform="translate(6, 8) scale(1.5556)">
    <rect width="36" height="36" rx="8" fill="{tile_fill}"/>
    <path d="M7.5 17.2 18 8l10.5 9.2" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M10.5 16v11.5h15V16" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round"/>
    <path d="M18 24.2c-3.4-2.2-4.6-3.6-4.6-5.1 0-1.3 1-2.2 2.2-2.2.9 0 1.9.5 2.4 1.5.5-1 1.5-1.5 2.4-1.5 1.2 0 2.2.9 2.2 2.2 0 1.5-1.2 2.9-4.6 5.1Z" fill="#fff"/>
  </g>
  <text x="74" y="46" font-family="Segoe UI, Roboto, Noto Sans KR, Malgun Gothic, Liberation Sans, sans-serif" font-size="28" font-weight="800" fill="{text_primary}">Welfarego</text>
  <rect x="218" y="21" width="94" height="30" rx="8" fill="{badge_bg}"/>
  <text x="265" y="42" text-anchor="middle" font-family="Segoe UI, Roboto, Noto Sans KR, Malgun Gothic, Liberation Sans, sans-serif" font-size="15" font-weight="800" fill="{badge_fg}" letter-spacing="1.5">OFFICE</text>
</svg>
"""


def make_about_svg() -> str:
    """Decorative modern geometric background artwork for the About dialog."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="372" height="354" viewBox="0 0 372 354">
  <defs>
    <linearGradient id="abGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2151C8" stop-opacity="0.11"/>
      <stop offset="100%" stop-color="#173D9E" stop-opacity="0.04"/>
    </linearGradient>
    <linearGradient id="abGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.13"/>
      <stop offset="100%" stop-color="#2151C8" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <rect x="16" y="16" width="340" height="322" rx="28" fill="url(#abGrad1)"/>
  <circle cx="312" cy="64" r="76" fill="url(#abGrad2)"/>
  <circle cx="60" cy="292" r="64" fill="url(#abGrad2)"/>
  <rect x="42" y="44" width="124" height="14" rx="7" fill="#2151C8" fill-opacity="0.09"/>
  <rect x="42" y="68" width="84" height="10" rx="5" fill="#2151C8" fill-opacity="0.06"/>
</svg>
"""


def _composite_layer(base: Image.Image, draw_fn) -> Image.Image:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    draw_fn(draw)
    return Image.alpha_composite(base, layer)


def generate_splash(width: int, height: int, is_highres: bool = False) -> Image.Image:
    """
    Generate crisp supersampled splash screen (intro.png: 644x199, intro-highres.png: 990x254)
    in portal royal navy (#2151C8 -> #14213D) with the exact site house+heart emblem.
    """
    scale = 2
    W, H = width * scale, height * scale
    img = create_diagonal_gradient(W, H, hex_to_rgb("#2151C8"), hex_to_rgb("#14213D"))

    img = _composite_layer(
        img,
        lambda d: d.ellipse(
            (W - int(H * 1.15), -int(H * 0.45), W + int(H * 0.4), int(H * 1.1)),
            fill=(96, 165, 250, 38),
        ),
    )

    card_x0 = W - int(W * 0.31)
    card_y0 = int(H * 0.16)
    card_x1 = W - int(W * 0.045)
    card_y1 = int(H * 0.74)
    img = _composite_layer(
        img,
        lambda d: d.rounded_rectangle(
            (card_x0, card_y0, card_x1, card_y1),
            radius=int(18 * scale),
            fill=(255, 255, 255, 24),
            outline=(255, 255, 255, 58),
            width=2,
        ),
    )

    def draw_card_inner(d: ImageDraw.ImageDraw) -> None:
        inner_x = card_x0 + int(16 * scale)
        inner_y = card_y0 + int(16 * scale)
        pill_colors = ["#60A5FA", "#34D399", "#FBBF24", "#F87171"]
        pw = int((34 if is_highres else 22) * scale)
        pgap = int((10 if is_highres else 7) * scale)
        for i, col in enumerate(pill_colors):
            px = inner_x + i * (pw + pgap)
            d.rounded_rectangle(
                (px, inner_y, px + pw, inner_y + int(9 * scale)),
                radius=int(4.5 * scale),
                fill=hex_to_rgba(col, 230),
            )
        for row in range(3):
            ry = inner_y + int((22 + row * 16) * scale)
            max_w = (card_x1 - inner_x) - int(18 * scale)
            rw = max(int(40 * scale), max_w - row * int(26 * scale))
            d.rounded_rectangle(
                (inner_x, ry, inner_x + rw, ry + int(7 * scale)),
                radius=int(3.5 * scale),
                fill=(255, 255, 255, 62),
            )

    img = _composite_layer(img, draw_card_inner)

    pad_x = int((42 if is_highres else 30) * scale)
    icon_size = int((76 if is_highres else 56) * scale)
    icon_y = int((48 if is_highres else 38) * scale)

    emblem_tile = render_portal_emblem_tile(out_size=icon_size, pad_ratio=0.0, bg_hex="#2E6BE6")
    emblem_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    emblem_layer.paste(emblem_tile, (pad_x, icon_y), emblem_tile)
    img = Image.alpha_composite(img, emblem_layer)

    def draw_text_and_track(d: ImageDraw.ImageDraw) -> None:
        text_x = pad_x + icon_size + int(18 * scale)
        title_font = load_font(FONT_CANDIDATES_BOLD, int((38 if is_highres else 28) * scale))
        badge_font = load_font(FONT_CANDIDATES_BOLD, int((17 if is_highres else 13) * scale))
        sub_font = load_font(FONT_CANDIDATES_MEDIUM, int((13 if is_highres else 10) * scale))

        title_y = icon_y + int((3 if is_highres else 2) * scale)
        d.text((text_x, title_y), "Welfarego", font=title_font, fill=(255, 255, 255, 255))
        tw = d.textlength("Welfarego", font=title_font)

        bx = int(text_x + tw + 12 * scale)
        by = title_y + int((8 if is_highres else 5) * scale)
        bw = int((88 if is_highres else 66) * scale)
        bh = int((28 if is_highres else 22) * scale)
        d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=int(7 * scale), fill=(255, 255, 255, 238))
        d.text(
            (bx + bw // 2, by + bh // 2),
            "OFFICE",
            font=badge_font,
            fill=hex_to_rgba("#2151C8", 255),
            anchor="mm",
        )

        sub_y = title_y + int((50 if is_highres else 36) * scale)
        d.text(
            (text_x, sub_y),
            "Modern Ribbon Suite  •  Writer  •  Calc  •  Impress  •  Draw",
            font=sub_font,
            fill=(219, 234, 254, 235),
        )

        track_y = int((210 if is_highres else 172) * scale)
        track_h = int((8 if is_highres else 6) * scale)
        d.rounded_rectangle(
            (pad_x, track_y, W - pad_x, track_y + track_h),
            radius=track_h // 2,
            fill=(255, 255, 255, 48),
        )

    img = _composite_layer(img, draw_text_and_track)
    return img.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)


def _draw_glyph_content(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    glyph_type: str,
    color_rgb: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    w = x1 - x0
    col_full = (*color_rgb, 232)
    col_soft = (*color_rgb, 128)
    col_faint = (*color_rgb, 56)

    if glyph_type == "suite":
        cols = [
            hex_to_rgb("#2151C8"),
            hex_to_rgb("#15803D"),
            hex_to_rgb("#C2410C"),
            hex_to_rgb("#D97706"),
        ]
        for i, c in enumerate(cols):
            yy = y0 + 44 + i * 62
            draw.rounded_rectangle((x0 + 48, yy, x1 - 36, yy + 34), radius=12, fill=(*c, 224))
    elif glyph_type == "writer":
        for i in range(5):
            yy = y0 + 42 + i * 54
            right = x1 - (36 if i % 2 == 0 else 68)
            draw.rounded_rectangle(
                (x0 + 44, yy, right, yy + 24),
                radius=10,
                fill=col_full if i == 0 else col_soft,
            )
    elif glyph_type == "calc":
        gx0, gy0 = x0 + 42, y0 + 44
        cell_w, cell_h = (w - 82) // 2, 50
        for r in range(4):
            for c in range(2):
                cx0 = gx0 + c * (cell_w + 12)
                cy0 = gy0 + r * (cell_h + 12)
                draw.rounded_rectangle(
                    (cx0, cy0, cx0 + cell_w, cy0 + cell_h),
                    radius=10,
                    fill=col_full if (r == 0 or (c == 0 and r == 1)) else col_faint,
                )
    elif glyph_type == "impress":
        draw.rounded_rectangle((x0 + 44, y0 + 42, x1 - 36, y0 + 74), radius=10, fill=col_full)
        bar_heights = [90, 145, 115]
        bw = 36
        gap = 20
        start_x = x0 + 54
        base_y = y1 - 46
        for i, bh in enumerate(bar_heights):
            bx = start_x + i * (bw + gap)
            draw.rounded_rectangle(
                (bx, base_y - bh, bx + bw, base_y),
                radius=10,
                fill=col_full if i == 1 else col_soft,
            )
    elif glyph_type == "draw":
        draw.ellipse((x0 + 48, y0 + 56, x0 + 168, y0 + 176), fill=col_soft, outline=col_full, width=8)
        draw.rounded_rectangle((x0 + 104, y0 + 132, x1 - 36, y1 - 54), radius=20, fill=col_full)
    elif glyph_type == "base":
        for i in range(3):
            yy = y0 + 52 + i * 78
            draw.rounded_rectangle(
                (x0 + 46, yy, x1 - 36, yy + 54),
                radius=22,
                fill=col_full if i == 0 else col_soft,
            )
            draw.ellipse((x1 - 74, yy + 18, x1 - 56, yy + 36), fill=(255, 255, 255, 235))
    elif glyph_type == "math":
        font = load_font(FONT_CANDIDATES_BOLD, 140)
        draw.text(((x0 + x1) // 2 + 8, (y0 + y1) // 2), "∑", font=font, fill=col_full, anchor="mm")
    else:
        for i in range(4):
            yy = y0 + 48 + i * 60
            draw.rounded_rectangle((x0 + 44, yy, x1 - 40, yy + 26), radius=10, fill=col_soft)


def draw_app_icon_canvas(
    accent_hex: str,
    dark_hex: str,
    badge_letter: str,
    glyph_type: str,
    is_document: bool = False,
    is_template: bool = False,
) -> Image.Image:
    # Main suite icon (soffice.ico) IS the exact portal #2151C8 house + heart icon!
    if glyph_type == "suite" and not is_document:
        return render_portal_emblem_tile(out_size=512, pad_ratio=0.04, bg_hex="#2151C8")

    S = 512
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c_main = hex_to_rgb(accent_hex)
    c_dark = hex_to_rgb(dark_hex)

    if not is_document:
        margin = 28
        tile = create_diagonal_gradient(S - margin * 2, S - margin * 2, c_main, c_dark)
        mask = Image.new("L", (S - margin * 2, S - margin * 2), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, S - margin * 2 - 1, S - margin * 2 - 1), radius=108, fill=255
        )
        img.paste(tile, (margin, margin), mask)

        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(
                (margin, margin, S - margin - 1, S - margin - 1),
                radius=108,
                outline=(255, 255, 255, 76),
                width=6,
            ),
        )

        card_box = (176, 88, 416, 424)
        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(
                (card_box[0] + 6, card_box[1] + 10, card_box[2] + 6, card_box[3] + 10),
                radius=32,
                fill=(0, 0, 0, 56),
            ),
        )
        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(card_box, radius=32, fill=(255, 255, 255, 252)),
        )
        img = _composite_layer(img, lambda d: _draw_glyph_content(d, card_box, glyph_type, c_main))

        # Front brand badge on left featuring the Welfarego house + heart glyph
        badge_box = (60, 160, 248, 348)
        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(
                (badge_box[0] + 5, badge_box[1] + 10, badge_box[2] + 5, badge_box[3] + 10),
                radius=42,
                fill=(0, 0, 0, 74),
            ),
        )

        def draw_badge(d: ImageDraw.ImageDraw) -> None:
            d.rounded_rectangle(
                badge_box,
                radius=42,
                fill=(*c_dark, 255),
                outline=(255, 255, 255, 235),
                width=6,
            )
            draw_portal_house_heart_glyph(
                d,
                float(badge_box[0] + 14),
                float(badge_box[1] + 14),
                float((badge_box[2] - badge_box[0]) - 28),
            )

        img = _composite_layer(img, draw_badge)
    else:
        sheet_box = (76, 36, 436, 476)
        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(
                (sheet_box[0] + 5, sheet_box[1] + 10, sheet_box[2] + 5, sheet_box[3] + 10),
                radius=32,
                fill=(0, 0, 0, 52),
            ),
        )

        def draw_sheet(d: ImageDraw.ImageDraw) -> None:
            d.rounded_rectangle(
                sheet_box,
                radius=32,
                fill=(255, 255, 255, 255),
                outline=(*c_main, 255),
                width=12,
            )
            header_h = 84 if not is_template else 104
            d.rounded_rectangle(
                (sheet_box[0], sheet_box[1], sheet_box[2], sheet_box[1] + header_h),
                radius=32,
                fill=(*c_main, 255),
            )
            d.rectangle(
                (sheet_box[0], sheet_box[1] + header_h - 32, sheet_box[2], sheet_box[1] + header_h),
                fill=(*c_main, 255),
            )
            if is_template:
                d.rectangle(
                    (sheet_box[0], sheet_box[1] + header_h - 16, sheet_box[2], sheet_box[1] + header_h),
                    fill=(*c_dark, 255),
                )
            font = load_font(FONT_CANDIDATES_BOLD, 48)
            d.text(
                (sheet_box[0] + 44, sheet_box[1] + header_h // 2 - (4 if is_template else 0)),
                badge_letter,
                font=font,
                fill=(255, 255, 255, 255),
                anchor="lm",
            )

        img = _composite_layer(img, draw_sheet)
        header_h = 84 if not is_template else 104
        content_box = (
            sheet_box[0] + 20,
            sheet_box[1] + header_h + 12,
            sheet_box[2] - 20,
            sheet_box[3] - 20,
        )
        img = _composite_layer(img, lambda d: _draw_glyph_content(d, content_box, glyph_type, c_main))

    return img


def _encode_ico_dib_rgba(img: Image.Image) -> bytes:
    w, h = img.size
    rgba = img.convert("RGBA")
    px = rgba.load()

    bih = struct.pack(
        "<IIIHHIIIIII",
        40,
        w,
        h * 2,
        1,
        32,
        0,
        w * h * 4,
        0,
        0,
        0,
        0,
    )

    xor_rows = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            xor_rows.extend((b, g, r, a))

    row_bytes = ((w + 31) // 32) * 4
    and_mask = bytearray()
    for y in range(h - 1, -1, -1):
        row = bytearray(row_bytes)
        for x in range(w):
            if px[x, y][3] == 0:
                row[x // 8] |= 1 << (7 - (x % 8))
        and_mask.extend(row)

    return bih + bytes(xor_rows) + bytes(and_mask)


def save_multi_size_ico(master: Image.Image, target_path: Path) -> None:
    entries: list[tuple[int, bytes]] = []
    for sz in ICO_SIZES:
        resized = master.resize((sz, sz), Image.Resampling.LANCZOS)
        if sz == 256:
            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            payload = buf.getvalue()
        else:
            payload = _encode_ico_dib_rgba(resized)
        entries.append((sz, payload))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    dir_entries = []
    payloads = []

    for sz, data in entries:
        w_byte = 0 if sz == 256 else sz
        h_byte = 0 if sz == 256 else sz
        dir_entries.append(
            struct.pack("<BBBBHHII", w_byte, h_byte, 0, 0, 1, 32, len(data), offset)
        )
        payloads.append(data)
        offset += len(data)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(header)
        for d in dir_entries:
            f.write(d)
        for p in payloads:
            f.write(p)


def generate_msi_banners(brand: dict) -> None:
    MSI_DIR.mkdir(parents=True, exist_ok=True)
    c_primary = hex_to_rgb(brand["colors"]["primary"])
    c_dark = hex_to_rgb(brand["colors"]["primary_dark"])
    c_ink = hex_to_rgb(brand["colors"]["ink"])

    # 1. Banner.bmp (632x57)
    W, H = 632, 57
    banner = Image.new("RGBA", (W, H), hex_to_rgba("#F5F7FD"))
    draw = ImageDraw.Draw(banner)
    draw.rectangle((0, H - 2, W, H), fill=hex_to_rgba("#D9E1F2"))
    ex = W - 190
    emb34 = render_portal_emblem_tile(out_size=34, pad_ratio=0.0, bg_hex="#2151C8")
    banner.paste(emb34, (ex, 11), emb34)
    f_b = load_font(FONT_CANDIDATES_BOLD, 15)
    f_s = load_font(FONT_CANDIDATES_BOLD, 11)
    draw.text((ex + 42, 21), "Welfarego", font=f_b, fill=(*c_ink, 255), anchor="lm")
    draw.text((ex + 42, 37), "OFFICE", font=f_s, fill=(*c_primary, 255), anchor="lm")
    banner.convert("RGB").save(MSI_DIR / "Banner.bmp", format="BMP")

    # 2. Image.bmp (162x312)
    W, H = 162, 312
    side = create_diagonal_gradient(W, H, c_primary, c_dark)
    emb64 = render_portal_emblem_tile(out_size=64, pad_ratio=0.0, bg_hex="#2E6BE6")
    side.paste(emb64, (28, 36), emb64)
    draw = ImageDraw.Draw(side)
    f_t = load_font(FONT_CANDIDATES_BOLD, 18)
    f_sub = load_font(FONT_CANDIDATES_BOLD, 12)
    f_note = load_font(FONT_CANDIDATES_MEDIUM, 10)
    draw.text((28, 122), "Welfarego", font=f_t, fill=(255, 255, 255, 255))
    draw.text((28, 146), "OFFICE", font=f_sub, fill=hex_to_rgba("#BFDBFE"))
    draw.text((28, 272), "Modern Ribbon Suite", font=f_note, fill=hex_to_rgba("#DBEAFE"))
    side_rgb = side.convert("RGB")
    side_rgb.save(MSI_DIR / "Image.bmp", format="BMP")

    # 3. Image_2.bmp (493x312)
    W, H = 493, 312
    full = Image.new("RGB", (W, H), (255, 255, 255))
    full.paste(side_rgb, (0, 0))
    full.save(MSI_DIR / "Image_2.bmp", format="BMP")

    # 4. Inno Setup WizardImage.bmp (164x314)
    W, H = 164, 314
    wiz_side = create_diagonal_gradient(W, H, c_primary, c_dark)
    emb66 = render_portal_emblem_tile(out_size=66, pad_ratio=0.0, bg_hex="#2E6BE6")
    wiz_side.paste(emb66, (28, 36), emb66)
    draw = ImageDraw.Draw(wiz_side)
    draw.text((28, 124), "Welfarego", font=f_t, fill=(255, 255, 255, 255))
    draw.text((28, 148), "OFFICE", font=f_sub, fill=hex_to_rgba("#BFDBFE"))
    draw.text((28, 258), "Modern Ribbon Suite", font=f_note, fill=hex_to_rgba("#DBEAFE"))
    draw.text((28, 274), "MPL-2.0 Open Source", font=f_note, fill=hex_to_rgba("#BFDBFE"))
    wiz_side.convert("RGB").save(MSI_DIR / "WizardImage.bmp", format="BMP")

    # 5. Inno Setup WizardSmall.bmp (55x58)
    W, H = 55, 58
    wiz_sm = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    emb46 = render_portal_emblem_tile(out_size=46, pad_ratio=0.0, bg_hex="#2151C8")
    wiz_sm.paste(emb46, (4, 6), emb46)
    wiz_sm.convert("RGB").save(MSI_DIR / "WizardSmall.bmp", format="BMP")


def main() -> None:
    brand = load_brand()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    MSI_DIR.mkdir(parents=True, exist_ok=True)

    # 1. SVG wordmarks & About artwork
    logo_svg = make_wordmark_svg(brand, dark_mode=False)
    logo_inv_svg = make_wordmark_svg(brand, dark_mode=True)
    about_svg = make_about_svg()

    (IMAGES_DIR / "logo.svg").write_text(logo_svg, encoding="utf-8")
    (IMAGES_DIR / "logo-sc.svg").write_text(logo_svg, encoding="utf-8")
    (IMAGES_DIR / "logo_inverted.svg").write_text(logo_inv_svg, encoding="utf-8")
    (IMAGES_DIR / "logo-sc_inverted.svg").write_text(logo_inv_svg, encoding="utf-8")
    (IMAGES_DIR / "about.svg").write_text(about_svg, encoding="utf-8")

    # 2. Splash screens & progress.conf
    generate_splash(644, 199, is_highres=False).save(IMAGES_DIR / "intro.png", format="PNG")
    generate_splash(990, 254, is_highres=True).save(IMAGES_DIR / "intro-highres.png", format="PNG")

    progress_conf = """PROGRESSBARCOLOR="96,165,250"
PROGRESSSIZE="584,6"
PROGRESSPOSITION="30,172"
PROGRESSFRAMECOLOR="33,81,200"
PROGRESSTEXTCOLOR="239,246,255"
PROGRESSTEXTBASELINE="160"
"""
    (IMAGES_DIR / "progress.conf").write_text(progress_conf, encoding="utf-8")

    # 3. MSI & Inno Setup bitmaps
    generate_msi_banners(brand)

    # 4. All 31 Windows ICO files
    icon_specs = [
        ("soffice.ico", "#2151C8", "#173D9E", "W", "suite", False, False),
        ("writer_app.ico", "#2151C8", "#173D9E", "W", "writer", False, False),
        ("calc_app.ico", "#15803D", "#14532D", "C", "calc", False, False),
        ("impress_app.ico", "#C2410C", "#7C2D12", "P", "impress", False, False),
        ("draw_app.ico", "#D97706", "#92400E", "D", "draw", False, False),
        ("base_app.ico", "#6D28D9", "#4C1D95", "B", "base", False, False),
        ("math_app.ico", "#334155", "#0F172A", "M", "math", False, False),
        ("text.ico", "#2151C8", "#173D9E", "W", "writer", True, False),
        ("oasis-text.ico", "#2151C8", "#173D9E", "W", "writer", True, False),
        ("text-template.ico", "#2151C8", "#173D9E", "W", "writer", True, True),
        ("oasis-text-template.ico", "#2151C8", "#173D9E", "W", "writer", True, True),
        ("master-document.ico", "#2151C8", "#173D9E", "W", "writer", True, False),
        ("oasis-master-document.ico", "#2151C8", "#173D9E", "W", "writer", True, False),
        ("oasis-web-template.ico", "#2151C8", "#173D9E", "H", "writer", True, True),
        ("spreadsheet.ico", "#15803D", "#14532D", "C", "calc", True, False),
        ("oasis-spreadsheet.ico", "#15803D", "#14532D", "C", "calc", True, False),
        ("spreadsheet-template.ico", "#15803D", "#14532D", "C", "calc", True, True),
        ("oasis-spreadsheet-template.ico", "#15803D", "#14532D", "C", "calc", True, True),
        ("presentation.ico", "#C2410C", "#7C2D12", "P", "impress", True, False),
        ("oasis-presentation.ico", "#C2410C", "#7C2D12", "P", "impress", True, False),
        ("presentation-template.ico", "#C2410C", "#7C2D12", "P", "impress", True, True),
        ("oasis-presentation-template.ico", "#C2410C", "#7C2D12", "P", "impress", True, True),
        ("drawing.ico", "#D97706", "#92400E", "D", "draw", True, False),
        ("oasis-drawing.ico", "#D97706", "#92400E", "D", "draw", True, False),
        ("drawing-template.ico", "#D97706", "#92400E", "D", "draw", True, True),
        ("oasis-drawing-template.ico", "#D97706", "#92400E", "D", "draw", True, True),
        ("database.ico", "#6D28D9", "#4C1D95", "B", "base", True, False),
        ("oasis-database.ico", "#6D28D9", "#4C1D95", "B", "base", True, False),
        ("formula.ico", "#334155", "#0F172A", "M", "math", True, False),
        ("oasis-formula.ico", "#334155", "#0F172A", "M", "math", True, False),
        ("oxt-extension.ico", "#2151C8", "#173D9E", "E", "suite", True, False),
    ]

    cache: dict[tuple, Image.Image] = {}
    for fname, acc, dark, letter, glyph, is_doc, is_tpl in icon_specs:
        key = (acc, dark, letter, glyph, is_doc, is_tpl)
        if key not in cache:
            cache[key] = draw_app_icon_canvas(acc, dark, letter, glyph, is_doc, is_tpl)
        save_multi_size_ico(cache[key], ICONS_DIR / fname)
        if not is_doc:
            cache[key].resize((256, 256), Image.Resampling.LANCZOS).save(
                IMAGES_DIR / fname.replace(".ico", ".png"), format="PNG"
            )

    print(
        f"Generated {len(icon_specs)} multi-resolution Windows ICO files, "
        f"splash screens, SVGs, and MSI bitmaps in {BRAND_DIR}."
    )


if __name__ == "__main__":
    main()
