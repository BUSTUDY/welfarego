# -*- coding: utf-8 -*-
"""
웰페어고 복지 서비스 조회 전용 Flask Blueprint.

canonical·OG·구조화 데이터는 전용 도메인을 사용한다.
데이터 수집 스크립트와 복지 데이터 파일은 기존 경로를 유지한다.
"""

import os
import re
import csv
import json
import gzip
import hashlib
import sys as _sys
from urllib.parse import quote

from flask import Blueprint, request, redirect, abort, current_app, json as _fjson

_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
if _scripts not in _sys.path:
    _sys.path.insert(0, _scripts)
import welfare_regions as _wr

welfare_bp = Blueprint("welfare", __name__)

WELFARE_GROUPS = {
    "청년복지":     ("청년",      "청년 복지서비스·지원금"),
    "노인복지":     ("노년",      "노인 복지서비스·어르신 지원"),
    "여성복지":     ("임신·출산", "여성 복지서비스·임신출산 지원"),
    "한부모복지":   ("한부모",    "한부모 가정 복지서비스"),
    "다자녀지원":   ("다자녀",    "다자녀 가정 복지서비스"),
    "저소득층지원": ("저소득",    "저소득층 복지서비스·생계 지원"),
}

_WELFARE_TITLE = "복지 서비스 찾기 | 내가 받을 수 있는 정부지원금 조회"
_WELFARE_DESC = ("나이·지역·소득만 입력하면 전국·시도·시군구 복지서비스를 한 번에 조회합니다. "
                 "청년복지, 노인복지, 여성복지, 부모급여·아동수당까지 로그인 없이 확인하세요.")

# --- Serve data JSON (for frontend) ---
# 복지 데이터는 실데이터 기준 수 MB라 그대로 내려보내면 모바일에서 매 방문마다
# 수 초씩 걸리고 데이터 요금도 나간다. gzip 으로 보내면 20배 이상 줄고,
# 하루 한 번만 갱신되므로 캐시를 걸어도 안전하다.
_welfare_blob = {"m": None, "raw": None, "gz": None, "etag": ""}


def _root():
    """이 블루프린트를 register_blueprint 한 Flask 앱의 루트 경로."""
    return os.path.dirname(os.path.abspath(__file__))


def _welfare_data_path():
    """실제 수집 데이터를 우선 쓰고, 없으면 동봉한 샘플로 폴백한다.

    패키지에 실데이터와 같은 이름의 샘플을 넣으면 배포할 때마다
    수집 결과를 덮어써 버린다. 그래서 파일명을 분리했다.
    """
    base = os.path.join(_root(), "data")
    real = os.path.join(base, "welfare_services.json")
    if os.path.exists(real):
        return real
    return os.path.join(base, "welfare_services.sample.json")


def _welfare_payload():
    path = _welfare_data_path()
    m = (os.path.getmtime(path), path)
    if _welfare_blob["m"] != m:
        raw = open(path, "rb").read()
        _welfare_blob.update(
            m=m, raw=raw,
            gz=gzip.compress(raw, 6),
            etag='W/"%s-%d"' % (hashlib.md5(raw).hexdigest()[:16], len(raw)),
            shards={},          # 아래 _welfare_shard 가 채운다
        )
    return _welfare_blob


# ── 지역별 조각(shard) ──────────────────────────────────────────────
# 복지서비스 전체는 14.5MB(gzip 2.4MB)다. 페이지가 열릴 때마다 이걸 통째로
# 받아서 브라우저에서 걸러 왔는데, /welfare 방문 한 번이 /btc 35번과 맞먹어
# Render 대역폭이 이것 때문에 터졌다.
#
# 그런데 welfare.html 은 지역을 고르면 어차피 '전국 + 그 지역'만 쓴다.
# 그래서 처음부터 그만큼만 보낸다. 필드를 빼는 방식도 검토했지만
# target·content 가 검색 색인과 거주요건 파싱에 쓰여서 건드리지 않았다.
#
# 조각은 파일이 아니라 메모리에서 만든다. 원본 JSON이 갱신되면
# _welfare_payload 가 shards 를 비우므로 자동으로 다시 만들어진다.
_WELFARE_REST = "__rest__"


