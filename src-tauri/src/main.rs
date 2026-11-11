//! Altyazı İndirici'nin Tauri kabuğu.
//!
//! Altyazı motoru Python ile yazılıdır ve `altyazi-server` adlı yan süreç olarak paketlenir.
//! Kabuk boş bir kapı ve rastgele bir erişim anahtarı seçer, sunucuyu başlatır, hazır olmasını
//! bekler ve arayüzü doğrudan o sunucudan yükleyen pencereyi açar. Pencere kapanınca sunucu da
//! kapatılır; kabuk beklenmedik biçimde ölürse sunucu, girdi borusu kapandığı için kendiliğinden çıkar.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

const TITLE: &str = "Altyazı İndirici";
/// Tek dosyalık Python paketi ilk açılışta kendini açtığı için sunucu birkaç saniye gecikebilir.
const STARTUP_LIMIT: Duration = Duration::from_secs(60);

struct Server(Mutex<Option<CommandChild>>);

fn free_port() -> std::io::Result<u16> {
    Ok(TcpListener::bind(("127.0.0.1", 0))?.local_addr()?.port())
}

/// İşletim sisteminin rastgele tohumladığı özetleyicilerden 128 bitlik erişim anahtarı üretir.
fn access_token() -> String {
    let part = || RandomState::new().build_hasher().finish();
    format!("{:016x}{:016x}", part(), part())
}

fn wait_for_server(port: u16) -> bool {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let started = Instant::now();
    while started.elapsed() < STARTUP_LIMIT {
        if TcpStream::connect_timeout(&address, Duration::from_millis(250)).is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(150));
    }
    false
}

fn stop_server(app: &AppHandle) {
    if let Some(child) = app.state::<Server>().0.lock().unwrap().take() {
        let _ = child.kill();
    }
}

fn fail(app: &AppHandle, message: &str) {
    app.dialog()
        .message(message)
        .title(TITLE)
        .kind(MessageDialogKind::Error)
        .blocking_show();
    stop_server(app);
    app.exit(1);
}

/// Ayarlar sayfasındaki "Klasör seç" düğmesi için sistemin klasör seçicisini açar.
#[tauri::command]
async fn choose_folder(app: AppHandle, initial: Option<String>) -> Option<String> {
    let mut dialog = app.dialog().file();
    if let Some(folder) = initial.filter(|folder| !folder.is_empty()) {
        dialog = dialog.set_directory(folder);
    }
    dialog.blocking_pick_folder().map(|folder| folder.to_string())
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Server(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![choose_folder])
        .setup(|app| {
            let port = free_port()?;
            let token = access_token();
            let (mut output, child) = app
                .shell()
                .sidecar("altyazi-server")?
                .args(["--serve", "--exit-with-stdin", "--port", &port.to_string(), "--token", &token])
                .spawn()?;
            *app.state::<Server>().0.lock().unwrap() = Some(child);
            // Sunucunun çıktısı okunmazsa borusu dolabilir; içerik kullanılmaz, yalnızca boşaltılır.
            tauri::async_runtime::spawn(async move { while output.recv().await.is_some() {} });

            let handle = app.handle().clone();
            thread::spawn(move || {
                if !wait_for_server(port) {
                    fail(&handle, "Altyazı motoru başlatılamadı. Programı yeniden açmayı deneyin.");
                    return;
                }
                let url = format!("http://127.0.0.1:{port}/?token={token}")
                    .parse()
                    .expect("yerel adres geçerli");
                let window = WebviewWindowBuilder::new(&handle, "main", WebviewUrl::External(url))
                    .title(TITLE)
                    .inner_size(1100.0, 780.0)
                    .min_inner_size(760.0, 560.0)
                    .build();
                if window.is_err() {
                    fail(&handle, "Program penceresi açılamadı. WebView2 Runtime kurulu olmalıdır.");
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Tauri uygulaması başlatılamadı");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            stop_server(handle);
        }
    });
}
