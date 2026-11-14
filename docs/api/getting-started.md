# Getting started with the designed NativeWeave API

Version: 0.4.0. **Design-stage consumer guide; NativeWeave product packages are not
released.** The examples below identify their validation scope. They are the
publication blueprint for B21/A16/B24, not instructions to install an existing
product. Exact declarations live in [the generated reference](reference.md).

## 1. Choose one engine and one ordinary application

The stable toolchain for this revision is .NET SDK 11.0.100 and C# 15.0. The initial
native release profiles are Linux x64 and Windows x64, subject to their actual
release gates. A normal consumer needs the .NET SDK and the platform's Native AOT
linker prerequisites when publishing AOT. It does not need Rust, Cargo, a remote
native build service, `rd.xml`, reflection-preservation files or manual FFI code.

Once a validated product release exists, the database journey will be:

```bash
dotnet new console -f net11.0 -n MyDatabaseApp
cd MyDatabaseApp
dotnet add package NativeWeave.Database.Sqlite --version <validated-release-version>
dotnet build
dotnet run
dotnet publish -c Release -r linux-x64 -p:PublishAot=true
```

For PostgreSQL replace the provider package with `NativeWeave.Database.PostgreSql`.
For an HTTP application start with `NativeWeave.Server`. Database providers do not
install Server, and Server does not install a database provider. Optional DI,
Hosting, gRPC and MCP packages extend those same owners. See the exact dependency
and asset closure in [NuGet consumption](nuget-and-consumption.md).

The application project needs no NativeWeave-specific bootstrapping target. Normal
SDK settings are sufficient:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net11.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
```

The command-line `PublishAot` switch enables publishing; it is not a user-maintained
compatibility workaround. Native linker installation remains an ordinary .NET
platform prerequisite, distinct from building Rust engines.

## 2. Define a model and query typed columns

The default product generator discovers an attributed model and emits static
descriptors in its namespace. Entity registration is not repeated in a builder.

```csharp
using NativeWeave.Data;

[WeaveTable("students", DescriptorName = "Students")]
public sealed partial record Student(
    [property: WeaveKey, WeaveColumn("id")] long Id,
    [property: WeaveColumn("name")] string Name,
    [property: WeaveColumn("age")] int Age,
    [property: WeaveColumn("email")] string? Email,
    [property: WeaveVersion, WeaveColumn("version")] long Version);
```

`Students.Table`, `Students.Id` and the other generated columns have exact generic
types. A property without `WeaveColumn` keeps its CLR property name exactly;
the explicit attributes above match the lowercase database schema and the
handwritten mapping. `WeaveVersion` marks the explicitly checked concurrency
token; it does not increment the version automatically.
The current [database consumer](../../experiments/public-api/NativeWeave.Api.Consumers/DatabaseExamples.cs)
contains the explicit handwritten equivalent of that output so the declaration
fixture can compile all calls without pretending the complete product generator
exists. The separate packaging probe executes a deliberately limited real
generator and verifies transitive installation; its supported subset is documented
in [the evidence guide](../../experiments/public-api/README.md).

With the table/schema created by an explicit migration, the consumer is:

```csharp
using NativeWeave.Database.Sqlite;
using NativeWeave.Query;

await using var source = SqliteDataSource.Create("students.db");
await using var session = await source.OpenSessionAsync(cancellationToken);
using var query = session.From(Students.Table);
var students = await query
    .WhereGreaterThanOrEqual(Students.Age, 18)
    .OrderBy(Students.Id)
    .Take(100)
    .SelectAll()
    .ToListAsync(cancellationToken);
```

This is the compiled `DatabaseExamples.MinimalAsync` shape, not executed SQL in
the design fixture. Construction validates and snapshots configuration; opening a
session performs the asynchronous pool/connection work. `await using` closes
session/source ownership, and `using` releases the native query builder. The
provider executes SQL through Rust SQLx; SeaQuery owns query AST and dialect work.

Dynamic conditions are ordinary C# control flow over the same typed builder:

```csharp
using var query = session.From(Students.Table);
if (minimumAge is int age)
    query.WhereGreaterThanOrEqual(Students.Age, age);
query.WhereIf(requireEmail, row => row.IsNotNull(Students.Email));
```

No `Expression.Compile`, dynamic assembly, runtime LINQ provider or per-model Rust
compilation is involved. `WhereIf(false, ...)` does not invoke its builder delegate.
Complex native expressions use scoped typed `SqlExpression<T>`/`SqlPredicate`
values. Their owner and lifetime restrictions are explicit in the
[ORM guide](guides.md#2-orm-and-fluent-composition).

For the first durable application, use a checksummed migration bundle. Do not hide
schema creation or automatic destructive migration inside `Create` or `Build`.
Connection strings, schema evolution and business models are normal application
configuration; AOT glue is framework responsibility.

## 3. Serve the first HTTP route

Install only the Server package for the ordinary host:

```csharp
using NativeWeave.Server;

