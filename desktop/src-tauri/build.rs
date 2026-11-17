fn main() {
    // 허브 화면(127.0.0.1:7700)이 부를 수 있는 앱 기능 목록 → capabilities/default.json 에서 허용
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&["browser_show", "browser_hide", "browser_go", "browser_url", "browser_eval"]),
    ))
    .expect("빌드 설정 실패");
}
