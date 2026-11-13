//! Research only: runtime-selected Rust protocol seams; no NativeWeave product ABI.
use bytes::{Buf, BufMut, Bytes};
use tonic::codec::{Codec, Decoder, Encoder, DecodeBuf, EncodeBuf};
use tonic::Status;

#[derive(Clone, Default)]
pub struct RawCodec;
pub struct RawEncoder;
pub struct RawDecoder;
impl Codec for RawCodec {
    type Encode = Bytes;
    type Decode = Bytes;
    type Encoder = RawEncoder;
    type Decoder = RawDecoder;
    fn encoder(&mut self) -> RawEncoder { RawEncoder }
    fn decoder(&mut self) -> RawDecoder { RawDecoder }
}
impl Encoder for RawEncoder {
    type Item = Bytes;
    type Error = Status;
    fn encode(&mut self, item: Bytes, dst: &mut EncodeBuf<'_>) -> Result<(), Status> {
        dst.put(item); Ok(())
    }
}
impl Decoder for RawDecoder {
    type Item = Bytes;
    type Error = Status;
    fn decode(&mut self, src: &mut DecodeBuf<'_>) -> Result<Option<Bytes>, Status> {
        Ok(Some(src.copy_to_bytes(src.remaining())))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
    use std::convert::Infallible;
    use http_body_util::{BodyExt, Full};
    use rmcp::{ServerHandler, model::ProtocolVersion};
    use rmcp::transport::streamable_http_server::{StreamableHttpService, StreamableHttpServerConfig, session::local::LocalSessionManager};

    fn wire(payload: &[u8]) -> Bytes {
        let mut out = vec![0]; out.extend_from_slice(&(payload.len() as u32).to_be_bytes());
        out.extend_from_slice(payload); out.into()
    }

    async fn unary(input: Bytes, calls: Arc<AtomicUsize>) -> http::Response<tonic::body::Body> {
        let svc = tower::service_fn(move |req: tonic::Request<Bytes>| {
            calls.fetch_add(1, Ordering::SeqCst);
            async move { Ok::<_, Status>(tonic::Response::new(req.into_inner())) }
        });
        tonic::server::Grpc::new(RawCodec).max_decoding_message_size(8).max_encoding_message_size(8)
            .unary(svc, http::Request::new(Full::new(input))).await
    }
    #[tokio::test]
    async fn tonic_runtime_bytes_codec_preserves_binary_and_empty() {
        for payload in [&b"a\0b"[..], &b""[..]] {
            let calls = Arc::new(AtomicUsize::new(0));
            let response = unary(wire(payload), calls.clone()).await;
            let body = response.into_body().collect().await.unwrap();
            assert_eq!(body.trailers().unwrap()["grpc-status"], "0");
            assert_eq!(body.to_bytes(), wire(payload));
            assert_eq!(calls.load(Ordering::SeqCst), 1);
        }
    }
    #[tokio::test]
    async fn tonic_rejects_oversize_before_handler() {
        let calls = Arc::new(AtomicUsize::new(0));
        let response = unary(wire(b"123456789"), calls.clone()).await;
        assert_eq!(response.headers()["grpc-status"], "11");
        assert_eq!(calls.load(Ordering::SeqCst), 0);
    }
    #[tokio::test]
    async fn tonic_rejects_truncated_frame_before_handler() {
        let calls = Arc::new(AtomicUsize::new(0));
        let response = unary(Bytes::from_static(&[0,0,0,0,8,b'a']), calls.clone()).await;
        assert_ne!(response.headers()["grpc-status"], "0");
        assert_eq!(calls.load(Ordering::SeqCst), 0);
    }
    #[tokio::test]
    async fn tonic_rejects_invalid_compression_flag_before_handler() {
        let calls = Arc::new(AtomicUsize::new(0));
        let response = unary(Bytes::from_static(&[2,0,0,0,0]), calls.clone()).await;
        assert_eq!(response.headers()["grpc-status"], "13");
        assert_eq!(calls.load(Ordering::SeqCst), 0);
    }
    #[tokio::test]
    async fn tonic_server_streaming_reuses_same_codec_and_trailers() {
        let svc = tower::service_fn(|_: tonic::Request<Bytes>| async {
            Ok::<_,Status>(tonic::Response::new(tokio_stream::iter([Ok(Bytes::from_static(b"a")),Ok(Bytes::from_static(b"bc"))])))
        });
        let response = tonic::server::Grpc::new(RawCodec).max_decoding_message_size(8).max_encoding_message_size(8)
            .server_streaming(svc,http::Request::new(Full::new(wire(b"start")))).await;
        let body=response.into_body().collect().await.unwrap();
        assert_eq!(body.trailers().unwrap()["grpc-status"], "0");
        let mut expect=wire(b"a").to_vec();expect.extend_from_slice(&wire(b"bc"));
        assert_eq!(body.to_bytes(),Bytes::from(expect));
    }

    #[derive(Clone)]
    struct ForeignMcp;
    impl ServerHandler for ForeignMcp {
        fn supported_protocol_versions(&self) -> std::borrow::Cow<'static,[ProtocolVersion]> {
            std::borrow::Cow::Owned(vec![ProtocolVersion::V_2026_07_28])
        }
    }
    fn mcp() -> StreamableHttpService<ForeignMcp,LocalSessionManager> {
        let cfg=StreamableHttpServerConfig::default()
            .with_legacy_session_mode(false).with_json_response(true)
            .with_stateless_protocol_metadata_required(true).with_max_request_body_bytes(64)
            .with_allowed_origins(["https://client.example:443"]).enforce_origin_validation();
        StreamableHttpService::new(||Ok(ForeignMcp),Arc::new(LocalSessionManager::default()),cfg)
    }
    #[tokio::test]
    async fn mcp_no_event_store_stateless_get_delete_are_405() {
        for method in ["GET","DELETE"] {
            let req=http::Request::builder().method(method).uri("http://localhost/mcp").header("host","localhost")
                .body(Full::new(Bytes::new())).unwrap();
            let response=mcp().handle(req).await;
            assert_eq!(response.status(),405);assert_eq!(response.headers()["allow"],"POST");
        }
    }
    #[tokio::test]
    async fn mcp_origin_and_host_are_checked_before_dispatch() {
        for (host,origin) in [("evil.example","https://client.example"),("localhost","https://evil.example")] {
            let req=http::Request::builder().method("POST").uri("/mcp").header("host",host).header("origin",origin)
                .body(Full::new(Bytes::new())).unwrap();
            assert!(mcp().handle(req).await.status().is_client_error());
        }
    }
    #[tokio::test]
    async fn mcp_streaming_body_limit_without_content_length() {
        let req=http::Request::builder().method("POST").uri("/mcp").header("host","localhost")
            .header("content-type","application/json").header("accept","application/json, text/event-stream")
            .header("mcp-protocol-version","2026-07-28")
            .body(Full::new(Bytes::from(vec![b' ';65]))).unwrap();
        assert_eq!(mcp().handle(req).await.status(),413);
    }
    #[tokio::test]
    async fn hyper_real_loopback_http1_runtime_handler() {
        use hyper_util::rt::TokioIo;
        let listener=tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address=listener.local_addr().unwrap();
        let server=tokio::spawn(async move {
            let (stream,_)=listener.accept().await.unwrap();
            let svc=hyper::service::service_fn(|req:hyper::Request<hyper::body::Incoming>| async move {
                let input=req.into_body().collect().await.unwrap().to_bytes();
                Ok::<_,Infallible>(hyper::Response::new(Full::new(input)))
            });
            hyper::server::conn::http1::Builder::new().serve_connection(TokioIo::new(stream),svc).await.unwrap();
        });
        let stream=tokio::net::TcpStream::connect(address).await.unwrap();
        let (mut client,connection)=hyper::client::conn::http1::handshake(TokioIo::new(stream)).await.unwrap();
        let driver=tokio::spawn(connection);
        let req=hyper::Request::builder().uri("/echo").header("host","localhost").header("connection","close")
            .body(Full::new(Bytes::from_static(b"runtime-route\0payload"))).unwrap();
        let response=client.send_request(req).await.unwrap();
        assert_eq!(response.into_body().collect().await.unwrap().to_bytes(),Bytes::from_static(b"runtime-route\0payload"));
        drop(client);driver.await.unwrap().unwrap();server.await.unwrap();
    }
}
