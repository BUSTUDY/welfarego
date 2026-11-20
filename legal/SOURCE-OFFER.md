# Source Code Availability & Written Offer (MPL-2.0)

In accordance with **Section 3.2 of the Mozilla Public License Version 2.0 (MPL-2.0)**, Welfarego provides complete source code access for all MPL-2.0 covered files modified in **Welfarego OFFICE**.

## How to Obtain the Complete Corresponding Source Code

1. **Welfarego OFFICE Modifications, Patches, and Build Configuration**
   - Public Git Repository: https://github.com/BUSTUDY/welfarego
   - Release Archives: Each Windows `.msi` release published on GitHub Releases is accompanied by a corresponding `WelfaregoOFFICE-<version>-source-patches.zip` archive containing all modified files, unified patches (`patches/*.patch`), build scripts, and license notices.

2. **Unmodified Upstream Base Source Code**
   - Upstream Project: LibreOffice (`https://github.com/LibreOffice/core`)
   - Exact Base Tag: `libreoffice-26.2.7.3`
   - Mirror / Archive: https://download.documentfoundation.org/libreoffice/src/26.2.7/

## Modified MPL-2.0 Files in Welfarego OFFICE

All modifications to upstream LibreOffice files are maintained as clean, inspectable patches in [`patches/`](../patches/):

- [`patches/0001-rebrand-welfarego-office.patch`](../patches/0001-rebrand-welfarego-office.patch) — Product name, Windows installer metadata/GUIDs, executable version info, Start Menu tooltips, README & URLs
- [`patches/0002-default-modern-ribbon-ui.patch`](../patches/0002-default-modern-ribbon-ui.patch) — Default Tabbed Ribbon UI, Sukapura SVG icons, Korean font defaults, clean first-run settings
- [`patches/0003-fluent-ribbon-rendering.patch`](../patches/0003-fluent-ribbon-rendering.patch) — Modern Fluent Ribbon C++ VCL rendering (`tabctrl.hxx`, `tabctrl.cxx`, `tabpage.cxx`, `toolbox.cxx`)

All modified upstream files remain licensed under **MPL-2.0**.
