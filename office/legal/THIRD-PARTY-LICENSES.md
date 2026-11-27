# Third-Party Open Source Licenses

Welfarego OFFICE distributes its Windows one-click installer (`WelfaregoOFFICE-Bundle.iss`) by packaging the official **LibreOffice 26.2.7 Windows x64 MSI** published by The Document Foundation (licensed primarily under **MPL-2.0**, together with its included **LGPLv3 / Apache-2.0 / MIT / BSD** third-party libraries) alongside original Welfarego branding, Korean Ribbon UI presets, and voluntary-click shortcut extensions under **MPL-2.0**.

Inside every installed copy of Welfarego OFFICE, LibreOffice's official generated license file (`C:\Program Files\LibreOffice\LICENSE.html` and `CREDITS.fodt`) lists the complete, exact license text for every compiled upstream library, and `C:\Program Files\LibreOffice\welfarego-legal\` stores Welfarego's `LICENSE`, `NOTICE`, `SOURCE-OFFER.md`, `THIRD-PARTY-LICENSES.md`, `PRIVACY.md`, and `INSTALLER-LICENSE-KO.txt`.

## Core Office Engine & UI

| Component | License | Upstream Project |
| --- | --- | --- |
| **LibreOffice 26.2.7 Core Engine** (`libreoffice-26.2.7.3`) | Mozilla Public License 2.0 (MPL-2.0) + included LGPLv3/Apache-2.0 components | https://download.documentfoundation.org/libreoffice/src/26.2.7/ |
| **Sukapura SVG Icon Theme** (Default icon theme) | Mozilla Public License 2.0 (MPL-2.0) | Rizal Muttaqin / LibreOffice |
| **Colibre SVG Icon Theme** (Fallback icon theme) | Creative Commons CC0 1.0 Universal | Andreas Kainz / LibreOffice |
| **Apache OpenOffice Derived Portions** | Apache License 2.0 | https://openoffice.apache.org/ |

## Major Bundled Open-Source Libraries (Upstream LibreOffice 26.2.7)

| Component | License | Purpose |
| --- | --- | --- |
| **Skia** | BSD-3-Clause | 2D hardware/software graphics rendering on Windows |
| **HarfBuzz** | MIT License | OpenType text shaping (Korean/CJK & Latin typography) |
| **ICU (International Components for Unicode)** | Unicode License | Unicode, collation, locale & BiDi support |
| **PDFium** | BSD-3-Clause | High-fidelity PDF viewing & image rendering |
| **OpenSSL** | Apache License 2.0 | Cryptographic document signing & TLS |
| **libxml2 / libxslt** | MIT License | ODF / OOXML XML parsing and transformation |
| **Expat** | MIT License | Fast streaming XML parser |
| **zlib / libpng / libjpeg-turbo / libwebp** | zlib / libpng / IJG / BSD-3-Clause | Compression & image codecs |
| **Boost** | Boost Software License 1.0 | C++ utility libraries |
| **Python (internal CPython)** | PSF License 2.0 | Built-in scripting & document automation |
| **FreeType / Cairo / Pixman** | FreeType License / MPL-1.1 / MIT | Font rasterization & vector graphics |
| **Hunspell** | MPL-1.1 / GPL / LGPL | Spell checking |
| **NSS / NSPR** | MPL-2.0 | Certificate & security services |
| **Upstream LGPLv3 / Optional Components** (e.g., `lpsolve`, `postgresql-sdbc`, `lotuswordpro`, `report-builder`, `mariadb-sdbc`, `gpgmepp`, `poppler`, additional icon themes) | LGPLv3 / GPLv2 (unmodified upstream MSI binaries; full source available at https://download.documentfoundation.org/libreoffice/src/26.2.7/) | Included unmodified in official TDF LibreOffice 26.2.7 MSI |

## Optional Pure MPL-2.0 Subset Source-Build Profile

For organizations wishing to compile a pure MPL-2.0 subset MSI from source without GPL/LGPL-only upstream modules, this repository also provides [`config/windows-x64.autogen.input`](../config/windows-x64.autogen.input) (`--enable-mpl-subset`), which excludes `breeze`/`elementary`/`karasa_jaga`, `poppler`, `lpsolve`, `postgresql-sdbc`, `lotuswordpro`, `report-builder`, `mariadb-sdbc`, and `gpgmepp`.

## Original Welfarego Assets

All visual branding assets under [`branding/`](../branding/) (`intro.png`, `intro-highres.png`, `logo*.svg`, `about.svg`, `msi/*.bmp`, `icons/*.ico`) are 100% original geometric artwork created for Welfarego OFFICE. No The Document Foundation or LibreOffice logos or icons are included.
