using System;
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
