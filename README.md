# Welfarego OFFICE

**Welfarego OFFICE**는 오픈소스 **LibreOffice 26.2.7.3 (MPL-2.0 Subset)** 을 기반으로 자체 브랜드 디자인과 **요즘 스타일의 모던 플루언트(Fluent) 리본 메뉴 UI** 를 적용한 **Windows x64 설치형 오피스(.msi)** 제작 저장소입니다.

상업적 이용(사내 배포, 고객사 납품, 유료 판매·유지보수 포함) 시 저작권 및 상표권 분쟁이 발생하지 않도록 **MPL-2.0 전용 서브셋 빌드(`--enable-mpl-subset`)** 와 **The Document Foundation(TDF) 상표·시각 자산 100% 분리** 규정을 설계 단계부터 반영했습니다.

---

## 주요 특징

### 1. 모던 플루언트(Fluent) 리본 메뉴 UI (`patches/0002`, `patches/0003`)
- **기본 리본 UI 자동 활성화**: Writer(문서), Calc(스프레드시트), Impress(프레젠테이션), Draw(드로잉) 첫 실행 시 구형 2줄 툴바 대신 **탭형 리본 메뉴(`Tabbed`)** 로 즉시 실행됩니다.
- **C++ VCL 리본 렌더링 개선 (`tabctrl.cxx`, `tabpage.cxx`, `toolbox.cxx`)**:
  - 구형 Windows 98/XP식 3D 탭 테두리(`TABP_PANE` / `TABP_TABITEM`)를 제거하고 플랫 헤더 스트립(`#F3F6F5`) + 화이트 리본 카드(`#FFFFFF`) 구조로 개선
  - 선택된 탭 하단에 **3px Welfarego Teal(`#08776A`) 액센트 인디케이터** 및 세미볼드 타이포그래피 적용
  - 마우스 오버·토글·클릭 버튼에 안티앨리어싱 **둥근 필(6px Radius) 플루언트 스타일** 적용
  - **Windows 다크 모드** 및 **HiDPI(125%/150%/200%) 배율** 자동 대응
- **모던 벡터 아이콘 & 한국어 타이포그래피**:
  - MPL-2.0 라이선스의 깔끔한 **Sukapura SVG** 벡터 아이콘 테마를 기본 적용 (GPL 아이콘 테마 제외)
  - 한국어 UI(`ko`) 및 영문 UI(`en-US`) 기본 포함, `Pretendard → Noto Sans CJK KR → 나눔고딕 → 맑은 고딕` 순의 모던 한글 폰트 우선순위 적용
  - 첫 실행 시 불필요한 팁 팝업, TDF 기부 버튼, 외부 크래시 리포트/업데이트 통신 비활성화

### 2. 자체 브랜드 정체성 & 상표권 완전 분리 (`patches/0001`, `branding/`)
- **제품명 / 공급자**: `Welfarego OFFICE` / `Welfarego`
- **독립 설치 경로 및 고유 MSI GUID**: `C:\Program Files\Welfarego OFFICE` 및 신규 발급된 `UPGRADECODE`/`PRODUCTCODE`를 사용하여, 기존에 공식 LibreOffice가 설치된 PC에서도 충돌·덮어쓰기 없이 나란히 설치됩니다.
- **100% 독자 제작 시각 자산 (`scripts/generate_branding.py`)**:
  - 스플래시 화면 (`intro.png`, `intro-highres.png`, `progress.conf`)
  - 시작 센터 / 정보 대화상자 SVG 로고 (`logo.svg`, `logo_inverted.svg`, `logo-sc.svg`, `logo-sc_inverted.svg`, `about.svg`)
  - Windows 실행파일·문서 확장자용 다중 해상도 `.ico` 아이콘 **31종 전체** (16px~256px 13개 레이어)
  - Windows Installer(`.msi`) 설치 마법사 배너 (`Banner.bmp`, `Image.bmp`, `Image_2.bmp`)

### 3. 상업적 오픈소스 라이선스 규정 준수 (`legal/`, `LICENSE`, `NOTICE`)
- **`--enable-mpl-subset`**: GPL/LGPL 전용 구성요소(`breeze`/`elementary`/`karasa_jaga` 아이콘, `poppler`, `lpsolve`, `postgresql-sdbc`, `lotuswordpro`, `report-builder`, `mariadb-sdbc`, `gpgmepp`)를 컴파일에서 완전히 제외하여 **순수 MPL-2.0 + 허용적 라이선스(Apache-2.0, MIT, BSD, CC0)** 로만 빌드됩니다.
- **MPL-2.0 제3.2조 소스 공개 자동화**: Windows MSI 빌드 시 수정 패치 및 라이선스 고지가 담긴 `WelfaregoOFFICE_*_MPL2_Source_Patches.zip`과 `SHA256SUMS.txt`를 자동으로 함께 패키징합니다.
- **상세 법무 체크리스트**: [`legal/COMPLIANCE-GUIDE.md`](legal/COMPLIANCE-GUIDE.md), [`legal/THIRD-PARTY-LICENSES.md`](legal/THIRD-PARTY-LICENSES.md), [`legal/SOURCE-OFFER.md`](legal/SOURCE-OFFER.md) 참고.

---

