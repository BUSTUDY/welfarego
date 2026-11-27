param(
    [string]$PayloadDir = $PSScriptRoot,
    [string]$AppVersion = "26.2.7",
    [string]$CreateDesktopShortcut = "1"
)

$ErrorActionPreference = "Stop"

function U([string]$Escaped) {
    return [System.Text.RegularExpressions.Regex]::Unescape($Escaped)
}

function Set-OrAddXmlProp([xml]$Doc, [System.Xml.XmlElement]$ParentObj, [string]$PropName, [string]$PropVal) {
    $existing = $ParentObj.SelectSingleNode("property[@name='$PropName']")
    if ($null -eq $existing) {
        $existing = $Doc.CreateElement("property")
        $existing.SetAttribute("name", $PropName)
        [void]$ParentObj.AppendChild($existing)
    }
    $existing.InnerText = $PropVal
}

# 1. Locate installed LibreOffice directory
$loCandidates = @(
    (Join-Path $env:ProgramFiles "LibreOffice")
)
try {
    $unoReg = Get-ItemProperty -Path "HKLM:\SOFTWARE\LibreOffice\UNO\InstallPath" -ErrorAction SilentlyContinue
    if ($null -ne $unoReg) {
        foreach ($prop in $unoReg.PSObject.Properties) {
            if ($prop.Name -notlike "PS*" -and $prop.Value -and (Test-Path $prop.Value)) {
                $loCandidates += (Split-Path -Parent $prop.Value)
            }
        }
    }
} catch {}

