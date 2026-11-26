# Third-Party Open Source Licenses

Welfarego OFFICE is built on top of the open-source LibreOffice codebase (MPL-2.0 subset) and includes third-party open-source components. During the Windows MSI build, LibreOffice's built-in license generator (`readlicense_oo`) compiles the complete, exact `LICENSE.html` / `LICENSE` file for every compiled library and embeds it inside the installed program directory.

Below is a summary of the primary upstream licenses used in a Welfarego OFFICE `--enable-mpl-subset` build.

## Core Office Engine & UI

| Component | License | Upstream Project |
| --- | --- | --- |
| **LibreOffice Core (MPL-2.0 Subset)** (`libreoffice-26.2.7.3`) | Mozilla Public License 2.0 (MPL-2.0) | https://github.com/LibreOffice/core |
| **Sukapura SVG Icon Theme** (Default icon theme) | Mozilla Public License 2.0 (MPL-2.0) | Rizal Muttaqin / LibreOffice |
| **Colibre SVG Icon Theme** (Fallback icon theme) | Creative Commons CC0 1.0 Universal | Andreas Kainz / LibreOffice |
| **Apache OpenOffice Derived Portions** | Apache License 2.0 | https://openoffice.apache.org/ |

## Major Bundled Open-Source Libraries (MPL-2.0 Compatible)

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
| **Hunspell** | MPL-1.1 / GPL / LGPL (used under MPL) | Spell checking |
| **NSS / NSPR** | MPL-2.0 | Certificate & security services |
| **CoinMP** | EPL-1.0 / CPL-1.0 (if enabled) | Calc optimization solver |

## Components Intentionally Excluded for Commercial Cleanliness

Because Welfarego OFFICE enables `--enable-mpl-subset` in [`config/windows-x64.autogen.input`](../config/windows-x64.autogen.input), the following GPL/LGPL-only upstream components are **excluded from compilation**:

- `breeze`, `elementary`, `karasa_jaga` icon themes (GPLv2/GPLv3/LGPLv3)
- `poppler` internal PDF-to-Draw vector importer (GPLv2)
- `lpsolve` Calc linear solver (LGPL)
- `postgresql-sdbc` driver (LGPL)
- `lotuswordpro` legacy filter (LGPL)
- `report-builder` Java extension (LGPL)
- `mariadb-sdbc` driver (LGPL)
- `gpgmepp` (LGPL)

## Original Welfarego Assets

All visual branding assets under [`branding/`](../branding/) (`intro.png`, `intro-highres.png`, `logo*.svg`, `about.svg`, `msi/*.bmp`, `icons/*.ico`) are 100% original geometric artwork created for Welfarego OFFICE. No The Document Foundation or LibreOffice logos or icons are included.
