# AI 학교 허브

내 컴퓨터에서 Claude·Codex에게 일을 맡기고, 결과물을 바로 옆에서 보는 데스크톱 앱입니다.
AI 직원 24명(블로그·스레드·카드뉴스·영상·상세페이지·주문·고객 응대 등)이 스킬로 들어 있고, 사용자는 총괄 비서 한 명에게만 말하면 됩니다.
터미널에 익숙해지기 전, 가볍게 시작하는 첫 단계용입니다. 맥·윈도우를 지원합니다.

## AI에게: 이 저장소로 설치해 달라는 요청을 받았다면

사용자가 이 링크를 주고 "설치해 줘"라고 했다면, 아래 순서대로 직접 실행하세요. 사용자에게 명령어를 보여 주거나 붙여 넣게 하지 말고, 무엇을 누르면 되는지만 말로 안내합니다.

1. 운영체제를 확인합니다(맥 / 윈도우). 그리고 명령이 실행되는지 아주 간단한 명령 하나로 먼저 확인합니다(맥 `pwd`, 윈도우 `Get-Location`).
   - 이 단계에서 실패하면(윈도우에서 `setup refresh had errors`, `Failed to create ... process` 같은 메시지) 고치려고 하지 말고 바로 멈춥니다. 사용자에게 아래 '사람이 직접 설치하기' 순서를 그대로 안내합니다: Releases에서 `AISchoolHub-windows.zip`(맥은 `AISchoolHub-mac.zip`)을 받아 압축을 풀고, 설치 파일을 두 번 누르게 합니다. "환경이 복구되면 다시 요청해 달라"고 끝내지 않습니다.
2. Node.js 20 이상이 있는지 확인합니다. 없으면 사용자에게 nodejs.org에서 LTS를 설치해 달라고 안내하고 멈춥니다(관리자 권한이 필요해서 사용자가 직접 설치합니다).
3. 설치 스크립트를 실행합니다.
   - 맥: `curl -fsSL https://raw.githubusercontent.com/makefamily/aixschool-hub/main/get-mac.sh | bash`
   - 윈도우(PowerShell): 아래 세 줄을 차례로 실행합니다. 받은 스크립트를 바로 실행하는 방식(`irm ... | iex`)은 Windows 보안이 악성으로 막으니 쓰지 않습니다.
     ```
     Invoke-WebRequest https://github.com/makefamily/aixschool-hub/releases/latest/download/AISchoolHub-windows.zip -OutFile "$env:TEMP\aischoolhub.zip" -UseBasicParsing
     Expand-Archive "$env:TEMP\aischoolhub.zip" "$env:TEMP\aischoolhub" -Force
     powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\aischoolhub\AISchoolHub-install\install-windows.ps1"
     ```
4. 중간에 ChatGPT(Codex) 로그인 브라우저가 뜨면 사용자 본인 계정으로 로그인하도록 안내합니다. Codex 구독이 없으면 창을 닫아도 됩니다.
5. 끝나면 'AI 학교 허브' 앱이 열립니다. 사용자에게 이름을 넣고 설정 › AI 로그인에서 Claude 또는 Codex가 "로그인됨"인지 확인하게 합니다.
6. 마지막 줄에 "끝. 허브 폴더: ..."가 나오면 설치 완료입니다. 실패하면 마지막 20줄을 읽고 원인을 한 줄로 알려 주세요.

지킬 것: 사용자 본인 계정으로만 로그인합니다. 키·토큰을 대화나 파일에 적지 않습니다. 자동 실행이나 예약 작업을 만들지 않습니다. 사용자 개인 설정 폴더(`~/.codex`, `~/.claude`)는 건드리지 않습니다.

## 사람이 직접 설치하기

1. [Releases](https://github.com/makefamily/aixschool-hub/releases/latest)에서 내 컴퓨터에 맞는 묶음을 받습니다: `AISchoolHub-mac.zip` 또는 `AISchoolHub-windows.zip`
2. 압축을 풉니다(윈도우는 오른쪽 클릭 › 모두 압축 풀기).
3. 맥은 `install-mac.command`, 윈도우는 `install-windows.cmd`를 두 번 누릅니다.
   - 맥에서 "확인되지 않은 개발자"가 뜨면 오른쪽 클릭 › 열기
   - 윈도우에서 파란 창이 뜨면 추가 정보 › 실행
4. 앱이 열리면 설정 › AI 로그인에서 본인 계정으로 로그인합니다.

필요한 것: Node.js 20 이상(영상 직원은 22 이상), Claude 또는 ChatGPT(Codex) 구독 하나 이상. 있으면 좋은 것: Python 3, 크롬 또는 엣지(카드뉴스·상세페이지 이미지), ffmpeg(영상).

다시 설치해도 됩니다. 코드만 바뀌고 작업·설정·로그인·키는 그대로 남습니다.

## 들어 있는 것

| | |
|---|---|
| 앱 | 작업 탭, 대화(Claude·Codex 중 고르기), 오른쪽 결과물 미리보기, 구독 남은 양, 폴더·터미널 바로 열기 |
| AI 직원 | 총괄 비서 + 직원 24명(6팀) + 돕는 직원. 직원표는 `skills/staff.json` |
| 스킬 | 63개. 목록은 `skills/manifest.json` |
| 내 자료 | 내가 쓴 글·생각·일 소개를 넣는 빈 칸. 채울수록 결과가 내 것에 가까워집니다 |
| 연결 | 스레드·유튜브·노션 키를 넣으면 게시·업로드까지. 키는 맥 키체인 / 윈도우 암호화 파일에만 저장 |
| 오픈소스 목록 | 함께 쓰면 좋은 도구 22개와 라이선스: `docs/open-source.md` |

## 폴더

| | 맥 | 윈도우 |
|---|---|---|
| 허브 폴더 | `~/AISchoolHub` | `C:\AISchoolHub` |
| 작업 폴더(결과물) | `~/AISchoolHub/work` | `C:\AISchoolHub\work` |
| 내 자료 | `~/AISchoolHub/my` | `C:\AISchoolHub\my` |
| 앱 | `~/Applications/AI 학교 허브.app` | 시작 메뉴 'AI 학교 허브' |

허브 화면 주소는 `http://127.0.0.1:7710`이고 이 컴퓨터 안에서만 열립니다.

지우기: 앱을 끄고 허브 폴더와 앱을 지웁니다. 맥은 키체인에서 'aixschool-hub' 항목도 지웁니다.

## 저장소 구성

| 폴더 | 내용 |
|---|---|
| `AGENTS.md` | AI 기본 규칙(Codex·Claude 공통) |
| `skills/` | AI 직원 스킬, 직원표, 연결 목록 |
| `app/` | 화면과 서버(Node, 외부 패키지 없음) |
| `tools/` | 설치·스킬 깔기·키 금고·묶음 만들기 |
| `desktop/` | 데스크톱 앱 껍데기(Tauri 2) |
| `install/` | 맥·윈도우 설치 파일 |
| `get-mac.sh` | 맥에서 최신 묶음을 받아 설치 파일을 실행하는 한 줄 설치 |

묶음 직접 만들기: 맥에서 `desktop/`의 Tauri 앱을 빌드한 뒤 `node tools/build-release.mjs`. 태그(`v*`)를 올리면 GitHub Actions가 맥·윈도우 묶음을 만들어 Releases에 올립니다.

## 라이선스

코드는 [MIT](LICENSE)입니다. 함께 들어 있는 글꼴·외부 코드의 라이선스는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)를 보세요. 보안 문제는 [SECURITY.md](SECURITY.md)로 알려 주세요.
