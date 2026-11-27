param(
    [string]$PayloadDir = $PSScriptRoot,
    [string]$AppVersion = "26.2.8",
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

function Set-CleanLabel([System.Xml.XmlElement]$Obj, [string]$NewText) {
    if ($null -eq $Obj) { return }
    $prop = $Obj.SelectSingleNode("property[@name='label']")
    if ($null -eq $prop) { return }
    if ($prop.HasAttribute("translatable")) { [void]$prop.Attributes.RemoveNamedItem("translatable") }
    if ($prop.HasAttribute("context")) { [void]$prop.Attributes.RemoveNamedItem("context") }
    $prop.InnerText = $NewText
}

function Insert-RibbonTab(
    [xml]$Doc,
    [System.Xml.XmlElement]$TabControl,
    [string]$BeforePageId,
    [string]$TabIdPrefix,
    [string]$TabLabelText,
    [array]$Groups
) {
    # Skip if already inserted
    if ($null -ne $Doc.SelectSingleNode("//object[@id='${TabIdPrefix}Label']")) { return }

    # Build page container: <child><object class="sfxlo-PriorityHBox" id="${TabIdPrefix} Tab">...
    $pageChild = $Doc.CreateElement("child")
    $hbox = $Doc.CreateElement("object")
    $hbox.SetAttribute("class", "sfxlo-PriorityHBox")
    $hbox.SetAttribute("id", "$TabIdPrefix Tab")
    Set-OrAddXmlProp $Doc $hbox "visible" "True"
    Set-OrAddXmlProp $Doc $hbox "can-focus" "False"
    Set-OrAddXmlProp $Doc $hbox "valign" "center"
    Set-OrAddXmlProp $Doc $hbox "vexpand" "True"

    $mergedChild = $Doc.CreateElement("child")
    $merged = $Doc.CreateElement("object")
    $merged.SetAttribute("class", "sfxlo-PriorityMergedHBox")
    $merged.SetAttribute("id", $TabIdPrefix)
    Set-OrAddXmlProp $Doc $merged "visible" "True"
    Set-OrAddXmlProp $Doc $merged "can-focus" "False"
    Set-OrAddXmlProp $Doc $merged "valign" "center"
    Set-OrAddXmlProp $Doc $merged "vexpand" "True"

    $gIdx = 0
    foreach ($grp in $Groups) {
        $optChild = $Doc.CreateElement("child")
        $opt = $Doc.CreateElement("object")
        $opt.SetAttribute("class", "VclOptionalBox")
        $opt.SetAttribute("id", "${TabIdPrefix}-Group-$gIdx")
        Set-OrAddXmlProp $Doc $opt "visible" "True"
        Set-OrAddXmlProp $Doc $opt "can-focus" "False"
        Set-OrAddXmlProp $Doc $opt "valign" "center"
        Set-OrAddXmlProp $Doc $opt "vexpand" "True"

        if ($gIdx -gt 0) {
            $sepChild = $Doc.CreateElement("child")
            $sep = $Doc.CreateElement("object")
            $sep.SetAttribute("class", "GtkSeparator")
            $sep.SetAttribute("id", "${TabIdPrefix}-Sep-$gIdx")
            Set-OrAddXmlProp $Doc $sep "visible" "True"
            Set-OrAddXmlProp $Doc $sep "can-focus" "False"
            Set-OrAddXmlProp $Doc $sep "margin-top" "5"
            Set-OrAddXmlProp $Doc $sep "margin-bottom" "5"
            Set-OrAddXmlProp $Doc $sep "orientation" "vertical"
            [void]$sepChild.AppendChild($sep)
            $sepPack = $Doc.CreateElement("packing")
            Set-OrAddXmlProp $Doc $sepPack "expand" "False"
            Set-OrAddXmlProp $Doc $sepPack "fill" "True"
            Set-OrAddXmlProp $Doc $sepPack "padding" "5"
            [void]$sepChild.AppendChild($sepPack)
            [void]$opt.AppendChild($sepChild)
        }

        $tbChild = $Doc.CreateElement("child")
        $tb = $Doc.CreateElement("object")
        $tb.SetAttribute("class", "sfxlo-NotebookbarToolBox")
        $tb.SetAttribute("id", "${TabIdPrefix}-TB-$gIdx")
        Set-OrAddXmlProp $Doc $tb "visible" "True"
        Set-OrAddXmlProp $Doc $tb "can-focus" "True"
        Set-OrAddXmlProp $Doc $tb "valign" "center"
        Set-OrAddXmlProp $Doc $tb "vexpand" "True"
        Set-OrAddXmlProp $Doc $tb "toolbar-style" "both"
        Set-OrAddXmlProp $Doc $tb "show-arrow" "False"
        Set-OrAddXmlProp $Doc $tb "icon_size" "3"

        $bIdx = 0
        foreach ($cmd in $grp) {
            $btnChild = $Doc.CreateElement("child")
            $btn = $Doc.CreateElement("object")
            $btn.SetAttribute("class", "GtkToolButton")
            $btn.SetAttribute("id", "${TabIdPrefix}-Btn-$gIdx-$bIdx")
            Set-OrAddXmlProp $Doc $btn "visible" "True"
            Set-OrAddXmlProp $Doc $btn "action-name" $cmd
            [void]$btnChild.AppendChild($btn)
            $btnPack = $Doc.CreateElement("packing")
            Set-OrAddXmlProp $Doc $btnPack "expand" "False"
            Set-OrAddXmlProp $Doc $btnPack "homogeneous" "False"
            [void]$btnChild.AppendChild($btnPack)
            [void]$tb.AppendChild($btnChild)
            $bIdx++
        }

        [void]$tbChild.AppendChild($tb)
        $tbPack = $Doc.CreateElement("packing")
        Set-OrAddXmlProp $Doc $tbPack "expand" "False"
        Set-OrAddXmlProp $Doc $tbPack "fill" "True"
        [void]$tbChild.AppendChild($tbPack)
        [void]$opt.AppendChild($tbChild)

        [void]$optChild.AppendChild($opt)
        $optPack = $Doc.CreateElement("packing")
        Set-OrAddXmlProp $Doc $optPack "expand" "False"
        Set-OrAddXmlProp $Doc $optPack "fill" "True"
        [void]$optChild.AppendChild($optPack)
        [void]$merged.AppendChild($optChild)
        $gIdx++
    }

    [void]$mergedChild.AppendChild($merged)
    $mPack = $Doc.CreateElement("packing")
    Set-OrAddXmlProp $Doc $mPack "expand" "True"
    Set-OrAddXmlProp $Doc $mPack "fill" "True"
    Set-OrAddXmlProp $Doc $mPack "position" "0"
    [void]$mergedChild.AppendChild($mPack)
    [void]$hbox.AppendChild($mergedChild)
    [void]$pageChild.AppendChild($hbox)

    # Build tab label: <child type="tab"><object class="GtkLabel" id="${TabIdPrefix}Label">...
    $tabChild = $Doc.CreateElement("child")
    $tabChild.SetAttribute("type", "tab")
    $lbl = $Doc.CreateElement("object")
    $lbl.SetAttribute("class", "GtkLabel")
    $lbl.SetAttribute("id", "${TabIdPrefix}Label")
    Set-OrAddXmlProp $Doc $lbl "visible" "True"
    Set-OrAddXmlProp $Doc $lbl "can-focus" "False"
    Set-OrAddXmlProp $Doc $lbl "label" $TabLabelText
    [void]$tabChild.AppendChild($lbl)
    $tPack = $Doc.CreateElement("packing")
    Set-OrAddXmlProp $Doc $tPack "tab-fill" "False"
    [void]$tabChild.AppendChild($tPack)

    # Insert before the target page child
    $refNode = $null
    foreach ($ch in $TabControl.ChildNodes) {
        if ($ch.Name -eq "child" -and -not $ch.HasAttribute("type")) {
            $obj = $ch.SelectSingleNode("object")
            if ($null -ne $obj -and $obj.GetAttribute("id") -eq $BeforePageId) {
                $refNode = $ch
                break
            }
        }
    }

    if ($null -ne $refNode) {
        [void]$TabControl.InsertBefore($pageChild, $refNode)
        [void]$TabControl.InsertBefore($tabChild, $refNode)
    } else {
        [void]$TabControl.AppendChild($pageChild)
        [void]$TabControl.AppendChild($tabChild)
    }
}

function Renumber-TabPositions([xml]$Doc, [System.Xml.XmlElement]$TabControl) {
    $pagePos = 0
    $tabPos = 0
    foreach ($ch in $TabControl.ChildNodes) {
        if ($ch.Name -ne "child") { continue }
        $isTab = ($ch.GetAttribute("type") -eq "tab")
        $pack = $ch.SelectSingleNode("packing")
        if ($null -eq $pack) {
            $pack = $Doc.CreateElement("packing")
            [void]$ch.AppendChild($pack)
        }
        if ($isTab) {
            Set-OrAddXmlProp $Doc $pack "position" ([string]$tabPos)
            $tabPos++
        } else {
            Set-OrAddXmlProp $Doc $pack "position" ([string]$pagePos)
            $pagePos++
        }
    }
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
Log-Step "Starting Welfarego OFFICE $AppVersion post-install configuration in $loDir (Desktop=$CreateDesktopShortcut)"

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

# 4. Deploy zz-welfarego-defaults.xcd (share\registry) & zz-welfarego-ko-labels.xcd (share\registry\res)
$regDir = Join-Path $loDir "share\registry"
$regResDir = Join-Path $regDir "res"
foreach ($obsolete in @(
    (Join-Path $regDir "welfarego-defaults.xcd"),
    (Join-Path $regResDir "zz-welfarego-defaults.xcd")
)) {
    if (Test-Path $obsolete) { Remove-Item -Path $obsolete -Force -ErrorAction SilentlyContinue }
}
Copy-Item -Path (Join-Path $PayloadDir "welfarego-defaults.xcd") -Destination (Join-Path $regDir "zz-welfarego-defaults.xcd") -Force
if ((Test-Path $regResDir) -and (Test-Path (Join-Path $PayloadDir "welfarego-ko-labels.xcd"))) {
    Copy-Item -Path (Join-Path $PayloadDir "welfarego-ko-labels.xcd") -Destination (Join-Path $regResDir "zz-welfarego-ko-labels.xcd") -Force
}
Log-Step "Deployed zz-welfarego-defaults.xcd and res/zz-welfarego-ko-labels.xcd."

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

# Unlock & reset stale .lock / cached extension state across local user profiles
$usersRoot = Split-Path -Parent $env:PUBLIC
if (-not $usersRoot -or -not (Test-Path $usersRoot)) { $usersRoot = "C:\Users" }
Get-ChildItem -Path $usersRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    foreach ($sub in @("AppData\Roaming\WelfaregoOffice", "AppData\Roaming\WelfaregoOFFICE", "AppData\Roaming\LibreOffice")) {
        $profRoot = Join-Path $_.FullName $sub
        if (Test-Path $profRoot) {
            $lockFile = Join-Path $profRoot "4\.lock"
            if (Test-Path $lockFile) { Remove-Item -Path $lockFile -Force -ErrorAction SilentlyContinue }
            $extCache = Join-Path $profRoot "4\user\extensions"
            if (Test-Path $extCache) { Remove-Item -Path $extCache -Recurse -Force -ErrorAction SilentlyContinue }
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

# 7. Customize Start Center UI (startcenter.ui) with crisp Korean labels
$scUiPath = Join-Path $loDir "share\config\soffice.cfg\sfx\ui\startcenter.ui"
if (Test-Path $scUiPath) {
    try {
        $scOrig = "$scUiPath.orig"
        if (-not (Test-Path $scOrig)) { Copy-Item -Path $scUiPath -Destination $scOrig -Force }
        $scDoc = New-Object System.Xml.XmlDocument
        $scDoc.PreserveWhitespace = $true
        $scDoc.XmlResolver = $null
        $scDoc.Load($scOrig)

        $scMap = @{
            "writer_all"        = (U "\uBB38\uC11C \uC791\uC131 (Document)")
            "calc_all"          = (U "\uC2A4\uD504\uB808\uB4DC\uC2DC\uD2B8 (Spreadsheet)")
            "impress_all"       = (U "\uD504\uB808\uC820\uD14C\uC774\uC158 (Presentation)")
            "draw_all"          = (U "\uB4DC\uB85C\uC789\u00B7PDF (Draw)")
            "math_all"          = (U "\uC218\uC2DD \uD3B8\uC9D1 (Math)")
            "database_all"      = (U "\uB370\uC774\uD130\uBCA0\uC774\uC2A4 (Base)")
            "clear_unavailable" = (U "\uC5C6\uB294 \uD30C\uC77C \uBAA9\uB85D \uC9C0\uC6B0\uAE30")
            "mbActions"         = (U "\uC791\uC5C5")
        }
        foreach ($kv in $scMap.GetEnumerator()) {
            $node = $scDoc.SelectSingleNode("//object[@id='$($kv.Key)']")
            Set-CleanLabel $node $kv.Value
        }
        $sw = New-Object System.IO.StreamWriter($scUiPath, $false, $utf8NoBom)
        try { $scDoc.Save($sw) } finally { $sw.Close() }
        Log-Step "Customized Start Center labels in startcenter.ui."
    } catch {
        Log-Step "WARN: Failed to customize startcenter.ui: $_"
    }
}

# 8. Customize Ribbon UI (notebookbar.ui) across all 4 apps:
#    - 100% Korean tab & menu labels (eliminates Insert/Layout/Field/Tools/Form/Master/3d English leftovers)
#    - Word/Excel/PowerPoint-familiar tabs (Design, Formulas, Transitions, Animations)
#    - Welfarego Practical Shortcuts on Home tab & [★ 실무포털·서식] tab
$koFile        = U "\uD30C\uC77C"
$koHome        = U "\uD648"
$koInsert      = U "\uC0BD\uC785"
$koDesign      = U "\uB514\uC790\uC778"
$koLayout      = U "\uB808\uC774\uC544\uC6C3"
$koPageLayout  = U "\uD398\uC774\uC9C0 \uB808\uC774\uC544\uC6C3"
$koFormulas    = U "\uC218\uC2DD"
$koData        = U "\uB370\uC774\uD130"
$koRefs        = U "\uCC38\uC870"
$koTransitions = U "\uD654\uBA74 \uC804\uD658"
$koAnimations  = U "\uC560\uB2C8\uBA54\uC774\uC158"
$koSlideShow   = U "\uC2AC\uB77C\uC774\uB4DC \uC1FC"
$koReview      = U "\uAC80\uD1A0"
$koView        = U "\uBCF4\uAE30"
$koTable       = U "\uD45C"
$koImage       = U "\uADF8\uB9BC"
$koDraw        = U "\uADF8\uB9AC\uAE30"
$koObject      = U "\uAC1C\uCCB4"
$koMedia       = U "\uBBF8\uB514\uC5B4"
$koPrint       = U "\uC778\uC1C4"
$koForm        = U "\uC591\uC2DD"
$koMaster      = U "\uB9C8\uC2A4\uD130"
$koOutline     = U "\uAC1C\uC694"
$koText        = U "\uD14D\uC2A4\uD2B8"
$koPage        = U "\uD398\uC774\uC9C0"
$ko3D          = U "3D \uAC1C\uCCB4"
$koTools       = U "\uB3C4\uAD6C"
$koHelp        = U "\uB3C4\uC6C0\uB9D0"
$koField       = U "\uD544\uB4DC"
$koStats       = U "\uD1B5\uACC4"
$koConvert     = U "\uBCC0\uD658"
$koPortalTab   = U "\u2605 \uC2E4\uBB34\uD3EC\uD138\u00B7\uC11C\uC2DD"
$koPortalMenu  = U "\uC804\uCCB4 \uC2E4\uBB34\uB3C4\uAD6C"

$commonTabLabels = @{
    "FileLabel"       = $koFile
    "HomeLabel"       = $koHome
    "InsertLabel"     = $koInsert
    "LayoutLabel"     = $koLayout
    "PageLabel"       = $koPage
    "ReferencesLabel" = $koRefs
    "DataLabel"       = $koData
    "SlideShowLabel"  = $koSlideShow
    "ReviewLabel"     = $koReview
    "ViewLabel"       = $koView
    "TableLabel"      = $koTable
    "ImageLabel"      = $koImage
    "DrawLabel"       = $koDraw
    "ObjectLabel"     = $koObject
    "MediaLabel"      = $koMedia
    "PrintLabel"      = $koPrint
    "FormLabel"       = $koForm
    "MasterLabel"     = $koMaster
    "OutlineLabel"    = $koOutline
    "TextLabel"       = $koText
    "3DObjectLabel"   = $ko3D
    "ExtensionLabel"  = $koPortalTab
    "ToolsLabel"      = $koTools
    "DevLabel"        = $koTools
}

$menuBtnTextMap = @{
    "_File"       = $koFile
    "_Help"       = $koHelp
    "_Home"       = $koHome
    "_Insert"     = $koInsert
    "Fiel_d"      = $koField
    "_Layout"     = $koLayout
    "_Slide Show" = $koSlideShow
    "_Review"     = $koReview
    "_View"       = $koView
    "_Table"      = $koTable
    "Ima_ge"      = $koImage
    "_Draw"       = $koDraw
    "_Object"     = $koObject
    "_Media"      = $koMedia
    "_Print"      = $koPrint
    "Fo_rm"       = $koForm
    "_Master"     = $koMaster
    "3_d"         = $ko3D
    "Convert"     = $koConvert
    "_Statistics" = $koStats
    "_Data"       = $koData
    "_Tools"      = $koTools
    "T_ext"       = $koText
    "E_xtension"  = $koPortalMenu
    "Reference_s" = $koRefs
}

foreach ($mod in @("swriter", "scalc", "simpress", "sdraw")) {
    $uiPath = Join-Path $loDir "share\config\soffice.cfg\modules\$mod\ui\notebookbar.ui"
    if (-not (Test-Path $uiPath)) { continue }

    try {
        $uiOrig = "$uiPath.orig"
        if (-not (Test-Path $uiOrig)) { Copy-Item -Path $uiPath -Destination $uiOrig -Force }

        $doc = New-Object System.Xml.XmlDocument
        $doc.PreserveWhitespace = $true
        $doc.XmlResolver = $null
        $doc.Load($uiOrig)

        # (a) Translate ALL tab labels to crisp Korean
        foreach ($kv in $commonTabLabels.GetEnumerator()) {
            $lblObj = $doc.SelectSingleNode("//object[@id='$($kv.Key)']")
            if ($null -ne $lblObj) {
                $txt = $kv.Value
                if ($mod -eq "scalc" -and $kv.Key -eq "LayoutLabel") { $txt = $koPageLayout }
                if ($mod -eq "simpress" -and $kv.Key -eq "LayoutLabel") { $txt = $koDesign }
                Set-CleanLabel $lblObj $txt
            }
        }

        # (b) Translate ALL right-side dropdown menu buttons (svtlo-ManagedMenuButton) to Korean
        foreach ($mb in $doc.SelectNodes("//object[@class='svtlo-ManagedMenuButton']")) {
            $pLbl = $mb.SelectSingleNode("property[@name='label']")
            if ($null -ne $pLbl -and $menuBtnTextMap.ContainsKey($pLbl.InnerText)) {
                $txt = $menuBtnTextMap[$pLbl.InnerText]
                if ($mod -eq "simpress" -and $pLbl.InnerText -eq "_Layout") { $txt = $koDesign }
                if ($mod -eq "scalc" -and $pLbl.InnerText -eq "_Layout") { $txt = $koPageLayout }
                Set-CleanLabel $mb $txt
            }
        }

        # (c) Enrich Ribbon with familiar Word / Excel / PowerPoint tabs
        $tabCtrl = $doc.SelectSingleNode("//object[@class='sfxlo-NotebookbarTabControl']")
        if ($null -ne $tabCtrl) {
            if ($mod -eq "swriter") {
                # Word-style [디자인] tab between [삽입] and [레이아웃]
                $designGroups = @(
                    @(".uno:ThemeDialog", ".uno:DesignerDialog", ".uno:ChangeTheme"),
                    @(".uno:Watermark", ".uno:PageDialog", ".uno:BorderDialog", ".uno:BackgroundColor"),
                    @(".uno:InsertPageHeader", ".uno:InsertPageFooter", ".uno:PageNumberWizard", ".uno:TitlePageDialog")
                )
                Insert-RibbonTab $doc $tabCtrl "Layout Tab" "WelfaregoDesign" $koDesign $designGroups
                Renumber-TabPositions $doc $tabCtrl
            }
            elseif ($mod -eq "scalc") {
                # Excel-style [수식] tab between [페이지 레이아웃] and [데이터]
                $formulaGroups = @(
                    @(".uno:FunctionDialog", ".uno:InputLineVisible", ".uno:ToggleFormula"),
                    @(".uno:DefineName", ".uno:AddName", ".uno:InsertName"),
                    @(".uno:ShowPrecedents", ".uno:ShowDependents", ".uno:ClearArrows", ".uno:AuditingFillMode"),
                    @(".uno:Calculate", ".uno:CalculateHard", ".uno:AutomaticCalculation")
                )
                Insert-RibbonTab $doc $tabCtrl "Data Tab" "WelfaregoFormulas" $koFormulas $formulaGroups
                Renumber-TabPositions $doc $tabCtrl
            }
            elseif ($mod -eq "simpress") {
                # PowerPoint-style [화면 전환] & [애니메이션] tabs between [디자인] and [슬라이드 쇼]
                $transGroups = @(
                    @(".uno:SlideChangeWindow", ".uno:PresentationCurrentSlide", ".uno:Presentation"),
                    @(".uno:RehearseTimings", ".uno:PresentationDialog", ".uno:DiaMode", ".uno:InsertSlide", ".uno:DuplicateSlide")
                )
                $animGroups = @(
                    @(".uno:CustomAnimation", ".uno:PresentationCurrentSlide", ".uno:Presentation"),
                    @(".uno:DrawText", ".uno:BasicShapes", ".uno:ArrowShapes", ".uno:SymbolShapes", ".uno:InsertGraphic", ".uno:InsertObjectChart")
                )
                Insert-RibbonTab $doc $tabCtrl "Slide Show Tab" "WelfaregoTransitions" $koTransitions $transGroups
                Insert-RibbonTab $doc $tabCtrl "Slide Show Tab" "WelfaregoAnimations" $koAnimations $animGroups
                Renumber-TabPositions $doc $tabCtrl
            }
        }

        # (d) Style AddonCommand (★ 실무포털·서식 tab) and surface shortcuts on Home tab
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
                Set-OrAddXmlProp $doc $packNode "expand" "False"
                Set-OrAddXmlProp $doc $packNode "fill" "True"
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
        Log-Step "Customized Korean full Ribbon notebookbar.ui for $mod."
    } catch {
        Log-Step "WARN: Failed to customize notebookbar.ui for ${mod}: $_"
    }
}

# 9. Replace "LibreOffice" shortcuts with intuitive English "Welfarego Office ..." names
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
    @{ Name = "Welfarego OFFICE"; Exe = "soffice.exe"; Ico = "soffice.ico"; Desc = "Welfarego OFFICE $AppVersion" },
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
    $sc.Description = "Welfarego OFFICE $AppVersion"
    $sc.Save()
    Log-Step "Created Desktop shortcut: $deskLnk"
}

# 10. Hide inner LibreOffice MSI from Control Panel & Settings (SystemComponent = 1)
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
Log-Step "Hid subordinate MSI entry from Control Panel; Welfarego OFFICE $AppVersion uninstaller active."

# 11. Refresh Windows Shell icon cache
try {
    Start-Process -FilePath "ie4uinit.exe" -ArgumentList "-show" -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
} catch {}
Log-Step "Completed Welfarego OFFICE $AppVersion post-install configuration."