def _welfare_shard(sido):
    """조각을 만든다.

      sido=None       전국 사업만 (어느 화면에서든 먼저 받는다)
      sido='서울특별시' 그 시도 사업만
      sido=_WELFARE_REST 전국분을 뺀 나머지 전부 (전국 검색용)

    전국분은 시도 조각에 넣지 않는다. 넣으면 지역 페이지가 두 번 받는다.
    나머지를 시도별로 쪼개 받으면 압축 효율이 떨어져 오히려 커지므로
    (16조각 합계 2,870KB > 통짜 2,000KB) 전국 검색용은 한 덩어리로 준다.
    """
    blob = _welfare_payload()
    key = sido or ""
    cached = blob["shards"].get(key)
    if cached:
        return cached

    doc = json.loads(blob["raw"].decode("utf-8"))
    items = doc.get("items", [])
    if sido == _WELFARE_REST:
        picked = [x for x in items if x.get("sido")]
    elif isinstance(sido, tuple) and sido[0] == "tag":
        # 대상별 페이지(청년복지·노인복지 등)용. 전국분은 이미 받았으므로
        # 지역이 있는 항목 중 그 태그가 붙은 것만 준다.
        t = sido[1]
        picked = [x for x in items
                  if x.get("sido") and t in (x.get("tags") or [])]
    elif sido:
        picked = [x for x in items if x.get("sido") == sido]
    else:
        picked = [x for x in items if not x.get("sido")]

    body = json.dumps(
        {"updated": doc.get("updated"), "count": len(picked),
         "shard": sido or "national", "items": picked},
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")

    out = {
        "raw": body,
        "gz": gzip.compress(body, 6),
        "etag": 'W/"%s-%d"' % (hashlib.md5(body).hexdigest()[:16], len(body)),
    }
    blob["shards"][key] = out
    return out


def _welfare_sido_list():
    blob = _welfare_payload()
    cached = blob["shards"].get("__list__")
    if cached:
        return cached
    doc = json.loads(blob["raw"].decode("utf-8"))
    names = sorted({x.get("sido") for x in doc.get("items", []) if x.get("sido")})
    blob["shards"]["__list__"] = names
    return names


def _welfare_tag_list():
    """대상별 페이지에서 쓰는 태그만 허용한다(아무 문자열로 조각을 만들지 않도록)."""
    return {t for t, _ in WELFARE_GROUPS.values()}


def _welfare_json_response(blob):
    """조각/전체 공통 응답. gzip · ETag · 캐시 헤더를 붙인다."""
    from flask import current_app as _app
    if request.headers.get("If-None-Match") == blob["etag"]:
        return "", 304
    accepts_gzip = "gzip" in request.headers.get("Accept-Encoding", "")
    body = blob["gz"] if accepts_gzip else blob["raw"]
    resp = _app.response_class(body, mimetype="application/json")
    if accepts_gzip:
        resp.headers["Content-Encoding"] = "gzip"
    resp.headers["Vary"] = "Accept-Encoding"
    resp.headers["ETag"] = blob["etag"]
    # 하루 1회 갱신 -> 1시간 캐시 후 ETag 로 재확인
    resp.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"
    return resp


@welfare_bp.route("/data/welfare_services.json")
def serve_welfare_data():
    """전체 데이터. 지역 없이 전국을 훑는 검색에만 필요하다."""
    try:
        return _welfare_json_response(_welfare_payload())
    except OSError:
        abort(404)


@welfare_bp.route("/data/welfare/national.json")
def serve_welfare_national():
    """전국 사업만. 어느 지역 페이지든 이건 항상 필요하다."""
    try:
        return _welfare_json_response(_welfare_shard(None))
    except OSError:
        abort(404)


@welfare_bp.route("/data/welfare/rest.json")
def serve_welfare_rest():
    """전국분을 뺀 나머지 전부. 지역 없이 전국을 훑는 검색에 쓴다."""
    try:
        return _welfare_json_response(_welfare_shard(_WELFARE_REST))
    except OSError:
        abort(404)


@welfare_bp.route("/data/welfare/tag/<tag>.json")
def serve_welfare_tag(tag):
    """대상별 페이지용. 그 태그가 붙은 지역 사업만 (전국분은 national.json).

    /청년복지 같은 페이지는 지역이 없어서 예전에는 전국을 다 받아야
    했다(rest 1,933KB). 태그로 걸러 주면 214~520KB 로 줄어든다.
    """
    try:
        if tag not in _welfare_tag_list():
            abort(404)
        return _welfare_json_response(_welfare_shard(("tag", tag)))
    except OSError:
        abort(404)


@welfare_bp.route("/data/welfare/sido/<sido>.json")
def serve_welfare_sido(sido):
    """시도 하나만. 지역을 고른 화면이 받는다."""
    try:
        if sido not in _welfare_sido_list():
            abort(404)
        return _welfare_json_response(_welfare_shard(sido))
    except OSError:
        abort(404)


def _welfare_links_html(cur_sido=None):
    """지역 링크를 HTML로 직접 만든다.

    네이버 검색로봇은 자바스크립트를 거의 실행하지 않는다. 링크를 JS로만
    만들면 246개 지역 페이지를 네이버가 발견하지 못한다. 그래서 서버가
    HTML로 찍어서 내보낸다.
    """
    sido = " ".join(
        f'<a href="/{quote(s)}">{s} 복지</a>' for s in _wr.SIDO)
    nearby = ""
    if cur_sido and _wr.SIDO.get(cur_sido):
        nearby = " ".join(
            f'<a href="/{quote(cur_sido + "-" + g)}">{g}</a>'
            for g in _wr.SIDO[cur_sido])
    return sido, nearby


def _welfare_html(title=None, desc=None, canonical=None, preset=None,
                  h1=None, eyebrow=None, intro=None, crumbs=None, cur_sido=None):
    """순수 HTML 템플릿을 읽어 SEO 요소만 바꿔서 돌려준다.

    제목뿐 아니라 h1·본문·지역 링크까지 서버에서 넣는다.
    구글은 JS를 렌더링하지만 네이버는 아니라서, JS로만 채우면
    246개 지역 페이지가 전부 같은 내용으로 보여 색인되지 않는다.
    """
    base = current_app.config.get("SITE_BASE", "https://welfarego.co.kr")

    path = os.path.join(current_app.root_path, "templates", "welfare.html")
    with open(path, encoding="utf-8") as fp:
        html = fp.read()

    if title:
        html = html.replace(f"<title>{_WELFARE_TITLE}</title>", f"<title>{title}</title>")
        html = html.replace(f'<meta property="og:title" content="{_WELFARE_TITLE}">',
                            f'<meta property="og:title" content="{title}">')
    if desc:
        html = html.replace(f'<meta name="description" content="{_WELFARE_DESC}">',
                            f'<meta name="description" content="{desc}">')
        html = html.replace('<meta property="og:description" content="나이·지역·소득만 입력하면 '
                            '전국·시도·시군구 복지서비스를 한 번에 조회합니다. 로그인도 공동인증서도 필요 없습니다.">',
                            f'<meta property="og:description" content="{desc}">')
    # 전용 도메인의 페이지별 정규 주소를 설정한다.
    canonical = canonical or f"{base}/"
    html = html.replace('<link rel="canonical" href="https://welfarego.co.kr/" />',
                        f'<link rel="canonical" href="{canonical}" />')
    html = html.replace('<meta property="og:url" content="https://welfarego.co.kr/">',
                        f'<meta property="og:url" content="{canonical}">')
    # WebApplication JSON-LD의 url 은 페이지별 canonical 이 아니라 앱 자체의
    # 대표 주소라, 어느 페이지든 사이트 루트를 가리켜야 한다.
    html = html.replace('"url":"https://welfarego.co.kr/"', f'"url":"{base}/"')

    # --- 본문(h1/eyebrow/intro)을 HTML에 직접 심는다 ---
    #
    # 예전에는 문구 전체를 정확히 일치시켜 바꿨는데, 템플릿 문구를 조금만
    # 손봐도 치환이 조용히 실패해서 지역 페이지가 기본 문구로 나갔다.
    # (실제로 아이콘 하나 때문에 eyebrow·intro 치환이 동시에 깨졌다)
    # 그래서 id 를 기준으로 안쪽 내용만 바꾼다. 앞에 붙은 아이콘은 보존한다.
    if h1 or eyebrow or intro:
        html = html.replace('<html lang="ko">', '<html lang="ko" data-ssr="1">')

    def _set_inner(doc, tag, el_id, new_inner, keep_icon=True):
        m = re.search(r'(<%s[^>]*id="%s"[^>]*>)(.*?)(</%s>)' % (tag, el_id, tag),
                      doc, re.S)
        if not m:
            return doc
        prefix = ""
        if keep_icon:
            ic = re.match(r'\s*<i[^>]*>\s*</i>\s*', m.group(2))
            if ic:
                prefix = ic.group(0)
        return doc[:m.start(2)] + prefix + new_inner + doc[m.end(2):]

    if eyebrow:
        html = _set_inner(html, "span", "eyebrow", eyebrow)
    if h1:
        html = _set_inner(html, "h1", "h1", h1, keep_icon=False)
    if intro:
        html = _set_inner(html, "p", "intro", intro, keep_icon=False)

    # --- 지역 링크를 HTML로 (네이버 크롤링 대응) ---
    sido_html, nearby_html = _welfare_links_html(cur_sido)
    html = html.replace('<div class="links" id="sidoLinks"></div>',
                        f'<div class="links" id="sidoLinks">{sido_html}</div>')
    if nearby_html:
        html = html.replace('<section class="sec" id="nearbySec" hidden>',
                            '<section class="sec" id="nearbySec">')
        html = html.replace('<span id="nearbyTitle"></span>',
                            f'<span id="nearbyTitle">{cur_sido} 시·군·구별 복지</span>')
        html = html.replace('<div class="links" id="nearbyLinks"></div>',
                            f'<div class="links" id="nearbyLinks">{nearby_html}</div>')

    # --- 빵부스러기 구조화 데이터 ---
    if crumbs:
        items = ",".join(
            json.dumps({"@type": "ListItem", "position": i + 1, "name": n,
                        "item": base + u}, ensure_ascii=False)
            for i, (n, u) in enumerate(crumbs))
        html = html.replace(
            '{"@type":"BreadcrumbList","itemListElement":[\n'
            '{"@type":"ListItem","position":1,"name":"복지 서비스 찾기","item":"https://welfarego.co.kr/"}]}',
            '{"@type":"BreadcrumbList","itemListElement":[' + items + ']}')

    if preset is not None:
        html = html.replace("window.__PRESET__ = null;",
                            "window.__PRESET__ = " + json.dumps(preset, ensure_ascii=False) + ";")
    return html


@welfare_bp.route("/")
def welfare_home():
    return _welfare_html(crumbs=[("복지 서비스 찾기", "/")])


@welfare_bp.route("/s/<svc_id>")
def welfare_service(svc_id):
    """공유 링크. 특정 복지서비스 하나를 펼쳐서 보여준다.

    검색 결과에서 공유 버튼을 누르면 이 주소가 만들어진다.
    받은 사람이 열면 그 사업만 바로 나온다.
    """
    base = current_app.config.get("SITE_BASE", "https://welfarego.co.kr")
    svc = None
    try:
        with open(_welfare_data_path(), encoding="utf-8") as fp:
            for it in json.load(fp).get("items", []):
                if str(it.get("id")) == svc_id:
                    svc = it
                    break
    except (OSError, json.JSONDecodeError):
        pass

    if not svc:
        # 데이터가 갱신되며 사라진 서비스일 수 있다. 검색기 첫 화면으로 보낸다.
        return redirect("/", code=302)

    name = svc.get("name", "복지 서비스")
    org = svc.get("org", "")
    desc = (svc.get("summary") or svc.get("target") or "")[:150]
    return _welfare_html(
        title=f"{name} | 신청자격·지원내용 | 복지 서비스 찾기",
        desc=f"{name}({org}) 지원대상과 신청방법을 확인하세요. {desc}",
        canonical=f"{base}/s/{svc_id}",
        eyebrow="복지 서비스 상세",
        h1=f'{name}',
        intro=(f"{org} 사업입니다. 아래에서 지원대상과 신청방법을 확인하고, "
               f"내 조건에 맞는 다른 혜택도 함께 찾아보세요."),
        crumbs=[("복지 서비스 찾기", "/"), (name, f"/s/{svc_id}")],
        preset={"region": None, "tag": None, "service": svc_id},
    )


@welfare_bp.route("/<path:slug>")
def welfare_region(slug):
    base = current_app.config.get("SITE_BASE", "https://welfarego.co.kr")

    # 대상별 페이지 (/청년복지)
    if slug in WELFARE_GROUPS:
        tag, headline = WELFARE_GROUPS[slug]
        return _welfare_html(
            title=f"{slug} 조회 | {headline} 한눈에 확인",
            desc=f"{headline}를 전국·시도·시군구 단계별로 모아 조회합니다. "
                 f"나이·지역·소득만 입력하면 신청 가능한 항목만 걸러서 보여드립니다.",
            canonical=f"{base}/{slug}",
            eyebrow=slug,
            h1=f'{headline} <span class="hl">조회</span>',
            intro=f"{headline}를 전국·시도·시군구 세 단계로 모아 확인할 수 있습니다. "
                  f"거주지와 나이, 소득을 입력하면 실제로 신청 가능한 항목만 남습니다.",
            crumbs=[("복지 서비스 찾기", "/"), (slug, f"/{slug}")],
            preset={"region": None, "tag": tag},
        )

    # 지역별 페이지 (/경기도-남양주시)
    parts = slug.split("-", 1)
    sido = _wr.normalize_sido(parts[0])
    sigungu = parts[1] if len(parts) > 1 else ""
    if not sido or (sigungu and sigungu not in _wr.SIDO.get(sido, [])):
        abort(404)

    label = f"{sido} {sigungu}".strip()
    name = sigungu or sido
    crumbs = [("복지 서비스 찾기", "/"), (sido, f"/{sido}")]
    if sigungu:
        crumbs.append((label, f"/{slug}"))

    return _welfare_html(
        title=f"{name} 복지 혜택 조회 | {name} 정부지원금 총정리",
        desc=f"{label} 주민이 신청할 수 있는 복지서비스를 전국·{sido}"
             f"{'·' + sigungu if sigungu else ''} 단계로 정리했습니다. "
             f"{name} 청년복지, 노인복지, 출산지원금을 로그인 없이 조회하세요.",
        canonical=f"{base}/{slug}",
        eyebrow=f"{name} 복지",
        h1=f'{name} <span class="hl">복지 서비스 찾기</span>',
        intro=(f"수천개의 복지 서비스 중 "
               f"{label} 주민이 신청할 수 있는 복지서비스와 정부지원금을 전국·{sido}"
               f"{'·' + sigungu if sigungu else ''} 세 단계로 정리했습니다. "
               f"나이와 소득만 추가로 입력하면 {name}에서 실제로 신청 가능한 혜택만 남습니다."),
        crumbs=crumbs,
        cur_sido=sido,
        preset={"region": {"sido": sido, "sigungu": sigungu, "label": label}, "tag": None},
    )


def welfare_sitemap_urls(site_base):
    """sitemap.xml 에 넣을 (경로, 우선순위, 변경주기) 목록.

    메인 + 대상별 + 지역별(시도 16 + 시군구 229) 전부 포함한다.
    이 목록이 빠지면 지역 롱테일 페이지가 검색엔진에 아예 제출되지 않는다.
    """
    urls = [("/", "1.0", "weekly")]
    for grp in WELFARE_GROUPS:
        urls.append((f"/{quote(grp)}", "0.7", "weekly"))
    for sd, guns in _wr.SIDO.items():
        urls.append((f"/{quote(sd)}", "0.7", "weekly"))
        for g in guns:
            urls.append((f"/{quote(sd + '-' + g)}", "0.6", "weekly"))
    return urls
