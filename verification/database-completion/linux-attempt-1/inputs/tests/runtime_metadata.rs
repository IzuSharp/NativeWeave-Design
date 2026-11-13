//! R20/R22/R24/R25: finite source-driven experiments; no product implementation.
use sea_orm::{ConnectionTrait, Database, DbBackend, Statement, dynamic::{FieldType, ModelType}};
use sea_query::{Alias, ArrayType, Expr, ExprTrait, IntoIden, JoinType, Order, Query, SqliteQueryBuilder, Value};
use sqlx::{Connection, Row};
use nw_database_boundary_probe::sqlite_arguments;
type TestResult = Result<(), Box<dyn std::error::Error + Send + Sync>>;

#[tokio::test]
async fn seaorm_public_dynamic_projection_needs_no_static_entity() -> TestResult {
    let db = Database::connect("sqlite::memory:").await?;
    // Runtime names: neither table has an EntityTrait/Model Rust declaration.
    for (table, field, value) in [("Students", "name", "Ada"), ("Projects", "title", "Native") ] {
        db.execute_unprepared(&format!("CREATE TABLE \"{table}\" (id INTEGER PRIMARY KEY, \"{field}\" TEXT NULL)")).await?;
        db.execute_raw(Statement::from_sql_and_values(DbBackend::Sqlite,
            format!("INSERT INTO \"{table}\" VALUES (?, ?)"), [1i64.into(), value.into()])).await?;
        let query = Query::select().columns([Alias::new("id"), Alias::new(field)])
            .from(Alias::new(table)).and_where(Expr::col(Alias::new("id")).eq(1i64)).to_owned();
        let row = db.query_one(&query).await?.expect("one runtime row");
        let shape = ModelType { fields: vec![FieldType::new(Alias::new("id").into_iden(), ArrayType::BigInt),
            FieldType::new(Alias::new(field).into_iden(), ArrayType::String)] };
        let model = shape.from_query_result(&row, "")?;
        assert_eq!(model.try_get("id")?, &Value::BigInt(Some(1)));
        assert_eq!(model.try_get(field)?, &Value::String(Some(value.to_string())));
        assert!(model.try_get("absent").is_err());
        let wrong = ModelType { fields: vec![FieldType::new(Alias::new(field).into_iden(), ArrayType::BigInt)] };
        assert!(wrong.from_query_result(&row, "").is_err());
        let missing = ModelType { fields: vec![FieldType::new(Alias::new("absent").into_iden(), ArrayType::String)] };
        assert!(missing.from_query_result(&row, "").is_err());
        db.execute_raw(Statement::from_sql_and_values(DbBackend::Sqlite,
            format!("UPDATE \"{table}\" SET \"{field}\" = ?"), [Value::String(None)])).await?;
        let null_row = db.query_one(&query).await?.expect("nullable row");
        assert_eq!(shape.from_query_result(&null_row, "")?.try_get(field)?, &Value::String(None));
    }
    db.close().await?;
    Ok(())
}

