using NativeWeave.SourceProbe;
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
