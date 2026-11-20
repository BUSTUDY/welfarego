# Welfarego OFFICE 상업적 오픈소스 라이선스 준수 가이드

> **주의:** 본 문서는 실무 엔지니어링 관점의 오픈소스 라이선스 체크리스트이며, 공식 법률 자문을 대체하지 않습니다. 대량 상용 판매·공공기관 납품 전에는 사내 법무팀 또는 오픈소스 전문 변호사의 최종 검토를 권장합니다.

---

## 1. 핵심 라이선스 구조 (왜 `--enable-mpl-subset`을 사용하는가?)

LibreOffice 원본 소스는 대부분 **MPL-2.0 (Mozilla Public License 2.0)** 이지만, 일부 선택 모듈(예: `breeze`/`elementary` 아이콘, `poppler` PDF 편집 임포트, `lpsolve`, `postgresql-sdbc`, `lotuswordpro`, `report-builder`)은 **GPL/LGPL** 전용 코드를 포함합니다.

Welfarego OFFICE 빌드 설정([`config/windows-x64.autogen.input`](../config/windows-x64.autogen.input))은 **`--enable-mpl-subset`** 을 기본 활성화하여 GPL/LGPL 전용 모듈을 컴파일 단계에서 완전히 제외합니다.

| 항목 | 적용 라이선스 | 상업적 이용/유료 판매 | 소스 공개 범위 |
| --- | --- | --- | --- |
| Welfarego OFFICE 코어 (LibreOffice 파생) | **MPL-2.0** | 허용 (사내 배포·유료 판매·유료 유지보수 모두 가능) | **파일 단위 카피레프트**: 기존 MPL-2.0 파일을 수정한 경우 해당 수정 파일(패치)의 소스를 공개해야 함 |
| Sukapura SVG 기본 아이콘 테마 | **MPL-2.0** | 허용 | 수정 시 수정 파일 공개 |
| Colibre 기본 아이콘 테마 | **CC0 1.0 (퍼블릭 도메인)** | 허용 | 제한 없음 |
| Welfarego 자체 로고·스플래시·아이콘·배너 | **Welfarego 독자 저작물** | 전권 보유 | 공개 의무 없음 (본 저장소에는 재현성 확보를 위해 포함) |
| 향후 별도 추가하는 독자 확장기능(`.oxt`) / 별도 실행 파일 | 독자 상용 라이선스 가능 | 허용 | 기존 MPL-2.0 파일을 수정하지 않은 **별도 파일**은 MPL-2.0 제3.3조(Larger Work)에 따라 비공개 상용 라이선스 결합 가능 |

---

## 2. 상업적 배포 시 반드시 지켜야 할 5대 의무 (MPL-2.0 & 상표법)

### (1) 상표권 분리 — The Document Foundation(TDF) 상표 정책 준수
TDF의 상표 정책에 따라, **자체 수정·재배포하는 오피스 제품에는 "LibreOffice" 이름과 공식 로고를 제품명으로 사용할 수 없습니다.** Welfarego OFFICE는 다음 항목을 전부 분리·교체했습니다.

- 제품명: `Welfarego OFFICE` (`--with-product-name="Welfarego OFFICE"`, `--with-vendor="Welfarego"`)
- Windows 설치 경로: `C:\Program Files\Welfarego OFFICE` (`WINDOWSBASISROOTNAME`)
- Windows MSI 고유 GUID (`UPGRADECODE`, `PRODUCTCODE`): 신규 UUID 발급으로 기존 공식 LibreOffice와 충돌·덮어쓰기 방지
- Windows 실행파일(`.exe`/`.dll`) 파일 속성: `include/default.rc`의 `ProductName`을 `Welfarego OFFICE`로 변경
- Windows 앱 및 기능(제어판) 표시 정보: `Property.ulf`, `Control.ulf`, 시작 메뉴 툴팁(`folderitem_ooo.ulf`)
- 시각 자산 전체 신규 제작: 스플래시 화면(`intro.png`, `intro-highres.png`), 시작 센터/정보 창 SVG(`logo*.svg`, `about.svg`), Windows 앱·문서 `.ico` 아이콘 31종 전체, MSI 설치 마법사 배너(`Banner.bmp`, `Image.bmp`, `Image_2.bmp`)
- 외부 통신 차단: TDF 온라인 업데이트(`UPDATEURL`), 크래시 리포트(`CrashReport=false`), 기부 배너(`ShowDonation=false`) 비활성화

