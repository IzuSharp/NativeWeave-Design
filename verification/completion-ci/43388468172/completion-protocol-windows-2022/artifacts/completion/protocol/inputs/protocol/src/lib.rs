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
    struct ForeignMcp { name: Arc<str> }
    impl ServerHandler for ForeignMcp {
        fn supported_protocol_versions(&self) -> std::borrow::Cow<'static,[ProtocolVersion]> {
            std::borrow::Cow::Owned(vec![ProtocolVersion::V_2026_07_28])
        }
        fn get_info(&self) -> rmcp::model::ServerConfig {
            rmcp::model::ServerConfig::new(rmcp::model::ServerCapabilities::builder().enable_tools().build())
                .with_protocol_version(ProtocolVersion::V_2026_07_28)
        }
        fn get_tool(&self,name:&str)->Option<rmcp::model::Tool>{
            (name==self.name.as_ref()).then(||rmcp::model::Tool::new(self.name.to_string(),"runtime registered probe",
                serde_json::json!({"type":"object","properties":{},"additionalProperties":false}).as_object().unwrap().clone()))
        }
        async fn call_tool(&self,request:rmcp::model::CallToolRequestParams,_context:rmcp::service::RequestContext<rmcp::RoleServer>)
            ->Result<rmcp::model::CallToolResponse,rmcp::ErrorData>{
            if self.get_tool(&request.name).is_none(){return Err(rmcp::ErrorData::invalid_params("unknown registered tool",None));}
            Ok(rmcp::model::CallToolResult::success(vec![rmcp::model::ContentBlock::text(self.name.to_string())]).into())
        }
    }
    fn mcp() -> StreamableHttpService<ForeignMcp,LocalSessionManager> {
        let cfg=StreamableHttpServerConfig::default()
            .with_legacy_session_mode(false).with_json_response(true)
            .with_stateless_protocol_metadata_required(true).with_max_request_body_bytes(64)
            .with_allowed_origins(["https://client.example:443"]).enforce_origin_validation();
        StreamableHttpService::new(||Ok(ForeignMcp{name:Arc::from("echo")}),Arc::new(LocalSessionManager::default()),cfg)
    }
    #[tokio::test]
    async fn mcp_runtime_tool_metadata_uses_one_compiled_handler(){
        for name in ["echo_a","echo_b"] {
            let mut cfg=mcp().config;cfg.max_request_body_bytes=2048;
            let service=StreamableHttpService::new(move||Ok(ForeignMcp{name:Arc::from(name)}),Arc::new(LocalSessionManager::default()),cfg);
            let body=serde_json::json!({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":name,"arguments":{},"_meta":{
                "io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}
            }}});
            let req=http::Request::builder().method("POST").uri("/mcp").header("host","localhost")
                .header("content-type","application/json").header("accept","application/json, text/event-stream")
                .header("mcp-protocol-version","2026-07-28").header("mcp-method","tools/call").header("mcp-name",name)
                .body(Full::new(Bytes::from(body.to_string()))).unwrap();
            let response=service.handle(req).await;assert_eq!(response.status(),200);
            let body=response.into_body().collect().await.unwrap().to_bytes();
            let value:serde_json::Value=serde_json::from_slice(&body).unwrap();
            assert!(value.get("error").is_none(),"{value}");assert_eq!(value["result"]["content"][0]["text"],name);
        }
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

    #[tokio::test]
    async fn hyper_real_loopback_http2_runtime_handler() {
        use hyper_util::rt::{TokioIo,TokioExecutor};
        let listener=tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address=listener.local_addr().unwrap();
        let server=tokio::spawn(async move {
            let (stream,_)=listener.accept().await.unwrap();
            let svc=hyper::service::service_fn(|req:hyper::Request<hyper::body::Incoming>| async move {
                assert_eq!(req.version(),http::Version::HTTP_2);
                let input=req.into_body().collect().await.unwrap().to_bytes();
                Ok::<_,Infallible>(hyper::Response::new(Full::new(input)))
            });
            hyper::server::conn::http2::Builder::new(TokioExecutor::new()).serve_connection(TokioIo::new(stream),svc).await
        });
        let stream=tokio::net::TcpStream::connect(address).await.unwrap();
        let (mut client,connection)=hyper::client::conn::http2::handshake(TokioExecutor::new(),TokioIo::new(stream)).await.unwrap();
        let driver=tokio::spawn(connection);
        let req=hyper::Request::builder().uri("http://localhost/echo")
            .body(Full::new(Bytes::from_static(b"h2\0payload"))).unwrap();
        let response=client.send_request(req).await.unwrap();
        assert_eq!(response.version(),http::Version::HTTP_2);
        assert_eq!(response.into_body().collect().await.unwrap().to_bytes(),Bytes::from_static(b"h2\0payload"));
        drop(client);driver.abort();let _=driver.await;
        tokio::time::timeout(std::time::Duration::from_secs(2),server).await.unwrap().unwrap().unwrap();
    }

    fn tls_pair(server_name:&'static str, trusted:bool) -> (rustls::ClientConnection,rustls::ServerConnection) {
        // Ephemeral self-signed localhost test identity, never persisted or deployed.
        let generated=rcgen::generate_simple_self_signed(vec!["localhost".to_string()]).unwrap();
        let cert=generated.cert.der().clone();
        let key=rustls::pki_types::PrivatePkcs8KeyDer::from(generated.signing_key.serialize_der());
        let provider=Arc::new(rustls::crypto::ring::default_provider());
        let mut server=rustls::ServerConfig::builder_with_provider(provider.clone()).with_safe_default_protocol_versions().unwrap()
            .with_no_client_auth().with_single_cert(vec![cert.clone()],key.into()).unwrap();
        server.alpn_protocols=vec![b"h2".to_vec(),b"http/1.1".to_vec()];
        let mut roots=rustls::RootCertStore::empty();if trusted {roots.add(cert).unwrap();}
        let mut client=rustls::ClientConfig::builder_with_provider(provider).with_safe_default_protocol_versions().unwrap()
            .with_root_certificates(roots).with_no_client_auth();client.alpn_protocols=vec![b"h2".to_vec()];
        (rustls::ClientConnection::new(Arc::new(client),server_name.try_into().unwrap()).unwrap(),rustls::ServerConnection::new(Arc::new(server)).unwrap())
    }
    fn exchange(client:&mut rustls::ClientConnection,server:&mut rustls::ServerConnection)->Result<(),rustls::Error>{
        for _ in 0..16 {
            let mut bytes=Vec::new();client.write_tls(&mut bytes).unwrap();
            if !bytes.is_empty(){server.read_tls(&mut &bytes[..]).unwrap();server.process_new_packets()?;}
            let mut bytes=Vec::new();server.write_tls(&mut bytes).unwrap();
            if !bytes.is_empty(){client.read_tls(&mut &bytes[..]).unwrap();client.process_new_packets()?;}
            if !client.is_handshaking() && !server.is_handshaking(){return Ok(());}
        }
        panic!("TLS fixture did not converge within 16 exchanges")
    }
    #[test]
    fn rustls_verified_handshake_alpn_and_close_notify(){
        let(mut c,mut s)=tls_pair("localhost",true);exchange(&mut c,&mut s).unwrap();
        assert_eq!(c.alpn_protocol(),Some(&b"h2"[..]));assert_eq!(s.alpn_protocol(),Some(&b"h2"[..]));
        c.send_close_notify();let mut data=Vec::new();c.write_tls(&mut data).unwrap();s.read_tls(&mut &data[..]).unwrap();
        assert!(s.process_new_packets().unwrap().peer_has_closed());
    }
    #[test]
    fn rustls_rejects_wrong_name_and_untrusted_certificate(){
        for(name,trusted) in [("wrong.example",true),("localhost",false)]{
            let(mut c,mut s)=tls_pair(name,trusted);assert!(exchange(&mut c,&mut s).is_err());
        }
    }
}
