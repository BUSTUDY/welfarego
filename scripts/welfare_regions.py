# -*- coding: utf-8 -*-
"""
행정 계층(전국 / 광역 / 기초) 판별 모듈.

핵심 아이디어
-------------
복지서비스는 실제로 3개 층에서 따로 만들어진다.
  - 중앙부처·공공기관  -> 전국 누구나
  - 광역지자체(시/도)  -> 그 시도민 전체
  - 기초지자체(시군구) -> 그 시군구민만

그래서 사용자에게는 시군구까지 입력받되,
결과는 세 층을 "누적"해서 보여줘야 누락이 없다.
(경기도 남양주시 = 전국 + 경기도 + 남양주시)
"""

import re

SIDO = {
    "서울특별시": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
                "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
                "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
                "서초구", "강남구", "송파구", "강동구"],
    "부산광역시": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구",
                "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"],
    "대구광역시": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"],
    # 2026-07-01 인천 행정체제 개편. 중구·동구 폐지, 서구는 서해구로 개칭하며
    # 북부를 검단구로 분리, 제물포구·영종구 신설. 2군8구 -> 2군9구.
    "인천광역시": ["미추홀구", "연수구", "남동구", "부평구", "계양구", "서해구",
                "검단구", "제물포구", "영종구", "강화군", "옹진군"],
    "대전광역시": ["동구", "중구", "서구", "유성구", "대덕구"],
    "울산광역시": ["중구", "남구", "동구", "북구", "울주군"],
    "세종특별자치시": [],  # 단층제 - 기초지자체 없음
    "경기도": ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시",
             "동두천시", "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시",
             "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시", "이천시",
             "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시",
             "연천군", "가평군", "양평군"],
    "강원특별자치도": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시",
                  "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군",
                  "양구군", "인제군", "고성군", "양양군"],
    "충청북도": ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군",
              "진천군", "괴산군", "음성군", "단양군"],
    "충청남도": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시",
              "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"],
    "전북특별자치도": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군",
                  "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"],
    # 2026-07-01 전라남도 + 광주광역시 통합 출범. 기초지자체는 그대로 유지된다.
    # 광주 5개 구(동/서/남/북/광산)와 전남 22개 시군이 한 광역 아래 놓인다.
    "전남광주통합특별시": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군",
                   "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군",
                   "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군",
                   "신안군", "동구", "서구", "남구", "북구", "광산구"],
    "경상북도": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시",
              "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군",
              "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"],
    "경상남도": ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시",
              "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군",
              "산청군", "함양군", "거창군", "합천군"],
    "제주특별자치도": ["제주시", "서귀포시"],
}

# API 소관기관명이 옛 명칭으로 들어오는 경우가 있어 함께 인식시킨다.
SIDO_ALIASES = {
    # 2026-07-01 통합 — 옛 명칭으로 들어오는 데이터도 통합시로 매핑한다
    "전라남도": "전남광주통합특별시", "전남": "전남광주통합특별시",
    "광주광역시": "전남광주통합특별시",
    # '광주시'는 경기도 광주시와 겹치므로 별칭에 넣지 않는다
    "전남광주특별시": "전남광주통합특별시", "광주전남특별시": "전남광주통합특별시",
    "서울시": "서울특별시", "서울": "서울특별시",
    "부산시": "부산광역시", "부산": "부산광역시",
    "대구시": "대구광역시", "대구": "대구광역시",
    "인천시": "인천광역시", "인천": "인천광역시",
    "대전시": "대전광역시", "대전": "대전광역시",
    "울산시": "울산광역시", "울산": "울산광역시",
    "세종시": "세종특별자치시", "세종": "세종특별자치시",
    "경기": "경기도",
    "강원도": "강원특별자치도", "강원": "강원특별자치도",
    "충북": "충청북도", "충남": "충청남도",
    "전라북도": "전북특별자치도", "전북": "전북특별자치도",
    "경북": "경상북도", "경남": "경상남도",
    "제주도": "제주특별자치도", "제주": "제주특별자치도",
}

# 옛 인천 구명이 정부 데이터에 당분간 그대로 들어올 수 있어 대응표를 둔다.
# '동구'는 전부 제물포구로 흡수돼 명확하지만, '중구'는 제물포구·영종구로
# 갈라져 어느 쪽인지 구 단위로 특정할 수 없다 — 잘못 짚느니 인천광역시
# 단위(REGIONAL)로만 인식되게 두는 편이 안전해서 별칭에 넣지 않는다.
_INCHEON_GU_ALIASES = {"동구": "제물포구", "서구": "서해구"}

NATIONAL = "national"
REGIONAL = "regional"
LOCAL = "local"

# 중앙부처·공공기관으로 간주할 접미사/키워드
_NATIONAL_HINTS = (
    "부", "청", "처", "위원회", "공단", "공사", "재단", "진흥원", "관리원",
    "연구원", "협회", "은행", "교육청", "본부", "센터",
)


