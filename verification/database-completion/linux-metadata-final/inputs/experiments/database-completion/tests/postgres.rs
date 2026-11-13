//! Run explicitly with --ignored; requires a disposable PostgreSQL database.
//! No environment variable is silently treated as a successful skipped test.
use futures_util::TryStreamExt;
use sqlx::{Connection, PgConnection, postgres::{PgConnectOptions, PgSslMode}};
use std::{str::FromStr, sync::{Arc, atomic::{AtomicBool, Ordering}}, time::Duration};
use tokio::{io::{AsyncReadExt, AsyncWriteExt}, net::{TcpListener, TcpStream}, time::timeout};
type TestResult = Result<(), Box<dyn std::error::Error + Send + Sync>>;

fn options() -> PgConnectOptions {
    PgConnectOptions::from_str(&std::env::var("DATABASE_URL").expect("DATABASE_URL is required for explicit PostgreSQL tests")).expect("valid PostgreSQL URL").ssl_mode(PgSslMode::Disable)
}
async fn connect() -> Result<PgConnection, sqlx::Error> { PgConnection::connect_with(&options()).await }

#[tokio::test]
#[ignore = "requires disposable PostgreSQL; run --test postgres -- --ignored"]
async fn statement_timeout_needs_rollback_before_same_connection_reuse() -> TestResult {
    let mut db=connect().await?;
    println!("PostgreSQL server: {}",sqlx::query_scalar::<_,String>("SELECT version()").fetch_one(&mut db).await?);
    let pid:i32=sqlx::query_scalar("SELECT pg_backend_pid()").fetch_one(&mut db).await?;
    sqlx::query("BEGIN").execute(&mut db).await?;
    sqlx::query("SET LOCAL statement_timeout='50ms'").execute(&mut db).await?;
    let e=sqlx::query("SELECT pg_sleep(10)").execute(&mut db).await.unwrap_err();
    assert_eq!(e.as_database_error().and_then(|x|x.code()).as_deref(),Some("57014"));
    let e=sqlx::query("SELECT 1").execute(&mut db).await.unwrap_err();
    assert_eq!(e.as_database_error().and_then(|x|x.code()).as_deref(),Some("25P02"));
    sqlx::query("ROLLBACK").execute(&mut db).await?;
    assert_eq!(sqlx::query_scalar::<_,i32>("SELECT pg_backend_pid()").fetch_one(&mut db).await?,pid);
    assert_eq!(sqlx::query_scalar::<_,i32>("SELECT 7").fetch_one(&mut db).await?,7);
    db.close().await?; Ok(())
}

#[tokio::test]
#[ignore = "requires disposable PostgreSQL; run --test postgres -- --ignored"]
async fn early_row_stream_drop_drains_before_next_query() -> TestResult {
    let mut db=connect().await?;
    let pid:i32=sqlx::query_scalar("SELECT pg_backend_pid()").fetch_one(&mut db).await?;
    { let mut rows=sqlx::query("SELECT n FROM generate_series(1,20000) n").fetch(&mut db);
      assert!(rows.try_next().await?.is_some()); }
    timeout(Duration::from_secs(10),db.ping()).await??;
    assert_eq!(sqlx::query_scalar::<_,i32>("SELECT pg_backend_pid()").fetch_one(&mut db).await?,pid);
    assert_eq!(sqlx::query_scalar::<_,i32>("SELECT 42").fetch_one(&mut db).await?,42);
    db.close().await?; Ok(())
}

