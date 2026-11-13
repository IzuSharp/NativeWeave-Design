//! Finite R27/R29 research probes over the actual Bytes/Tokio/Hyper Body APIs.
//! No FFI implementation, transport test, RSS bound or production acceptance.
#[cfg(test)]
mod tests {
    use bytes::Bytes;
    use hyper::body::{Body, Frame};
    use std::{
        convert::Infallible,
        future::{Future, poll_fn},
        pin::Pin,
        sync::{Arc, atomic::{AtomicUsize, Ordering}},
        task::{Context, Poll},
    };
    use tokio::sync::{OwnedSemaphorePermit, Semaphore, mpsc};

    struct Payload {
        data: Box<[u8]>,
        _credit: OwnedSemaphorePermit,
    }
    impl AsRef<[u8]> for Payload {
        fn as_ref(&self) -> &[u8] { &self.data }
    }

    // Called only after capacity and byte reservations are held. The owner,
    // not the message slot or response future, owns the byte reservation.
    fn materialize(size: usize, credit: OwnedSemaphorePermit, allocations: &AtomicUsize) -> Bytes {
        allocations.fetch_add(1, Ordering::SeqCst);
        Bytes::from_owner(Payload { data: vec![42; size].into_boxed_slice(), _credit: credit })
    }

    #[derive(Debug, PartialEq)]
    enum EnqueueError { InvalidSize, Closed }

    async fn enqueue(
        tx: mpsc::Sender<Frame<Bytes>>,
        credits: Arc<Semaphore>,
        max_bytes: usize,
        size: usize,
        allocations: Arc<AtomicUsize>,
    ) -> Result<(), EnqueueError> {
        if size == 0 || size > max_bytes {
            return Err(EnqueueError::InvalidSize);
        }
        let count = u32::try_from(size).map_err(|_| EnqueueError::InvalidSize)?;
        let message = tx.reserve_owned().await.map_err(|_| EnqueueError::Closed)?;
        let bytes = credits.acquire_many_owned(count).await.map_err(|_| EnqueueError::Closed)?;
        message.send(Frame::data(materialize(size, bytes, &allocations)));
        // This means locally enqueued, never that a remote peer consumed data.
        Ok(())
    }

    struct ChannelBody(mpsc::Receiver<Frame<Bytes>>);
    impl Body for ChannelBody {
        type Data = Bytes;
        type Error = Infallible;
        fn poll_frame(mut self: Pin<&mut Self>, cx: &mut Context<'_>)
            -> Poll<Option<Result<Frame<Bytes>, Infallible>>> {
            self.0.poll_recv(cx).map(|item| item.map(Ok))
        }
    }

    #[tokio::test]
    async fn byte_credit_survives_last_retained_slice() {
        let budget = Arc::new(Semaphore::new(4));
        let allocations = AtomicUsize::new(0);
        let permit = budget.clone().acquire_many_owned(4).await.unwrap();
        let original = materialize(4, permit, &allocations);
        let clone = original.clone();
        let retained_slice = original.slice(1..3);
        drop(original);
        drop(clone);
        assert_eq!(&retained_slice[..], &[42, 42]);
        assert_eq!(budget.available_permits(), 0, "a slice retains its entire owner allocation");
        drop(retained_slice);
        assert_eq!(budget.available_permits(), 4);
        assert_eq!(allocations.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn receiver_drop_releases_queued_but_not_external_bytes() {
        let budget = Arc::new(Semaphore::new(8));
        let allocations = Arc::new(AtomicUsize::new(0));
        let (tx, mut rx) = mpsc::channel(2);
        enqueue(tx.clone(), budget.clone(), 8, 4, allocations.clone()).await.unwrap();
        enqueue(tx, budget.clone(), 8, 4, allocations).await.unwrap();
        let retained = rx.recv().await.unwrap().into_data().unwrap();
        drop(rx);
        assert_eq!(budget.available_permits(), 4, "only the queued owner's bytes were released");
        assert_eq!(retained.len(), 4);
        drop(retained);
        assert_eq!(budget.available_permits(), 8);
    }

    #[tokio::test]
    async fn cancelled_byte_wait_restores_message_capacity_before_allocating() {
        let budget = Arc::new(Semaphore::new(4));
        let allocations = Arc::new(AtomicUsize::new(0));
        let held = materialize(4, budget.clone().acquire_many_owned(4).await.unwrap(), &allocations);
        let (tx, _rx) = mpsc::channel(1);
        let mut pending = Box::pin(enqueue(tx.clone(), budget.clone(), 4, 4, allocations.clone()));
        assert!(poll_fn(|cx| Poll::Ready(pending.as_mut().poll(cx).is_pending())).await);
        assert_eq!(tx.capacity(), 0, "message slot is reserved while waiting for byte credit");
        assert_eq!(allocations.load(Ordering::SeqCst), 1, "waiting must not allocate another payload");
        drop(pending);
        assert_eq!(tx.capacity(), 1);
        assert_eq!(budget.available_permits(), 0, "the unrelated retained owner is still live");
        drop(held);
        assert_eq!(budget.available_permits(), 4);
    }

    #[tokio::test]
    async fn channel_close_does_not_revoke_an_already_reserved_send() {
        let budget = Arc::new(Semaphore::new(4));
        let allocations = AtomicUsize::new(0);
        let (tx, mut rx) = mpsc::channel::<Frame<Bytes>>(1);
        let reserved = tx.reserve_owned().await.unwrap();
        rx.close();
        let payload = materialize(4, budget.clone().acquire_many_owned(4).await.unwrap(), &allocations);
        let sender = reserved.send(Frame::data(payload));
        assert!(sender.is_closed());
        let retained = rx.recv().await.expect("Tokio permits a pre-close reservation").into_data().unwrap();
        assert!(rx.recv().await.is_none());
        assert_eq!(budget.available_permits(), 0);
        drop(retained);
        assert_eq!(budget.available_permits(), 4);
    }

    #[tokio::test]
    async fn oversized_chunk_is_rejected_before_reservations_or_allocation() {
        let budget = Arc::new(Semaphore::new(4));
        let allocations = Arc::new(AtomicUsize::new(0));
        let (tx, _rx) = mpsc::channel(1);
        assert_eq!(enqueue(tx.clone(), budget.clone(), 4, 5, allocations.clone()).await,
                   Err(EnqueueError::InvalidSize));
        assert_eq!(enqueue(tx.clone(), budget.clone(), 4, 0, allocations.clone()).await,
                   Err(EnqueueError::InvalidSize));
        assert_eq!(tx.capacity(), 1);
        assert_eq!(budget.available_permits(), 4);
        assert_eq!(allocations.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn body_end_does_not_retire_an_externally_retained_frame() {
        let budget = Arc::new(Semaphore::new(4));
        let allocations = Arc::new(AtomicUsize::new(0));
        let (tx, rx) = mpsc::channel(1);
        enqueue(tx, budget.clone(), 4, 4, allocations).await.unwrap();
        let mut body = ChannelBody(rx);
        let retained = poll_fn(|cx| Pin::new(&mut body).poll_frame(cx)).await
            .unwrap().unwrap().into_data().unwrap();
        assert!(poll_fn(|cx| Pin::new(&mut body).poll_frame(cx)).await.is_none());
        drop(body);
        assert_eq!(budget.available_permits(), 0, "Body EOF is not final byte-owner retirement");
        assert_eq!(&retained[..], &[42; 4]);
        drop(retained);
        assert_eq!(budget.available_permits(), 4);
    }
}
