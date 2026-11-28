#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod job_object;
mod proxy;

use std::net::SocketAddr;
use std::sync::{Arc, Mutex};

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, RunEvent};

use crate::backend::BackendProcess;

struct AppState {
    backend: Arc<Mutex<Option<BackendProcess>>>,
    proxy_task: Arc<Mutex<Option<tokio::task::JoinHandle<()>>>>,
}

fn show_error_dialog(title: &str, message: &str) {
    use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};
    let mut t: Vec<u16> = title.encode_utf16().collect();
    t.push(0);
    let mut m: Vec<u16> = message.encode_utf16().collect();
    m.push(0);
    unsafe {
        MessageBoxW(std::ptr::null_mut(), m.as_ptr(), t.as_ptr(), MB_OK | MB_ICONERROR);
    }
}

fn show_main_window(app: &tauri::AppHandle) {
    let app_handle = app.clone();
    let _ = app.run_on_main_thread(move || {
        if let Some(window) = app_handle.get_webview_window("main") {
            let _ = window.unminimize();
            let _ = window.show();
            let _ = window.set_focus();
        }
    });
}

fn shutdown_resources(app: &tauri::AppHandle) {
    let state = app.state::<AppState>();
    if let Ok(mut guard) = state.proxy_task.lock() {
        if let Some(handle) = guard.take() {
            handle.abort();
        }
    };
    if let Ok(mut guard) = state.backend.lock() {
        if let Some(proc) = guard.take() {
            proc.shutdown();
        }
    };
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            show_main_window(app);
        }))
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            backend: Arc::new(Mutex::new(None)),
            proxy_task: Arc::new(Mutex::new(None)),
        })
        .setup(|app| {
            let show_item = MenuItem::with_id(app, "show", "เปิด OmniCut", true, None::<&str>)?;
            let quit_item =
                MenuItem::with_id(app, "quit", "ออกจากโปรแกรม", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_item, &quit_item])?;

            let mut tray_builder = TrayIconBuilder::new()
                .menu(&menu)
                .tooltip("OmniCut Pro Studio")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main_window(app),
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                });

            if let Some(icon) = app.default_window_icon().cloned() {
                tray_builder = tray_builder.icon(icon);
            }
            let _tray = tray_builder.build(app)?;

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match backend::start_backend().await {
                    Ok(proc) => {
                        let api_key = proc.api_key.clone();
                        let backend_port = proc.port;
                        {
                            let state = app_handle.state::<AppState>();
                            if let Ok(mut guard) = state.backend.lock() {
                                *guard = Some(proc);
                            };
                        }

                        let upstream = SocketAddr::from(([127, 0, 0, 1], backend_port));
                        match proxy::start_proxy(upstream, api_key).await {
                            Ok((proxy_port, handle)) => {
                                {
                                    let state = app_handle.state::<AppState>();
                                    if let Ok(mut guard) = state.proxy_task.lock() {
                                        *guard = Some(handle);
                                    };
                                }

                                let nav_handle = app_handle.clone();
                                let _ = app_handle.run_on_main_thread(move || {
                                    if let Some(window) = nav_handle.get_webview_window("main") {
                                        let target = format!("http://127.0.0.1:{proxy_port}/");
                                        if let Ok(url) = target.parse() {
                                            let _ = window.navigate(url);
                                        }
                                        let _ = window.unminimize();
                                        let _ = window.show();
                                        let _ = window.set_focus();
                                    }
                                });
                            }
                            Err(err) => {
                                eprintln!("[OmniCut Desktop] Loopback proxy failed: {err}");
                                show_error_dialog("OmniCut Pro Studio - Startup Error", &err);
                                app_handle.exit(1);
                            }
                        }
                    }
                    Err(err) => {
                        eprintln!("[OmniCut Desktop] Backend startup failed: {err}");
                        show_error_dialog("OmniCut Pro Studio - Startup Error", &err);
                        app_handle.exit(1);
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| match event {
            RunEvent::ExitRequested { .. } | RunEvent::Exit => {
                shutdown_resources(app_handle);
            }
            _ => {}
        });
}
