//! R27/R29 actual Tower/Hyper Body fixtures. No C# handler, TLS, socket load,
//! weak-memory proof or production adapter is implied by these finite tests.
#[cfg(test)]
mod tests {
    use hyper::{body::{Body,Bytes,Frame},Request,Response};
    use std::{convert::Infallible,future::poll_fn,pin::Pin,sync::{Arc,Mutex,atomic::{AtomicUsize,Ordering}},task::{Context,Poll},time::Duration};
    use tokio::sync::{mpsc,oneshot,Notify,OwnedSemaphorePermit,Semaphore};
    use tower::{Service,ServiceExt};

    // One stream slot lives until both Body and the simulated foreign callback
    // have retired. This is not a byte allocator or an async cleanup protocol.
    struct Slot { _permit:OwnedSemaphorePermit }
    struct TrackedBody {
        rx:mpsc::Receiver<Frame<Bytes>>,
        slot:Option<Arc<Slot>>,
        live:Arc<AtomicUsize>,
        counted:bool,
    }
    fn channel(slot:Option<Arc<Slot>>,live:&Arc<AtomicUsize>)->(mpsc::Sender<Frame<Bytes>>,TrackedBody) {
        let(tx,rx)=mpsc::channel(1);live.fetch_add(1,Ordering::SeqCst);
        (tx,TrackedBody{rx,slot,live:live.clone(),counted:true})
    }
    impl TrackedBody {
        fn retire(&mut self) {
            if self.counted { self.live.fetch_sub(1,Ordering::SeqCst);self.counted=false; }
            self.slot.take();
        }
    }
    impl Drop for TrackedBody { fn drop(&mut self){self.retire()} }
    impl Body for TrackedBody {
        type Data=Bytes;type Error=Infallible;
        fn poll_frame(mut self:Pin<&mut Self>,cx:&mut Context<'_>)->Poll<Option<Result<Frame<Bytes>,Infallible>>> {
            match self.rx.poll_recv(cx) {
                Poll::Ready(Some(frame))=>Poll::Ready(Some(Ok(frame))),
                Poll::Ready(None)=>{self.retire();Poll::Ready(None)},
                Poll::Pending=>Poll::Pending,
            }
        }
        fn is_end_stream(&self)->bool{!self.counted}
    }
    struct Empty;
    impl Body for Empty {
        type Data=Bytes;type Error=Infallible;
        fn poll_frame(self:Pin<&mut Self>,_:&mut Context<'_>)->Poll<Option<Result<Frame<Bytes>,Infallible>>>{Poll::Ready(None)}
        fn is_end_stream(&self)->bool{true}
    }