def region_options():
    """프론트엔드 자동완성용 평면 리스트."""
    out = []
    for sido, guns in SIDO.items():
        if not guns:
            out.append({"sido": sido, "sigungu": "", "label": sido})
            continue
        for g in guns:
            out.append({"sido": sido, "sigungu": g, "label": f"{sido} {g}"})
    return out


def normalize_sido(name: str) -> str:
    if not name:
        return ""
    name = name.strip()
    if name in SIDO:
        return name
    return SIDO_ALIASES.get(name, "")


def classify_org(org_name: str, *hints):
    """
    소관기관명으로 (계층, 시도, 시군구)를 판별한다.

    hints 는 부서명·접수기관명 등 보조 필드. 시군구 이름이 여러 시도에
    존재할 때(중구·동구·서구·남구·북구·강서구·고성군) 시도를 특정하는 데 쓴다.
    이 보정이 없으면 해당 29개 지자체 서비스가 영구히 표시되지 않는다.

    예)  '보건복지부'                    -> (national, '', '')
         '경기도'                        -> (regional, '경기도', '')
         '경기도 남양주시'                -> (local, '경기도', '남양주시')
         '중구' + hint '부산광역시청'      -> (local, '부산광역시', '중구')
    """
    if not org_name:
        return NATIONAL, "", ""

    org = org_name.strip()

    # 1) '경기도 남양주시' 처럼 시도가 앞에 붙은 형태 (별칭 표기 포함)
    prefixes = [(k, k) for k in SIDO] + [(a, c) for a, c in SIDO_ALIASES.items()]
    prefixes.sort(key=lambda x: -len(x[0]))       # 긴 이름 우선
    for raw, canon in prefixes:
        if not org.startswith(raw):
            continue
        rest = org[len(raw):].strip()
        if not rest:
            return REGIONAL, canon, ""
        # 인천의 옛 구 이름이 그대로 들어오면 새 이름으로 바꿔서 찾는다.
        # (SIDO 목록엔 새 이름만 있어서 이 변환 없이는 매칭에 실패해
        #  '인천 동구 보건소'가 인천광역시(REGIONAL)로만 잡히고
        #  제물포구(LOCAL)까지는 못 짚는다)
        if canon == "인천광역시":
            for old_g, new_g in _INCHEON_GU_ALIASES.items():
                if rest.startswith(old_g):
                    rest = new_g + rest[len(old_g):]
                    break
        for g in SIDO.get(canon, []):
            if rest.startswith(g):
                return LOCAL, canon, g
        return REGIONAL, canon, ""       # 시도 산하 부서명 등

    # 2) 시군구명 단독
    matches = [(sido, g) for sido, guns in SIDO.items() for g in guns if org.startswith(g)]
    if matches:
        best = max(len(g) for _, g in matches)
        matches = [m for m in matches if len(m[1]) == best]
        if len(matches) == 1:
            return LOCAL, matches[0][0], matches[0][1]

        blob = " ".join(h for h in hints if h)
        if blob:
            for sido, g in matches:
                if sido in blob:
                    return LOCAL, sido, g
                short = sido.replace("통합특별시", "").replace("특별자치시", "") \
                            .replace("특별자치도", "").replace("광역시", "") \
                            .replace("특별시", "").replace("도", "")
                if short and short in blob:
                    return LOCAL, sido, g
        return LOCAL, "", matches[0][1]

    # 3) 아직 모르는 지자체 이름일 수 있다.
    #
    #    행정구역은 계속 바뀐다(2026-07 전남광주통합특별시 출범). 모르는 이름을
    #    무조건 '전국'으로 돌리면 그 지역 사업이 전국 사용자에게 노출된다.
    #    실제로 이 때문에 남양주 사용자에게 곡성군 사업이 떴다.
    #    그래서 지자체처럼 보이면 이름을 그대로 달아 '지역 사업'으로 표시한다.
    #    사용자 지역과 문자열이 다르면 matches_region 에서 걸러진다.
    if _looks_like_local_gov(org):
        parts = org.split()
        head = parts[0]
        if len(parts) >= 2 and parts[1][-1:] in ("시", "군", "구"):
            return LOCAL, head, parts[1]
        if head[-1:] in ("시", "군", "구") and len(parts) == 1 and not _is_wide_area(head):
            return LOCAL, "", head      # 시도 불명 -> 노출하지 않음
        return REGIONAL, head, ""

    # 4) '재단법인OO구OO재단' 처럼 지자체 이름이 중간에 박힌 산하기관.
    #    앞에서 걸리지 않아 전국 사업으로 새고 있었다(실데이터 52건).
    #    이름 안에 시군구가 들어 있으면 그 지역 사업으로 본다.
    inner = _find_inner_region(org)
    if inner:
        return inner

    # 5) 중앙부처·공공기관
    return NATIONAL, "", ""


