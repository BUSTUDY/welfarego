<#
.SYNOPSIS
    Build Welfarego OFFICE Windows x64 MSI installer from LibreOffice 26.2.7.3 source.

.DESCRIPTION
    Orchestrates the full Windows build pipeline:
      1. Verifies/clones LibreOffice core at the pinned tag in branding/brand.json
      2. Applies Welfarego OFFICE patches, original branding graphics, icons, MSI bitmaps, and autogen.input
      3. Runs ./autogen.sh and parallel make inside Cygwin (or WSL2 Ubuntu)
      4. Collects the built Windows .msi installer and generates an MPL-2.0 compliant modified source archive
         plus SHA256SUMS.txt into dist/

.PARAMETER WorkDir
    Directory where LibreOffice core and external tarballs will be placed (use a short ASCII path like C:\lo).

.PARAMETER CygwinRoot
    Path to Cygwin64 root directory (default: C:\cygwin64).

.PARAMETER SkipClone
    Reuse an existing LibreOffice checkout inside WorkDir\core.

.EXAMPLE
    .\scripts\build-windows.ps1 -WorkDir C:\lo
#>

[CmdletBinding()]
param(
    [string]$WorkDir = "C:\lo",
    [string]$CygwinRoot = "C:\cygwin64",
    [switch]$SkipClone
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Brand = Get-Content (Join-Path $RepoRoot "branding\brand.json") -Raw | ConvertFrom-Json
$UpstreamTag = $Brand.upstream_tag
$UpstreamRepo = $Brand.upstream_repo
$Version = $Brand.package_version
$ProductNoSpaces = $Brand.product_name_no_spaces

$CoreDir = Join-Path $WorkDir "core"
$ExtTarDir = Join-Path $WorkDir "ext-tar"
$DistDir = Join-Path $RepoRoot "dist"
$CygBash = Join-Path $CygwinRoot "bin\bash.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building $($Brand.product_name) $Version (Windows x64 MSI)" -ForegroundColor Cyan
Write-Host " Upstream base: $UpstreamTag (MPL-2.0 Subset)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $CygBash)) {
    throw "Cygwin bash not found at $CygBash. Install Cygwin64 with LibreOffice build dependencies first (see README.md)."
}

New-Item -ItemType Directory -Force -Path $WorkDir, $ExtTarDir, $DistDir | Out-Null

# 1. Verify compliance before spending hours compiling
Write-Host "`n[1/5] Running compliance verification..." -ForegroundColor Green
python (Join-Path $RepoRoot "scripts\verify_compliance.py")
if ($LASTEXITCODE -ne 0) { throw "Compliance verification failed." }

# 2. Clone or clean LibreOffice core checkout + Korean translations submodule
# CRITICAL: LibreOffice Windows/Cygwin builds require LF line endings (core.autocrlf=false)
git config --global core.autocrlf false
if (-not $SkipClone -or -not (Test-Path (Join-Path $CoreDir ".git"))) {
    if (Test-Path $CoreDir) {
        Write-Host "`n[2/5] Resetting existing LibreOffice checkout..." -ForegroundColor Green
        git -C $CoreDir config core.autocrlf false
        git -C $CoreDir reset --hard $UpstreamTag
        git -C $CoreDir clean -fdx -e translations
    } else {
        Write-Host "`n[2/5] Shallow-cloning LibreOffice $UpstreamTag (LF line endings)..." -ForegroundColor Green
        git clone -c core.autocrlf=false --depth 1 --branch $UpstreamTag $UpstreamRepo $CoreDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed." }
    }
} else {
    Write-Host "`n[2/5] Reusing existing checkout at $CoreDir (resetting tracked files)..." -ForegroundColor Green
    git -C $CoreDir checkout -- .
}

$TranslationsDir = Join-Path $CoreDir "translations"
if (-not (Test-Path (Join-Path $TranslationsDir "source\ko"))) {
    Write-Host "  Fetching Korean translations ($UpstreamTag, sparse source/ko)..." -ForegroundColor Green
    if (Test-Path $TranslationsDir) { Remove-Item $TranslationsDir -Recurse -Force }
    git clone -c core.autocrlf=false --depth 1 --branch $UpstreamTag --filter=blob:none --sparse https://github.com/LibreOffice/translations.git $TranslationsDir
    if ($LASTEXITCODE -ne 0) { throw "git clone translations failed." }
    git -C $TranslationsDir sparse-checkout set source/ko
    if ($LASTEXITCODE -ne 0) { throw "sparse-checkout source/ko failed." }
}

