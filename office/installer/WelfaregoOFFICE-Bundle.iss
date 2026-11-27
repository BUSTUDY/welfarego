; Welfarego OFFICE Bundle — Windows x64 One-Click Setup (.exe) Inno Setup 6 Script
; Packages the official LibreOffice Windows x64 MSI (MPL-2.0) together with:
;   1. Portal-matched Welfarego OFFICE branding & #2151C8 house+heart icons
;   2. Modern Tabbed Ribbon UI (notebookbar.ui) + Sukapura SVG default preset
;   3. Welfarego Practical Shortcuts on Home tab & [★ 실무포털·서식] Ribbon tab (voluntary-click only)

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
AppName=Welfarego OFFICE
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
VersionInfoProductName=Welfarego OFFICE
VersionInfoProductVersion={#AppVersion}.0
VersionInfoDescription=Welfarego OFFICE {#AppVersion} Windows x64 Setup (Modern Ribbon UI + Practical Shortcuts / MPL-2.0)
VersionInfoCopyright=Derived from LibreOffice (MPL-2.0). Branding, preset & shortcuts by Welfarego.

[Languages]
Name: "korean"; MessagesFile: "Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
korean.TaskDesktop=바탕 화면에 Welfarego OFFICE 바로 가기 만들기
english.TaskDesktop=Create Welfarego OFFICE desktop shortcut
korean.TaskMsoAssoc=MS Office 문서(.docx, .xlsx, .pptx)를 기본 프로그램으로 연결
english.TaskMsoAssoc=Associate MS Office files (.docx, .xlsx, .pptx)
korean.InstallingMsi=Welfarego OFFICE 핵심 엔진({#AppVersion} 64비트 한국어)을 설치하고 있습니다. 약 1~2분 소요됩니다...
english.InstallingMsi=Installing Welfarego OFFICE core suite ({#AppVersion} x64). This may take 1-2 minutes...
korean.InstallingExt=Welfarego 브랜드 아이콘, 모던 리본 메뉴 및 [실무포털·서식] 바로가기를 구성하는 중...
english.InstallingExt=Applying Welfarego branding, Modern Ribbon UI, and Practical Shortcuts...
korean.LaunchApp=설치 완료 후 Welfarego OFFICE 지금 실행
english.LaunchApp=Launch Welfarego OFFICE now

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktop}"
Name: "msoassoc"; Description: "{cm:TaskMsoAssoc}"; Flags: unchecked

[Files]
Source: "{#MsiFile}"; DestDir: "{tmp}"; DestName: "LibreOffice_Win_x86-64.msi"; Flags: deleteafterinstall nocompression
Source: "configure-installed-office.ps1"; DestDir: "{tmp}\wg-payload"; Flags: deleteafterinstall
Source: "..\config\welfarego-defaults.xcd"; DestDir: "{tmp}\wg-payload"; Flags: deleteafterinstall
Source: "..\extensions\welfarego-links.oxt"; DestDir: "{tmp}\wg-payload"; Flags: deleteafterinstall
Source: "..\branding\icons\*.ico"; DestDir: "{tmp}\wg-payload\icons"; Flags: deleteafterinstall
Source: "..\branding\images\intro.png"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\intro-highres.png"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\logo.svg"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\logo-sc.svg"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\logo_inverted.svg"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\logo-sc_inverted.svg"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\branding\images\about.svg"; DestDir: "{tmp}\wg-payload\images"; Flags: deleteafterinstall
Source: "..\LICENSE"; DestDir: "{tmp}\wg-payload\legal"; Flags: deleteafterinstall
Source: "..\NOTICE"; DestDir: "{tmp}\wg-payload\legal"; Flags: deleteafterinstall
Source: "..\legal\PRIVACY.md"; DestDir: "{tmp}\wg-payload\legal"; Flags: deleteafterinstall

[Run]
#if DryRun == "0"
Filename: "taskkill.exe"; Parameters: "/F /IM soffice.bin /IM soffice.exe /T"; Flags: runhidden waituntilterminated; StatusMsg: "{cm:InstallingMsi}"
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\LibreOffice_Win_x86-64.msi"" {code:GetMsiUiFlag} /norestart ALLUSERS=1 CREATEDESKTOPLINK=0 UI_LANGS=ko,en_US {code:GetMsiProperties}"; StatusMsg: "{cm:InstallingMsi}"; Flags: waituntilterminated
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\wg-payload\configure-installed-office.ps1"" -PayloadDir ""{tmp}\wg-payload"" -AppVersion ""{#AppVersion}"" -CreateDesktopShortcut ""{code:GetDesktopFlag}"""; StatusMsg: "{cm:InstallingExt}"; Flags: runhidden waituntilterminated
Filename: "{autopf}\LibreOffice\program\soffice.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
#endif

[Code]
function GetMsiUiFlag(Param: String): String;
begin
  if WizardSilent then
    Result := '/qn'
  else
    Result := '/qb!';
end;

function GetMsiProperties(Param: String): String;
begin
  if WizardIsTaskSelected('msoassoc') then
    Result := 'REGISTER_ALL_MSO_TYPES=1'
  else
    Result := 'REGISTER_NO_MSO_TYPES=1';
end;

function GetDesktopFlag(Param: String): String;
begin
  if WizardIsTaskSelected('desktopicon') then
    Result := '1'
  else
    Result := '0';
end;
