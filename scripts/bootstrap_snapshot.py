"""Copy the public deployment snapshot once, before switching Render's repository."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "data/welfare_services.json": ("https://welfarego.co.kr/data/welfare_services.json", "4ffde58903cc772c3a0b35f775faa6ac3b0ab3365c56abd592f5b8838e40c910"),
    "static/og/welfare.png": ("https://welfarego.co.kr/static/og/welfare.png", "73a0a1662a2f00244756e09f831eb9748e20ca1a52a0cfbeeb01150e157e30d8"),
}

def bootstrap(root=ROOT):
    for relative, (url, expected) in ASSETS.items():
        target = Path(root) / relative
        if target.exists():
            print(f"Already present: {relative}")
            continue
        with urlopen(Request(url, headers={"Cache-Control": "no-cache"}), timeout=90) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise RuntimeError(f"Snapshot checksum changed: {relative}; inspect the source before retrying")
        if relative.endswith(".json"):
            document = json.loads(payload)
            if len(document.get("items", [])) < 1000:
                raise RuntimeError("Snapshot contains too few services")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, target)
        print(f"Copied: {relative} ({len(payload):,} bytes)")

if __name__ == "__main__":
    bootstrap()
