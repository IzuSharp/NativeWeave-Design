//! R20/R21/R25 finite SQLx lifetime experiments, not a NativeWeave product API.
//! Real SQLite worker/transactions are used. No PostgreSQL, C# AOT, hard cancellation
//! deadline, OS-thread join, performance or production-acceptance claim follows.
#[cfg(test)]
mod tests {
    use sea_query::{Alias, Order, Query, SqliteQueryBuilder};
    use sqlx::{Connection, Row, SqliteConnection, SqlitePool};
    use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
    use std::future::{Future, poll_fn};
    use std::pin::Pin;
    use std::sync::{Arc, mpsc, atomic::{AtomicBool, AtomicUsize, Ordering}};
    use std::task::Poll;
    use std::time::Duration;

    type TestResult = Result<(), Box<dyn std::error::Error + Send + Sync>>;
    const WAIT: Duration = Duration::from_secs(10);

    fn options() -> SqliteConnectOptions {
        SqliteConnectOptions::new()
            .filename(":memory:")
            .in_memory(true)
            .shared_cache(false)
            .command_buffer_size(8)
            .row_buffer_size(1)
    }

    async fn pool() -> Result<SqlitePool, sqlx::Error> {
        SqlitePoolOptions::new()
            .max_connections(1)
            .min_connections(0)
            .connect_with(options())
            .await
    }

    async fn assert_pending_once<F: Future + ?Sized>(mut future: Pin<&mut F>) {
        poll_fn(|cx| match future.as_mut().poll(cx) {
            Poll::Pending => Poll::Ready(()),
            Poll::Ready(_) => panic!("fixture required a pending operation"),
        }).await;
    }

    async fn mark_connection(conn: &mut SqliteConnection) -> Result<(), sqlx::Error> {
        // TEMP state proves later observations use this physical connection,
        // rather than a replacement connection which happens to be clean.
        sqlx::query("CREATE TEMP TABLE owner_marker (id INTEGER)").execute(&mut *conn).await?;
        sqlx::query("INSERT INTO owner_marker VALUES (731)").execute(&mut *conn).await?;
        Ok(())
    }

    async fn assert_same_connection(conn: &mut SqliteConnection) -> Result<(), sqlx::Error> {
        assert_eq!(sqlx::query_scalar::<_, i64>("SELECT id FROM owner_marker")
            .fetch_one(conn).await?, 731);
        Ok(())
    }

    #[tokio::test]
    async fn dropped_transaction_rolls_back_before_same_connection_reuse() -> TestResult {
        let pool = pool().await?;
        let mut conn = pool.acquire().await?;
        mark_connection(&mut conn).await?;
        sqlx::query("CREATE TABLE items (id INTEGER)").execute(&mut *conn).await?;
        let mut tx = conn.begin().await?;
        sqlx::query("INSERT INTO items VALUES (1)").execute(&mut *tx).await?;
        drop(tx); // schedules SQLx rollback; this statement alone is not an acknowledgment.
        drop(conn); // SQLx's pool-return path must advance its own cleanup.

        let mut next = tokio::time::timeout(WAIT, pool.acquire()).await??;
        assert_same_connection(&mut next).await?;
        assert_eq!(sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM items")
            .fetch_one(&mut *next).await?, 0);
        drop(next);
        tokio::time::timeout(WAIT, pool.close()).await?;
        Ok(())
    }