#[tokio::test]
#[ignore = "requires disposable PostgreSQL; run --test postgres -- --ignored"]
async fn codec_roundtrip_and_loss_are_observed() -> TestResult {
    let mut db=connect().await?;
    let uuid=uuid::Uuid::from_bytes([0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff]);
    let decimal=rust_decimal::Decimal::from_str("123456.125")?;
    let instant=chrono::DateTime::<chrono::Utc>::from_timestamp(1_700_000_000,123456000).unwrap();
    let actual:(uuid::Uuid,rust_decimal::Decimal,chrono::DateTime<chrono::Utc>,Option<i64>)=
        sqlx::query_as("SELECT $1::uuid,$2::numeric,$3::timestamptz,$4::bigint")
        .bind(uuid).bind(decimal).bind(instant).bind(None::<i64>).fetch_one(&mut db).await?;
    assert_eq!(actual,(uuid,decimal,instant,None));
    assert!(sqlx::query_scalar::<_,rust_decimal::Decimal>("SELECT 1e100::numeric").fetch_one(&mut db).await.is_err());
    let precise=chrono::DateTime::<chrono::Utc>::from_timestamp(1_700_000_000,123456789).unwrap();
    let rounded:chrono::DateTime<chrono::Utc>=sqlx::query_scalar("SELECT $1::timestamptz").bind(precise).fetch_one(&mut db).await?;
    assert_ne!(rounded,precise,"raw provider does not enforce NativeWeave's reject-loss policy");
    assert_eq!(rounded.timestamp_subsec_nanos(),123456000);
    db.close().await?; Ok(())
}

/// Test-only PostgreSQL protocol proxy. It forwards the startup packet, then
/// framed messages; after forwarding COMMIT it consumes the server response
/// through ReadyForQuery without sending any of it to the client. No TLS here.
async fn commit_ack_loss_proxy(listener: TcpListener, upstream: (String,u16),
    observed_commit: Arc<AtomicBool>) -> TestResult {
    let (client,_)=listener.accept().await?;
    let server=TcpStream::connect(upstream).await?;
    let (mut cr,mut cw)=client.into_split(); let (mut sr,mut sw)=server.into_split();
    let armed=Arc::new(AtomicBool::new(false)); let writer_armed=armed.clone();
    let request=tokio::spawn(async move {
        let n=cr.read_u32().await?;
        if !(8..=1_048_576).contains(&n) { return Err(std::io::Error::other("invalid startup frame")); }
        let mut bytes=vec![0; n as usize-4];cr.read_exact(&mut bytes).await?;
        sw.write_u32(n).await?;sw.write_all(&bytes).await?;
        loop {
            let tag=match cr.read_u8().await { Ok(t)=>t,Err(e) if e.kind()==std::io::ErrorKind::UnexpectedEof=>break,Err(e)=>return Err(e) };
            let n=cr.read_u32().await?;
            if !(4..=1_048_576).contains(&n) { return Err(std::io::Error::other("invalid request frame")); }
            let mut bytes=vec![0;n as usize-4];cr.read_exact(&mut bytes).await?;
            if tag==b'Q' && bytes==b"COMMIT\0" { writer_armed.store(true,Ordering::SeqCst); }
            sw.write_u8(tag).await?;sw.write_u32(n).await?;sw.write_all(&bytes).await?;
        }
        Ok::<(),std::io::Error>(())
    });
    let mut command_complete=false;
    let response:TestResult=async {
        loop {
            let tag=sr.read_u8().await?;let n=sr.read_u32().await?;
            if !(4..=1_048_576).contains(&n) { return Err(std::io::Error::other("invalid response frame").into()); }
            let mut bytes=vec![0;n as usize-4];sr.read_exact(&mut bytes).await?;
            if armed.load(Ordering::SeqCst) {
                if tag==b'C' { command_complete=bytes==b"COMMIT\0"; }
                if tag==b'Z' {
                    if !command_complete || bytes!=b"I" { return Err(std::io::Error::other("expected COMMIT then idle ReadyForQuery").into()); }
                    observed_commit.store(true,Ordering::SeqCst);cw.shutdown().await?;break;
                }
            } else { cw.write_u8(tag).await?;cw.write_u32(n).await?;cw.write_all(&bytes).await?; }
        }
        Ok(())
    }.await;
    request.abort();let _=request.await;response
}

