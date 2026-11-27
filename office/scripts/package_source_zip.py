#!/usr/bin/env python3
"""Package the Welfarego OFFICE corresponding source archive (MPL-2.0 §3.2 / LGPLv3 §4)."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

OFFICE_ROOT = Path(__file__).resolve().parent.parent
INCLUDE_ROOTS = (
    "LICENSE",
    "NOTICE",
    "README.md",
    "legal",
    "config",
    "installer",
    "extensions",
    "patches",
    "scripts",
)


def default_version() -> str:
    brand_path = OFFICE_ROOT / "branding" / "brand.json"
    if brand_path.is_file():
        data = json.loads(brand_path.read_text(encoding="utf-8"))
        if data.get("package_version"):
            return str(data["package_version"])
    return "26.2.9"


def build_source_zip(output_path: Path, version: str) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    top_dir = f"WelfaregoOFFICE_{version}_Source"
    file_count = 0
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE_ROOTS:
            path = OFFICE_ROOT / item
            if path.is_file():
                zf.write(path, arcname=f"{top_dir}/{item}")
                file_count += 1
            elif path.is_dir():
                for sub in sorted(path.rglob("*")):
                    if sub.is_file() and "__pycache__" not in sub.parts and sub.suffix != ".pyc":
                        rel = sub.relative_to(OFFICE_ROOT).as_posix()
                        zf.write(sub, arcname=f"{top_dir}/{rel}")
                        file_count += 1
    return file_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Welfarego OFFICE source archive ZIP.")
    parser.add_argument("--version", default=default_version(), help="Welfarego OFFICE version")
    parser.add_argument("--output", type=Path, required=True, help="Output ZIP file path")
    args = parser.parse_args()

    count = build_source_zip(args.output, args.version)
    size = args.output.stat().st_size
    print(f"[OK] Packaged {args.output.name} ({count} files, {size:,} bytes)")


if __name__ == "__main__":
    main()
