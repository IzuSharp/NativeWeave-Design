#!/usr/bin/env python3
"""Research only. Builds one native binary, then changes only the C# entity.
This deliberately synchronous, SQLite-only, Int64/text prototype is NOT the
production async ABI, a general ORM, an SQL semantic proof, or a benchmark.
"""
import hashlib, json, os, pathlib, shutil, sqlite3, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT / 'work'
EVIDENCE = ROOT / 'evidence'
EVIDENCE.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
records = []
def write(path, text):
    p = WORK / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
def run(name, command, cwd=WORK, env=None, expected=0):
    started = time.time()
    with (EVIDENCE / (name + '.log')).open('w') as f:
        p = subprocess.run(command, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
    records.append({'name': name, 'command': command, 'exit_code': p.returncode,
                    'expected_exit': expected, 'elapsed_seconds': time.time()-started,
                    'log': name + '.log'})
    (EVIDENCE/'commands.json').write_text(json.dumps(records, indent=2)+'\n')
    if (expected == 0 and p.returncode != 0) or (expected != 0 and p.returncode == 0):
        print((EVIDENCE/(name+'.log')).read_text()[-14000:])
        raise RuntimeError('Unexpected exit: ' + name)

def digest(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

write('native/Cargo.toml', '''[package]
name = "nw-source-probe"
version = "0.0.1"
edition = "2024"
[lib]
name = "nw_source_probe"
crate-type = ["cdylib", "rlib"]
[dependencies]
sea-query = { version = "=1.0.2", default-features = false, features = ["backend-sqlite", "backend-postgres", "thread-safe"] }
sea-query-sqlx = { version = "=0.9.1", features = ["sqlx-sqlite"] }
sqlx = { version = "=0.9.0", default-features = false, features = ["runtime-tokio", "sqlite"] }
tokio = { version = "=1.54.1", features = ["rt", "net", "time"] }
serde_json = "1.0"
''')
write('native/src/lib.rs', r'''use sea_query::*;
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
''')
write('managed/NativeWeave.SourceProbe.csproj', '''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net11.0</TargetFramework><Nullable>enable</Nullable><AllowUnsafeBlocks>true</AllowUnsafeBlocks><IsAotCompatible>true</IsAotCompatible><PackageId>NativeWeave.SourceProbe</PackageId><Version>0.0.1</Version><Authors>NativeWeave research</Authors><Description>Non-production source-driven feasibility probe</Description></PropertyGroup><ItemGroup><None Include="../native/target/release/libnw_source_probe.so" Pack="true" PackagePath="runtimes/linux-x64/native/libnw_source_probe.so" /></ItemGroup></Project>''')
write('managed/Query.cs', r'''using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
namespace NativeWeave.SourceProbe;
public readonly record struct Column<T,V>(string Name);
public sealed record Table<T>(string Name,Func<JsonElement,T> Read);
public sealed class NativeHandle:SafeHandleZeroOrMinusOneIsInvalid{
 public NativeHandle():base(true){} internal NativeHandle(nint p):base(true){SetHandle(p);}
 protected override bool ReleaseHandle(){Native.nw_drop(handle);return true;}
}
[StructLayout(LayoutKind.Sequential)]internal struct Buffer{public nint Data;public nuint Length;}
internal static unsafe class Native{
 const string Lib="nw_source_probe";
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_new(byte* s,nuint n,out nint h);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern void nw_drop(nint h);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_column(NativeHandle h,byte* s,nuint n,uint kind);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_ge(NativeHandle h,byte* s,nuint n,long value);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_eq(NativeHandle h,byte* s,nuint n,byte* v,nuint m);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_order_limit(NativeHandle h,byte* s,nuint n,ulong limit);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_render(NativeHandle h,uint dialect,out Buffer b);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern int nw_execute(NativeHandle h,byte* s,nuint n,out Buffer b);
 [DllImport(Lib,CallingConvention=CallingConvention.Cdecl)]internal static extern void nw_free(Buffer b);
}
// Synchronous, exclusive-use research API. No production async or thread-safety claim.
public sealed unsafe class Query<T>:IDisposable{
 readonly NativeHandle handle;readonly Table<T> table;
 public Query(Table<T> table){this.table=table;var a=Encoding.UTF8.GetBytes(table.Name);fixed(byte* p=a){Check(Native.nw_new(p,(nuint)a.Length,out var h));handle=new NativeHandle(h);}}
 static void Check(int status){if(status!=0)throw new InvalidOperationException("Native status "+status);}
 public Query<T> Select(Column<T,long> c)=>Column(c.Name,1);
 public Query<T> Select(Column<T,string> c)=>Column(c.Name,2);
 Query<T> Column(string name,uint kind){var a=Encoding.UTF8.GetBytes(name);fixed(byte* p=a)Check(Native.nw_column(handle,p,(nuint)a.Length,kind));return this;}
 public Query<T> WhereGe(Column<T,long> c,long value){var a=Encoding.UTF8.GetBytes(c.Name);fixed(byte* p=a)Check(Native.nw_ge(handle,p,(nuint)a.Length,value));return this;}
 public Query<T> WhereEq(Column<T,string> c,string value){var a=Encoding.UTF8.GetBytes(c.Name);var b=Encoding.UTF8.GetBytes(value);fixed(byte* p=a)fixed(byte* q=b)Check(Native.nw_eq(handle,p,(nuint)a.Length,q,(nuint)b.Length));return this;}
 public Query<T> OrderTake(Column<T,long> c,ulong limit){var a=Encoding.UTF8.GetBytes(c.Name);fixed(byte* p=a)Check(Native.nw_order_limit(handle,p,(nuint)a.Length,limit));return this;}
 static string Consume(Buffer b){try{if(b.Length>1024*1024)throw new InvalidOperationException("Result budget");return Encoding.UTF8.GetString(new ReadOnlySpan<byte>((void*)b.Data,checked((int)b.Length)));}finally{Native.nw_free(b);}}
 public string Render(bool postgres=false){Check(Native.nw_render(handle,postgres?1u:0u,out var b));return Consume(b);}
 public IReadOnlyList<T> Run(string databaseUrl){var a=Encoding.UTF8.GetBytes(databaseUrl);int status;Buffer b;fixed(byte* p=a)status=Native.nw_execute(handle,p,(nuint)a.Length,out b);string text=Consume(b);if(status!=0)throw new InvalidOperationException(text);using var doc=JsonDocument.Parse(text);var rows=new List<T>();foreach(var row in doc.RootElement.EnumerateArray())rows.Add(table.Read(row));return rows;}
 public void Dispose()=>handle.Dispose();
}
''')
write('app/App.csproj', '''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net11.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings><PublishAot>true</PublishAot><InvariantGlobalization>true</InvariantGlobalization></PropertyGroup><ItemGroup><PackageReference Include="NativeWeave.SourceProbe" Version="0.0.1" /></ItemGroup></Project>''')
write('app/Program.cs', r'''using NativeWeave.SourceProbe;
using System.Text.Json;
static void Assert(bool ok,string message){if(!ok)throw new Exception(message);Console.WriteLine("PASS "+message);}
string url=args[0];
using(var q=new Query<Student>(Students.Table)){
 var rows=q.Select(Students.Id).Select(Students.Name).WhereGe(Students.Id,1).OrderTake(Students.Id,10).Run(url);
 Assert(rows.Count==2&&rows[0].Name=="Ada","Student real SQLx/SQLite select");
}
using(var q=new Query<Student>(Students.Table)){
 q.Select(Students.Id).Select(Students.Name).WhereEq(Students.Name,"x' OR 1=1 --");
 Assert(!q.Render().Contains("OR 1=1"),"value is not interpolated SQL");
 Assert(q.Run(url).Count==1,"injection-shaped value is a parameter");
 Assert(q.Render(true).Contains("$1"),"PostgreSQL placeholder rendering only");
}
using(var q=new Query<Student>(Students.Table)){
 bool rejected=false;try{q.OrderTake(Students.Id,101);}catch(InvalidOperationException){rejected=true;}Assert(rejected,"native row budget rejects overflow");
}
using(var q=new Query<Student>(new Table<Student>("missing",Students.Table.Read))){
 bool rejected=false;try{q.Select(Students.Id).Select(Students.Name).Run(url);}catch(InvalidOperationException){rejected=true;}Assert(rejected,"database error crosses boundary as failure");
}
Extra.Run(url);
public sealed record Student(long Id,string Name);
public static class Students{
 public static readonly Table<Student> Table=new("student",static e=>new(e.GetProperty("Id").GetInt64(),e.GetProperty("Name").GetString()!));
 public static readonly Column<Student,long> Id=new("Id");public static readonly Column<Student,string> Name=new("Name");
}
''')
write('app/Extra.cs','public static class Extra { public static void Run(string url) {} }\n')
fixture=WORK/'fixture.db'
with sqlite3.connect(fixture) as db:
    db.executescript('CREATE TABLE student(Id INTEGER PRIMARY KEY, Name TEXT NOT NULL); CREATE TABLE app_user(Id INTEGER PRIMARY KEY, Name TEXT NOT NULL);')
    db.executemany('INSERT INTO student VALUES(?,?)',[(1,'Ada'),(2,"x' OR 1=1 --")])
    db.execute('INSERT INTO app_user VALUES(7,?)',('Grace',))
run('environment',['bash','-c','rustc --version; cargo --version; dotnet --info; uname -a'])
run('cargo-lock',['cargo','generate-lockfile'],WORK/'native')
run('rust-tests',['cargo','test','--locked'],WORK/'native')
run('native-release',['cargo','build','--release','--locked'],WORK/'native')
run('cargo-metadata',['cargo','metadata','--locked','--format-version','1'],WORK/'native')
shutil.copyfile(WORK/'native/Cargo.lock',EVIDENCE/'Cargo.lock')
lib=WORK/'native/target/release/libnw_source_probe.so'
before=digest(lib)
run('pack',['dotnet','pack','managed/NativeWeave.SourceProbe.csproj','-c','Release','-o','feed'])
write('app/NuGet.Config',f'''<configuration><packageSources><clear/><add key="probe" value="{WORK / 'feed'}"/><add key="nuget" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>''')
# The consumer phase is intentionally unable to invoke Cargo/rustc through PATH.
# This is invocation isolation, NOT a claim that the runner has no Rust installed.
blocked=WORK/'no-rust';blocked.mkdir(exist_ok=True)
for name in ['cargo','rustc','rustup']:
    p=blocked/name;p.write_text('#!/bin/sh\necho "Rust invocation forbidden in consumer phase" >&2\nexit 97\n');p.chmod(0o755)
env=os.environ.copy();env['PATH']=str(blocked)+os.pathsep+env['PATH']
url='sqlite:'+str(fixture)
run('consumer-build',['dotnet','build','app/App.csproj','-c','Release','-r','linux-x64'],env=env)
run('consumer-run',['dotnet','run','--project','app/App.csproj','-c','Release','-r','linux-x64','--no-build','--',url],env=env)
run('consumer-aot-publish',['dotnet','publish','app/App.csproj','-c','Release','-r','linux-x64','-o','publish-v1'],env=env)
run('consumer-aot-run',[str(WORK/'publish-v1/App'),url],env=env)
write('app/Extra.cs',r'''using NativeWeave.SourceProbe;
public sealed record User(long Id,string Name);
public static class Extra{
 public static void Run(string url){
  var table=new Table<User>("app_user",static e=>new(e.GetProperty("Id").GetInt64(),e.GetProperty("Name").GetString()!));
  var id=new Column<User,long>("Id");var name=new Column<User,string>("Name");
  using var q=new Query<User>(table);var rows=q.Select(id).Select(name).WhereGe(id,7).Run(url);
  if(rows.Count!=1||rows[0].Name!="Grace")throw new System.Exception("new entity");
  System.Console.WriteLine("PASS new User entity uses identical native library");
 }
}
''')
run('new-entity-build',['dotnet','build','app/App.csproj','-c','Release','-r','linux-x64'],env=env)
run('new-entity-run',['dotnet','run','--project','app/App.csproj','-c','Release','-r','linux-x64','--no-build','--',url],env=env)
run('new-entity-aot-publish',['dotnet','publish','app/App.csproj','-c','Release','-r','linux-x64','-o','publish-v2'],env=env)
run('new-entity-aot-run',[str(WORK/'publish-v2/App'),url],env=env)
# A wrong entity column must be rejected by ordinary C# type checking.
write('app/Bad.cs',r'''using NativeWeave.SourceProbe; public static class Bad { public static void Test(Query<Student> q){q.Select(new Column<User,long>("Id"));} }''')
run('wrong-entity-compile-negative',['dotnet','build','app/App.csproj','-c','Release','-r','linux-x64'],env=env,expected=1)
(WORK/'app/Bad.cs').unlink()
after=digest(lib)
assert before==after
assert digest(WORK/'publish-v1/libnw_source_probe.so')==before
assert digest(WORK/'publish-v2/libnw_source_probe.so')==before
result={'status':'passed','run_id':os.environ.get('GITHUB_RUN_ID'),'native_sha256_before':before,'native_sha256_after':after,'source_probe_sha256':digest(__file__),'new_entity_required_native_rebuild':False,'consumer_rust_invocations':'PATH denied by exit97 shims','row_types':['Int64','text'],'platform':'linux-x64','database':'SQLite','transport':'bounded query / JSON result prototype','mapping':'explicit static C# descriptors and DTO constructors, no Source Generator executed','not_proven':['Windows','PostgreSQL execution','production async/cancellation ABI','transaction commit ambiguity','streaming','throughput/latency/memory improvement','full ORM semantics','actual clean machine without installed Rust','source-generator implementation']}
(EVIDENCE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
