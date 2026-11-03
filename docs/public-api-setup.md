# 공공 API 신청·운영 안내

## 활용신청

공공데이터포털에 로그인한 뒤 아래 페이지에서 **활용신청 → 신청 내용 작성 → 제출**합니다.
승인 후 마이페이지 → 데이터활용 → OpenAPI → 활용신청 현황에서 해당 API를 열어
일반 인증키(Decoding)를 확인합니다. 인증키는 채팅·소스코드·스크린샷에 넣지 않습니다.

| 용도 | 신청할 API | Actions Secret (분야별 키가 다를 때) |
| --- | --- | --- |
| 복지시설 채용 | [사회복지시설정보서비스](https://www.data.go.kr/data/15001848/openapi.do) | `WELFARE_JOBS_KEY` |
| 장기요양기관 | [장기요양기관 검색](https://www.data.go.kr/data/15059029/openapi.do) | `LONGTERMCARE_KEY` |
| 공모사업 | [국고보조금 정보](https://www.data.go.kr/data/15097584/openapi.do)의 **공모사업** 기능 | `BOJO_KEY` |

[보조금 통합포털 API 안내](https://www.bojo.go.kr/ga/retrieveOpnApi.do)에서도 신청 안내로 이동할 수 있습니다.
국고보조금 **공모사업 상세**(15156853)는 다른 API입니다. 현재 수집기는 승인받은 **국고보조금 정보**(15097584)의 `T_OPD_PBNS`를 사용합니다.

## GitHub에 인증키 등록

[welfarego Actions Secrets 설정](https://github.com/BUSTUDY/welfarego/settings/secrets/actions)에서
**New repository secret**을 누릅니다. 같은 계정의 공통 인증키로 세 API를 모두 승인받았다면
`WELFARE_API_KEY` 하나로 등록할 수 있습니다. 기존 `GOV24_KEY` 또는 `KOSSI_KEY`도 공통 키의
대체값으로 재사용합니다. 각 API의 활용 승인은 각각 필요합니다.

코드의 선택 순서는 분야별 키 → `WELFARE_API_KEY` → `GOV24_KEY` → `KOSSI_KEY`입니다.
Actions에서는 공통 키가 없을 때 기존 키를 공통 키 환경변수로 전달합니다.
Encoding 키도 한 번만 디코딩해 전송하지만, 가능하면 Decoding 키를 사용합니다.

## 갱신과 장애 처리

- 기존 복지서비스 수집: 매일 **05:00 KST** (`update-welfare.yml`).
- 신규 세 분야 수집: 매일 **05:30 KST** (`update-portal.yml`).
- 수동 실행: Actions → **포털 공공데이터 갱신** → **Run workflow**.
- `data/portal_jobs.json`, `data/portal_care.json`, `data/portal_grants.json`을 각각 생성합니다.
- 전체 페이지를 수집·검증한 뒤 임시 파일을 원자적으로 교체합니다. 실패 시 기존 데이터를 유지합니다.
- 연결 오류·인증 실패·페이지 반복·수집 중 총 건수 변경을 감지합니다.
- 한 분야가 실패해도 나머지 분야는 계속 수집합니다. 로그에 키나 응답 본문을 남기지 않습니다.
- 방문할 때 외부 API를 호출하지 않습니다. 정기 수집된 파일을 캐시해 사용합니다.
- 기관 목록은 공단 최신 코드의 16개 시도를 조회합니다(전남광주통합특별시 포함). 기관기호와 유형코드를 합쳐 항목을 구분합니다.
- 채용·공모는 30일보다 오래전에 마감한 항목을 제외합니다.
- 공모는 해당 연도, 10~12월에는 다음 연도 공고도 조회하고 복지 관련 키워드로 분류합니다.

승인 직후에는 인증정보가 제공기관에 반영될 때까지 시간이 걸릴 수 있습니다.
실패한 작업의 요약 오류 코드로 승인 상태·공통 키 계정·호출 한도를 점검합니다.

## 제공 범위

- 채용: 공고명·시설명·업무·채용 분야·접수일·급여·문의처 등 원문 제공 필드.
- 기관: 기관기호·유형·시도/시군구 코드·지정일. 상세 주소·전화번호·입소 현황은 추정하지 않습니다.
- 기관 유형명은 공단 [공식 검색](https://www.longtermcare.or.kr/npbs/r/a/201/selectLtcoSrch.web?menuId=npe0000000650)의
  유형별 조회 결과와 대조한 코드에 한해 표시합니다. 미확인 코드는 그대로 둡니다.
- 공모는 신청 접수기간(`RCEPT_*`)을 사용합니다. 사업기간이나 공고기간으로 대체하지 않습니다.
- 지역 미제공 공모는 기관명에 명시된 시도로 공모기관 소재지를 분류합니다. 사업 대상 지역을 추정하지 않습니다.
- 관심 항목은 브라우저에 식별자만 저장합니다. 열람할 때 현재 스냅샷으로 마감 상태를 확인합니다.
- 복지 관련 공모 분류는 시설의 지원자격을 보장하지 않습니다. 최종 자격은 원문을 확인해야 합니다.

## 로컬 점검

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
python welfare_app.py
```

키를 로컬 환경변수로 설정했다면 `python scripts/update_portal.py jobs`로 한 분야를 확인할 수 있습니다.
키는 저장소 파일이나 명령 인수에 작성하지 않습니다.
