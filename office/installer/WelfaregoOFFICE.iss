; Welfarego OFFICE — Windows x64 Setup (.exe) Inno Setup 6 Script
; Wraps the source-compiled WelfaregoOFFICE Windows x64 MSI installer into a
; modern one-click Korean/English .exe installer with full MPL-2.0 notices.

#ifndef AppVersion
  #define AppVersion "26.2.7.3"
#endif

#ifndef MsiFile
  #define MsiFile "..\dist\WelfaregoOFFICE_26.2.7.3_Win_x86-64.msi"
#endif

#ifndef OutputDirPath
  #define OutputDirPath "..\dist"
#endif

#ifndef DryRun
  #define DryRun "0"
#endif

[Setup]
AppId={{D28F63A9-4E1C-49B7-8F52-9A7C3E6B12D0}
AppName=Welfarego OFFICE
AppVersion={#AppVersion}
AppVerName=Welfarego OFFICE {#AppVersion}
AppPublisher=Welfarego
AppPublisherURL=https://github.com/BUSTUDY/welfarego
AppSupportURL=https://github.com/BUSTUDY/welfarego/issues
AppUpdatesURL=https://github.com/BUSTUDY/welfarego/releases
DefaultDirName={autopf}\Welfarego OFFICE
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
; The embedded Windows MSI registers the official Add/Remove Programs uninstaller.
; Disabling the outer bootstrapper uninstall entry avoids duplicate entries in Windows Settings.
Uninstallable=no
CreateUninstallRegKey=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Welfarego
VersionInfoProductName=Welfarego OFFICE
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription=Welfarego OFFICE {#AppVersion} Windows x64 Setup (Fluent Ribbon / MPL-2.0)
VersionInfoCopyright=Copyright (c) LibreOffice contributors and Welfarego (MPL-2.0)

[Languages]
Name: "korean"; MessagesFile: "Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
korean.TaskDesktop=바탕 화면에 Welfarego OFFICE 바로 가기 만들기
english.TaskDesktop=Create a Welfarego OFFICE desktop shortcut
korean.TaskMsoAssoc=Microsoft Office 문서(.docx, .xlsx, .pptx)를 기본 프로그램으로 연결
english.TaskMsoAssoc=Associate Microsoft Office files (.docx, .xlsx, .pptx) with Welfarego OFFICE
korean.InstallingMsi=Welfarego OFFICE 본체(MSI)를 설치하고 있습니다. 약 1~2분 소요됩니다...
english.InstallingMsi=Installing Welfarego OFFICE core package (MSI). This may take 1-2 minutes...
korean.LaunchApp=Welfarego OFFICE 지금 실행
english.LaunchApp=Launch Welfarego OFFICE now

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktop}"
Name: "msoassoc"; Description: "{cm:TaskMsoAssoc}"; Flags: unchecked

[Files]
; Embedded Windows MSI package unpacked to {tmp} and executed via msiexec
Source: "{#MsiFile}"; DestDir: "{tmp}"; DestName: "WelfaregoOFFICE.msi"; Flags: deleteafterinstall nocompression
; Commercial open-source compliance documents installed under Program Files\Welfarego OFFICE\legal
Source: "..\LICENSE"; DestDir: "{autopf}\Welfarego OFFICE\legal"; Flags: ignoreversion
Source: "..\NOTICE"; DestDir: "{autopf}\Welfarego OFFICE\legal"; Flags: ignoreversion
Source: "..\legal\SOURCE-OFFER.md"; DestDir: "{autopf}\Welfarego OFFICE\legal"; Flags: ignoreversion
Source: "..\legal\THIRD-PARTY-LICENSES.md"; DestDir: "{autopf}\Welfarego OFFICE\legal"; Flags: ignoreversion
Source: "..\legal\PRIVACY.md"; DestDir: "{autopf}\Welfarego OFFICE\legal"; Flags: ignoreversion
; Bundled MPL-2.0 voluntary-click menu & toolbar shortcuts extension (.oxt)
Source: "..\extensions\welfarego-links.oxt"; DestDir: "{autopf}\Welfarego OFFICE\share\extensions"; Flags: ignoreversion

[Run]
#if DryRun == "0"
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\WelfaregoOFFICE.msi"" /qb! ALLUSERS=1 {code:GetMsiProperties}"; StatusMsg: "{cm:InstallingMsi}"; Flags: waituntilterminated
Filename: "{autopf}\Welfarego OFFICE\program\unopkg.com"; Parameters: "add --shared --force ""{autopf}\Welfarego OFFICE\share\extensions\welfarego-links.oxt"""; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{autopf}\Welfarego OFFICE\program\soffice.exe"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent
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
