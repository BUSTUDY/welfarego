$ErrorActionPreference = "SilentlyContinue"

# 1. Stop any running Welfarego Office processes
Start-Process -FilePath "taskkill.exe" -ArgumentList "/F /IM soffice.bin /IM soffice.exe /T" -WindowStyle Hidden -Wait | Out-Null

# 2. Uninstall underlying LibreOffice MSI silently by ProductCode
$uninstRoots = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($root in $uninstRoots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem -Path $root | ForEach-Object {
        $p = Get-ItemProperty -Path $_.PSPath
        if ($null -ne $p -and ($p.DisplayName -like "LibreOffice*" -or $p.Comments -like "*LibreOffice*") -and $_.PSChildName -match "^\{[0-9A-Fa-f\-]+\}$") {
            $guid = $_.PSChildName
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/x $guid /qn /norestart" -WindowStyle Hidden -Wait | Out-Null
        }
    }
}

# 3. Remove Welfarego OFFICE Desktop & Start Menu shortcuts
$publicDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
if (-not $publicDesktop) { $publicDesktop = "C:\Users\Public\Desktop" }
$userDesktop = [Environment]::GetFolderPath("Desktop")
$commonPrograms = [Environment]::GetFolderPath("CommonPrograms")
if (-not $commonPrograms) { $commonPrograms = "C:\ProgramData\Microsoft\Windows\Start Menu\Programs" }

foreach ($desk in @($publicDesktop, $userDesktop)) {
    if ($desk -and (Test-Path $desk)) {
        Remove-Item -Path (Join-Path $desk "Welfarego OFFICE.lnk") -Force
        Get-ChildItem -Path $desk -Filter "LibreOffice*.lnk" | Remove-Item -Force
    }
}
if ($commonPrograms -and (Test-Path $commonPrograms)) {
    Remove-Item -Path (Join-Path $commonPrograms "Welfarego OFFICE") -Recurse -Force
}