$loDir = $loCandidates | Where-Object { Test-Path (Join-Path $_ "program\soffice.exe") } | Select-Object -First 1
if (-not $loDir) {
    throw "Core office installation not found under Program Files."
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$installLog = Join-Path $loDir "welfarego-install.log"
function Log-Step([string]$Msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
    try { Add-Content -Path $installLog -Value $line -Encoding UTF8 } catch {}
}
Log-Step "Starting Welfarego OFFICE post-install configuration in $loDir (Desktop=$CreateDesktopShortcut)"

# 2. Clean stray raw .oxt inside share\extensions from older bundle builds
$strayOxt = Join-Path $loDir "share\extensions\welfarego-links.oxt"
if (Test-Path $strayOxt) {
    Remove-Item -Path $strayOxt -Force -ErrorAction SilentlyContinue
}

# 3. Copy Welfarego icons, splash, Start Center SVGs, uninstaller helper, and legal notices
$brandIconsDest = Join-Path $loDir "welfarego-brand\icons"
$legalDest = Join-Path $loDir "welfarego-legal"
$uninstDest = Join-Path $loDir "welfarego-uninst"
$shellDest = Join-Path $loDir "program\shell"
New-Item -ItemType Directory -Force -Path $brandIconsDest | Out-Null
New-Item -ItemType Directory -Force -Path $legalDest | Out-Null
New-Item -ItemType Directory -Force -Path $uninstDest | Out-Null
New-Item -ItemType Directory -Force -Path $shellDest | Out-Null

Copy-Item -Path (Join-Path $PayloadDir "icons\*.ico") -Destination $brandIconsDest -Force
Copy-Item -Path (Join-Path $PayloadDir "images\intro.png") -Destination (Join-Path $loDir "program\intro.png") -Force
Copy-Item -Path (Join-Path $PayloadDir "images\intro-highres.png") -Destination (Join-Path $loDir "program\intro-highres.png") -Force
foreach ($svg in @("logo.svg", "logo-sc.svg", "logo_inverted.svg", "logo-sc_inverted.svg", "about.svg")) {
    $srcSvg = Join-Path $PayloadDir "images\$svg"
    if (Test-Path $srcSvg) {
        Copy-Item -Path $srcSvg -Destination (Join-Path $shellDest $svg) -Force
    }
}
if (Test-Path (Join-Path $PayloadDir "legal")) {
    Copy-Item -Path (Join-Path $PayloadDir "legal\*") -Destination $legalDest -Force
}
$uninstPs1 = Join-Path $PayloadDir "uninstall-welfarego-office.ps1"
if (Test-Path $uninstPs1) {
    Copy-Item -Path $uninstPs1 -Destination (Join-Path $uninstDest "uninstall-welfarego-office.ps1") -Force
}
Log-Step "Copied Welfarego icons, splash screens, Start Center SVGs, and uninstaller helper."

# 4. Deploy zz-welfarego-defaults.xcd to BOTH share\registry and share\registry\res
$regDir = Join-Path $loDir "share\registry"
$regResDir = Join-Path $regDir "res"
$oldXcd = Join-Path $regDir "welfarego-defaults.xcd"
if (Test-Path $oldXcd) {
    Remove-Item -Path $oldXcd -Force -ErrorAction SilentlyContinue
}
Copy-Item -Path (Join-Path $PayloadDir "welfarego-defaults.xcd") -Destination (Join-Path $regDir "zz-welfarego-defaults.xcd") -Force
if (Test-Path $regResDir) {
    Copy-Item -Path (Join-Path $PayloadDir "welfarego-defaults.xcd") -Destination (Join-Path $regResDir "zz-welfarego-defaults.xcd") -Force
}
Log-Step "Deployed zz-welfarego-defaults.xcd."

# 5. Clean CRLF update of bootstrap.ini & soffice.ini (using .orig backup for idempotency)
$bootstrapIni = Join-Path $loDir "program\bootstrap.ini"
if (Test-Path $bootstrapIni) {
    $bootstrapOrig = "$bootstrapIni.orig"
    if (-not (Test-Path $bootstrapOrig)) {
        Copy-Item -Path $bootstrapIni -Destination $bootstrapOrig -Force
    }
    $bsLines = [System.IO.File]::ReadAllLines($bootstrapOrig, $utf8NoBom) | ForEach-Object {
        if ($_.StartsWith("UserInstallation=")) {
            'UserInstallation=$SYSUSERCONFIG/WelfaregoOffice/4'
        } else {
            $_
        }
    }
    [System.IO.File]::WriteAllText($bootstrapIni, (($bsLines -join "`r`n") + "`r`n"), $utf8NoBom)
}

$sofficeIni = Join-Path $loDir "program\soffice.ini"
if (-not (Test-Path $sofficeIni)) {
    $sofficeIni = Join-Path $loDir "program\sofficerc"
}
if (Test-Path $sofficeIni) {
    $sofficeOrig = "$sofficeIni.orig"
    if (-not (Test-Path $sofficeOrig)) {
        Copy-Item -Path $sofficeIni -Destination $sofficeOrig -Force
    }
    $soLines = [System.IO.File]::ReadAllLines($sofficeOrig, $utf8NoBom) | ForEach-Object {
        if ($_.StartsWith("ProgressBarColor=")) {
            "ProgressBarColor=96,165,250"
        } elseif ($_.StartsWith("ProgressFrameColor=")) {
            "ProgressFrameColor=33,81,200"
        } else {
            $_
        }
    }
    [System.IO.File]::WriteAllText($sofficeIni, (($soLines -join "`r`n") + "`r`n"), $utf8NoBom)
}

# Unlock & remove any stale .lock or elevated extension cache across all local user profiles
$usersRoot = Split-Path -Parent $env:PUBLIC
if (-not $usersRoot -or -not (Test-Path $usersRoot)) { $usersRoot = "C:\Users" }
Get-ChildItem -Path $usersRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    foreach ($sub in @("AppData\Roaming\WelfaregoOffice", "AppData\Roaming\WelfaregoOFFICE", "AppData\Roaming\LibreOffice")) {
        $profRoot = Join-Path $_.FullName $sub
        if (Test-Path $profRoot) {
            $lockFile = Join-Path $profRoot "4\.lock"
            if (Test-Path $lockFile) {
                Remove-Item -Path $lockFile -Force -ErrorAction SilentlyContinue
            }
            $extCache = Join-Path $profRoot "4\user\extensions"
            if (Test-Path $extCache) {
                Remove-Item -Path $extCache -Recurse -Force -ErrorAction SilentlyContinue
            }
            try {
                Start-Process -FilePath "icacls.exe" -ArgumentList "`"$profRoot`" /reset /T /C /Q" -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
            } catch {}
        }
    }
}
Log-Step "Updated bootstrap.ini, soffice.ini, and unlocked user profile directories."

# 6. Install Welfarego Practical Shortcuts extension (.oxt) for all users via Start-Process
$unopkg = Join-Path $loDir "program\unopkg.com"
$oxtPath = Join-Path $PayloadDir "welfarego-links.oxt"
if ((Test-Path $unopkg) -and (Test-Path $oxtPath)) {
    $unoArgs = "add --shared --suppress-license --force `"$oxtPath`""
    $unoProc = Start-Process -FilePath $unopkg -ArgumentList $unoArgs -WindowStyle Hidden -Wait -PassThru
    Log-Step "unopkg add exited with code $($unoProc.ExitCode)."
}

# 7. Customize Ribbon UI (notebookbar.ui) idempotently from .orig backup
$tabLabelKo = U "\u2605 \uC2E4\uBB34\uD3EC\uD138\u00B7\uC11C\uC2DD"
$menuBtnKo  = U "\uC804\uCCB4 \uC2E4\uBB34\uB3C4\uAD6C"

foreach ($mod in @("swriter", "scalc", "simpress", "sdraw")) {
    $uiPath = Join-Path $loDir "share\config\soffice.cfg\modules\$mod\ui\notebookbar.ui"
    if (-not (Test-Path $uiPath)) { continue }

    try {
        $uiOrig = "$uiPath.orig"
        if (-not (Test-Path $uiOrig)) {
            Copy-Item -Path $uiPath -Destination $uiOrig -Force
        }

        $doc = New-Object System.Xml.XmlDocument
        $doc.PreserveWhitespace = $true
        $doc.XmlResolver = $null
        $doc.Load($uiOrig)

        $extLbl = $doc.SelectSingleNode("//object[@id='ExtensionLabel']/property[@name='label']")
        if ($null -ne $extLbl) {
            [void]$extLbl.Attributes.RemoveNamedItem("translatable")
            [void]$extLbl.Attributes.RemoveNamedItem("context")
            $extLbl.InnerText = $tabLabelKo
        }

        $extMenuBtn = $doc.SelectSingleNode("//object[@id='Extension-ExtensionButton:Menu Addons']/property[@name='label']")
        if ($null -ne $extMenuBtn) {
            [void]$extMenuBtn.Attributes.RemoveNamedItem("translatable")
            [void]$extMenuBtn.Attributes.RemoveNamedItem("context")
            $extMenuBtn.InnerText = $menuBtnKo
        }

        $addonCmd = $doc.SelectSingleNode("//object[@id='AddonCommand']")
        if ($null -ne $addonCmd) {
            Set-OrAddXmlProp $doc $addonCmd "toolbar-style" "both"
            Set-OrAddXmlProp $doc $addonCmd "show-arrow" "False"
            Set-OrAddXmlProp $doc $addonCmd "icon_size" "3"
        }

        if ($mod -in @("swriter", "scalc")) {
            $homeBox = $doc.SelectSingleNode("//object[@id='Home']")
            $existingHomeAddon = $doc.SelectSingleNode("//object[@id='WelfaregoHomeAddons']")
            if (($null -ne $homeBox) -and ($null -eq $existingHomeAddon)) {
                $childNode = $doc.CreateElement("child")
                $mergeObj = $doc.CreateElement("object")
                $mergeObj.SetAttribute("class", "NotebookBarAddonsToolMergePoint")
                $mergeObj.SetAttribute("id", "WelfaregoHomeAddons")
                Set-OrAddXmlProp $doc $mergeObj "visible" "True"
                Set-OrAddXmlProp $doc $mergeObj "can-focus" "False"
                Set-OrAddXmlProp $doc $mergeObj "valign" "center"
                Set-OrAddXmlProp $doc $mergeObj "vexpand" "True"
                Set-OrAddXmlProp $doc $mergeObj "toolbar-style" "both"
                Set-OrAddXmlProp $doc $mergeObj "show-arrow" "False"
                Set-OrAddXmlProp $doc $mergeObj "icon_size" "3"
                [void]$childNode.AppendChild($mergeObj)

                $packNode = $doc.CreateElement("packing")
                $pExp = $doc.CreateElement("property")
                $pExp.SetAttribute("name", "expand")
                $pExp.InnerText = "False"
                $pFill = $doc.CreateElement("property")
                $pFill.SetAttribute("name", "fill")
                $pFill.InnerText = "True"
                [void]$packNode.AppendChild($pExp)
                [void]$packNode.AppendChild($pFill)
                [void]$childNode.AppendChild($packNode)

                [void]$homeBox.AppendChild($childNode)
            }
        }

        $sw = New-Object System.IO.StreamWriter($uiPath, $false, $utf8NoBom)
        try {
            $doc.Save($sw)
        } finally {
            $sw.Close()
        }
        Log-Step "Customized notebookbar.ui for $mod."
    } catch {
        Log-Step "WARN: Failed to customize notebookbar.ui for ${mod}: $_"
    }
}

# 8. Replace "LibreOffice" shortcuts with intuitive English "Welfarego Office ..." names
$publicDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
if (-not $publicDesktop) { $publicDesktop = "C:\Users\Public\Desktop" }
$userDesktop = [Environment]::GetFolderPath("Desktop")
$commonPrograms = [Environment]::GetFolderPath("CommonPrograms")
if (-not $commonPrograms) { $commonPrograms = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs" }

foreach ($desk in @($publicDesktop, $userDesktop)) {
    if ($desk -and (Test-Path $desk)) {
        Get-ChildItem -Path $desk -Filter "LibreOffice*.lnk" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    }
}
if ($commonPrograms -and (Test-Path $commonPrograms)) {
    Get-ChildItem -Path $commonPrograms -Filter "LibreOffice*" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

$wsh = New-Object -ComObject WScript.Shell
$wgMenuDir = Join-Path $commonPrograms "Welfarego OFFICE"
Remove-Item -Path $wgMenuDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $wgMenuDir | Out-Null

$shortcutSpecs = @(
    @{ Name = "Welfarego OFFICE"; Exe = "soffice.exe"; Ico = "soffice.ico"; Desc = "Welfarego OFFICE" },
    @{ Name = "Welfarego Office Document"; Exe = "swriter.exe"; Ico = "writer_app.ico"; Desc = "Welfarego Office Document" },
    @{ Name = "Welfarego Office Spreadsheet"; Exe = "scalc.exe"; Ico = "calc_app.ico"; Desc = "Welfarego Office Spreadsheet" },
    @{ Name = "Welfarego Office Presentation"; Exe = "simpress.exe"; Ico = "impress_app.ico"; Desc = "Welfarego Office Presentation" },
    @{ Name = "Welfarego Office Draw"; Exe = "sdraw.exe"; Ico = "draw_app.ico"; Desc = "Welfarego Office Draw" }
)

foreach ($sp in $shortcutSpecs) {
    $lnkPath = Join-Path $wgMenuDir ($sp.Name + ".lnk")
    $sc = $wsh.CreateShortcut($lnkPath)
    $sc.TargetPath = Join-Path $loDir ("program\" + $sp.Exe)
    $sc.WorkingDirectory = Join-Path $loDir "program"
    $sc.IconLocation = (Join-Path $brandIconsDest $sp.Ico) + ",0"
    $sc.Description = $sp.Desc
    $sc.Save()
}

if ($CreateDesktopShortcut -eq "1" -and $publicDesktop) {
    New-Item -ItemType Directory -Force -Path $publicDesktop | Out-Null
    $deskLnk = Join-Path $publicDesktop "Welfarego OFFICE.lnk"
    $sc = $wsh.CreateShortcut($deskLnk)
    $sc.TargetPath = Join-Path $loDir "program\soffice.exe"
    $sc.WorkingDirectory = Join-Path $loDir "program"
    $sc.IconLocation = (Join-Path $brandIconsDest "soffice.ico") + ",0"
    $sc.Description = "Welfarego OFFICE"
    $sc.Save()
    Log-Step "Created Desktop shortcut: $deskLnk"
}

# 9. Hide inner LibreOffice MSI from Control Panel (appwiz.cpl) & Settings (SystemComponent = 1)
#    so ONLY Inno Setup's "Welfarego OFFICE" entry is visible in Control Panel and Installed Apps!
$uninstRoots = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($root in $uninstRoots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem -Path $root -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            if ($_.PSChildName -notlike "*8F3D2A1C*") {
                $p = Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue
                if ($null -ne $p -and ($p.DisplayName -like "LibreOffice*" -or ($p.WindowsInstaller -eq 1 -and $p.DisplayName -like "Welfarego OFFICE*"))) {
                    New-ItemProperty -Path $_.PSPath -Name "SystemComponent" -Value 1 -PropertyType DWord -Force | Out-Null
                }
            }
        } catch {}
    }
}

$msiUserProducts = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Products"
if (Test-Path $msiUserProducts) {
    Get-ChildItem -Path $msiUserProducts -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $ip = Join-Path $_.PSPath "InstallProperties"
            if (Test-Path $ip) {
                $p = Get-ItemProperty -Path $ip -ErrorAction SilentlyContinue
                if ($null -ne $p -and $p.DisplayName -like "LibreOffice*") {
                    New-ItemProperty -Path $ip -Name "SystemComponent" -Value 1 -PropertyType DWord -Force | Out-Null
                }
            }
        } catch {}
    }
}
Log-Step "Hid subordinate MSI entry from Control Panel; Welfarego OFFICE uninstaller active."

# 10. Notify Windows Shell to refresh shortcut & taskbar icons immediately
try {
    Start-Process -FilePath "ie4uinit.exe" -ArgumentList "-show" -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
} catch {}
Log-Step "Completed Welfarego OFFICE post-install configuration."
