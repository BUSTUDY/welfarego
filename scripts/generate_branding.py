#!/usr/bin/env python3
"""
Generate all original branding assets for Welfarego OFFICE.

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
]

FONT_CANDIDATES_MEDIUM = [
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf",
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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


def make_wordmark_svg(brand: dict, dark_mode: bool = False) -> str:
    """
    Create crisp SVG wordmark for Start Center & About Dialog.
    Matches LibreOffice brand SVG aspect ratio (360x72).
    """
    text_primary = "#FFFFFF" if dark_mode else "#192D2A"
    accent = "#14B8A6" if dark_mode else brand["colors"]["primary"]
    accent_dark = "#0D9488" if dark_mode else brand["colors"]["primary_dark"]
    badge_bg = "#134E4A" if dark_mode else "#E6F4F1"
    badge_fg = "#5EEAD4" if dark_mode else brand["colors"]["primary"]

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="360" height="72" viewBox="0 0 360 72">
  <defs>
    <linearGradient id="wgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{accent}"/>
      <stop offset="100%" stop-color="{accent_dark}"/>
    </linearGradient>
  </defs>
  <rect x="4" y="8" width="56" height="56" rx="14" fill="url(#wgGrad)"/>
  <rect x="14" y="16" width="24" height="32" rx="4" fill="#FFFFFF" fill-opacity="0.22"/>
  <path d="M16 25 L22.5 47 L29.5 32 L36.5 47 L43 25" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="45" cy="23" r="3.2" fill="#5EEAD4"/>
  <text x="74" y="46" font-family="Segoe UI, Roboto, Noto Sans KR, Liberation Sans, sans-serif" font-size="28" font-weight="800" fill="{text_primary}">Welfarego</text>
  <rect x="218" y="21" width="90" height="30" rx="8" fill="{badge_bg}"/>
  <text x="263" y="42" text-anchor="middle" font-family="Segoe UI, Roboto, Noto Sans KR, Liberation Sans, sans-serif" font-size="15" font-weight="800" fill="{badge_fg}" letter-spacing="1.5">OFFICE</text>
</svg>
"""


def make_about_svg() -> str:
    """
    Create decorative modern geometric background artwork for the About dialog.
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="372" height="354" viewBox="0 0 372 354">
  <defs>
    <linearGradient id="abGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#08776A" stop-opacity="0.11"/>
      <stop offset="100%" stop-color="#2B579A" stop-opacity="0.04"/>
    </linearGradient>
    <linearGradient id="abGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#14B8A6" stop-opacity="0.13"/>
      <stop offset="100%" stop-color="#08776A" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <rect x="16" y="16" width="340" height="322" rx="28" fill="url(#abGrad1)"/>
  <circle cx="312" cy="64" r="76" fill="url(#abGrad2)"/>
  <circle cx="60" cy="292" r="64" fill="url(#abGrad2)"/>
  <rect x="42" y="44" width="124" height="14" rx="7" fill="#08776A" fill-opacity="0.09"/>
  <rect x="42" y="68" width="84" height="10" rx="5" fill="#08776A" fill-opacity="0.06"/>
</svg>
"""


def _composite_layer(base: Image.Image, draw_fn) -> Image.Image:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    draw_fn(draw)
    return Image.alpha_composite(base, layer)


