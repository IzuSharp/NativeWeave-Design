use sea_query::*;
use sea_query_sqlx::SqlxBinder;
use sqlx::Row;
use std::{panic::{catch_unwind, AssertUnwindSafe}, ptr, slice, str};

// All pointers must originate from this module and remain live for the call.
// C# SafeHandle supplies call leases. This is not an arbitrary-pointer-safe ABI.
struct QueryHandle { stmt: SelectStatement, columns: Vec<(String,u32)>, terms: usize }
#[repr(C)]
pub struct Buffer { pub data: *mut u8, pub len: usize }
fn output(out: *mut Buffer, bytes: Vec<u8>) {
    let len = bytes.len();
    let data = Box::into_raw(bytes.into_boxed_slice()) as *mut u8;
    unsafe { *out = Buffer { data, len }; }
}
fn input(p: *const u8, len: usize) -> Result<String,String> {
    if len > 4096 || (len != 0 && p.is_null()) { return Err("input budget/pointer".into()); }
    let bytes = if len == 0 { &[] } else { unsafe { slice::from_raw_parts(p,len) } };
    str::from_utf8(bytes).map(str::to_owned).map_err(|_| "invalid UTF-8".into())
}
fn status(f: impl FnOnce() -> Result<(),String>) -> i32 {
    match catch_unwind(AssertUnwindSafe(f)) { Ok(Ok(())) => 0, Ok(Err(_))=>1, Err(_)=>2 }
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_new(p:*const u8,n:usize,out:*mut *mut std::ffi::c_void)->i32 {
    if out.is_null(){return 1} unsafe{*out=ptr::null_mut()};
    status(|| { let table=input(p,n)?; if table.is_empty(){return Err("empty table".into())}
        let mut stmt=Query::select(); stmt.from(Alias::new(table)).limit(100);
        unsafe{*out=Box::into_raw(Box::new(QueryHandle{stmt,columns:vec![],terms:0})).cast()}; Ok(()) })
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_drop(p:*mut std::ffi::c_void){ if !p.is_null(){unsafe{drop(Box::from_raw(p.cast::<QueryHandle>()))}} }
#[unsafe(no_mangle)]
pub extern "C" fn nw_column(p:*mut std::ffi::c_void,s:*const u8,n:usize,kind:u32)->i32 {
    if p.is_null(){return 1} status(|| {let q=unsafe{&mut *p.cast::<QueryHandle>()};
        if q.columns.len()>=32 || !(kind==1||kind==2){return Err("column budget/type".into())}
        let name=input(s,n)?; q.stmt.column(Alias::new(name.clone())); q.columns.push((name,kind)); Ok(())})
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_ge(p:*mut std::ffi::c_void,s:*const u8,n:usize,v:i64)->i32 {
    if p.is_null(){return 1} status(||{let q=unsafe{&mut *p.cast::<QueryHandle>()};
        if q.terms>=128{return Err("term budget".into())} let col=input(s,n)?;
        q.stmt.and_where(Expr::col(Alias::new(col)).gte(v));q.terms+=1;Ok(())})
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_eq(p:*mut std::ffi::c_void,s:*const u8,n:usize,v:*const u8,m:usize)->i32 {
    if p.is_null(){return 1} status(||{let q=unsafe{&mut *p.cast::<QueryHandle>()};
        if q.terms>=128{return Err("term budget".into())}let col=input(s,n)?;let value=input(v,m)?;
        q.stmt.and_where(Expr::col(Alias::new(col)).eq(value));q.terms+=1;Ok(())})
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_order_limit(p:*mut std::ffi::c_void,s:*const u8,n:usize,limit:u64)->i32 {
    if p.is_null(){return 1}status(||{if limit>100{return Err("row budget".into())}
        let q=unsafe{&mut *p.cast::<QueryHandle>()};q.stmt.order_by(Alias::new(input(s,n)?),Order::Asc).limit(limit);Ok(())})
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_render(p:*mut std::ffi::c_void,dialect:u32,out:*mut Buffer)->i32 {
    if p.is_null()||out.is_null(){return 1} unsafe{*out=Buffer{data:ptr::null_mut(),len:0}};
    status(||{let q=unsafe{&*p.cast::<QueryHandle>()};let(sql,values)=match dialect{0=>q.stmt.build(SqliteQueryBuilder),1=>q.stmt.build(PostgresQueryBuilder),_=>return Err("dialect".into())};
        output(out,serde_json::to_vec(&serde_json::json!({"sql":sql,"parameter_count":values.0.len()})).unwrap());Ok(())})
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_execute(p:*mut std::ffi::c_void,s:*const u8,n:usize,out:*mut Buffer)->i32 {
    if p.is_null()||out.is_null(){return 1} unsafe{*out=Buffer{data:ptr::null_mut(),len:0}};
    let result=catch_unwind(AssertUnwindSafe(||->Result<Vec<u8>,String>{
        let q=unsafe{&*p.cast::<QueryHandle>()};if q.columns.is_empty(){return Err("no projection".into())}
        let url=input(s,n)?;let (sql,values)=q.stmt.build_sqlx(SqliteQueryBuilder);
        let rt=tokio::runtime::Builder::new_current_thread().enable_all().build().map_err(|e|e.to_string())?;
        rt.block_on(async{
            let pool=sqlx::sqlite::SqlitePoolOptions::new().max_connections(1).connect(&url).await.map_err(|e|e.to_string())?;
            let rows=sqlx::query_with(sqlx::AssertSqlSafe(sql.as_str()),values).fetch_all(&pool).await.map_err(|e|e.to_string())?;
            let mut result=Vec::new();
            for row in rows{let mut obj=serde_json::Map::new();for(i,(name,kind))in q.columns.iter().enumerate(){
                let value=match kind{1=>serde_json::to_value(row.try_get::<Option<i64>,_>(i).map_err(|e|e.to_string())?).unwrap(),
                2=>serde_json::to_value(row.try_get::<Option<String>,_>(i).map_err(|e|e.to_string())?).unwrap(),_=>unreachable!()};obj.insert(name.clone(),value);}
                result.push(serde_json::Value::Object(obj));}
            pool.close().await;serde_json::to_vec(&result).map_err(|e|e.to_string())
        })
    }));
    match result{Ok(Ok(bytes))=>{output(out,bytes);0},Ok(Err(e))=>{output(out,e.into_bytes());1},Err(_)=>{output(out,b"panic contained".to_vec());2}}
}
#[unsafe(no_mangle)]
pub extern "C" fn nw_free(b:Buffer){if !b.data.is_null(){unsafe{drop(Box::from_raw(ptr::slice_from_raw_parts_mut(b.data,b.len)))}}}

#[cfg(test)]mod tests{
 use super::*;
 #[test]fn dynamic_identifiers_and_parameters(){
  let mut q=Query::select();q.column(Alias::new("Id")).from(Alias::new("odd\"table")).and_where(Expr::col(Alias::new("Name")).eq("x' OR 1=1 --"));
  let(sql,values)=q.build(PostgresQueryBuilder);assert!(sql.contains("\"odd\"\"table\""));assert!(sql.contains("$1"));assert!(!sql.contains("OR 1=1"));assert_eq!(values.0.len(),1);
 }
 #[test]fn crud_and_advanced_shapes(){
  let t=Alias::new("people");let id=Alias::new("Id");let name=Alias::new("Name");
  let insert=Query::insert().into_table(t.clone()).columns([id.clone(),name.clone()]).values([1i64.into(),"A".into()]).unwrap().to_owned();
  assert!(insert.build(SqliteQueryBuilder).0.starts_with("INSERT"));
  let update=Query::update().table(t.clone()).value(name.clone(),"B").and_where(Expr::col(id.clone()).eq(1i64)).to_owned();assert_eq!(update.build(PostgresQueryBuilder).1.0.len(),2);
  let delete=Query::delete().from_table(t.clone()).and_where(Expr::col(id.clone()).eq(2i64)).to_owned();assert!(delete.build(PostgresQueryBuilder).0.starts_with("DELETE"));
  let sub=Query::select().column(id.clone()).from(t.clone()).to_owned();
  let mut q=Query::select();q.column((Alias::new("p"),id.clone())).from_as(t,Alias::new("p"))
   .join_subquery(JoinType::LeftJoin,sub.clone(),Alias::new("s"),Expr::col((Alias::new("p"),id.clone())).equals((Alias::new("s"),id.clone())))
   .cond_where(Condition::any().add(Expr::col((Alias::new("p"),id.clone())).is_null()).add(Expr::col((Alias::new("p"),id.clone())).gte(1i64)))
   .group_by_col((Alias::new("p"),id.clone())).and_having(Expr::col((Alias::new("p"),id.clone())).count().gt(0i64));
  assert!(q.build(PostgresQueryBuilder).0.contains("HAVING"));
  let cte=CommonTableExpression::new().table_name(Alias::new("subset")).query(sub).to_owned();
  let mut select=Query::select();select.column(id.clone()).from(Alias::new("subset")).with_cte(WithClause::new().cte(cte).to_owned());assert!(select.build(SqliteQueryBuilder).0.starts_with("WITH"));
  let mut window=Query::select();window.expr(Expr::col(id.clone()).max().over(WindowStatement::partition_by(name)).alias("w")).from(Alias::new("people"));assert!(window.build(PostgresQueryBuilder).0.contains("OVER"));
 }
 #[test]fn sqlite_execution_crud_and_bad_shape(){
  let rt=tokio::runtime::Builder::new_current_thread().enable_all().build().unwrap();rt.block_on(async{
   let pool=sqlx::SqlitePool::connect("sqlite::memory:").await.unwrap();
   sqlx::query("CREATE TABLE people(Id INTEGER PRIMARY KEY, Name TEXT)").execute(&pool).await.unwrap();
   let insert=Query::insert().into_table(Alias::new("people")).columns([Alias::new("Id"),Alias::new("Name")]).values([1i64.into(),"A".into()]).unwrap().to_owned();let(s,v)=insert.build_sqlx(SqliteQueryBuilder);sqlx::query_with(sqlx::AssertSqlSafe(s.as_str()),v).execute(&pool).await.unwrap();
   let update=Query::update().table(Alias::new("people")).value(Alias::new("Name"),"B").and_where(Expr::col(Alias::new("Id")).eq(1i64)).to_owned();let(s,v)=update.build_sqlx(SqliteQueryBuilder);assert_eq!(sqlx::query_with(sqlx::AssertSqlSafe(s.as_str()),v).execute(&pool).await.unwrap().rows_affected(),1);
   let q=Query::select().column(Alias::new("Name")).from(Alias::new("people")).to_owned();let(s,v)=q.build_sqlx(SqliteQueryBuilder);let row=sqlx::query_with(sqlx::AssertSqlSafe(s.as_str()),v).fetch_one(&pool).await.unwrap();assert_eq!(row.get::<String,_>(0),"B");
   let delete=Query::delete().from_table(Alias::new("people")).to_owned();let(s,v)=delete.build_sqlx(SqliteQueryBuilder);assert_eq!(sqlx::query_with(sqlx::AssertSqlSafe(s.as_str()),v).execute(&pool).await.unwrap().rows_affected(),1);
   // A builder is not a database validator: missing columns render but fail execution.
   let invalid=Query::select().column(Alias::new("Missing")).from(Alias::new("no_such_table")).to_owned();let(s,v)=invalid.build_sqlx(SqliteQueryBuilder);assert!(sqlx::query_with(sqlx::AssertSqlSafe(s.as_str()),v).fetch_all(&pool).await.is_err());pool.close().await;
  });
 }
 #[test]fn unchecked_unsigned_binder_negative_control(){
  use sqlx::IntoArguments;let value=sea_query_sqlx::SqlxValues(Values(vec![Value::BigUnsigned(Some(u64::MAX))]));
  assert!(catch_unwind(AssertUnwindSafe(||{let _:sqlx::sqlite::SqliteArguments=value.into_arguments();})).is_err());
 }
}
