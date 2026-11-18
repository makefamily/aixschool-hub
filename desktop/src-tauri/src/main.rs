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
fn find_node() -> PathBuf {
    let h = home();
    let c: Vec<PathBuf> = if cfg!(windows) {
        vec![PathBuf::from(r"C:\Program Files\nodejs\node.exe"), h.join(r"AppData\Local\Programs\nodejs\node.exe")]
    } else {
        vec![PathBuf::from("/opt/homebrew/bin/node"), PathBuf::from("/usr/local/bin/node"), h.join(".volta/bin/node")]
    };
    c.into_iter().find(|p| p.exists()).unwrap_or_else(|| PathBuf::from("node"))
}

fn up() -> bool { TcpStream::connect_timeout(&([127, 0, 0, 1], port()).into(), Duration::from_millis(300)).is_ok() }

fn start_server() -> Option<Child> {
    if up() { return None; } // 이미 켜져 있으면 그대로 쓴다
    let repo = find_repo()?;
    let mut cmd = Command::new(find_node());
    cmd.arg(repo.join("app").join("server.mjs")).current_dir(&repo).env("AIHUB_HOME", hub_home());
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
    let child = cmd.spawn().ok();
    let t = Instant::now();
    while !up() && t.elapsed() < Duration::from_secs(20) { std::thread::sleep(Duration::from_millis(250)); }
    child
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
            let child = start_server();
            app.manage(Server(Mutex::new(child)));

            let start = format!("{}{}", base_url(), std::env::var("AIHUB_START_PATH").unwrap_or_default()); // 점검용: 특정 화면으로 바로 열기
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(start.parse().unwrap()))
                .title("AI 학교 허브")
                .inner_size(1360.0, 860.0)
                .min_inner_size(380.0, 600.0)
                .build()?;

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
