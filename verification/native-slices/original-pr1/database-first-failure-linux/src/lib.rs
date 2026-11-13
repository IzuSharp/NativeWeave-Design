//! R22/R25 finite source-informed binder fixture, not a production ORM/ABI.
//! SeaQuery owns native statements. This adapter handles only the enumerated
//! scalar subset and never treats AssertSqlSafe as input sanitization.
use sea_query::{Value, Values};
use sqlx::{Arguments, Encode, Sqlite, Type, sqlite::SqliteArguments};

#[derive(Debug, PartialEq, Eq)]
pub enum Failure { Limit, Overflow, Unsupported(&'static str), Encoding(String) }
impl std::fmt::Display for Failure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { write!(f, "{self:?}") }
}
impl std::error::Error for Failure {}

fn add<'q, T: Encode<'q, Sqlite> + Type<Sqlite>>(a: &mut SqliteArguments, v: T) -> Result<(), Failure> {
    a.add(v).map_err(|e| Failure::Encoding(e.to_string()))
}
/// Preflight the limited fixture's argument conversion before allocating Arguments.
/// This does not bound an AST/Value already allocated by its caller or whole RSS.
pub fn sqlite_arguments(values: Values) -> Result<SqliteArguments, Failure> {
    if values.0.len() > 64 { return Err(Failure::Limit); }
    let mut bytes = 0usize;
    for v in &values.0 {
        let cost = match v {
            Value::Bool(_) => 1,
            Value::Int(_) | Value::BigInt(_) => 8,
            Value::BigUnsigned(Some(v)) if *v > i64::MAX as u64 => return Err(Failure::Overflow),
            Value::BigUnsigned(_) => 8,
            Value::String(v) => v.as_ref().map_or(0, String::len),
            Value::Bytes(v) => v.as_ref().map_or(0, Vec::len),
            _ => return Err(Failure::Unsupported("value variant outside finite fixture")),
        };
        bytes = bytes.checked_add(cost).ok_or(Failure::Limit)?;
        if bytes > 4096 { return Err(Failure::Limit); }
    }
    let mut args = SqliteArguments::default();
    for v in values.0 {
        match v {
            Value::Bool(v) => add(&mut args, v)?,
            Value::Int(v) => add(&mut args, v)?,
            Value::BigInt(v) => add(&mut args, v)?,
            Value::BigUnsigned(v) => add(&mut args, v.map(i64::try_from).transpose().map_err(|_| Failure::Overflow)?)?,
            Value::String(v) => add(&mut args, v)?,
            Value::Bytes(v) => add(&mut args, v)?,
            _ => return Err(Failure::Unsupported("value variant outside finite fixture")),
        }
    }
    Ok(args)
}

/// The native statement is private. Unsupported semantics are rejected at the
/// exposed entry point, not detected by searching a rendered SQL string.
pub struct SqliteSelect(sea_query::SelectStatement);
impl SqliteSelect {
    pub fn id_from(table: String) -> Result<Self, Failure> {
        if table.is_empty() || table.len() > 128 { return Err(Failure::Limit); }
        use sea_query::{Alias, Query};
        Ok(Self(Query::select().column(Alias::new("id")).from(Alias::new(table)).to_owned()))
    }
    pub fn for_update(self) -> Result<Self, Failure> { Err(Failure::Unsupported("SQLite row locking")) }
    pub fn build(self) -> (String, Values) { self.0.build(sea_query::SqliteQueryBuilder) }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sea_query::*;
    use sqlx::{Database, Row};
    use std::sync::atomic::{AtomicUsize, Ordering};
    type TestResult = Result<(), Box<dyn std::error::Error + Send + Sync>>;

    #[test]
    fn argument_bounds_null_and_unsigned() {
        assert_eq!(sqlite_arguments(Values(vec![Value::BigUnsigned(Some(u64::MAX))])).unwrap_err(), Failure::Overflow);
        assert_eq!(sqlite_arguments(Values(vec![Value::String(Some("x".repeat(4097)))])).unwrap_err(), Failure::Limit);
        assert_eq!(sqlite_arguments(Values(vec![Value::Int(Some(1));65])).unwrap_err(), Failure::Limit);
        assert!(matches!(sqlite_arguments(Values(vec![Value::Double(Some(1.0))])), Err(Failure::Unsupported(_))));
        let a = sqlite_arguments(Values(vec![Value::BigUnsigned(None), Value::BigInt(Some(2)), Value::String(None), Value::Bytes(Some(vec![1,2]))])).unwrap();
        assert_eq!(a.len(),4);
    }

    struct FailAfterWrite;
    impl Type<Sqlite> for FailAfterWrite {
        fn type_info() -> <Sqlite as Database>::TypeInfo { <i64 as Type<Sqlite>>::type_info() }
    }
    impl<'q> Encode<'q, Sqlite> for FailAfterWrite {
        fn encode_by_ref(&self, buf: &mut <Sqlite as Database>::ArgumentBuffer) -> Result<sqlx::encode::IsNull, sqlx::error::BoxDynError> {
            let _ = <i64 as Encode<'q,Sqlite>>::encode_by_ref(&123, buf)?;
            Err(std::io::Error::other("injected encoder failure after partial write").into())
        }
    }
    #[test]
    fn encoding_error_is_propagated_and_native_arguments_roll_back() {
        let mut a = SqliteArguments::default();
        add(&mut a, 7i64).unwrap();
        assert!(matches!(add(&mut a,FailAfterWrite),Err(Failure::Encoding(_))));
        assert_eq!(a.len(),1, "SQLx removes partially encoded argument");
    }