# 3. Apply Welfarego OFFICE patches, branding assets, and autogen.input
Write-Host "`n[3/5] Applying Welfarego OFFICE patches & branding..." -ForegroundColor Green
$CygCore = (& (Join-Path $CygwinRoot "bin\cygpath.exe") -u $CoreDir).Trim()
$CygBrand = "$CygCore/welfarego-branding"
$CygExtTar = (& (Join-Path $CygwinRoot "bin\cygpath.exe") -u $ExtTarDir).Trim()

python (Join-Path $RepoRoot "scripts\apply_patches.py") `
    --lo-dir $CoreDir `
    --branding-arg $CygBrand `
    --external-tar $CygExtTar `
    --extra-buildid "Welfarego OFFICE $Version (Fluent Ribbon / MPL-2.0)"
if ($LASTEXITCODE -ne 0) { throw "apply_patches.py failed." }

# 4. Run autogen.sh and build MSI inside Cygwin (LF-normalized to avoid CRLF errors in Cygwin bash)
Write-Host "`n[4/5] Running autogen.sh and compiling Windows x64 MSI..." -ForegroundColor Green
$BuildCmd = @(
    "set -euo pipefail",
    "export PATH=`"/usr/local/bin:/usr/bin:`$PATH`"",
    "cd `"$CygCore`"",
    "./autogen.sh",
    "/usr/local/bin/make.exe build"
) -join "`n"
& $CygBash --login -c $BuildCmd
if ($LASTEXITCODE -ne 0) { throw "LibreOffice/Welfarego OFFICE compilation failed." }

# 5. Collect Windows MSI installer + MPL-2.0 source archive + Setup .exe
Write-Host "`n[5/5] Packaging deliverables into $DistDir..." -ForegroundColor Green
$InstallSearchRoot = Join-Path $CoreDir "workdir\installation"
$MsiCandidates = Get-ChildItem -Path $InstallSearchRoot -Filter "*.msi" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "msi[\\/]install[\\/]" } |
    Sort-Object Length -Descending
if (-not $MsiCandidates) {
    $MsiCandidates = Get-ChildItem -Path $InstallSearchRoot -Filter "*.msi" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object Length -Descending
}
if (-not $MsiCandidates) {
    throw "No .msi file found under $InstallSearchRoot."
}

$BestMsi = $MsiCandidates | Select-Object -First 1
$DestMsi = Join-Path $DistDir "${ProductNoSpaces}_${Version}_Win_x86-64.msi"
Copy-Item -Path $BestMsi.FullName -Destination $DestMsi -Force
Write-Host "  MSI ready: $DestMsi ($($BestMsi.Length) bytes, from $($BestMsi.FullName))" -ForegroundColor Yellow

# Generate MPL-2.0 Section 3.2 source disclosure bundle
$SourceZip = Join-Path $DistDir "${ProductNoSpaces}_${Version}_MPL2_Source_Patches.zip"
if (Test-Path $SourceZip) { Remove-Item $SourceZip -Force }
Compress-Archive -Path `
    (Join-Path $RepoRoot "LICENSE"), `
    (Join-Path $RepoRoot "NOTICE"), `
    (Join-Path $RepoRoot "legal"), `
    (Join-Path $RepoRoot "patches"), `
    (Join-Path $RepoRoot "config"), `
    (Join-Path $RepoRoot "installer"), `
    (Join-Path $RepoRoot "extensions"), `
    (Join-Path $RepoRoot "branding\brand.json"), `
    (Join-Path $RepoRoot "scripts") `
    -DestinationPath $SourceZip

# Wrap compiled MSI into one-click Windows Setup .exe (Inno Setup 6)
& (Join-Path $PSScriptRoot "build-exe.ps1") -MsiPath $DestMsi
if ($LASTEXITCODE -ne 0) { throw "Setup .exe packaging failed." }

Write-Host "`n[DONE] Build complete! Deliverables in: $DistDir" -ForegroundColor Cyan
Get-ChildItem $DistDir | Format-Table Name, Length
