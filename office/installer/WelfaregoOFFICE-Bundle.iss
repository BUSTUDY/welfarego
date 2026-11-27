; Welfarego OFFICE Bundle — Windows x64 One-Click Setup (.exe) Inno Setup 6 Script
; Packages the official LibreOffice Windows x64 MSI (MPL-2.0) together with:
;   1. Modern Tabbed Ribbon UI + Sukapura SVG default preset (welfarego-defaults.xcd)
;   2. Welfarego Practical Shortcuts Extension (welfarego-links.oxt, voluntary-click only)
;   3. Korean/English wizard and MPL-2.0 open-source compliance notices

#ifndef AppVersion
  #define AppVersion "26.2.7"
#endif

#ifndef MsiFile
  #define MsiFile "..\dist\LibreOffice_26.2.7_Win_x86-64.msi"
#endif

#ifndef OutputDirPath
  #define OutputDirPath "..\dist"
#endif

#ifndef DryRun
  #define DryRun "0"
#endif

[Setup]
AppId={{8F3D2A1C-5B94-4E71-9A20-6C4E8B1D7F30}
AppName=Welfarego OFFICE (LibreOffice 기반 통합판)
AppVersion={#AppVersion}
AppVerName=Welfarego OFFICE {#AppVersion}
AppPublisher=Welfarego
AppPublisherURL=https://welfarego.co.kr/office
AppSupportURL=https://welfarego.co.kr/office
AppUpdatesURL=https://welfarego.co.kr/office
DefaultDirName={autopf}\LibreOffice
DisableDirPage=yes
DisableProgramGroupPage=yes
LicenseFile=..\legal\INSTALLER-LICENSE-KO.txt
SetupIconFile=..\branding\icons\soffice.ico
WizardImageFile=..\branding\msi\WizardImage.bmp
WizardSmallImageFile=..\branding\msi\WizardSmall.bmp
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Compression=lzma2/fast
SolidCompression=no
OutputDir={#OutputDirPath}
OutputBaseFilename=WelfaregoOFFICE_{#AppVersion}_Setup_x64
Uninstallable=no
CreateUninstallRegKey=no
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany=Welfarego
VersionInfoProductName=Welfarego OFFICE Bundle
VersionInfoProductVersion={#AppVersion}.0
VersionInfoDescription=Welfarego OFFICE {#AppVersion} Windows x64 Setup (Ribbon UI + Practical Shortcuts / MPL-2.0)
VersionInfoCopyright=Derived from LibreOffice (MPL-2.0). Shortcuts & preset by Welfarego.

[Languages]
Name: "korean"; MessagesFile: "Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
korean.TaskDesktop=바탕 화면에 오피스 바로 가기 만들기
english.TaskDesktop=Create desktop shortcut
korean.TaskMsoAssoc=MS Office 문서(.docx, .xlsx, .pptx)를 기본 프로그램으로 연결
english.TaskMsoAssoc=Associate MS Office files (.docx, .xlsx, .pptx)
korean.InstallingMsi=오피스 본체(LibreOffice {#AppVersion} 64비트 한국어)를 설치하고 있습니다. 약 1~2분 소요됩니다...
english.InstallingMsi=Installing core office suite (LibreOffice {#AppVersion} x64). This may take 1-2 minutes...
korean.InstallingExt=모던 리본 메뉴 설정 및 [실무포털·서식] 바로가기 확장기능을 적용하는 중...
english.InstallingExt=Applying Modern Ribbon UI preset and Welfarego Shortcuts extension...
korean.LaunchApp=설치 완료 후 오피스 지금 실행
english.LaunchApp=Launch Office now

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktop}"
Name: "msoassoc"; Description: "{cm:TaskMsoAssoc}"; Flags: unchecked

[Files]
Source: "{#MsiFile}"; DestDir: "{tmp}"; DestName: "LibreOffice_Win_x86-64.msi"; Flags: deleteafterinstall nocompression
Source: "..\config\welfarego-defaults.xcd"; DestDir: "{autopf}\LibreOffice\share\registry"; Flags: ignoreversion
Source: "..\extensions\welfarego-links.oxt"; DestDir: "{autopf}\LibreOffice\share\extensions"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{autopf}\LibreOffice\welfarego-legal"; Flags: ignoreversion
Source: "..\NOTICE"; DestDir: "{autopf}\LibreOffice\welfarego-legal"; Flags: ignoreversion
Source: "..\legal\PRIVACY.md"; DestDir: "{autopf}\LibreOffice\welfarego-legal"; Flags: ignoreversion

[Run]
#if DryRun == "0"
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\LibreOffice_Win_x86-64.msi"" /qb! ALLUSERS=1 UI_LANGS=ko,en_US {code:GetMsiProperties}"; StatusMsg: "{cm:InstallingMsi}"; Flags: waituntilterminated
Filename: "{autopf}\LibreOffice\program\unopkg.com"; Parameters: "add --shared --force ""{autopf}\LibreOffice\share\extensions\welfarego-links.oxt"""; StatusMsg: "{cm:InstallingExt}"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{autopf}\LibreOffice\program\soffice.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
#endif

[Code]
function GetMsiProperties(Param: String): String;
var
  Props: String;
begin
  Props := '';
  if WizardIsTaskSelected('desktopicon') then
    Props := Props + ' CREATEDESKTOPLINK=1'
  else
    Props := Props + ' CREATEDESKTOPLINK=0';

  if WizardIsTaskSelected('msoassoc') then
    Props := Props + ' REGISTER_ALL_MSO_TYPES=1'
  else
    Props := Props + ' REGISTER_NO_MSO_TYPES=1';

  Result := Props;
end;
