//! Independent design-review regression. Not a product transport or a framing parser.
use bytes::{Bytes,Buf,BufMut};
use tonic::{Status,codec::{Codec,Decoder,Encoder,DecodeBuf,EncodeBuf}};
#[derive(Clone)]
pub struct RawCodec;
pub struct RawEncoder;
pub struct RawDecoder;
impl Codec for RawCodec {
    type Encode=Bytes;type Decode=Bytes;type Encoder=RawEncoder;type Decoder=RawDecoder;
    fn encoder(&mut self)->RawEncoder{RawEncoder}
    fn decoder(&mut self)->RawDecoder{RawDecoder}
}
impl Encoder for RawEncoder {
    type Item=Bytes;type Error=Status;
    fn encode(&mut self,item:Bytes,dst:&mut EncodeBuf<'_>)->Result<(),Status>{dst.put(item);Ok(())}
}
impl Decoder for RawDecoder {
    type Item=Bytes;type Error=Status;
    fn decode(&mut self,src:&mut DecodeBuf<'_>)->Result<Option<Bytes>,Status>{Ok(Some(src.copy_to_bytes(src.remaining())))}
}

/// Native policy only; all frame assembly/length/compression remains in Tonic.
#[derive(Clone)]
pub struct SingleRequestCodec;
pub struct SingleRequestDecoder { inner: RawDecoder, seen: bool }
impl Codec for SingleRequestCodec {
    type Encode=Bytes;type Decode=Bytes;type Encoder=RawEncoder;type Decoder=SingleRequestDecoder;
    fn encoder(&mut self)->RawEncoder {RawEncoder}
    fn decoder(&mut self)->SingleRequestDecoder {SingleRequestDecoder{inner:RawDecoder,seen:false}}
}
impl Decoder for SingleRequestDecoder {
    type Item=Bytes;type Error=Status;
    fn decode(&mut self,src:&mut DecodeBuf<'_>)->Result<Option<Bytes>,Status>{
        if self.seen {return Err(Status::invalid_argument("single-request method accepts exactly one message"));}
        let result=self.inner.decode(src)?;
        if result.is_some(){self.seen=true;}
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use http_body_util::{Full,BodyExt};
    use std::sync::{Arc,atomic::{AtomicUsize,Ordering}};
    fn frame(b:&[u8])->Vec<u8>{let mut v=vec![0];v.extend_from_slice(&(b.len() as u32).to_be_bytes());v.extend_from_slice(b);v}
    fn twice()->Bytes {let mut v=frame(b"first");v.extend(frame(b"second"));v.into()}
    async fn unary<C:Codec<Decode=Bytes,Encode=Bytes>>(codec:C,input:Bytes,calls:Arc<AtomicUsize>)->http::Response<tonic::body::Body>{
        let svc=tower::service_fn(move|req:tonic::Request<Bytes>|{calls.fetch_add(1,Ordering::SeqCst);async move{Ok::<_,Status>(tonic::Response::new(req.into_inner()))}});
        tonic::server::Grpc::new(codec).max_decoding_message_size(8).max_encoding_message_size(8).unary(svc,http::Request::new(Full::new(input))).await
    }
    #[tokio::test]
    async fn unguarded_unary_accepts_first_and_discards_second(){
        let calls=Arc::new(AtomicUsize::new(0));let r=unary(RawCodec,twice(),calls.clone()).await;
        let body=r.into_body().collect().await.unwrap();assert_eq!(body.trailers().unwrap()["grpc-status"],"0");assert_eq!(body.to_bytes().as_ref(),frame(b"first"));assert_eq!(calls.load(Ordering::SeqCst),1);
        println!("NEGATIVE: two framed messages accepted by raw Tonic unary; handler called once with first message");
    }
    #[tokio::test]
    async fn guarded_unary_rejects_second_before_handler(){
        let calls=Arc::new(AtomicUsize::new(0));let r=unary(SingleRequestCodec,twice(),calls.clone()).await;
        assert_eq!(r.headers()["grpc-status"],"3");assert_eq!(calls.load(Ordering::SeqCst),0);
    }
    #[tokio::test]
    async fn guarded_server_streaming_rejects_second_before_handler(){
        let calls=Arc::new(AtomicUsize::new(0));let count=calls.clone();
        let svc=tower::service_fn(move|_:tonic::Request<Bytes>|{count.fetch_add(1,Ordering::SeqCst);async{Ok::<_,Status>(tonic::Response::new(tokio_stream::iter([Ok(Bytes::from_static(b"ok"))])))}});
        let r=tonic::server::Grpc::new(SingleRequestCodec).max_decoding_message_size(8).server_streaming(svc,http::Request::new(Full::new(twice()))).await;
        assert_eq!(r.headers()["grpc-status"],"3");assert_eq!(calls.load(Ordering::SeqCst),0);
    }
    #[tokio::test]
    async fn guarded_single_binary_and_empty_messages_remain_valid(){
        for b in [&b"a\0b"[..],&b""[..]]{
            let calls=Arc::new(AtomicUsize::new(0));let r=unary(SingleRequestCodec,Bytes::from(frame(b)),calls.clone()).await;
            let body=r.into_body().collect().await.unwrap();assert_eq!(body.trailers().unwrap()["grpc-status"],"0");assert_eq!(body.to_bytes().as_ref(),frame(b));assert_eq!(calls.load(Ordering::SeqCst),1);
        }
    }
    #[tokio::test]
    async fn missing_message_is_rejected_before_handler(){
        let calls=Arc::new(AtomicUsize::new(0));let r=unary(SingleRequestCodec,Bytes::new(),calls.clone()).await;
        assert_eq!(r.headers()["grpc-status"],"13");assert_eq!(calls.load(Ordering::SeqCst),0);
    }
}
