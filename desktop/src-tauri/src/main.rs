// AI 학교 허브 데스크톱 껍데기: 이 PC의 Node로 허브 서버를 켜고, 창과 내장 브라우저만 맡는다.
// MF 허브 껍데기를 수강생용으로 줄인 것. 자동 시작·상주·알림 없음(창을 닫으면 끝난다).
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{LogicalPosition, LogicalSize, Manager, WebviewBuilder, WebviewUrl, WebviewWindowBuilder};

// MF 허브(7700)와 겹치지 않는 포트. 한 PC에서 둘 다 켤 수 있다.
// 점검용: AIHUB_PORT 로 다른 포트를 쓸 수 있다(서버도 같은 값을 읽는다).
fn port() -> u16 { std::env::var("AIHUB_PORT").ok().and_then(|v| v.parse().ok()).unwrap_or(7710) }
fn base_url() -> String { format!("http://127.0.0.1:{}/", port()) }

struct Server(Mutex<Option<Child>>);

fn home() -> PathBuf {
    std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" }).map(PathBuf::from).unwrap_or_default()
}

// 허브 폴더: 맥 ~/AISchoolHub, 윈도우 C:\AISchoolHub. 코드는 그 안의 hub 폴더.
fn hub_home() -> PathBuf {
    if let Some(p) = std::env::var_os("AIHUB_HOME") { return PathBuf::from(p); }
    if cfg!(windows) { PathBuf::from(r"C:\AISchoolHub") } else { home().join("AISchoolHub") }
}
fn find_repo() -> Option<PathBuf> {
    let p = hub_home().join("hub");
    if p.join("app").join("server.mjs").exists() { Some(p) } else { None }
}

// Node 위치: 앱을 Finder·시작 메뉴로 열면 PATH가 짧아서 흔한 설치 자리를 직접 본다.
// 공식 설치 파일·nvm·scoop·volta 자리까지 보고, 없으면 PATH의 node.
fn find_node() -> PathBuf {
    let h = home();
    let env = |k: &str| std::env::var_os(k).map(PathBuf::from);
    let mut c: Vec<PathBuf> = Vec::new();
    if cfg!(windows) {
        c.push(PathBuf::from(r"C:\Program Files\nodejs\node.exe"));
        if let Some(p) = env("NVM_SYMLINK") { c.push(p.join("node.exe")); }
        if let Some(p) = env("LOCALAPPDATA") { c.push(p.join(r"Programs\nodejs\node.exe")); c.push(p.join(r"Volta\bin\node.exe")); }
        c.push(h.join(r"AppData\Local\Programs\nodejs\node.exe"));
        c.push(PathBuf::from(r"C:\Program Files (x86)\nodejs\node.exe"));
        c.push(PathBuf::from(r"C:\Program Files\Volta\node.exe"));
        c.push(h.join(r"scoop\apps\nodejs-lts\current\node.exe"));
        c.push(h.join(r"scoop\apps\nodejs\current\node.exe"));
    } else {
        c.push(PathBuf::from("/opt/homebrew/bin/node"));
        c.push(PathBuf::from("/usr/local/bin/node"));
        c.push(h.join(".volta/bin/node"));
        // nvm: 가장 높은 판
        if let Ok(rd) = std::fs::read_dir(h.join(".nvm/versions/node")) {
            let mut v: Vec<PathBuf> = rd.flatten().map(|e| e.path().join("bin/node")).filter(|p| p.exists()).collect();
            v.sort_by_key(|p| p.parent().and_then(|b| b.parent()).and_then(|d| d.file_name()).map(|n| n.to_string_lossy().trim_start_matches('v').split('.').map(|x| x.parse::<u32>().unwrap_or(0)).collect::<Vec<_>>()).unwrap_or_default());
            if let Some(p) = v.pop() { c.push(p); }
        }
        c.push(PathBuf::from("/opt/local/bin/node"));
    }
    c.into_iter().find(|p| p.exists()).unwrap_or_else(|| PathBuf::from("node"))
}

fn up() -> bool { TcpStream::connect_timeout(&([127, 0, 0, 1], port()).into(), Duration::from_millis(300)).is_ok() }

// 서버를 켠다(기다리지 않음). 이미 켜져 있거나 허브 폴더가 없으면 None.
// 껍데기 판·위치를 넘겨서, 허브 업데이트가 껍데기도 새로 깔아야 하는지 알 수 있게 한다.
fn spawn_server(ver: &str) -> Option<Child> {
    if up() { return None; }
    let repo = find_repo()?;
    let mut cmd = Command::new(find_node());
    cmd.arg(repo.join("app").join("server.mjs")).current_dir(&repo).env("AIHUB_HOME", hub_home()).env("AIHUB_SHELL_VERSION", ver);
    if let Ok(exe) = std::env::current_exe() { cmd.env("AIHUB_SHELL_PATH", exe); }
    if !cfg!(windows) {
        // 맥: Codex·Claude·git을 찾을 수 있게 흔한 경로를 붙인다
        let path = std::env::var("PATH").unwrap_or_default();
        cmd.env("PATH", format!("/opt/homebrew/bin:/usr/local/bin:{}/.local/bin:{}", home().display(), path));
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // 검은 콘솔 창 없이
    }
    // 서버 기록을 허브 폴더 hub.log 에 남긴다(오류 원인 확인용)
    let hub_home = hub_home();
    let _ = std::fs::create_dir_all(&hub_home);
    if let Ok(f) = std::fs::OpenOptions::new().create(true).append(true).open(hub_home.join("hub.log")) {
        if let Ok(f2) = f.try_clone() { cmd.stdout(f).stderr(f2); }
    }
    cmd.spawn().ok()
}

