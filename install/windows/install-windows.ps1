# AI 학교 허브 윈도우 설치. 묶음 파일을 푼 폴더에서 install-windows.cmd 를 두 번 눌러 실행한다.
# 하는 일: Node 확인 -> Codex(허브 폴더 안)·Claude 프로그램 확인 -> 허브 폴더(C:\AISchoolHub) 만들기 -> 스킬·규칙 깔기 -> 앱 설치·열기
# 학생 본인 계정으로만 로그인한다. 다른 사람 계정·키는 넣지 않는다. 자동 실행·예약 작업은 만들지 않는다.
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$HubHome = if ($env:AIHUB_HOME) { $env:AIHUB_HOME } else { 'C:\AISchoolHub' }

function Say($m) { Write-Output "[AI 학교 허브] $m" }
function Need($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Say "윈도우 설치 시작 · 허브 폴더 $HubHome"
if (-not (Need node)) {
  Say 'Node가 없어요. nodejs.org 에서 LTS 설치 파일을 받아 설치한 뒤 다시 실행하세요.'
  Start-Process 'https://nodejs.org/ko/download'
  exit 1
}

# 0) 허브 앱이 켜져 있으면 끈다(켜진 채로는 hub 폴더를 바꿀 수 없다)
Get-Process aixschool-hub -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$HubHome\hub\*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 1) 허브 코드: 묶음의 hub 폴더를 그대로 옮긴다(이전 설치가 있으면 코드만 바꾸고 작업·설정은 남긴다)
New-Item -ItemType Directory -Force $HubHome | Out-Null
if (Test-Path "$HubHome\hub.new") { Remove-Item -Recurse -Force "$HubHome\hub.new" }
Copy-Item -Recurse "$Here\hub" "$HubHome\hub.new"
if (Test-Path "$HubHome\hub") { Remove-Item -Recurse -Force "$HubHome\hub" }
Rename-Item "$HubHome\hub.new" 'hub'

# 2) Codex 프로그램: 허브 폴더 안에만 깐다(관리자 권한 없이). 이미 있으면 건너뛴다.
if (-not (Test-Path "$HubHome\cli\node_modules\@openai\codex\bin\codex.js")) {
  Say 'Codex 프로그램 설치 중(허브 폴더 안)...'
  New-Item -ItemType Directory -Force "$HubHome\cli" | Out-Null
  try { & npm install --prefix "$HubHome\cli" --no-audit --no-fund '@openai/codex' | Out-Null } catch { Say 'Codex 설치 실패 - Claude만으로도 허브는 돌아가요' }
}

# 3) Claude 프로그램: 없으면 공식 설치 파일로 설치
$claudeExe = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
if (-not (Need claude) -and -not (Test-Path $claudeExe)) {
  Say 'Claude 프로그램 설치 중(공식 설치 파일)...'
  try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression } catch { Say 'Claude 설치 실패 - Codex만으로도 허브는 돌아가요' }
}

# 4) 허브 폴더·스킬·규칙. Codex 로그인 창이 뜨면 학생 본인 계정으로 로그인한다.
$env:AIHUB_HOME = $HubHome
& node "$HubHome\hub\tools\setup.mjs"

# 5) 앱: 관리자 권한 없이 내 계정에만 조용히 설치 -> 실행
$setup = Get-ChildItem $Here -Filter '*setup*.exe' | Select-Object -First 1
if ($setup) {
  Start-Process $setup.FullName -ArgumentList '/S' -Wait
  $app = Get-ChildItem "$env:LOCALAPPDATA" -Recurse -Filter 'aixschool-hub.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($app) { Start-Process $app.FullName } else { Say '앱 위치를 못 찾았어요. 시작 메뉴에서 AI 학교 허브를 여세요.' }
} else { Say '앱 설치 파일이 묶음에 없어요.' }
Say "끝. 허브 폴더: $HubHome"
Say '앱에서 설정 > AI 로그인으로 Claude 로그인 상태를 확인하세요.'