#[tokio::test]
#[ignore = "requires disposable PostgreSQL; run --test postgres -- --ignored"]
async fn lost_commit_response_is_error_with_durable_effect() -> TestResult {
    let opts=options();let mut observer=PgConnection::connect_with(&opts).await?;
    sqlx::query("DROP TABLE IF EXISTS nw_commit_ack_loss").execute(&mut observer).await?;
    sqlx::query("CREATE TABLE nw_commit_ack_loss(id INTEGER PRIMARY KEY,result TEXT NOT NULL)").execute(&mut observer).await?;
    let listener=TcpListener::bind("127.0.0.1:0").await?;let port=listener.local_addr()?.port();
    let observed=Arc::new(AtomicBool::new(false));
    let proxy=tokio::spawn(commit_ack_loss_proxy(listener,(opts.get_host().to_string(),opts.get_port()),observed.clone()));
    let mut client=PgConnection::connect_with(&opts.clone().host("127.0.0.1").port(port)).await?;
    let mut tx=client.begin().await?;
    sqlx::query("INSERT INTO nw_commit_ack_loss VALUES(1,'durable')").execute(&mut *tx).await?;
    let commit_result=timeout(Duration::from_secs(10),tx.commit()).await?;
    assert!(commit_result.is_err(),"client must not have received the discarded acknowledgment");
    timeout(Duration::from_secs(10),proxy).await???;
    assert!(observed.load(Ordering::SeqCst));
    assert_eq!(sqlx::query_scalar::<_,String>("SELECT result FROM nw_commit_ack_loss WHERE id=1").fetch_one(&mut observer).await?,"durable");
    sqlx::query("DROP TABLE nw_commit_ack_loss").execute(&mut observer).await?;
    observer.close().await?;Ok(())
}

#[tokio::test]
#[ignore = "requires disposable PostgreSQL; run --test postgres -- --ignored"]
async fn conflict_cte_old_snapshot_needs_separate_recovery_statement() -> TestResult {
    let mut setup=connect().await?;
    sqlx::query("DROP TABLE IF EXISTS nw_idempotency_snapshot").execute(&mut setup).await?;
    sqlx::query("CREATE TABLE nw_idempotency_snapshot(key TEXT PRIMARY KEY,request_hash TEXT NOT NULL,operation_id BIGINT NOT NULL)").execute(&mut setup).await?;
    let mut holder=connect().await?;let mut tx=holder.begin().await?;
    sqlx::query("INSERT INTO nw_idempotency_snapshot VALUES('k','same',1)").execute(&mut *tx).await?;
    let mut contender=connect().await?;
    let pid:i32=sqlx::query_scalar("SELECT pg_backend_pid()").fetch_one(&mut contender).await?;
    let pending=tokio::spawn(async move {
        let row=sqlx::query_scalar::<_,i64>("WITH inserted AS (INSERT INTO nw_idempotency_snapshot VALUES('k','same',2) ON CONFLICT(key) DO NOTHING RETURNING operation_id) SELECT operation_id FROM inserted UNION ALL SELECT operation_id FROM nw_idempotency_snapshot WHERE key='k' LIMIT 1").fetch_optional(&mut contender).await;
        (contender,row)
    });
    // Synchronize with the actual server lock wait, not an assumed sleep window.
    timeout(Duration::from_secs(10),async {
        loop {
            let waiting:bool=sqlx::query_scalar("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=$1 AND NOT granted)").bind(pid).fetch_one(&mut setup).await?;
            if waiting { break; }
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
        Ok::<(),sqlx::Error>(())
    }).await??;
    tx.commit().await?;
    let (mut contender,old_snapshot)=timeout(Duration::from_secs(10),pending).await??;
    assert_eq!(old_snapshot?,None,"same-statement SELECT can miss the conflicting row");
    let recovered:(i64,String)=sqlx::query_as("SELECT operation_id,request_hash FROM nw_idempotency_snapshot WHERE key='k'").fetch_one(&mut contender).await?;
    assert_eq!(recovered,(1,"same".into()));
    contender.close().await?;holder.close().await?;
    sqlx::query("DROP TABLE nw_idempotency_snapshot").execute(&mut setup).await?;setup.close().await?;Ok(())
}