## 디렉터리 구조

```text
.
├── .github/workflows/
│   ├── verify.yml                       # 푸시/PR마다 라이선스·자산·업스트림 패치 적용 자동 검증
│   └── build-windows-msi.yml            # Windows x64 MSI + MPL-2.0 소스 아카이브 자동 빌드
├── branding/
│   ├── brand.json                       # 제품명·버전·색상·URL 단일 설정 파일
│   ├── images/                          # 스플래시 PNG, SVG 로고, 앱 아이콘 프리뷰
│   ├── icons/                           # 31종 Windows 다중 해상도 .ico 아이콘
│   └── msi/                             # MSI 설치 마법사 비트맵 (Banner/Image)
├── config/
│   └── windows-x64.autogen.input        # Windows x64 MPL-2.0 Subset 릴리스 빌드 설정
├── legal/
│   ├── COMPLIANCE-GUIDE.md              # 상업적 배포 오픈소스 규정 준수 체크리스트 (한국어)
│   ├── THIRD-PARTY-LICENSES.md          # 포함/제외 서드파티 오픈소스 라이선스 목록
│   ├── SOURCE-OFFER.md                  # MPL-2.0 제3.2조 소스코드 제공 안내
│   └── PRIVACY.md                       # 오프라인·무텔레메트리 개인정보 정책
├── patches/
│   ├── 0001-rebrand-welfarego-office.patch
│   ├── 0002-default-modern-ribbon-ui.patch
│   └── 0003-fluent-ribbon-rendering.patch
├── preview/
│   └── ribbon-design-preview.html       # 브라우저에서 열어보는 모던 리본 UI 디자인 미리보기
├── scripts/
│   ├── generate_branding.py             # 독자 브랜딩 이미지 및 31종 .ico 재생성기
│   ├── apply_patches.py                 # LibreOffice 소스에 패치·브랜딩·autogen.input 적용
│   ├── verify_compliance.py             # 자동 라이선스·상표·패치 무결성 검증 스크립트
│   └── build-windows.ps1                # Windows x64 MSI 원커맨드 빌드 스크립트
├── LICENSE                              # Mozilla Public License 2.0 전문
└── NOTICE                               # 업스트림 저작권·상표 고지
```

---

## 빌드 방법 (Windows x64 `.msi` 생성)

### 방법 A. GitHub Actions에서 빌드
1. 저장소 상단 **Actions → Build Welfarego OFFICE Windows x64 MSI → Run workflow** 클릭
2. `runner` 선택:
   - `self-hosted` (권장: 16코어 이상, RAM 32GB+, SSD 80GB+ Windows 머신에서 약 1~2시간 소요)
   - `windows-2022` (GitHub 호스팅 4코어 러너 — 디스크 확보 및 캐시가 설정되어 있으나, 콜드 빌드 시 LibreOffice 특성상 6시간 제한에 근접할 수 있음)
3. 완료 후 Artifacts 또는 `v*` 태그 Release에서 다음 산출물을 다운로드합니다:
   - `WelfaregoOFFICE_26.2.7.3_Win_x86-64.msi` (설치 파일)
   - `WelfaregoOFFICE_26.2.7.3_MPL2_Source_Patches.zip` (MPL-2.0 소스 공개 아카이브)
   - `SHA256SUMS.txt`

### 방법 B. 로컬 Windows PC에서 직접 빌드 (가장 빠르고 안정적)
**권장 사양:** Windows 10/11 64-bit, RAM 16GB 이상(32GB 권장), NVMe SSD 여유 공간 80GB 이상, Visual Studio 2022 (Desktop development with C++ + ATL + Windows 11 SDK)

1. Cygwin64 (`C:\cygwin64`) 설치 및 LibreOffice 빌드 필수 패키지 설치 (`autoconf, automake, bison, cabextract, flex, gettext, gettext-devel, gperf, nasm, patch, perl, perl-Archive-Zip, perl-Font-TTF, perl-Digest-MD5, unzip, wget, zip`)
2. PowerShell(관리자 또는 일반)에서 실행:
   ```powershell
   .\scripts\build-windows.ps1 -WorkDir C:\lo -CygwinRoot C:\cygwin64
   ```
3. 완료되면 `dist\` 폴더에 `.msi` 설치 파일과 MPL-2.0 소스 패치 아카이브가 생성됩니다.

---

## 검증 및 브랜딩 커스터마이징

```bash
# 1. 브랜딩 이미지·31종 Windows 아이콘 재생성
python3 scripts/generate_branding.py

# 2. 오픈소스 규정 준수 및 자산 무결성 자동 검사
python3 scripts/verify_compliance.py
```

---

## 라이선스

본 저장소의 Welfarego OFFICE 패치 및 빌드 스크립트는 **Mozilla Public License Version 2.0 (MPL-2.0)** 으로 배포됩니다. 자세한 내용은 [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`legal/COMPLIANCE-GUIDE.md`](legal/COMPLIANCE-GUIDE.md)를 확인하세요.

*"LibreOffice"와 "The Document Foundation"은 The Document Foundation의 등록상표입니다. Welfarego OFFICE는 독립적인 파생 배포판이며 The Document Foundation과 제휴하거나 보증을 받지 않았습니다.*