await using var app = NativeServer.CreateBuilder().Build();
app.MapGet("/", static () => Results.Text("Hello from Rust + C#"));
await app.RunAsync(cancellationToken);
```

This exact shape is compiled in `ServerExamples.MinimalAsync`. Build freezes host
configuration; routes/middleware remain configurable until startup freezes the
application route snapshot. Rust owns listeners, TLS, HTTP and network scheduling.
No Kestrel server or ASP.NET FrameworkReference is required in the product package.
The Design project's optional offline framework reference is a compiler fixture,
not the promised product dependency graph.

Typed JSON uses static serializer metadata:

```csharp
var builder = NativeServer.CreateBuilder();
builder.UseJson(ServerJsonContext.Default);
await using var app = builder.Build();
app.MapPost<CreateGreeting, Greeting>("/greetings",
    static (request, token) => Task.FromResult(new Greeting(request.Name)));
await app.RunAsync(cancellationToken);
```

The complete DTO and `JsonSerializerContext` declarations are in
[ServerExamples.cs](../../experiments/public-api/NativeWeave.Api.Consumers/ServerExamples.cs).
They use the standard System.Text.Json source generator. A later product handler
generator may supply declared static metadata automatically, under the same
diagnostics and AOT rules. It must never fall back to arbitrary reflection to make
a missing DTO registration appear to work.

## 4. Add configuration and DI without another initialization path

Database manual configuration uses the same source builder as DI:

```csharp
var source = new NativeWeave.Database.DataSourceBuilder()
    .UseSqlite("students.db")
    .ConfigureLimits(new NativeWeave.Database.DatabaseLimits { MaxConnections = 4 })
    .Build();
```

The actual extension namespace and complete imports are in the compiled database
example. With the optional Database.DependencyInjection package:

```csharp
services.AddNativeWeaveDatabase(builder => builder
    .UseSqlite("students.db")
    .ConfigureLimits(new DatabaseLimits { MaxConnections = 4 }));
```

The container owns that singleton source. Application operations own sessions and
transactions. Server builders use familiar `Services`, `Configuration` and
`Logging`; the Hosting package attaches a native application to an existing host
provider. It must not call `BuildServiceProvider` again. Request scopes are created
only for endpoints that use scoped services; static routes do not pay for a scope
they never request.

## 5. Publish and change the application

The intended supported commands remain normal `dotnet build/run/publish`.
Publishing selects the matching native asset and manifest; there is no consumer
Cargo invocation. An entity/DTO/handler change updates managed generated output
and the application binary. The native asset hash stays identical unless the
application selects a genuinely new native capability or engine version.

The design packaging probe has actual Linux x64 evidence for package restore,
generator discovery, a new model/DTO, negative diagnostics, normal publishing and
Native AOT execution against a precompiled research codec. It removes Rust tools
from the consumer process PATH but does not call the host a pristine machine.
That probe validates the mechanism and a finite generator subset. Full ORM,
Server, Windows product operation, production workload and release claims still
require the existing Delivery gates.

## 6. Diagnose a failure at the correct boundary

| Symptom | Public diagnostic and next action |
| --- | --- |
| Model member cannot be represented | Source generator diagnostic at the model; use a supported codec or the explicit static mapping seam |
| A column belongs to the wrong entity | C# generic type error; correct the table/column pairing |
| A provider cannot execute an advanced operation | Database capability failure before side effects; choose the supported provider/operation |
| Native asset is absent or wrong for the RID | `NWPKG002`/`NWPKG003` or the corresponding `EngineLoadException`; restore the matching package/profile |
| Managed/native versions or content disagree | Package-closure/ABI/hash diagnostic with expected and observed identity; deploy one complete verified closure |
| Request or query is cancelled | Observe cancellation, then let disposal/retirement join retained owners; cancellation does not prove no external effect occurred |
| Commit acknowledgement was lost | `CommitOutcomeUnknownException`; reconcile using the application's recovery identity instead of blindly retrying |

The [guides](guides.md) describe streaming, transactions, errors, memory, extension
and upgrade rules. Future published examples must link to the exact compiled
sample and actual product evidence, replacing design labels only after those
checks pass.