#[tokio::test]
async fn native_join_aggregate_matches_independent_sql_oracle() -> TestResult {
    let mut db = sqlx::SqliteConnection::connect("sqlite::memory:").await?;
    sqlx::raw_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY); CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER, amount INTEGER); INSERT INTO parent VALUES (1),(2),(3); INSERT INTO child VALUES (10,1,7),(11,1,9),(12,2,NULL);").execute(&mut db).await?;
    let query = Query::select()
        .column((Alias::new("parent"), Alias::new("id")))
        .expr(Expr::col((Alias::new("child"), Alias::new("id"))).count())
        .expr(Expr::col((Alias::new("child"), Alias::new("amount"))).sum())
        .from(Alias::new("parent"))
        .join(JoinType::LeftJoin, Alias::new("child"),
            Expr::col((Alias::new("parent"), Alias::new("id"))).equals((Alias::new("child"), Alias::new("parent_id"))))
        .group_by_col((Alias::new("parent"), Alias::new("id")))
        .order_by((Alias::new("parent"), Alias::new("id")), Order::Asc).to_owned();
    let (sql, values) = query.build(SqliteQueryBuilder);
    let actual = sqlx::query_with(sqlx::AssertSqlSafe(sql), sqlite_arguments(values)?).fetch_all(&mut db).await?;
    let expected: Vec<(i64,i64,Option<i64>)> = sqlx::query_as("SELECT p.id,COUNT(c.id),SUM(c.amount) FROM parent p LEFT JOIN child c ON p.id=c.parent_id GROUP BY p.id ORDER BY p.id").fetch_all(&mut db).await?;
    let decoded: Vec<(i64,i64,Option<i64>)> = actual.iter().map(|r| Ok((r.try_get(0)?,r.try_get(1)?,r.try_get(2)?))).collect::<Result<_,sqlx::Error>>()?;
    assert_eq!(decoded, expected);
    assert_eq!(decoded, vec![(1,2,Some(16)), (2,1,None), (3,0,None)]);
    db.close().await?; Ok(())
}

#[tokio::test]
async fn native_cas_preserves_tenant_and_not_set_null_distinction() -> TestResult {
    let mut db=sqlx::SqliteConnection::connect("sqlite::memory:").await?;
    sqlx::query("CREATE TABLE item(tenant INTEGER,id INTEGER,version INTEGER,name TEXT NULL,untouched TEXT,PRIMARY KEY(tenant,id))").execute(&mut db).await?;
    sqlx::query("INSERT INTO item VALUES (7,1,0,'old','keep'),(8,1,0,'other','keep')").execute(&mut db).await?;
    let update=Query::update().table(Alias::new("item"))
        .value(Alias::new("name"),Value::String(None))
        .value(Alias::new("version"),1i64)
        .and_where(Expr::col(Alias::new("tenant")).eq(7i64))
        .and_where(Expr::col(Alias::new("id")).eq(1i64))
        .and_where(Expr::col(Alias::new("version")).eq(0i64)).to_owned();
    for expected in [1,0] { let (sql,values)=update.build(SqliteQueryBuilder);
        assert_eq!(sqlx::query_with(sqlx::AssertSqlSafe(sql),sqlite_arguments(values)?).execute(&mut db).await?.rows_affected(), expected); }
    let row:(Option<String>,String,i64)=sqlx::query_as("SELECT name,untouched,version FROM item WHERE tenant=7 AND id=1").fetch_one(&mut db).await?;
    assert_eq!(row,(None,"keep".into(),1));
    assert_eq!(sqlx::query_scalar::<_,String>("SELECT name FROM item WHERE tenant=8 AND id=1").fetch_one(&mut db).await?,"other");
    db.close().await?; Ok(())
}

#[tokio::test]
async fn sqlite_foreign_key_and_savepoint_recovery_are_explicit() -> TestResult {
    let mut db=sqlx::SqliteConnection::connect("sqlite::memory:").await?;
    sqlx::query("PRAGMA foreign_keys=ON").execute(&mut db).await?;
    sqlx::raw_sql("CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(id INTEGER PRIMARY KEY,parent_id INTEGER REFERENCES parent(id)); INSERT INTO parent VALUES(1);").execute(&mut db).await?;
    let mut tx=db.begin().await?;
    sqlx::query("SAVEPOINT nw_1").execute(&mut *tx).await?;
    assert!(sqlx::query("INSERT INTO child VALUES(1,999)").execute(&mut *tx).await.is_err());
    sqlx::query("ROLLBACK TO SAVEPOINT nw_1").execute(&mut *tx).await?;
    sqlx::query("RELEASE SAVEPOINT nw_1").execute(&mut *tx).await?;
    sqlx::query("INSERT INTO child VALUES(2,1)").execute(&mut *tx).await?;
    tx.commit().await?;
    assert_eq!(sqlx::query_scalar::<_,i64>("SELECT COUNT(*) FROM child").fetch_one(&mut db).await?,1);
    db.close().await?; Ok(())
}