    #[tokio::test]
    async fn early_stream_drop_unblocks_bounded_row_queue_and_reuses_connection() -> TestResult {
        let pool = pool().await?;
        let mut conn = pool.acquire().await?;
        mark_connection(&mut conn).await?;
        sqlx::query("CREATE TABLE numbers (n INTEGER PRIMARY KEY)").execute(&mut *conn).await?;
        sqlx::query("WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<1000) INSERT INTO numbers SELECT n FROM seq")
            .execute(&mut *conn).await?;
        let (sql, values) = Query::select().column(Alias::new("n"))
            .from(Alias::new("numbers")).order_by(Alias::new("n"), Order::Asc)
            .to_owned().build(SqliteQueryBuilder);
        assert!(values.0.is_empty());
        let query = sqlx::query(sqlx::AssertSqlSafe(sql));
        let mut rows = query.fetch(&mut *conn);
        let first = tokio::time::timeout(WAIT, poll_fn(|cx| rows.as_mut().poll_next(cx)))
            .await?.expect("one row")?;
        assert_eq!(first.try_get::<i64, _>(0)?, 1);
        drop(first);
        drop(rows); // stops row-channel consumption; not a universal sqlite3_step interrupt.

        assert_eq!(tokio::time::timeout(WAIT,
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM numbers").fetch_one(&mut *conn))
            .await??, 1000);
        assert_same_connection(&mut conn).await?;
        drop(conn);
        tokio::time::timeout(WAIT, pool.close()).await?;
        Ok(())
    }

    #[tokio::test]
    async fn canceled_acquire_waiter_does_not_lose_the_only_pool_permit() -> TestResult {
        let pool = pool().await?;
        let mut held = pool.acquire().await?;
        mark_connection(&mut held).await?;
        let mut waiter = Box::pin(pool.acquire());
        assert_pending_once(waiter.as_mut()).await;
        drop(waiter);
        drop(held);
        let mut next = tokio::time::timeout(WAIT, pool.acquire()).await??;
        assert_same_connection(&mut next).await?;
        assert_eq!(pool.size(), 1);
        drop(next);
        tokio::time::timeout(WAIT, pool.close()).await?;
        Ok(())
    }

    #[tokio::test]
    async fn dropping_dispatched_commit_before_ack_can_still_commit() -> TestResult {
        let mut conn = SqliteConnection::connect_with(&options()).await?;
        sqlx::query("CREATE TABLE items (id INTEGER)").execute(&mut conn).await?;
        let (entered_tx, entered_rx) = tokio::sync::oneshot::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let mut entered = Some(entered_tx);
        conn.lock_handle().await?.set_commit_hook(move || {
            if let Some(signal) = entered.take() {
                let _ = signal.send(());
                // Deliberately blocked TEST-ONLY native hook: the managed task never
                // blocks here. Production cancellation/control callbacks must not copy this.
                // Dropping release_tx on a test error also releases this hook.
                let _ = release_rx.recv();
            }
            true // allow SQLite to commit after the test releases the hook.
        });

        let mut tx = conn.begin().await?;
        sqlx::query("INSERT INTO items VALUES (99)").execute(&mut *tx).await?;
        let mut commit = Box::pin(tx.commit());
        assert_pending_once(commit.as_mut()).await; // dispatch; no success observed.
        tokio::time::timeout(WAIT, entered_rx).await??; // worker entered actual SQLite COMMIT.
        drop(commit); // lose the application acknowledgment and trigger SQLx Drop cleanup.
        release_tx.send(())?;

        let count = tokio::time::timeout(WAIT,
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM items").fetch_one(&mut conn))
            .await??;
        assert_eq!(count, 1, "future cancellation must not be represented as confirmed rollback");
        conn.lock_handle().await?.remove_commit_hook();
        // A later ordinary transaction still works after lost-ack compensation.
        let mut next = conn.begin().await?;
        sqlx::query("INSERT INTO items VALUES (100)").execute(&mut *next).await?;
        next.rollback().await?;
        assert_eq!(sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM items")
            .fetch_one(&mut conn).await?, 1);
        tokio::time::timeout(WAIT, conn.close()).await??;
        Ok(())
    }

    #[tokio::test]
    async fn progress_cancel_state_is_removed_before_next_operation() -> TestResult {
        let mut conn = SqliteConnection::connect_with(&options()).await?;
        let old_cancel = Arc::new(AtomicBool::new(true));
        let old_calls = Arc::new(AtomicUsize::new(0));
        let flag = old_cancel.clone();
        let calls = old_calls.clone();
        conn.lock_handle().await?.set_progress_handler(1, move || {
            calls.fetch_add(1, Ordering::SeqCst);
            !flag.load(Ordering::SeqCst)
        });
        let failed = sqlx::query_scalar::<_, i64>("SELECT 42").fetch_one(&mut conn).await;
        assert!(matches!(failed, Err(sqlx::Error::Database(_))));
        assert!(old_calls.load(Ordering::SeqCst) > 0);
        conn.lock_handle().await?.remove_progress_handler();
        assert_eq!(Arc::strong_count(&old_cancel), 1, "native hook capture was released");
        let old_count = old_calls.load(Ordering::SeqCst);
        old_cancel.store(false, Ordering::SeqCst);

        let new_cancel = Arc::new(AtomicBool::new(false));
        let new_calls = Arc::new(AtomicUsize::new(0));
        let flag = new_cancel.clone();
        let calls = new_calls.clone();
        conn.lock_handle().await?.set_progress_handler(1, move || {
            calls.fetch_add(1, Ordering::SeqCst);
            !flag.load(Ordering::SeqCst)
        });
        old_cancel.store(true, Ordering::SeqCst); // late old-operation intent must be isolated.
        assert_eq!(sqlx::query_scalar::<_, i64>("SELECT 43").fetch_one(&mut conn).await?, 43);
        assert!(new_calls.load(Ordering::SeqCst) > 0);
        assert_eq!(old_calls.load(Ordering::SeqCst), old_count);
        conn.lock_handle().await?.remove_progress_handler();
        assert_eq!(Arc::strong_count(&new_cancel), 1);
        tokio::time::timeout(WAIT, conn.close()).await??;
        Ok(())
    }

    #[tokio::test]
    async fn pool_close_waits_for_checked_out_owner_and_rejects_new_acquire() -> TestResult {
        let pool = pool().await?;
        let held = pool.acquire().await?;
        let mut closing = Box::pin(pool.close());
        assert_pending_once(closing.as_mut()).await;
        assert!(pool.is_closed());
        assert!(matches!(pool.acquire().await, Err(sqlx::Error::PoolClosed)));
        drop(held);
        tokio::time::timeout(WAIT, closing).await?;
        assert_eq!(pool.size(), 0);
        // Pool close completion is not an observed OS JoinHandle/thread exit.
        Ok(())
    }
}