def generate_splash(width: int, height: int, is_highres: bool = False) -> Image.Image:
    """
    Generate crisp supersampled splash screen (intro.png: 644x199, intro-highres.png: 990x254).
    Uses proper alpha_composite layering so translucent glass effects render cleanly.
    """
    scale = 2
    W, H = width * scale, height * scale
    img = create_diagonal_gradient(W, H, hex_to_rgb("#075C53"), hex_to_rgb("#0A2E2B"))

    # Ambient geometric glow shapes
    img = _composite_layer(
        img,
        lambda d: d.ellipse(
            (W - int(H * 1.15), -int(H * 0.45), W + int(H * 0.4), int(H * 1.1)),
            fill=(20, 184, 166, 36),
        ),
    )
    img = _composite_layer(
        img,
        lambda d: d.ellipse(
            (W - int(H * 0.72), int(H * 0.12), W + int(H * 0.48), int(H * 1.32)),
            fill=(255, 255, 255, 22),
        ),
    )

    # Modern stylized glass ribbon card motif on the right
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
            outline=(255, 255, 255, 55),
            width=2,
        ),
    )

    def draw_card_inner(d: ImageDraw.ImageDraw) -> None:
        inner_x = card_x0 + int(16 * scale)
        inner_y = card_y0 + int(16 * scale)
        pill_colors = ["#38BDF8", "#34D399", "#FB923C", "#A78BFA"]
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
                fill=(255, 255, 255, 58),
            )

    img = _composite_layer(img, draw_card_inner)

    # Left glass emblem squircle + stylized W mark
    pad_x = int((42 if is_highres else 30) * scale)
    icon_size = int((76 if is_highres else 56) * scale)
    icon_y = int((48 if is_highres else 38) * scale)

    def draw_emblem(d: ImageDraw.ImageDraw) -> None:
        d.rounded_rectangle(
            (pad_x, icon_y, pad_x + icon_size, icon_y + icon_size),
            radius=int(icon_size * 0.26),
            fill=(20, 184, 166, 55),
            outline=(94, 234, 212, 195),
            width=max(2, scale),
        )
        pts = [
            (pad_x + icon_size * 0.22, icon_y + icon_size * 0.30),
            (pad_x + icon_size * 0.36, icon_y + icon_size * 0.72),
            (pad_x + icon_size * 0.50, icon_y + icon_size * 0.45),
            (pad_x + icon_size * 0.64, icon_y + icon_size * 0.72),
            (pad_x + icon_size * 0.78, icon_y + icon_size * 0.30),
        ]
        d.line(pts, fill=(255, 255, 255, 255), width=int(icon_size * 0.095), joint="curve")
        r_dot = int(icon_size * 0.065)
        dx = int(pad_x + icon_size * 0.80)
        dy = int(icon_y + icon_size * 0.26)
        d.ellipse((dx - r_dot, dy - r_dot, dx + r_dot, dy + r_dot), fill=(94, 234, 212, 255))

    img = _composite_layer(img, draw_emblem)

    # Title, OFFICE pill, subtitle, and progress track
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
        d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=int(7 * scale), fill=(20, 184, 166, 240))
        d.text(
            (bx + bw // 2, by + bh // 2),
            "OFFICE",
            font=badge_font,
            fill=(6, 44, 40, 255),
            anchor="mm",
        )

        sub_y = title_y + int((50 if is_highres else 36) * scale)
        d.text(
            (text_x, sub_y),
            "Modern Fluent Ribbon Suite  •  Writer  •  Calc  •  Impress  •  Draw",
            font=sub_font,
            fill=(204, 251, 241, 225),
        )

        track_y = int((210 if is_highres else 172) * scale)
        track_h = int((8 if is_highres else 6) * scale)
        d.rounded_rectangle(
            (pad_x, track_y, W - pad_x, track_y + track_h),
            radius=track_h // 2,
            fill=(255, 255, 255, 42),
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
            hex_to_rgb("#2B579A"),
            hex_to_rgb("#107C41"),
            hex_to_rgb("#C43E1C"),
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

        # Floating white document sheet on right with composited shadow
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

        # Front brand badge on left with composited shadow
        badge_box = (64, 164, 248, 348)
        img = _composite_layer(
            img,
            lambda d: d.rounded_rectangle(
                (badge_box[0] + 5, badge_box[1] + 10, badge_box[2] + 5, badge_box[3] + 10),
                radius=40,
                fill=(0, 0, 0, 74),
            ),
        )

        def draw_badge(d: ImageDraw.ImageDraw) -> None:
            d.rounded_rectangle(
                badge_box,
                radius=40,
                fill=(*c_dark, 255),
                outline=(255, 255, 255, 232),
                width=6,
            )
            font = load_font(FONT_CANDIDATES_BOLD, 108)
            cx = (badge_box[0] + badge_box[2]) // 2
            cy = (badge_box[1] + badge_box[3]) // 2
            d.text((cx, cy), badge_letter, font=font, fill=(255, 255, 255, 255), anchor="mm")

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
    """
    Encode an RGBA PIL Image as a 32-bit Windows ICO DIB (BITMAPINFOHEADER + bottom-up BGRA + AND mask).
    Standard Windows ICO entries <= 128px use BMP DIB for universal compatibility with rc.exe & Shell.
    """
    w, h = img.size
    rgba = img.convert("RGBA")
    px = rgba.load()

    # BITMAPINFOHEADER (40 bytes): biHeight is 2*h (XOR + AND masks)
    bih = struct.pack(
        "<IIIHHIIIIII",
        40,      # biSize
        w,       # biWidth
        h * 2,   # biHeight (XOR + AND)
        1,       # biPlanes
        32,      # biBitCount
        0,       # biCompression = BI_RGB
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

    # 1-bit AND mask padded to 32-bit (4-byte) boundary per row
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
    """
    Write a Windows ICO file containing all 13 standard HiDPI sizes (16..256px).
    Sizes <= 128 use 32-bit BMP DIB; 256px uses compressed PNG (standard Windows Vista/10/11 ICO).
    """
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
    """
    Generate Windows Installer (MSI) bitmaps:
    - Banner.bmp (632 x 57) - wizard header banner
    - Image.bmp (162 x 312) - welcome/finish sidebar graphic
    - Image_2.bmp (493 x 312) - full welcome graphic
    """
    MSI_DIR.mkdir(parents=True, exist_ok=True)
    c_primary = hex_to_rgb(brand["colors"]["primary"])
    c_dark = hex_to_rgb(brand["colors"]["primary_dark"])
    c_ink = hex_to_rgb(brand["colors"]["ink"])

    # 1. Banner.bmp (632x57)
    W, H = 632, 57
    banner = Image.new("RGB", (W, H), hex_to_rgb("#F7F9F7"))
    draw = ImageDraw.Draw(banner)
    draw.rectangle((0, H - 2, W, H), fill=hex_to_rgb("#E3E9E6"))
    ex = W - 186
    draw.rounded_rectangle((ex, 12, ex + 33, 45), radius=8, fill=c_primary)
    f_w = load_font(FONT_CANDIDATES_BOLD, 18)
    f_b = load_font(FONT_CANDIDATES_BOLD, 15)
    f_s = load_font(FONT_CANDIDATES_BOLD, 11)
    draw.text((ex + 16, 28), "W", font=f_w, fill=(255, 255, 255), anchor="mm")
    draw.text((ex + 42, 21), "Welfarego", font=f_b, fill=c_ink, anchor="lm")
    draw.text((ex + 42, 37), "OFFICE", font=f_s, fill=c_primary, anchor="lm")
    banner.save(MSI_DIR / "Banner.bmp", format="BMP")

    # 2. Image.bmp (162x312)
    W, H = 162, 312
    side = create_diagonal_gradient(W, H, c_primary, c_dark).convert("RGB")
    draw = ImageDraw.Draw(side)
    draw.rounded_rectangle((28, 36, 92, 100), radius=16, fill=hex_to_rgb("#14B8A6"))
    f_big = load_font(FONT_CANDIDATES_BOLD, 36)
    draw.text((60, 68), "W", font=f_big, fill=(255, 255, 255), anchor="mm")
    f_t = load_font(FONT_CANDIDATES_BOLD, 18)
    f_sub = load_font(FONT_CANDIDATES_BOLD, 12)
    f_note = load_font(FONT_CANDIDATES_MEDIUM, 10)
    draw.text((28, 122), "Welfarego", font=f_t, fill=(255, 255, 255))
    draw.text((28, 146), "OFFICE", font=f_sub, fill=hex_to_rgb("#99F6E4"))
    draw.text((28, 272), "Modern Ribbon Suite", font=f_note, fill=hex_to_rgb("#CCFBF1"))
    side.save(MSI_DIR / "Image.bmp", format="BMP")

    # 3. Image_2.bmp (493x312)
    W, H = 493, 312
    full = Image.new("RGB", (W, H), (255, 255, 255))
    full.paste(side, (0, 0))
    full.save(MSI_DIR / "Image_2.bmp", format="BMP")


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

    progress_conf = """PROGRESSBARCOLOR="20,184,166"
PROGRESSSIZE="584,6"
PROGRESSPOSITION="30,172"
PROGRESSFRAMECOLOR="13,148,136"
PROGRESSTEXTCOLOR="240,253,250"
PROGRESSTEXTBASELINE="160"
"""
    (IMAGES_DIR / "progress.conf").write_text(progress_conf, encoding="utf-8")

    # 3. MSI Installer bitmaps
    generate_msi_banners(brand)

    # 4. All 31 Windows ICO files matching sysui/desktop/icons/*.ico
    icon_specs = [
        ("soffice.ico", "#08776A", "#075C53", "W", "suite", False, False),
        ("writer_app.ico", "#2B579A", "#1E3A8A", "W", "writer", False, False),
        ("calc_app.ico", "#107C41", "#065F46", "C", "calc", False, False),
        ("impress_app.ico", "#C43E1C", "#9A3412", "P", "impress", False, False),
        ("draw_app.ico", "#D97706", "#92400E", "D", "draw", False, False),
        ("base_app.ico", "#7460A7", "#5B21B6", "B", "base", False, False),
        ("math_app.ico", "#475569", "#1E293B", "M", "math", False, False),
        ("text.ico", "#2B579A", "#1E3A8A", "W", "writer", True, False),
        ("oasis-text.ico", "#2B579A", "#1E3A8A", "W", "writer", True, False),
        ("text-template.ico", "#2B579A", "#1E3A8A", "W", "writer", True, True),
        ("oasis-text-template.ico", "#2B579A", "#1E3A8A", "W", "writer", True, True),
        ("master-document.ico", "#2B579A", "#1E3A8A", "W", "writer", True, False),
        ("oasis-master-document.ico", "#2B579A", "#1E3A8A", "W", "writer", True, False),
        ("oasis-web-template.ico", "#08776A", "#075C53", "H", "writer", True, True),
        ("spreadsheet.ico", "#107C41", "#065F46", "C", "calc", True, False),
        ("oasis-spreadsheet.ico", "#107C41", "#065F46", "C", "calc", True, False),
        ("spreadsheet-template.ico", "#107C41", "#065F46", "C", "calc", True, True),
        ("oasis-spreadsheet-template.ico", "#107C41", "#065F46", "C", "calc", True, True),
        ("presentation.ico", "#C43E1C", "#9A3412", "P", "impress", True, False),
        ("oasis-presentation.ico", "#C43E1C", "#9A3412", "P", "impress", True, False),
        ("presentation-template.ico", "#C43E1C", "#9A3412", "P", "impress", True, True),
        ("oasis-presentation-template.ico", "#C43E1C", "#9A3412", "P", "impress", True, True),
        ("drawing.ico", "#D97706", "#92400E", "D", "draw", True, False),
        ("oasis-drawing.ico", "#D97706", "#92400E", "D", "draw", True, False),
        ("drawing-template.ico", "#D97706", "#92400E", "D", "draw", True, True),
        ("oasis-drawing-template.ico", "#D97706", "#92400E", "D", "draw", True, True),
        ("database.ico", "#7460A7", "#5B21B6", "B", "base", True, False),
        ("oasis-database.ico", "#7460A7", "#5B21B6", "B", "base", True, False),
        ("formula.ico", "#475569", "#1E293B", "M", "math", True, False),
        ("oasis-formula.ico", "#475569", "#1E293B", "M", "math", True, False),
        ("oxt-extension.ico", "#08776A", "#075C53", "E", "suite", True, False),
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
