use std::net::SocketAddr;
use std::sync::Arc;

use bytes::Bytes;
use http_body_util::{combinators::BoxBody, BodyExt, Empty};
use hyper::body::Incoming;
use hyper::header::{HeaderName, HeaderValue, HOST, UPGRADE};
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request, Response, StatusCode};
use hyper_util::rt::TokioIo;
use tokio::net::{TcpListener, TcpStream};

type ProxyBody = BoxBody<Bytes, hyper::Error>;

fn empty_body() -> ProxyBody {
    Empty::<Bytes>::new()
        .map_err(|never| match never {})
        .boxed()
}

pub async fn start_proxy(
    upstream_addr: SocketAddr,
    api_key: String,
) -> Result<(u16, tokio::task::JoinHandle<()>), String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|e| format!("Failed to bind loopback proxy on 127.0.0.1:0: {e}"))?;
    let port = listener
        .local_addr()
        .map_err(|e| format!("Failed to read proxy local_addr: {e}"))?
        .port();

    let api_key = Arc::new(api_key);
    let handle = tokio::spawn(async move {
        loop {
            let Ok((stream, _)) = listener.accept().await else {
                break;
            };
            let key = Arc::clone(&api_key);
            tokio::spawn(async move {
                let io = TokioIo::new(stream);
                let svc = service_fn(move |req| {
                    forward_request(req, upstream_addr, Arc::clone(&key))
                });
                let _ = http1::Builder::new()
                    .preserve_header_case(true)
                    .title_case_headers(true)
                    .serve_connection(io, svc)
                    .with_upgrades()
                    .await;
            });
        }
    });

    Ok((port, handle))
}

fn sanitize_and_inject_headers<B>(
    req: &mut Request<B>,
    upstream_addr: SocketAddr,
    api_key: &str,
) {
    let headers = req.headers_mut();

    // Strip all inbound x-forwarded-* headers
    let to_remove: Vec<HeaderName> = headers
        .keys()
        .filter(|name| name.as_str().to_ascii_lowercase().starts_with("x-forwarded-"))
        .cloned()
        .collect();
    for name in to_remove {
        headers.remove(&name);
    }

    // Rewrite Host to upstream loopback address
    if let Ok(host_val) = HeaderValue::from_str(&upstream_addr.to_string()) {
        headers.insert(HOST, host_val);
    }

    // Inject ephemeral X-API-Key
    if let Ok(key_val) = HeaderValue::from_str(api_key) {
        headers.insert(HeaderName::from_static("x-api-key"), key_val);
    }
}

async fn forward_request(
    mut req: Request<Incoming>,
    upstream_addr: SocketAddr,
    api_key: Arc<String>,
) -> Result<Response<ProxyBody>, hyper::Error> {
    let is_upgrade = req.headers().contains_key(UPGRADE);
    sanitize_and_inject_headers(&mut req, upstream_addr, &api_key);

    let upstream_stream = match TcpStream::connect(upstream_addr).await {
        Ok(s) => s,
        Err(_) => {
            return Ok(Response::builder()
                .status(StatusCode::BAD_GATEWAY)
                .body(empty_body())
                .unwrap());
        }
    };

    let io = TokioIo::new(upstream_stream);
    let (mut sender, conn) = match hyper::client::conn::http1::handshake(io).await {
        Ok(parts) => parts,
        Err(_) => {
            return Ok(Response::builder()
                .status(StatusCode::BAD_GATEWAY)
                .body(empty_body())
                .unwrap());
        }
    };

    tokio::spawn(async move {
        let _ = conn.with_upgrades().await;
    });

    if is_upgrade {
        let client_upgrade = hyper::upgrade::on(&mut req);
        let mut upstream_res = match sender.send_request(req).await {
            Ok(res) => res,
            Err(_) => {
                return Ok(Response::builder()
                    .status(StatusCode::BAD_GATEWAY)
                    .body(empty_body())
                    .unwrap());
            }
        };

        if upstream_res.status() == StatusCode::SWITCHING_PROTOCOLS {
            let upstream_upgrade = hyper::upgrade::on(&mut upstream_res);
            tokio::spawn(async move {
                if let Ok((c, u)) = tokio::try_join!(client_upgrade, upstream_upgrade) {
                    let mut c_io = TokioIo::new(c);
                    let mut u_io = TokioIo::new(u);
                    let _ = tokio::io::copy_bidirectional(&mut c_io, &mut u_io).await;
                }
            });
        }

        let (parts, body) = upstream_res.into_parts();
        return Ok(Response::from_parts(parts, body.boxed()));
    }

    match sender.send_request(req).await {
        Ok(res) => {
            let (parts, body) = res.into_parts();
            Ok(Response::from_parts(parts, body.boxed()))
        }
        Err(_) => Ok(Response::builder()
            .status(StatusCode::BAD_GATEWAY)
            .body(empty_body())
            .unwrap()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use http_body_util::Full;

    async fn start_mock_upstream() -> (SocketAddr, tokio::task::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = tokio::spawn(async move {
            loop {
                let Ok((stream, _)) = listener.accept().await else {
                    break;
                };
                tokio::spawn(async move {
                    let io = TokioIo::new(stream);
                    let svc = service_fn(|req: Request<Incoming>| async move {
                        let api_key = req
                            .headers()
                            .get("x-api-key")
                            .and_then(|v| v.to_str().ok())
                            .unwrap_or("")
                            .to_string();
                        let has_x_forwarded = req
                            .headers()
                            .keys()
                            .any(|k| k.as_str().to_ascii_lowercase().starts_with("x-forwarded-"));
                        let host = req
                            .headers()
                            .get(HOST)
                            .and_then(|v| v.to_str().ok())
                            .unwrap_or("")
                            .to_string();

                        let payload = format!(
                            "key={api_key};forwarded={has_x_forwarded};host={host}"
                        );
                        Ok::<_, hyper::Error>(Response::new(
                            Full::new(Bytes::from(payload))
                                .map_err(|never| -> hyper::Error { match never {} })
                                .boxed(),
                        ))
                    });
                    let _ = http1::Builder::new().serve_connection(io, svc).await;
                });
            }
        });
        (addr, handle)
    }

    #[tokio::test]
    async fn proxy_injects_api_key_strips_x_forwarded_and_streams_body() {
        let (upstream_addr, upstream_handle) = start_mock_upstream().await;
        let (proxy_port, proxy_handle) =
            start_proxy(upstream_addr, "ephemeral-test-key".to_string())
                .await
                .unwrap();

        let stream = TcpStream::connect(("127.0.0.1", proxy_port)).await.unwrap();
        let io = TokioIo::new(stream);
        let (mut sender, conn) = hyper::client::conn::http1::handshake(io).await.unwrap();
        tokio::spawn(async move {
            let _ = conn.await;
        });

        let req = Request::builder()
            .method("GET")
            .uri("/api/status")
            .header("Host", format!("127.0.0.1:{proxy_port}"))
            .header("x-forwarded-for", "203.0.113.9")
            .header("X-Forwarded-Proto", "https")
            .header("x-api-key", "spoofed-key")
            .body(Empty::<Bytes>::new())
            .unwrap();

        let res = sender.send_request(req).await.unwrap();
        assert_eq!(res.status(), StatusCode::OK);
        let body_bytes = res.into_body().collect().await.unwrap().to_bytes();
        let body_str = String::from_utf8(body_bytes.to_vec()).unwrap();

        assert_eq!(
            body_str,
            format!("key=ephemeral-test-key;forwarded=false;host={upstream_addr}")
        );

        proxy_handle.abort();
        upstream_handle.abort();
    }
}
