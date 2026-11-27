# -*- coding: utf-8 -*-
"""경량 인메모리 슬라이딩 윈도우 속도 제한기 (Render 대역폭·CPU 보호용).

정상 이용자(시설장·사회복지사)의 서식 일괄 열람·다운로드는 전혀 방해하지 않으면서,
비정상 자동화 스크립트·봇의 무한 반복 다운로드만 선제 차단한다.
"""

from collections import OrderedDict, deque
import math
import threading
import time

from flask import Response, current_app, request

MAX_TRACKED_KEYS = 4096

# 버킷별 (윈도우 초, 허용 횟수) 규칙
BUCKET_RULES = {
    # 20종 전체 ZIP(523KB) 및 소스 ZIP: 분당 6회, 시간당 25회
    "zip": ((60.0, 6), (3600.0, 25)),
    # 개별 서식(.hwpx/.hwp/.docx/.xlsx) 및 설치파일 리다이렉트: 분당 45회, 시간당 240회
    "download": ((60.0, 45), (3600.0, 240)),
    # 일반 동적 웹페이지·인쇄 미리보기: 분당 120회
    "page": ((60.0, 120),),
}

_lock = threading.Lock()
_history = OrderedDict()  # (bucket, ip) -> deque[float]


def get_client_ip(req=None):
    """Cloudflare·Render 프록시 헤더를 우선 확인하여 클라이언트 IP를 반환한다."""
    req = req or request
    for header in ("CF-Connecting-IP", "True-Client-IP", "X-Forwarded-For"):
        raw = req.headers.get(header, "")
        if raw:
            first = raw.split(",")[0].strip()
            if first:
                return first[:64]
    return (req.remote_addr or "unknown")[:64]


def classify_request(path):
    """요청 경로에 적용할 속도 제한 버킷 이름을 반환한다 (제외 대상이면 None)."""
    if path == "/healthz" or path.startswith("/static/"):
        return None
    if path in ("/forms/bundle.zip", "/office/download/mpl2-source.zip"):
        return "zip"
    if (
        path.startswith("/forms/")
        and (
            path.endswith((".hwpx", ".docx", ".xlsx"))
            or path.endswith("/gov.hwp")
        )
    ) or path in ("/office/download/setup", "/office/download/welfarego-links.oxt"):
        return "download"
    return "page"


def check_rate_limit(bucket, ip, now=None):
    """허용 여부를 검사하고 (allowed: bool, retry_after_sec: int)를 반환한다."""
    rules = BUCKET_RULES.get(bucket)
    if not rules:
        return True, 0

    now = time.monotonic() if now is None else now
    max_window = max(w for w, _ in rules)
    key = (bucket, ip)

    with _lock:
        dq = _history.get(key)
        if dq is not None:
            _history.move_to_end(key)
            cutoff = now - max_window
            while dq and dq[0] <= cutoff:
                dq.popleft()
        else:
            dq = deque()
            _history[key] = dq
            while len(_history) > MAX_TRACKED_KEYS:
                _history.popitem(last=False)

        for window_sec, limit in rules:
            win_cutoff = now - window_sec
            # 윈도우 내 요청 수 계산
            count = sum(1 for ts in dq if ts > win_cutoff)
            if count >= limit:
                oldest_in_win = next((ts for ts in dq if ts > win_cutoff), now)
                retry_after = max(1, int(math.ceil((oldest_in_win + window_sec) - now)))
                return False, retry_after

        dq.append(now)
        return True, 0


def reset_rate_limits():
    """테스트 격리를 위해 저장된 요청 기록을 초기화한다."""
    with _lock:
        _history.clear()


def enforce_request_rate_limit():
    """Flask before_request 훅: 한도 초과 시 429 응답을 반환한다."""
    if current_app.config.get("TESTING") and not current_app.config.get("RATELIMIT_IN_TESTS"):
        return None

    bucket = classify_request(request.path)
    if not bucket:
        return None

    ip = get_client_ip(request)
    allowed, retry_after = check_rate_limit(bucket, ip)
    if allowed:
        return None

    html = (
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>요청 한도 안내 | 웰페어고</title>"
        "<style>body{font-family:-apple-system,'Malgun Gothic',sans-serif;background:#f5f7fa;"
        "color:#1e293b;display:flex;align-items:center;justify-content:center;min-height:85vh;margin:0;padding:16px}"
        ".box{max-width:440px;background:#fff;border:1px solid #dbe2ea;border-radius:10px;padding:26px 24px;line-height:1.6}"
        "h1{font-size:1.1rem;margin:0 0 8px;color:#1d4ed8}p{font-size:0.9rem;margin:0 0 14px;color:#475569}"
        "a{display:inline-block;padding:8px 14px;background:#1d4ed8;color:#fff;text-decoration:none;"
        "border-radius:6px;font-size:0.85rem;font-weight:700}</style></head><body>"
        "<div class='box'><h1>잠시 후 다시 시도해 주세요</h1>"
        f"<p>안정적인 무료 서식 제공을 위해 짧은 시간 내 과도한 연속 요청이 일시 제한되었습니다. "
        f"약 <strong>{retry_after}초</strong> 후 다시 이용해 주세요.</p>"
        "<a href='/forms'>서식자료실로 돌아가기</a></div></body></html>"
    )
    return Response(
        html,
        status=429,
        mimetype="text/html; charset=utf-8",
        headers={
            "Retry-After": str(retry_after),
            "Cache-Control": "no-store",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )
