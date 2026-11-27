# -*- coding: utf-8 -*-
"""Welfarego OFFICE 다운로드·정품 확인서 입력 검증 및 GitHub 비공개 CSV 기록 모듈.

- 이상한 기관명(1~2글자, 자음·모음 나열, 영문/숫자 난수, 반복 문자, 테스트어 등)을 서버 단에서 차단한다.
- Render 환경변수 `GITHUB_LOG_TOKEN`(비공개 저장소 Contents 쓰기 권한 PAT)이 설정되어 있으면
  백그라운드 스레드로 `GITHUB_LOG_REPO`(기본: `BUSTUDY/welfarego-logs`)의 CSV 파일에 행을 누적 기록한다.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent
LOCAL_LOG_DIR = ROOT / "data" / "runtime_logs"

_JAMO_RE = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]")
_HANGUL_SYLLABLE_RE = re.compile(r"[가-힣]")
_ALLOWED_CHARS_RE = re.compile(r"^[가-힣A-Za-z0-9\s·ㆍ\-\(\)&.,/]+$")
_REPEAT3_RE = re.compile(r"(.)\1\1")
_ASCII_MASH_RE = re.compile(r"(asdf|qwer|zxcv|hjkl|yuio|abcd|1234|test|admin|sample|dummy)", re.I)

_DUMMY_ORG_WORDS = {
    "테스트",
    "테스트기관",
    "테스트센터",
    "아무거나",
    "없음",
    "모름",
    "미입력",
    "기관명",
    "센터명",
    "시설명",
    "샘플",
    "샘플기관",
    "샘플센터",
    "임시",
    "임시기관",
    "가나다",
    "가나다라",
    "홍길동",
    "관리자",
    "사용자",
    "기본값",
    "주야간",
    "복지관",
    "요양원",
}

DOWNLOAD_CSV_PATH = "logs/office_downloads.csv"
DOWNLOAD_CSV_HEADER = ["일시(KST)", "구분", "기관명", "사용인원(명)", "설치버전"]

CERT_CSV_PATH = "logs/license_certificates.csv"
CERT_CSV_HEADER = ["일시(KST)", "기관명", "시설장(대표자)", "설치인원(명)", "오피스버전"]

_github_lock = threading.Lock()


def validate_org_name(raw_org: str | None) -> tuple[bool, str]:
    """기관명 유효성을 검사하여 (통과 여부, 정제된 기관명 또는 오류 메시지)를 반환한다."""
    cleaned = re.sub(r"\s+", " ", (raw_org or "").strip())
    if not cleaned:
        return False, "기관명을 입력해 주세요. (예: 행복주·야간보호센터)"

    compact = cleaned.replace(" ", "")
    if len(compact) < 3:
        return False, "기관명은 공백 제외 3글자 이상 정확히 입력해 주세요."
    if len(cleaned) > 60:
        return False, "기관명은 60자 이내로 입력해 주세요."
    if _JAMO_RE.search(cleaned):
        return False, "자음·모음 나열(예: ㅁㄴㅇㄹ, ㅋㅋㅋ)은 사용할 수 없습니다. 정확한 한글 기관명을 입력해 주세요."
    if not _ALLOWED_CHARS_RE.match(cleaned):
        return False, "기관명에 사용할 수 없는 특수문자가 포함되어 있습니다."
    if _REPEAT3_RE.search(compact):
        return False, "같은 글자가 3회 이상 반복된 기관명은 사용할 수 없습니다."

    hangul_chars = _HANGUL_SYLLABLE_RE.findall(cleaned)
    if len(hangul_chars) < 2:
        return False, "영문·숫자 나열 대신 실제 한글 기관명(완성형 한글 2글자 이상 포함)을 입력해 주세요."
    if len(set(hangul_chars)) < 2:
        return False, "의미 없는 반복 한글 대신 실제 기관명을 입력해 주세요."

    lowered_compact = compact.lower()
    if lowered_compact in _DUMMY_ORG_WORDS or _ASCII_MASH_RE.search(lowered_compact):
        return False, "테스트·임시 문구 대신 실제 사용하시는 기관명을 입력해 주세요."

    return True, cleaned


def validate_user_count(raw_users: str | int | None) -> tuple[bool, int | str]:
    """사용(설치) 인원(1~500명)을 검사한다."""
    s = str(raw_users or "").strip()
    m = re.match(r"^(\d{1,4})\s*(?:명|대|인)?$", s)
    if not m:
        return False, "사용(설치) 인원은 1 이상 숫자로 입력해 주세요. (예: 12)"
    count = int(m.group(1))
    if count < 1 or count > 500:
        return False, "사용(설치) 인원은 1명 이상 500명 이하로 입력해 주세요."
    return True, count


def _csv_row_line(values: list[object]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([str(v) for v in values])
    return buf.getvalue()


def _append_local_csv(rel_path: str, header: list[str], row: list[object]) -> None:
    try:
        target = LOCAL_LOG_DIR / Path(rel_path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        need_header = not target.exists() or target.stat().st_size == 0
        with target.open("a", encoding="utf-8", newline="") as f:
            if need_header:
                f.write("\ufeff" + _csv_row_line(header))
            f.write(_csv_row_line(row))
    except OSError:
        pass


def _append_github_csv(rel_path: str, header: list[str], row: list[object], commit_msg: str) -> bool:
    token = os.environ.get("GITHUB_LOG_TOKEN", "").strip()
    if not token:
        return False
    repo = os.environ.get("GITHUB_LOG_REPO", "BUSTUDY/welfarego-logs").strip()
    branch = os.environ.get("GITHUB_LOG_BRANCH", "main").strip() or "main"
    api_url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "welfarego-office-logger",
    }

    with _github_lock:
        for attempt in range(3):
            sha = None
            existing_text = ""
            get_req = urllib.request.Request(f"{api_url}?ref={branch}", headers=headers, method="GET")
            try:
                with urllib.request.urlopen(get_req, timeout=8) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    sha = payload.get("sha")
                    raw_b64 = payload.get("content", "")
                    existing_text = base64.b64decode(raw_b64).decode("utf-8")
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    return False
            except Exception:
                return False

            if not existing_text:
                existing_text = "\ufeff" + _csv_row_line(header)
            elif not existing_text.endswith("\n"):
                existing_text += "\n"

            updated_text = existing_text + _csv_row_line(row)
            put_body: dict[str, object] = {
                "message": commit_msg,
                "content": base64.b64encode(updated_text.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if sha:
                put_body["sha"] = sha

            put_req = urllib.request.Request(
                api_url,
                data=json.dumps(put_body).encode("utf-8"),
                headers={**headers, "Content-Type": "application/json"},
                method="PUT",
            )
            try:
                with urllib.request.urlopen(put_req, timeout=10) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except urllib.error.HTTPError as exc:
                if exc.code == 409 and attempt < 2:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                return False
            except Exception:
                return False
    return False


def _dispatch_log(rel_path: str, header: list[str], row: list[object], commit_msg: str, async_mode: bool = True) -> None:
    _append_local_csv(rel_path, header, row)
    if not os.environ.get("GITHUB_LOG_TOKEN", "").strip():
        return
    if async_mode:
        t = threading.Thread(
            target=_append_github_csv,
            args=(rel_path, header, row, commit_msg),
            daemon=True,
        )
        t.start()
    else:
        _append_github_csv(rel_path, header, row, commit_msg)


def record_office_download(org_name: str, user_count: int, version: str, fmt: str = "exe") -> None:
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    row = [now_kst, fmt.upper(), org_name, user_count, version]
    _dispatch_log(
        DOWNLOAD_CSV_PATH,
        DOWNLOAD_CSV_HEADER,
        row,
        f"log(download): {org_name} ({user_count}명)",
    )


def record_license_certificate(org_name: str, rep_name: str, user_count: int, version: str) -> None:
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    row = [now_kst, org_name, rep_name, user_count, version]
    _dispatch_log(
        CERT_CSV_PATH,
        CERT_CSV_HEADER,
        row,
        f"log(certificate): {org_name} ({user_count}명)",
    )
