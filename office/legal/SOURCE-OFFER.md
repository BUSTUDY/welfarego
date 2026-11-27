# Source Code Availability & Written Offer (MPL-2.0 / LGPLv3)

In accordance with **Section 3.2 of the Mozilla Public License Version 2.0 (MPL-2.0)** and **Section 4 of the GNU Lesser General Public License Version 3 (LGPLv3)**, Welfarego provides complete corresponding source code access for **Welfarego OFFICE** and all upstream open-source components it redistributes.

## How to Obtain the Complete Corresponding Source Code

1. **Welfarego OFFICE Modifications, Scripts, Extension & Build Configuration (MPL-2.0)**
   - **Public GitHub Repository**: https://github.com/BUSTUDY/welfarego (see [`office/`](../))
   - **GitHub Release Source Archive**: Every Windows installer release published at https://github.com/BUSTUDY/welfarego/releases includes a matching `WelfaregoOFFICE_<version>_Source.zip` archive right alongside the installer `.exe`.
   - **Direct Portal Download**: https://welfarego.co.kr/office/download/mpl2-source.zip

2. **Unmodified Upstream LibreOffice 26.2.7 Engine Source Code (MPL-2.0 / LGPLv3 / Apache-2.0)**
   - **Official Document Foundation Source Tarballs**: https://download.documentfoundation.org/libreoffice/src/26.2.7/
   - **Official Git Repository**: https://git.libreoffice.org/core (mirror: https://github.com/LibreOffice/core, branch `libreoffice-26-2` / tag `libreoffice-26.2.7.3`)

3. **Written Offer (3-Year Availability)**
   - For at least three (3) years from the date of distribution, anyone may obtain the complete corresponding source code free of charge from the URLs above, or by contacting `sllwe7@gmail.com`.

## Included Welfarego Source Files & Patches

All Welfarego customizations, configuration overlays, localization overrides, installer scripts, extensions, and optional C++ patches are openly maintained under **MPL-2.0**:

- [`config/welfarego-defaults.xcd`](../config/welfarego-defaults.xcd) — Product title/app UI names, Tabbed Ribbon UI (`notebookbar.ui`), `HasMenubar=true`, `Sukapura SVG` icon theme, `WelfaregoModern` light color scheme, disabled English first-run dialog
- [`config/welfarego-ko-labels.xcd`](../config/welfarego-ko-labels.xcd) — Korean localization overrides for upstream untranslated Ribbon commands
- [`installer/WelfaregoOFFICE-Bundle.iss`](../installer/WelfaregoOFFICE-Bundle.iss), [`installer/configure-installed-office.ps1`](../installer/configure-installed-office.ps1), [`installer/uninstall-welfarego-office.ps1`](../installer/uninstall-welfarego-office.ps1) — Windows x64 one-click bundle installer, Korean Ribbon tab enrichment (`Design`, `Formulas`, `Transitions`, `Animations`), shortcut/Control Panel setup, and clean uninstaller
- [`extensions/welfarego-links/`](../extensions/welfarego-links/) — Voluntary-click UNO Python ProtocolHandler (`welfarego_links.py`), `Addons.xcu`, `ProtocolHandler.xcu`, `description.xml`
- [`scripts/generate_branding.py`](../scripts/generate_branding.py), [`scripts/build_extension.py`](../scripts/build_extension.py) — 100% original Welfarego icon, splash, and extension generators
- [`patches/0001-rebrand-welfarego-office.patch`](../patches/0001-rebrand-welfarego-office.patch), [`patches/0002-default-modern-ribbon-ui.patch`](../patches/0002-default-modern-ribbon-ui.patch), [`patches/0003-fluent-ribbon-rendering.patch`](../patches/0003-fluent-ribbon-rendering.patch) — Optional source-build patches for custom MSI builds
