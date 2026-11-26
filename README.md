# welfarego

[welfarego.co.kr](https://welfarego.co.kr) — **2026 주·야간보호시설 실무 안내 포털** 저장소입니다.
국민건강보험공단 「2026년 재가급여(주야간보호) 평가 매뉴얼」과 보건복지부 최신 고시(제2025-247호·제2026-189호), 노인장기요양보험법 시행규칙 별지 서식을 기준으로 주·야간보호시설 운영에 필요한 평가·운영·서식·무료 오피스 기능을 하나의 포털로 제공합니다.
광고, 회원가입, 방문 추적 코드 및 외부 CDN은 포함하지 않습니다.

## 주요 서비스 및 경로

| 서비스 | 경로 | 제공 내용 |
| --- | --- | --- |
| 포털 메인 | `/` | 4대 핵심 실무 포털 안내, 실시간 4대 영역 모의 점수·서류 점검률, 주요 서식 바로받기 |
| 주·야간보호 평가매뉴얼 | `/evaluation` | 2026 공단 36개 평가지표(100점) 전체 해설, A등급 자가진단·연동 감점 자동잠금, 주기별 실무 일정 34건, 면담·시연 대비 18건, 표본 수 계산기 |
| 주·야간보호 운영매뉴얼 | `/operations` | 2026 최신 고시 수가표·본인부담금/월한도액 계산기, 법정 인력배치·48.6% 의무 인건비 진단기, 장기근속장려금, 입소~30일 SOP, 법정교육 10종, 현지조사 예방 8선 |
| 최신 서식자료실 | `/forms` | 법정 별지 4종 + 2026 평가 필수 표준서식 16종 (총 20종, 기관명·기관기호 자동 기입 후 `DOCX`·`XLSX`·일괄 `ZIP`·A4 인쇄 제공) |
| 무료 오피스 다운로드 | `/office` | 영세 사회복지시설용 무료 오피스(`Welfarego OFFICE`, MPL-2.0) 설치 안내, 웹 리본 UI 체험(`/office/preview`), 기관 비치용 정품 확인서 발급(`/office/license-certificate`), 소스·패치 ZIP |
| 포털·출처·개인정보 안내 | `/about` | 공식 법령·고시 출처 목록, 로컬 저장 안내, 저작권·면책 안내 |

- 기존 `/daycare`, `/daycare/evaluation`, `/daycare/operations`, `/daycare/forms` 경로는 각각 `/`, `/evaluation`, `/operations`, `/forms`로 `301` 영구 리다이렉트합니다.
- **Welfarego OFFICE** (LibreOffice 26.2 MPL-2.0 Subset) 브랜딩·패치·인스톨러·법무 문서 원본은 [`office/`](office/README.md) 디렉터리에 보존되어 있습니다.

## 로컬 실행

별도 DB나 외부 API 키 없이 실행됩니다.

```sh
pip install -r requirements.txt
gunicorn welfare_app:app
```

개발 환경에서는 `python welfare_app.py`로 실행합니다(기본 포트 `5001`, 환경변수 `PORT`로 변경 가능).

## Render 배포 설정

- Repository: `https://github.com/BUSTUDY/welfarego`
- Branch: `main`
- Root Directory: 비워 둠
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn welfare_app:app`
- Health Check Path: `/healthz`

선택 환경변수:
- `WELFARE_SITE_BASE`: 기본값 `https://welfarego.co.kr`
- `WELFAREGO_OFFICE_EXE_URL` / `WELFAREGO_OFFICE_MSI_URL`: 자체 빌드한 Welfarego OFFICE 설치 파일 직접 URL이 준비되면 설정합니다(미설정 시 LibreOffice 26.2 한국어 공식 다운로드 페이지로 안내).

## 광고 차단 및 검색 설정

- `/ads.txt`는 `410 Gone`으로 응답합니다.
- canonical, Open Graph 및 JSON-LD 구조화 데이터는 `SITE_BASE` 도메인을 사용합니다.
- `robots_welfare.txt`, `llms_welfare.txt`, `/sitemap.xml`을 독립 제공합니다.

## 검증

```sh
python -m unittest discover -s tests -v
```