def _find_inner_region(org: str):
    """기관명 안에 있는 지역 이름을 찾는다.

    '재단법인영등포구미래교육재단'  -> 서울특별시 영등포구
    '부천도시공사'                -> 경기도 부천시   (접미사 없이 어간만 있음)
    '강동문화재단'                -> 서울특별시 강동구

    지자체 산하기관은 그 지역 주민만 쓸 수 있는데, 이름에 '시/구'가
    안 붙어 있으면 못 알아보고 전국 사업으로 새어나갔다.
    """
    if not any(w in org for w in _AGENCY_WORDS):
        return None
    # '한국·대한·국민·전국·중앙' 으로 시작하면 전국 기관이다.
    # (예: 국가평생교육진흥원 안에 '가평' 이 들어 있어 오인할 수 있다)
    if org.startswith(_NATIONWIDE_PREFIX):
        return None

    cands = []
    # 1) 시군구 전체 이름 (긴 이름 우선)
    for sido, guns in SIDO.items():
        for g in guns:
            if len(g) >= 3 and g in org:
                cands.append((len(g), LOCAL, sido, g))
    # 2) 접미사를 뗀 어간 ('부천도시공사' 의 '부천')
    if not cands:
        for stem, owners in _GUN_STEMS.items():
            if stem not in org:
                continue
            if len(owners) > 1:          # 강서구(서울/부산)처럼 겹치면 판단 보류
                continue
            sido, g = owners[0]
            cands.append((len(stem), LOCAL, sido, g))
    # 3) 시도 어간 ('전북문화재단' 의 '전북')
    if not cands:
        for stem, sido in _SIDO_STEMS.items():
            if stem in org:
                cands.append((len(stem), REGIONAL, sido, ""))

    if not cands:
        return None
    cands.sort(reverse=True)
    best = cands[0]
    # 같은 길이의 후보가 서로 다른 지역을 가리키면 확정하지 않는다
    top = [c for c in cands if c[0] == best[0]]
    if len({(c[2], c[3]) for c in top}) > 1:
        return None
    return best[1], best[2], best[3]


_AGENCY_WORDS = ("공사", "공단", "재단", "센터", "진흥원", "문화원",
                 "장학회", "복지관", "평생교육", "체육회", "관광공사")
_NATIONWIDE_PREFIX = ("한국", "대한", "국민", "전국", "중앙", "국가", "국제")


def _build_stems():
    """시군구·시도 이름에서 접미사를 뗀 어간 표를 만든다."""
    guns, sidos = {}, {}
    for sido, gs in SIDO.items():
        for g in gs:
            st = re.sub(r"[시군구]$", "", g)
            if len(st) >= 2:
                guns.setdefault(st, []).append((sido, g))
        st = re.sub(r"(특별자치시|특별자치도|통합특별시|광역시|특별시|도)$", "", sido)
        if len(st) >= 2:
            sidos[st] = sido
    return guns, sidos


_GUN_STEMS, _SIDO_STEMS = _build_stems()

# 기관 이름에 흔히 쓰이는 줄임말. '재단법인충남경제진흥원' 처럼
# '충청남' 이 아니라 '충남' 으로 적히면 위 표로는 못 잡는다.
_SIDO_STEMS.update({
    "충남": "충청남도", "충북": "충청북도",
    "경남": "경상남도", "경북": "경상북도",
    "전남": "전남광주통합특별시", "광주": "전남광주통합특별시",
})


# 중앙행정기관·공공기관에서 흔한 꼬리말. 지자체 판별에서 제외하는 데 쓴다.
_CENTRAL_TAIL = ("부", "청", "처", "원", "회", "단", "사", "관", "소", "국", "실", "교")


def _is_wide_area(token: str) -> bool:
    return token.endswith(("특별시", "광역시", "특별자치시", "특별자치도", "통합특별시")) \
        or (token.endswith("도") and len(token) >= 3)


def _looks_like_local_gov(org: str) -> bool:
    """이름만 보고 지방자치단체로 보이는지 판단한다."""
    head = org.split()[0] if org.split() else ""
    if not head:
        return False
    if _is_wide_area(head):
        return True
    # '○○시 ○○과' 처럼 시군구가 앞에 오는 경우
    if head[-1:] in ("시", "군", "구") and head[-1:] not in _CENTRAL_TAIL:
        return True
    return False


def tier_of(service: dict):
    """정규화된 서비스 dict에 계층 정보를 붙인다. 보조 필드로 동명 시군구를 해소한다."""
    tier, sido, sigungu = classify_org(
        service.get("org", ""),
        service.get("dept", ""), service.get("reception", ""), service.get("tel", ""),
    )
    service["tier"] = tier
    service["sido"] = sido
    service["sigungu"] = sigungu
    return service


def matches_region(service: dict, user_sido: str, user_sigungu: str) -> bool:
    """사용자 지역 기준으로 이 서비스를 보여줄지 결정."""
    tier = service.get("tier")
    if tier == NATIONAL:
        return True
    if tier == REGIONAL:
        return service.get("sido") == user_sido
    if tier == LOCAL:
        if not service.get("sido"):
            return False  # 시도 특정 실패 항목은 노출하지 않음
        return service.get("sido") == user_sido and service.get("sigungu") == user_sigungu
    return False