    #[tokio::test]
    async fn tower_response_future_negative_control_does_not_limit_live_bodies() {
        let live=Arc::new(AtomicUsize::new(0));let copy=live.clone();
        let inner=tower::service_fn(move |():()| {
            let(_tx,body)=channel(None,&copy);
            async move {Ok::<_,Infallible>(Response::new(body))}
        });
        let mut svc=tower::limit::ConcurrencyLimit::new(inner,1);
        let first=svc.ready().await.unwrap().call(()).await.unwrap();
        // The first body has not been polled or dropped, yet the service admits a second.
        let second=tokio::time::timeout(Duration::from_secs(1),async{svc.ready().await.unwrap().call(()).await.unwrap()}).await.unwrap();
        assert_eq!(live.load(Ordering::SeqCst),2);
        drop(first);drop(second);assert_eq!(live.load(Ordering::SeqCst),0);
    }
    #[tokio::test]
    async fn body_and_callback_share_one_admission_slot() {
        let slots=Arc::new(Semaphore::new(1));let live=Arc::new(AtomicUsize::new(0));
        let slot=Arc::new(Slot{_permit:slots.clone().try_acquire_owned().unwrap()});
        let callback=slot.clone();let(tx,body)=channel(Some(slot),&live);
        assert!(slots.clone().try_acquire_owned().is_err());
        drop(body);
        tokio::time::timeout(Duration::from_secs(1),tx.closed()).await.unwrap();
        assert_eq!(live.load(Ordering::SeqCst),0);
        assert_eq!(slots.available_permits(),0, "callback still owns the slot");
        drop(callback);assert_eq!(slots.available_permits(),1);
    }
    #[tokio::test]
    async fn bounded_body_queue_and_eof_release() {
        let slots=Arc::new(Semaphore::new(1));let live=Arc::new(AtomicUsize::new(0));
        let slot=Arc::new(Slot{_permit:slots.clone().try_acquire_owned().unwrap()});
        let(tx,mut body)=channel(Some(slot),&live);
        tx.try_send(Frame::data(Bytes::from_static(b"one"))).unwrap();
        assert!(matches!(tx.try_send(Frame::data(Bytes::from_static(b"two"))),Err(mpsc::error::TrySendError::Full(_))));
        let frame=poll_fn(|cx|Pin::new(&mut body).poll_frame(cx)).await.unwrap().unwrap();
        assert_eq!(frame.into_data().unwrap(),Bytes::from_static(b"one"));
        assert_eq!(slots.available_permits(),0);
        drop(tx);assert!(poll_fn(|cx|Pin::new(&mut body).poll_frame(cx)).await.is_none());
        assert_eq!(slots.available_permits(),1);assert_eq!(live.load(Ordering::SeqCst),0);
        drop(body);assert_eq!(live.load(Ordering::SeqCst),0);
    }
    #[tokio::test]
    async fn hyper_http1_service_future_and_streamed_body_on_real_duplex_transport() {
        use hyper_util::rt::TokioIo;
        let(server_io,client_io)=tokio::io::duplex(4096);
        let(completion_tx,completion_rx)=oneshot::channel::<TrackedBody>();
        let completion_rx=Arc::new(Mutex::new(Some(completion_rx)));
        let entered=Arc::new(Notify::new());let signal=entered.clone();
        let service=hyper::service::service_fn(move |_request| {
            let wait=completion_rx.lock().unwrap().take().expect("one request in fixture");
            let signal=signal.clone();
            async move {
                signal.notify_one();
                let body=wait.await.expect("simulated foreign handler completes");
                Ok::<_,Infallible>(Response::new(body))
            }
        });
        let server=tokio::spawn(async move{hyper::server::conn::http1::Builder::new().serve_connection(TokioIo::new(server_io),service).await});
        let(mut sender,connection)=hyper::client::conn::http1::handshake(TokioIo::new(client_io)).await.unwrap();
        let client=tokio::spawn(connection);
        let response_task=tokio::spawn(async move{
            let req=Request::builder().uri("/").header("Host","nativeweave.fixture").body(Empty).unwrap();
            let response=sender.send_request(req).await.unwrap();
            (sender,response)
        });
        tokio::time::timeout(Duration::from_secs(2),entered.notified()).await.unwrap();
        assert!(!response_task.is_finished(), "response must await handler completion");
        let slots=Arc::new(Semaphore::new(1));let live=Arc::new(AtomicUsize::new(0));
        let slot=Arc::new(Slot{_permit:slots.clone().try_acquire_owned().unwrap()});let callback=slot.clone();
        let(tx,body)=channel(Some(slot),&live);
        tx.send(Frame::data(Bytes::from_static(b"hello "))).await.unwrap();
        assert!(completion_tx.send(body).is_ok());
        let(sender,response)=tokio::time::timeout(Duration::from_secs(2),response_task).await.unwrap().unwrap();
        assert_eq!(response.status(),200);
        let producer=tokio::spawn(async move{tx.send(Frame::data(Bytes::from_static(b"world"))).await.unwrap();});
        let mut incoming=response.into_body();let mut received=Vec::new();
        while let Some(frame)=tokio::time::timeout(Duration::from_secs(2),poll_fn(|cx|Pin::new(&mut incoming).poll_frame(cx))).await.unwrap(){
            if let Ok(bytes)=frame.unwrap().into_data(){received.extend_from_slice(&bytes);}
        }
        producer.await.unwrap();assert_eq!(received,b"hello world");
        assert_eq!(live.load(Ordering::SeqCst),0);assert_eq!(slots.available_permits(),0);
        drop(callback);assert_eq!(slots.available_permits(),1);
        drop(sender);
        tokio::time::timeout(Duration::from_secs(2),client).await.unwrap().unwrap().unwrap();
        tokio::time::timeout(Duration::from_secs(2),server).await.unwrap().unwrap().unwrap();
    }
}
