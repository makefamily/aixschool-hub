# AI School Hub one-line installer for Windows: downloads the latest release bundle and runs install-windows.ps1.
# ASCII only so it works both with 'irm | iex' and when run as a file on PowerShell 5.
# Creates no auto-start or scheduled tasks. Uses only the user's own accounts and keys.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Repo = if ($env:AIHUB_REPO) { $env:AIHUB_REPO } else { 'makefamily/aixschool-hub' }
$Url = if ($env:AIHUB_ZIP_URL) { $env:AIHUB_ZIP_URL } else { "https://github.com/$Repo/releases/latest/download/AISchoolHub-windows.zip" }
$Tmp = Join-Path $env:TEMP ("aischoolhub-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $Tmp | Out-Null
try {
  Write-Output '[AI School Hub] Downloading the latest bundle...'
  $ProgressPreference = 'SilentlyContinue'
  Invoke-WebRequest $Url -OutFile "$Tmp\hub.zip" -UseBasicParsing
  Expand-Archive "$Tmp\hub.zip" "$Tmp\x" -Force
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$Tmp\x\AISchoolHub-install\install-windows.ps1"
} finally {
  Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