    #[test]
    fn sqlite_silent_row_lock_negative_control_and_explicit_rejection() {
        let raw = Query::select().column(Alias::new("id")).from(Alias::new("items")).lock(LockType::Update).to_owned();
        assert!(!raw.build(SqliteQueryBuilder).0.contains("FOR UPDATE"));
        assert!(raw.build(PostgresQueryBuilder).0.contains("FOR UPDATE"));
        assert!(matches!(SqliteSelect::id_from("items".into()).unwrap().for_update(),Err(Failure::Unsupported("SQLite row locking"))));
    }

    async fn execute(pool: &sqlx::SqlitePool, sql: String, values: Values, sends: &AtomicUsize) -> Result<u64, Box<dyn std::error::Error+Send+Sync>> {
        let arguments = sqlite_arguments(values)?;
        sends.fetch_add(1,Ordering::SeqCst);
        Ok(sqlx::query_with(sqlx::AssertSqlSafe(sql),arguments).execute(pool).await?.rows_affected())
    }
    #[tokio::test]
    async fn overflow_rejected_before_database_send() -> TestResult {
        let pool = sqlx::sqlite::SqlitePoolOptions::new().max_connections(1).connect("sqlite::memory:").await?;
        sqlx::query("CREATE TABLE items (id INTEGER)").execute(&pool).await?;
        let q = Query::insert().into_table(Alias::new("items")).columns([Alias::new("id")]).values([Value::BigUnsigned(Some(u64::MAX))])?.to_owned();
        let (sql,values)=q.build(SqliteQueryBuilder);let sends=AtomicUsize::new(0);
        let error=execute(&pool,sql,values,&sends).await.unwrap_err();
        assert_eq!(error.downcast_ref::<Failure>(),Some(&Failure::Overflow));
        assert_eq!(sends.load(Ordering::SeqCst),0);
        let n:i64=sqlx::query_scalar("SELECT COUNT(*) FROM items").fetch_one(&pool).await?;assert_eq!(n,0);
        pool.close().await;Ok(())
    }

    #[tokio::test]
    async fn runtime_tables_native_crud_and_injection_value() -> TestResult {
        let pool=sqlx::sqlite::SqlitePoolOptions::new().max_connections(1).connect("sqlite::memory:").await?;
        let sends=AtomicUsize::new(0);
        for table in ["Students", "Users\"2026"] {
            let create=Table::create().table(Alias::new(table)).col(ColumnDef::new(Alias::new("id")).big_integer().primary_key()).col(ColumnDef::new(Alias::new("name")).text()).to_owned();
            sqlx::query(sqlx::AssertSqlSafe(create.to_string(SqliteQueryBuilder))).execute(&pool).await?;
            let hostile="x' OR 1=1 --";
            let insert=Query::insert().into_table(Alias::new(table)).columns([Alias::new("id"),Alias::new("name")]).values([1i64.into(),hostile.into()])?.to_owned();
            let (sql,values)=insert.build(SqliteQueryBuilder);assert!(!sql.contains(hostile));
            assert_eq!(execute(&pool,sql,values,&sends).await?,1);
            let q=Query::select().column(Alias::new("name")).from(Alias::new(table)).and_where(Expr::col(Alias::new("name")).eq(hostile)).limit(8).to_owned();
            let (sql,values)=q.build(SqliteQueryBuilder);
            let row=sqlx::query_with(sqlx::AssertSqlSafe(sql),sqlite_arguments(values)?).fetch_one(&pool).await?;
            assert_eq!(row.try_get::<String,_>(0)?,hostile);
            assert!(row.try_get::<i64,_>(0).is_err(), "typed descriptor cannot excuse unchecked decoding");
            let update=Query::update().table(Alias::new(table)).value(Alias::new("name"),Value::String(None)).and_where(Expr::col(Alias::new("id")).eq(1i64)).to_owned();
            let (sql,values)=update.build(SqliteQueryBuilder);assert_eq!(execute(&pool,sql,values,&sends).await?,1);
            let (sql,values)=q.build(SqliteQueryBuilder);
            assert!(sqlx::query_with(sqlx::AssertSqlSafe(sql),sqlite_arguments(values)?).fetch_optional(&pool).await?.is_none());
            let delete=Query::delete().from_table(Alias::new(table)).and_where(Expr::col(Alias::new("name")).is_null()).to_owned();
            let (sql,values)=delete.build(SqliteQueryBuilder);assert_eq!(execute(&pool,sql,values,&sends).await?,1);
        }
        assert_eq!(sends.load(Ordering::SeqCst),6);pool.close().await;Ok(())
    }

    #[tokio::test]
    async fn explicit_transaction_rollback_and_schema_error() -> TestResult {
        let pool=sqlx::sqlite::SqlitePoolOptions::new().max_connections(1).connect("sqlite::memory:").await?;
        sqlx::query("CREATE TABLE items (id INTEGER)").execute(&pool).await?;
        let mut tx=pool.begin().await?;
        let q=Query::insert().into_table(Alias::new("items")).columns([Alias::new("id")]).values([1i64.into()])?.to_owned();
        let (sql,values)=q.build(SqliteQueryBuilder);
        sqlx::query_with(sqlx::AssertSqlSafe(sql),sqlite_arguments(values)?).execute(&mut *tx).await?;
        tx.rollback().await?;
        assert_eq!(sqlx::query_scalar::<_,i64>("SELECT COUNT(*) FROM items").fetch_one(&pool).await?,0);
        let q=Query::select().column(Alias::new("missing")).from(Alias::new("items")).to_owned();
        let (sql,values)=q.build(SqliteQueryBuilder);
        assert!(sqlx::query_with(sqlx::AssertSqlSafe(sql),sqlite_arguments(values)?).fetch_one(&pool).await.is_err());
        pool.close().await;Ok(())
    }
}
