use std::fs::{self, OpenOptions};
use std::net::{SocketAddr, TcpStream};
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use http_body_util::Empty;
use hyper::body::Bytes;
use hyper::Request;
use hyper_util::rt::TokioIo;
use tokio::net::TcpStream as TokioTcpStream;
use windows_sys::Win32::System::Console::{GenerateConsoleCtrlEvent, CTRL_BREAK_EVENT};

use crate::job_object::JobObject;

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;

pub const BACKEND_PORT: u16 = 8000;
pub const HYPERFRAMES_PORT: u16 = 3002;

pub struct BackendProcess {
    pub child: Child,
    pub job: JobObject,
    pub port: u16,
    pub api_key: String,
    #[allow(dead_code)]
    pub workspace_root: PathBuf,
    #[allow(dead_code)]
    pub external_hyperframes: bool,
}

impl BackendProcess {
    pub fn shutdown(mut self) {
        let pid = self.child.id();
        if self.child.try_wait().ok().flatten().is_none() {
            let signaled = unsafe { GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, pid) } != 0;
            if signaled {
                let deadline = Instant::now() + Duration::from_secs(4);
                while Instant::now() < deadline {
                    if self.child.try_wait().ok().flatten().is_some() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(100));
                }
            }
            if self.child.try_wait().ok().flatten().is_none() {
                let _ = self.child.kill();
                let _ = self.child.wait();
            }
        }
        drop(self.job);
    }
}

fn is_valid_workspace(dir: &Path) -> bool {
    dir.join("scripts").join("api_server.py").is_file()
}

pub fn discover_workspace_root() -> Result<PathBuf, String> {
    // 1. Explicit env override
    if let Ok(env_root) = std::env::var("OMNICUT_WORKSPACE_ROOT") {
        let p = PathBuf::from(env_root.trim());
        if is_valid_workspace(&p) {
            return Ok(p);
        }
    }

    // 2. %APPDATA%\OmniCut\desktop.json
    if let Ok(appdata) = std::env::var("APPDATA") {
        let cfg_path = PathBuf::from(appdata).join("OmniCut").join("desktop.json");
        if let Ok(raw) = fs::read_to_string(&cfg_path) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&raw) {
                if let Some(ws) = val.get("workspace_root").and_then(|v| v.as_str()) {
                    let p = PathBuf::from(ws);
                    if is_valid_workspace(&p) {
                        return Ok(p);
                    }
                }
            }
        }
    }

    // 3. Ancestor search from executable & current working directory
    let mut seeds = Vec::new();
    if let Ok(exe) = std::env::current_exe() {
        seeds.push(exe);
    }
    if let Ok(cwd) = std::env::current_dir() {
        seeds.push(cwd);
    }
    for seed in seeds {
        for ancestor in seed.ancestors() {
            if is_valid_workspace(ancestor) {
                return Ok(ancestor.to_path_buf());
            }
        }
    }

    Err(
        "Could not locate OmniCut workspace root (scripts/api_server.py). Set OMNICUT_WORKSPACE_ROOT or %APPDATA%\\OmniCut\\desktop.json."
            .to_string(),
    )
}

fn is_port_listening(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok()
}

fn pick_backend_port() -> Result<u16, String> {
    if !is_port_listening(BACKEND_PORT) {
        return Ok(BACKEND_PORT);
    }
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("Port {BACKEND_PORT} is busy and failed to bind fallback port: {e}"))?;
    let port = listener
        .local_addr()
        .map_err(|e| format!("Failed to read fallback port: {e}"))?
        .port();
    drop(listener);
    Ok(port)
}

pub async fn start_backend() -> Result<BackendProcess, String> {
    let workspace_root = discover_workspace_root()?;
    let port = pick_backend_port()?;

    // Preserve external HyperFrames preview on :3002 if already running; spawn :3002 only on-demand.
    let external_hyperframes = is_port_listening(HYPERFRAMES_PORT);

    let python_exe = workspace_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");
    if !python_exe.is_file() {
        return Err(format!(
            "Python virtual environment not found at {}",
            python_exe.display()
        ));
    }

    let tmp_dir = workspace_root.join(".tmp");
    fs::create_dir_all(&tmp_dir)
        .map_err(|e| format!("Failed to create .tmp directory: {e}"))?;
    let log_path = tmp_dir.join("desktop_backend.log");
    let stdout_file = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(&log_path)
        .map_err(|e| format!("Failed to open backend log {}: {e}", log_path.display()))?;
    let stderr_file = stdout_file
        .try_clone()
        .map_err(|e| format!("Failed to clone backend log handle: {e}"))?;

    let api_key = uuid::Uuid::new_v4().to_string();
    let job = JobObject::new()?;

    let child = Command::new(&python_exe)
        .arg("scripts/api_server.py")
        .current_dir(&workspace_root)
        .creation_flags(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
        .env("FASTAPI_RELOAD", "false")
        .env("OMNICUT_HOST", "127.0.0.1")
        .env("OMNICUT_PORT", port.to_string())
        .env("OMNICUT_AUTH_DISABLED", "false")
        .env("OMNICUT_REQUIRE_AUTH", "true")
        .env("OMNICUT_API_KEY", &api_key)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(Stdio::from(stdout_file))
        .stderr(Stdio::from(stderr_file))
        .spawn()
        .map_err(|e| format!("Failed to spawn Python backend: {e}"))?;

    if let Err(e) = job.assign_child(&child) {
        return Err(e);
    }

    let mut proc = BackendProcess {
        child,
        job,
        port,
        api_key,
        workspace_root,
        external_hyperframes,
    };

    wait_for_health(&mut proc, &log_path).await?;
    Ok(proc)
}

async fn check_health_once(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let Ok(Ok(stream)) =
        tokio::time::timeout(Duration::from_millis(500), TokioTcpStream::connect(addr)).await
    else {
        return false;
    };

    let io = TokioIo::new(stream);
    let Ok((mut sender, conn)) = hyper::client::conn::http1::handshake(io).await else {
        return false;
    };

    tokio::spawn(async move {
        let _ = conn.await;
    });

    let Ok(req) = Request::builder()
        .method("GET")
        .uri("/api/health")
        .header("Host", format!("127.0.0.1:{port}"))
        .body(Empty::<Bytes>::new())
    else {
        return false;
    };

    match tokio::time::timeout(Duration::from_millis(800), sender.send_request(req)).await {
        Ok(Ok(res)) => res.status().is_success(),
        _ => false,
    }
}

async fn wait_for_health(proc: &mut BackendProcess, log_path: &Path) -> Result<(), String> {
    let port = proc.port;
    let deadline = Instant::now() + Duration::from_secs(20);
    while Instant::now() < deadline {
        if let Ok(Some(status)) = proc.child.try_wait() {
            let tail = fs::read_to_string(log_path).unwrap_or_default();
            return Err(format!(
                "Backend exited prematurely with {status}. Log:\n{tail}"
            ));
        }

        if check_health_once(port).await {
            return Ok(());
        }

        tokio::time::sleep(Duration::from_millis(150)).await;
    }

    let tail = fs::read_to_string(log_path).unwrap_or_default();
    Err(format!(
        "Timed out waiting for http://127.0.0.1:{port}/api/health after 20s. Log:\n{tail}"
    ))
}