> **주의:** About(정보) 대화상자와 `NOTICE`에서 **"Derived from LibreOffice" (LibreOffice 파생 제품임)** 라고 사실을 표기하는 것은 **명시적 출처 고지**로서 허용되며 권장됩니다. 단, TDF가 보증하거나 공식 제휴한 것처럼 오인시키는 표현은 금지됩니다.

### (2) 수정한 소스코드 공개 의무 (MPL-2.0 제3.2조)
바이너리(`.msi` 설치 파일)를 외부 고객·사용자에게 배포(무료/유료 불문)할 때는 다음을 함께 제공해야 합니다.
1. 수정한 모든 MPL-2.0 파일의 소스코드 (본 저장소의 `patches/*.patch` 및 기반 LibreOffice 태그 `libreoffice-26.2.7.3` 명시, 또는 CI가 자동 생성하는 `WelfaregoOFFICE-*-modified-source.zip` 아카이브)
2. 사용자가 소스코드를 어디서 받을 수 있는지 안내하는 고지문 (`legal/SOURCE-OFFER.md` — 설치 패키지 내부에도 자동 포함)

### (3) 저작권·라이선스 고지 보존 (MPL-2.0 제3.1조, Apache-2.0 제4조)
- 설치 패키지 및 배포물에 [`LICENSE`](../LICENSE)(MPL-2.0 전문), [`NOTICE`](../NOTICE), [`legal/THIRD-PARTY-LICENSES.md`](THIRD-PARTY-LICENSES.md)를 반드시 포함합니다.
- 기존 LibreOffice 소스 파일 상단의 저작권 헤더와 MPL-2.0 라이선스 헤더를 절대 삭제하지 않습니다.

### (4) 하위 라이선스 제한 금지 (MPL-2.0 제3.2조)
- Welfarego OFFICE의 MPL-2.0 영역에 대해서는 최종 사용자에게 추가 사용 제한(예: "역설계 금지", "재배포 금지")을 부과할 수 없습니다.
- 상용 EULA/서비스 약관을 작성할 때는 *"본 제품에 포함된 오픈소스 구성요소는 해당 오픈소스 라이선스(MPL-2.0 등)가 우선 적용됩니다"* 라는 조항을 명시하세요.

### (5) 폰트 저작권 주의사항 (한국어 환경)
- **Windows 기본 폰트(`맑은 고딕`, `바탕`, `굴림` 등)의 폰트 파일(`.ttf`)을 MSI 설치 파일에 절대 동봉하지 마세요.** 본 프로젝트의 `VCL.xcu` 패치는 OS에 이미 설치된 폰트를 참조(fallback)만 할 뿐, Microsoft 독점 폰트를 포함하지 않습니다.
- 추후 설치 파일에 한글 폰트를 함께 묶고 싶다면 **SIL OFL 1.1** 라이선스의 무료 상업용 폰트만 사용하세요:
  - **Pretendard** (SIL OFL 1.1)
  - **Noto Sans KR / Noto Serif KR** (SIL OFL 1.1)
  - **나눔고딕 / 나눔명조 / 나눔스퀘어** (SIL OFL 1.1)
  - 폰트 번들링 시 해당 폰트의 `OFL.txt` 전문을 함께 패키징해야 합니다.

---

## 3. 자동 컴플라이언스 검증

저장소 커밋 및 배포 전에 항상 아래 검증 스크립트를 실행합니다(GitHub Actions `verify.yml`에서도 자동 실행).

```bash
python3 scripts/verify_compliance.py
```

검증 항목:
1. `LICENSE`(MPL-2.0), `NOTICE`, `legal/*.md` 존재 및 필수 고지 문구 확인
2. 브랜딩 SVG/설정 파일에 TDF/LibreOffice 상표 오용 문자열 잔존 여부 검사
3. 31종 Windows `.ico` 아이콘, 스플래시, MSI 배너 규격 및 해상도 검증
4. `config/windows-x64.autogen.input`에 `--enable-mpl-subset`, `--enable-release-build`, `--disable-online-update` 및 GPL 아이콘 테마 제외 여부 확인
5. `patches/*.patch`의 구문 및 파일 헤더 무결성 확인
