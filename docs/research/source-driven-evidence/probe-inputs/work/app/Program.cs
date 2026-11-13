using NativeWeave.SourceProbe;
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
