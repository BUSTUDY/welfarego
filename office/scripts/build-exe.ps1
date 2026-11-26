<#
.SYNOPSIS
    Package a compiled Welfarego OFFICE Windows x64 MSI into a single-click Setup .exe using Inno Setup 6.

.PARAMETER MsiPath
    Path to the compiled WelfaregoOFFICE_*.msi file (defaults to newest .msi in dist/).

.PARAMETER DryRun
    If set, builds a smoke-test .exe without requiring a full compiled MSI (for CI syntax/packaging verification).

.EXAMPLE
    .\scripts\build-exe.ps1
    .\scripts\build-exe.ps1 -MsiPath dist\WelfaregoOFFICE_26.2.7.3_Win_x86-64.msi
#>

[CmdletBinding()]
param(
    [string]$MsiPath = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Brand = Get-Content (Join-Path $RepoRoot "branding\brand.json") -Raw | ConvertFrom-Json
$Version = $Brand.package_version
$DistDir = Join-Path $RepoRoot "dist"
$IssFile = Join-Path $RepoRoot "installer\WelfaregoOFFICE.iss"

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

# Locate Inno Setup 6 compiler (ISCC.exe)
$IsccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $Iscc = $cmd.Source }
}

if (-not $Iscc) {
    Write-Host "Inno Setup 6 not found. Installing via Chocolatey..." -ForegroundColor Yellow
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install innosetup -y --no-progress
        $Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
}

if (-not $Iscc) {
    throw "Inno Setup 6 (ISCC.exe) not found. Please install Inno Setup 6 from https://jrsoftware.org/isinfo.php"
}

Write-Host "Using Inno Setup compiler: $Iscc" -ForegroundColor Cyan

$DryFlag = "0"
if ($DryRun) {
    $DryFlag = "1"
    $MsiPath = Join-Path $DistDir "_smoke_placeholder.msi"
    Set-Content -Path $MsiPath -Value "Welfarego OFFICE Inno Setup smoke test placeholder" -Encoding ASCII
} else {
    if (-not $MsiPath) {
        $Found = Get-ChildItem -Path $DistDir -Filter "*.msi" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $Found) {
            throw "No .msi file found in $DistDir. Run scripts\build-windows.ps1 first or pass -MsiPath."
        }
        $MsiPath = $Found.FullName
    }
    $MsiPath = (Resolve-Path $MsiPath).Path
}

Write-Host "Packaging .exe installer from MSI: $MsiPath" -ForegroundColor Green

# Ensure Korean.isl has UTF-8 BOM so Inno Setup 6 detects UTF-8 Korean characters accurately
$KoreanIsl = Join-Path $RepoRoot "installer\Korean.isl"
$IslText = Get-Content -Path $KoreanIsl -Raw -Encoding UTF8
[System.IO.File]::WriteAllText($KoreanIsl, $IslText, (New-Object System.Text.UTF8Encoding($true)))

# Ensure INSTALLER-LICENSE-KO.txt has UTF-8 BOM + CRLF for Windows RichEdit display
$LicKo = Join-Path $RepoRoot "legal\INSTALLER-LICENSE-KO.txt"
$LicText = (Get-Content -Path $LicKo -Raw -Encoding UTF8) -replace "`r?`n", "`r`n"
[System.IO.File]::WriteAllText($LicKo, $LicText, (New-Object System.Text.UTF8Encoding($true)))

& $Iscc `
    "/DAppVersion=$Version" `
    "/DMsiFile=$MsiPath" `
    "/DOutputDirPath=$DistDir" `
    "/DDryRun=$DryFlag" `
    $IssFile

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE"
}

if ($DryRun -and (Test-Path $MsiPath)) {
    Remove-Item $MsiPath -Force
}

$ExpectedExe = Join-Path $DistDir "WelfaregoOFFICE_${Version}_Setup_x64.exe"
if (-not (Test-Path $ExpectedExe)) {
    throw "Expected Setup .exe was not generated at $ExpectedExe"
}

# Refresh SHA256SUMS.txt
$Checksums = Get-ChildItem -Path $DistDir -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" } | ForEach-Object {
    $hash = (Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash.ToLower()
    "$hash  $($_.Name)"
}
Set-Content -Path (Join-Path $DistDir "SHA256SUMS.txt") -Value $Checksums -Encoding UTF8

Write-Host "`n[OK] Windows Setup .exe generated: $ExpectedExe" -ForegroundColor Green
Get-Item $ExpectedExe | Format-Table Name, Length
