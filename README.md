# welfarego

[welfarego.co.kr](https://welfarego.co.kr)의 독립 저장소입니다.
복지시설 일자리, 부모님 돌봄기관, 우리 동네 복지혜택, 시설 공공 지원사업과
기존 복지서비스 검색을 하나의 포털로 제공합니다. 지역/대상별 검색 주소도 유지합니다.
광고 및 방문 추적 코드는 포함하지 않습니다.

## 실행

| 서비스 | 경로 | 제공 내용 |
| --- | --- | --- |
| 홈페이지 | `/` | 다섯 가지 서비스, 채용·공모, 마감 일정, 복지혜택 |
| 기존 맞춤 복지검색 | `/welfare` | 나이·지역·소득에 따른 기존 검색 |
| 복지시설 일자리 | `/jobs` | 지역·채용 분야·접수 상태 검색 |
| 부모님 돌봄기관 | `/care` | 지역·기관 유형 검색, 최대 3개 기관 비교 |
| 우리 동네 복지혜택 | `/benefits` | 지역·관심 분야·지원대상별 탐색 |
| 시설 공공 지원사업 | `/grants` | 복지 관련 공공 공모와 신청 접수기간 |
| 관심 공고 | `/saved` | 브라우저에 저장한 항목과 현재 마감 상태 |

API 신청, 인증키 등록과 제공 범위는 [공공 API 운영 안내](docs/public-api-setup.md)에 정리했습니다.
신규 데이터는 매일 05:30 KST에 수집합니다. 방문 시 외부 API를 호출하지 않습니다.
수집에 실패하면 마지막 정상 데이터를 유지합니다. 별도 DB나 회원가입 없이 동작합니다.

```sh
pip install -r requirements.txt
gunicorn welfare_app:app
```

로컬에서는 `python welfare_app.py`로 실행합니다.

## Render 연결

기존 welfarego 서비스의 Repository를 이 저장소로 변경합니다.

- Repository: `https://github.com/BUSTUDY/welfarego`
- Branch: `main`
- Root Directory: 비워 둠
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn welfare_app:app`
- Health Check Path: `/healthz`

기존 커스텀 도메인은 그대로 사용합니다. 새 서비스나 DNS 변경은 필요 없습니다.
초기 snapshot 워크플로가 성공하여 데이터와 이미지가 저장된 뒤 연결을 바꿉니다.

## 복지 데이터 갱신

이 저장소의 **Settings → Secrets and variables → Actions**에 다음 값을 등록합니다.

| 이름 | 용도 |
| --- | --- |
| `GOV24_KEY` | 보조금24 수집에 필요한 필수 인증키 |
| `KOSSI_KEY` | 지자체복지서비스 수집을 사용할 경우 필요한 인증키 |

API 키는 파일이나 공개 로그에 넣지 않습니다.
기존 저장소의 Secrets 값은 GitHub가 다시 읽어 주지 않으므로 인증키 보관처에서 등록해야 합니다.
키를 등록하기 전에도 저장된 전체 데이터로 사이트 조회는 동작합니다.
정기 수집은 키 설정이 필요합니다. 매일 오전 5시(KST), 또는 Actions에서 수동 실행합니다.

초기 이관 시에는 `Initial welfare snapshot`이 기존 공개 복지 사이트의 데이터와 이미지를
한 번만 복사하고 SHA-256을 확인합니다. 파일이 이미 있으면 외부에서 다시 가져오지 않습니다.
이후 데이터는 이 저장소에서 정부 API로 직접 수집합니다.

`Check welfare app`은 광고/추적 부재, 정규 주소, 데이터 API 및 앱 동작을 검사합니다.
`복지 데이터 점검파일 만들기`와 `지자체복지서비스 API 진단`은 수동 진단용입니다.

## 광고 및 검색 설정

- `/ads.txt`는 410 Gone으로 응답합니다.
- canonical, OG 및 구조화 데이터는 welfarego 도메인을 사용합니다.
- `robots_welfare.txt`와 `llms_welfare.txt`를 독립 제공하고 `/sitemap.xml`을 생성합니다.

## 검증

```sh
python -m unittest discover -s tests -v
```