fn hub_url() -> String { format!("{}{}", base_url(), std::env::var("AIHUB_START_PATH").unwrap_or_default()) } // 점검용: 특정 화면으로 바로 열기

// 감시: 2초마다 서버를 본다. 꺼져 있으면 다시 켜고, 다시 뜨면 창을 허브 화면으로 옮긴다.
// (예전에는 처음 20초만 기다리고 끝이라, 늦게 뜨거나 중간에 꺼지면 창에 '연결 거부'가 남았다)
fn watch(app: tauri::AppHandle, ver: String, mut was_up: bool) {
    let mut down = 0u32;
    loop {
        std::thread::sleep(Duration::from_secs(2));
        if up() {
            if !was_up { if let (Some(w), Ok(u)) = (app.get_webview_window("main"), hub_url().parse()) { let _ = w.navigate(u); } }
            was_up = true; down = 0; continue;
        }
        was_up = false; down += 1;
        // 업데이트로 서버가 스스로 다시 켜지는 중일 수 있어 4초 기다린 뒤 켜고, 그래도 안 뜨면 30초마다 다시 시도
        if down == 2 || down % 15 == 0 {
            let st = app.state::<Server>();
            let mut g = st.0.lock().unwrap();
            let alive = g.as_mut().map(|c| matches!(c.try_wait(), Ok(None))).unwrap_or(false);
            if !alive { if let Some(c) = spawn_server(&ver) { *g = Some(c); } }
        }
    }
}

fn show(app: &tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") { let _ = w.show(); let _ = w.unminimize(); let _ = w.set_focus(); }
}

// ── 내장 브라우저: 오른쪽 미리보기 자리에 별도 웹 화면(자식 웹뷰)을 띄운다. iframe이 막힌 사이트도 보인다.
// 허브 화면이 미리보기 자리의 위치·크기를 알려 주면 그 위에 겹쳐 그린다. (Tauri unstable 기능 — 버전 고정)
#[tauri::command]
async fn browser_show(app: tauri::AppHandle, url: String, x: f64, y: f64, w: f64, h: f64) -> Result<String, String> {
    let win = app.get_window("main").ok_or("창 없음")?;
    let pos = LogicalPosition::new(x, y);
    let size = LogicalSize::new(w.max(50.0), h.max(50.0));
    if let Some(v) = app.get_webview("preview") {
        let _ = v.set_position(pos); let _ = v.set_size(size); let _ = v.show();
        if !url.is_empty() && v.url().map(|u| u.as_str() != url).unwrap_or(true) { v.navigate(url.parse().map_err(|e| format!("{e}"))?).map_err(|e| e.to_string())?; }
        return Ok(v.url().map(|u| u.to_string()).unwrap_or_default());
    }
    let mut data = home(); data.push(if cfg!(windows) { r"AppData\Local\AISchoolHub-browser" } else { "Library/Application Support/AISchoolHub-browser" });
    let b = WebviewBuilder::new("preview", WebviewUrl::External(url.parse().map_err(|e| format!("{e}"))?)).data_directory(data);
    win.add_child(b, pos, size).map_err(|e| e.to_string())?;
    Ok(url)
}
#[tauri::command]
async fn browser_hide(app: tauri::AppHandle) { if let Some(v) = app.get_webview("preview") { let _ = v.hide(); } }
#[tauri::command]
async fn browser_go(app: tauri::AppHandle, action: String) -> Result<String, String> {
    let v = app.get_webview("preview").ok_or("미리보기 없음")?;
    match action.as_str() {
        "back" => v.eval("history.back()").map_err(|e| e.to_string())?,
        "forward" => v.eval("history.forward()").map_err(|e| e.to_string())?,
        "reload" => v.reload().map_err(|e| e.to_string())?,
        _ => {}
    }
    Ok(v.url().map(|u| u.to_string()).unwrap_or_default())
}
#[tauri::command]
async fn browser_url(app: tauri::AppHandle) -> String { app.get_webview("preview").and_then(|v| v.url().ok()).map(|u| u.to_string()).unwrap_or_default() }
#[tauri::command]
async fn browser_eval(app: tauri::AppHandle, js: String) -> Result<(), String> { app.get_webview("preview").ok_or("미리보기 없음")?.eval(&js).map_err(|e| e.to_string()) }

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![browser_show, browser_hide, browser_go, browser_url, browser_eval])
        .setup(|app| {
            let ver = app.package_info().version.to_string();
            let child = spawn_server(&ver);
            app.manage(Server(Mutex::new(child)));

            // 3초 안에 뜨면 허브 화면을 바로, 아니면 '켜는 중' 화면을 먼저 열고 감시가 넘겨 준다
            let t = Instant::now();
            while !up() && t.elapsed() < Duration::from_secs(3) { std::thread::sleep(Duration::from_millis(150)); }
            let ready = up();
            let first = if ready { WebviewUrl::External(hub_url().parse().unwrap()) } else { WebviewUrl::App("index.html".into()) };
            WebviewWindowBuilder::new(app, "main", first)
                .title("AI 학교 허브")
                .inner_size(1360.0, 860.0)
                .min_inner_size(380.0, 600.0)
                .build()?;

            let h = app.handle().clone();
            std::thread::spawn(move || watch(h, ver, ready));
            Ok(())
        })
        // 창을 닫으면 앱도 끝난다(상주하지 않음)
        .build(tauri::generate_context!())
        .expect("AI 학교 허브를 시작하지 못했어요")
        .run(|app, e| {
            if let tauri::RunEvent::Exit = e {
                if let Some(mut c) = app.state::<Server>().0.lock().unwrap().take() { let _ = c.kill(); }
            }
            #[cfg(target_os = "macos")]
            if let tauri::RunEvent::Reopen { .. } = e { show(app); }
        });
}
