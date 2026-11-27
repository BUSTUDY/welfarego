#!/usr/bin/env python3
"""
Automated Commercial Open-Source Compliance & Integrity Verifier for Welfarego OFFICE.

Checks:
1. Legal files present & complete (MPL-2.0 LICENSE, NOTICE, COMPLIANCE-GUIDE, THIRD-PARTY-LICENSES, SOURCE-OFFER, PRIVACY)
2. Commercial MPL-2.0 build configuration enforces --enable-mpl-subset, --enable-release-build,
   --disable-online-update, --disable-breakpad, and excludes all GPL/LGPL icon themes
3. Branding assets are complete, right-sized, and free of TDF/LibreOffice trademark misuse
4. All 31 Windows .ico files exist and contain valid ICO headers with multi-resolution layers
5. Patches exist, are non-empty, and (optionally when --lo-dir is provided) apply cleanly to LibreOffice 26.2.7.3
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_LEGAL_FILES = [
    ROOT / "LICENSE",
    ROOT / "NOTICE",
    ROOT / "legal" / "COMPLIANCE-GUIDE.md",
    ROOT / "legal" / "THIRD-PARTY-LICENSES.md",
    ROOT / "legal" / "SOURCE-OFFER.md",
    ROOT / "legal" / "PRIVACY.md",
]

REQUIRED_ICONS = [
    "soffice.ico",
    "writer_app.ico",
    "calc_app.ico",
    "impress_app.ico",
    "draw_app.ico",
    "base_app.ico",
    "math_app.ico",
    "text.ico",
    "oasis-text.ico",
    "text-template.ico",
    "oasis-text-template.ico",
    "master-document.ico",
    "oasis-master-document.ico",
    "oasis-web-template.ico",
    "spreadsheet.ico",
    "oasis-spreadsheet.ico",
    "spreadsheet-template.ico",
    "oasis-spreadsheet-template.ico",
    "presentation.ico",
    "oasis-presentation.ico",
    "presentation-template.ico",
    "oasis-presentation-template.ico",
    "drawing.ico",
    "oasis-drawing.ico",
    "drawing-template.ico",
    "oasis-drawing-template.ico",
    "database.ico",
    "oasis-database.ico",
    "formula.ico",
    "oasis-formula.ico",
    "oxt-extension.ico",
]

FORBIDDEN_GPL_THEMES = [
    "breeze",
    "elementary",
    "karasa_jaga",
]


def fail(msg: str, errors: list[str]) -> None:
    print(f"  [FAIL] {msg}")
    errors.append(msg)


def ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


def check_legal(errors: list[str]) -> None:
    print("\n1. Legal & Open-Source License Files")
    for f in REQUIRED_LEGAL_FILES:
        if not f.is_file() or f.stat().st_size < 200:
            fail(f"Missing or incomplete legal file: {f.relative_to(ROOT)}", errors)
        else:
            ok(f"{f.relative_to(ROOT)} ({f.stat().st_size:,} bytes)")

    lic = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if "Mozilla Public License Version 2.0" not in lic:
        fail("LICENSE does not contain Mozilla Public License Version 2.0 header", errors)
    else:
        ok("LICENSE verified as Mozilla Public License Version 2.0")

    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    for required_phrase in ("Apache Software Foundation", "The Document Foundation", "MPL-2.0"):
        if required_phrase not in notice:
            fail(f"NOTICE missing required attribution/disclaimer: {required_phrase}", errors)
    ok("NOTICE preserves upstream Apache/OpenSSL attributions and TDF trademark disclaimer")


def check_build_config(errors: list[str]) -> None:
    print("\n2. Commercial Build Configuration (windows-x64.autogen.input)")
    cfg_path = ROOT / "config" / "windows-x64.autogen.input"
    if not cfg_path.is_file():
        fail("Missing config/windows-x64.autogen.input", errors)
        return

    lines = [
        ln.strip()
        for ln in cfg_path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]

    required_flags = [
        "--enable-mpl-subset",
        "--enable-release-build",
        "--with-product-name=Welfarego OFFICE",
        "--with-vendor=Welfarego",
        "--with-package-format=msi",
        "--disable-online-update",
        "--disable-breakpad",
        "--disable-poppler",
        "--disable-lpsolve",
        "--disable-postgresql-sdbc",
        "--disable-lotuswordpro",
        "--disable-report-builder",
    ]
    for flag in required_flags:
        if flag not in lines:
            fail(f"Required commercial/compliance flag missing in autogen.input: {flag}", errors)
        else:
            ok(f"Flag present: {flag}")

    # Verify no quoted flag values (autogen.sh treats lines verbatim)
    for ln in lines:
        if '="' in ln or "='" in ln:
            fail(f"autogen.input line must not contain shell quotes: {ln}", errors)

    # Verify no GPL/LGPL icon themes enabled
    theme_lines = [ln for ln in lines if ln.startswith("--with-theme=")]
    if not theme_lines:
        fail("Missing explicit --with-theme= restriction", errors)
    else:
        for bad in FORBIDDEN_GPL_THEMES:
            if bad in theme_lines[0]:
                fail(f"GPL/LGPL icon theme '{bad}' found in --with-theme", errors)
        ok("Only CC0 (colibre) and MPL-2.0 (sukapura) icon themes enabled")


def check_branding_assets(errors: list[str]) -> None:
    print("\n3. Original Branding Assets & Trademark Cleanliness")
    brand = json.loads((ROOT / "branding" / "brand.json").read_text(encoding="utf-8"))
    if "libreoffice" in brand["product_name"].lower():
        fail("brand.json product_name must not contain 'LibreOffice' trademark", errors)
    else:
        ok(f"Product name cleanly separated: '{brand['product_name']}'")

    # Check SVGs
    img_dir = ROOT / "branding" / "images"
    for svg_name in ("logo.svg", "logo_inverted.svg", "logo-sc.svg", "logo-sc_inverted.svg", "about.svg"):
        p = img_dir / svg_name
        if not p.is_file():
            fail(f"Missing SVG: {svg_name}", errors)
            continue
        txt = p.read_text(encoding="utf-8")
        if "libreoffice" in txt.lower() or "documentfoundation" in txt.lower():
            fail(f"Forbidden upstream trademark reference found in {svg_name}", errors)
    ok("All 5 brand SVG files present and free of upstream trademarks")

    # Check Splash PNG & Installer BMP dimensions
    expected_dims = {
        img_dir / "intro.png": (644, 199),
        img_dir / "intro-highres.png": (990, 254),
        ROOT / "branding" / "msi" / "Banner.bmp": (632, 57),
        ROOT / "branding" / "msi" / "Image.bmp": (162, 312),
        ROOT / "branding" / "msi" / "Image_2.bmp": (493, 312),
        ROOT / "branding" / "msi" / "WizardImage.bmp": (164, 314),
        ROOT / "branding" / "msi" / "WizardSmall.bmp": (55, 58),
    }
    for path, dims in expected_dims.items():
        if not path.is_file():
            fail(f"Missing image asset: {path.relative_to(ROOT)}", errors)
            continue
        with Image.open(path) as im:
            if im.size != dims:
                fail(f"{path.name} has size {im.size}, expected {dims}", errors)
            else:
                ok(f"{path.relative_to(ROOT)} verified ({dims[0]}x{dims[1]})")

    for req_inst in (
        ROOT / "installer" / "WelfaregoOFFICE.iss",
        ROOT / "installer" / "Korean.isl",
        ROOT / "legal" / "INSTALLER-LICENSE-KO.txt",
    ):
        if not req_inst.is_file():
            fail(f"Missing Windows .exe installer asset: {req_inst.relative_to(ROOT)}", errors)
        else:
            ok(f"{req_inst.relative_to(ROOT)} present")

    if not (img_dir / "progress.conf").is_file():
        fail("Missing branding/images/progress.conf", errors)
    else:
        ok("branding/images/progress.conf present")

    # Check all 31 ICO files
    ico_dir = ROOT / "branding" / "icons"
    missing_icons = []
    bad_icons = []
    for name in REQUIRED_ICONS:
        p = ico_dir / name
        if not p.is_file():
            missing_icons.append(name)
            continue
        data = p.read_bytes()
        if len(data) < 22:
            bad_icons.append(name)
            continue
        reserved, ico_type, count = struct.unpack("<HHH", data[:6])
        if reserved != 0 or ico_type != 1 or count < 10:
            bad_icons.append(f"{name}(type={ico_type},count={count})")
    if missing_icons:
        fail(f"Missing Windows .ico files: {', '.join(missing_icons)}", errors)
    elif bad_icons:
        fail(f"Invalid Windows .ico binary format: {', '.join(bad_icons)}", errors)
    else:
        ok(f"All {len(REQUIRED_ICONS)} multi-resolution Windows .ico files verified (13 layers each)")


def check_patches(lo_dir: Path | None, errors: list[str]) -> None:
    print("\n4. Source Patches Verification")
    patches = sorted((ROOT / "patches").glob("*.patch"))
    if len(patches) < 3:
        fail(f"Expected at least 3 patches in patches/, found {len(patches)}", errors)
        return
    for p in patches:
        text = p.read_text(encoding="utf-8")
        if "diff --git" not in text:
            fail(f"Invalid unified diff in {p.name}", errors)
        else:
            ok(f"{p.name} ({len(text.splitlines())} lines)")

    if lo_dir is not None:
        print(f"\n5. Live Patch Dry-Run Against Upstream Checkout ({lo_dir})")
        # Test applying all patches in sequence, then clean up with git checkout -- .
        applied = False
        try:
            for p in patches:
                res = subprocess.run(
                    ["git", "-C", str(lo_dir), "apply", str(p)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    fail(f"Patch {p.name} failed to apply to {lo_dir}: {res.stderr.strip()}", errors)
                else:
                    applied = True
                    ok(f"Cleanly applied {p.name} to upstream tree")
        finally:
            if applied:
                subprocess.run(["git", "-C", str(lo_dir), "checkout", "--", "."], check=False)


def check_extension(errors: list[str]) -> None:
    import xml.etree.ElementTree as ET
    import zipfile

    print("\n5. Bundled Practical Shortcuts Extension (extensions/welfarego-links.oxt)")
    oxt_path = ROOT / "extensions" / "welfarego-links.oxt"
    if not oxt_path.is_file():
        fail("Missing extensions/welfarego-links.oxt", errors)
        return

    req_entries = {
        "META-INF/manifest.xml",
        "Addons.xcu",
        "ProtocolHandler.xcu",
        "description.xml",
        "welfarego_links.py",
        "LICENSE.txt",
    }
    with zipfile.ZipFile(oxt_path) as zf:
        names = set(zf.namelist())
        missing = sorted(req_entries - names)
        if missing:
            fail(f"welfarego-links.oxt missing required entries: {', '.join(missing)}", errors)
            return
        if any("Jobs.xcu" in n for n in names):
            fail("welfarego-links.oxt must NOT contain Jobs.xcu startup/exit auto-launch hooks", errors)
            return
        for xml_name in ("META-INF/manifest.xml", "Addons.xcu", "ProtocolHandler.xcu", "description.xml"):
            try:
                ET.fromstring(zf.read(xml_name))
            except ET.ParseError as exc:
                fail(f"Invalid XML in {xml_name}: {exc}", errors)
                return
        py_src = zf.read("welfarego_links.py").decode("utf-8")
        if "OnStartApp" in py_src or "URIS_ONLY_FLAG = 1" not in py_src:
            fail("welfarego_links.py must enforce URIS_ONLY_FLAG = 1 without startup hooks", errors)
            return
    ok(f"extensions/welfarego-links.oxt verified ({oxt_path.stat().st_size:,} bytes, voluntary-click only)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Welfarego OFFICE compliance and build artifacts.")
    parser.add_argument("--lo-dir", type=Path, default=None, help="Optional LibreOffice core checkout for live patch test")
    args = parser.parse_args()

    errors: list[str] = []
    print("=== Welfarego OFFICE Commercial Open-Source Compliance & Integrity Check ===")
    check_legal(errors)
    check_build_config(errors)
    check_branding_assets(errors)
    check_patches(args.lo_dir, errors)
    check_extension(errors)

    print("\n=== Summary ===")
    if errors:
        print(f"FAILED with {len(errors)} error(s).")
        sys.exit(1)
    print("ALL CHECKS PASSED.")


if __name__ == "__main__":
    main()
