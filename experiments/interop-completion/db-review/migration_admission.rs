//! Independent research review: raw BEGIN does not update SQLx transaction depth.
use sqlx::{Connection, SqliteConnection, migrate::Migrator};
type TestResult = Result<(), Box<dyn std::error::Error + Send + Sync>>;

fn migrations(label: &str, fail_second: bool) -> Result<std::path::PathBuf, std::io::Error> {
    let dir = std::env::temp_dir().join(format!("nw-independent-{label}-{}", std::process::id()));
    std::fs::create_dir(&dir)?;
    std::fs::write(dir.join("1_initial.sql"), "CREATE TABLE review_created(id INTEGER PRIMARY KEY);")?;
    if fail_second {
        std::fs::write(dir.join("2_fail.sql"), "CREATE TABLE review_partial(id INTEGER); INSERT INTO does_not_exist VALUES(1);")?;
    }
    Ok(dir)
}

#[tokio::test]
async fn raw_begin_negative_fails_nested_migrator_begin() -> TestResult {
    let dir = migrations("raw", false)?;
    let migrator = Migrator::new(dir.as_path()).await?;
    let mut conn = SqliteConnection::connect("sqlite::memory:").await?;
    sqlx::query("BEGIN IMMEDIATE").execute(&mut conn).await?;
    assert!(!conn.is_in_transaction(), "raw SQL bypassed SQLx's tracked transaction depth");
    let error = migrator.run(&mut conn).await.unwrap_err();
    println!("RAW_BEGIN_NEGATIVE: {error}");
    assert!(error.to_string().contains("cannot start a transaction within a transaction"));
    sqlx::query("ROLLBACK").execute(&mut conn).await?;
    conn.close().await?;
    std::fs::remove_dir_all(dir)?;
    Ok(())
}

#[tokio::test]
async fn tracked_begin_with_keeps_migrator_nested_and_outer_atomic() -> TestResult {
    let dir = migrations("tracked", false)?;
    let migrator = Migrator::new(dir.as_path()).await?;
    assert!(migrator.iter().all(|m| !m.no_tx));
    let mut conn = SqliteConnection::connect("sqlite::memory:").await?;
    let mut tx = conn.begin_with("BEGIN IMMEDIATE").await?;
    assert!(tx.is_in_transaction());
    migrator.run(&mut *tx).await?;
    assert!(tx.is_in_transaction(), "migration's nested commit must preserve outer transaction");
    tx.rollback().await?;
    assert!(!conn.is_in_transaction());
    assert_eq!(sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('review_created','_sqlx_migrations')").fetch_one(&mut conn).await?, 0);

    let mut tx = conn.begin_with("BEGIN IMMEDIATE").await?;
    migrator.run(&mut *tx).await?;
    tx.commit().await?;
    assert_eq!(sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM _sqlx_migrations").fetch_one(&mut conn).await?, 1);
    conn.close().await?;
    std::fs::remove_dir_all(dir)?;
    Ok(())
}

#[tokio::test]
async fn failed_nested_migration_rolls_back_whole_outer_batch() -> TestResult {
    let dir = migrations("failed", true)?;
    let migrator = Migrator::new(dir.as_path()).await?;
    let mut conn = SqliteConnection::connect("sqlite::memory:").await?;
    let mut tx = conn.begin_with("BEGIN IMMEDIATE").await?;
    assert!(migrator.run(&mut *tx).await.is_err());
    tx.rollback().await?;
    assert!(!conn.is_in_transaction());
    assert_eq!(sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('review_created','review_partial','_sqlx_migrations')").fetch_one(&mut conn).await?, 0);
    conn.close().await?;
    std::fs::remove_dir_all(dir)?;
    Ok(())
}
