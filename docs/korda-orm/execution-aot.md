# Korda.Orm execution, generation and Native AOT

Status: proposed design for `Korda-Orm-01`; source-reviewed with a bounded Linux
Native AOT probe, with product validation still required. This document owns execution-specific decisions. The shared
[contracts](contracts.md) own the SQL command boundary and its identifiers.
Neither this document nor documentation CI accepts an implemented product.

## 1. Decision

Keep the SQL framework independent of all database drivers. A rendered command
shape (`RenderedTemplate`, contract ORM-C03) contains SQL, an ordered typed parameter
layout/occurrence map, a dialect profile, capability proof and a result description.
A `BoundCommand`/invocation binds owned typed arguments to that template. Execution
consumes the bound command without interpreting its AST or rediscovering parameters
by parsing its SQL. Reusable templates contain no request values; they have a
different ownership from per-invocation arguments even if a convenience API returns
both together.

Use mature .NET drivers for connections, pooling, protocol, I/O, preparation,
transactions and cancellation. Korda owns the small boundary that binds values and
materializes declared result shapes. The default design uses explicit or generated
typed binders and projectors, informed by Dapper.AOT's source. It does not depend on
Dapper call-site interception or on Dapper.AOT's runtime API remaining stable.

A Dapper.AOT bridge remains a separately gated optional integration. It must prove
which call shapes are intercepted, whether its parameter protocol is AOT-safe, and
whether its additional conversion work is justified. This does not limit users
who only want SQL and parameters from the DSL.

## 2. Source and version baseline

Source snapshots were inspected on 2026-11-28. These are research pins, not a claim
that every combination has been compiled, executed or performance-tested.

| Component | Stable release inspected | Commit | License at this snapshot |
| --- | --- | --- | --- |
| Dapper.AOT | 1.1.0 | [0e071bf05e54caecfa98c885b075fa3e247f3ecc](https://github.com/DapperLib/DapperAOT/tree/0e071bf05e54caecfa98c885b075fa3e247f3ecc) | Apache-2.0; separate branding restriction in `License.txt` |
| Dapper | 2.1.100 | [188094784256da61d7a37c43ea54c64213c2ce7c](https://github.com/DapperLib/Dapper/tree/188094784256da61d7a37c43ea54c64213c2ce7c) | Apache-2.0; separate logo notice |
| Npgsql | 11.0.0 | [4d174200ed48e3e3ab16419dbf84dd655da59de6](https://github.com/npgsql/npgsql/tree/4d174200ed48e3e3ab16419dbf84dd655da59de6) | PostgreSQL license |
| MySqlConnector | 3.0.0 | [95875a195369f0dd804f63ded2f95da3fed59ec2](https://github.com/mysql-net/MySqlConnector/tree/95875a195369f0dd804f63ded2f95da3fed59ec2) | MIT; inspect notices for selected optional dependencies |
| Microsoft.Data.Sqlite | 11.0.0, from EF Core | [9e685c7a52d1a344d133a3d370e458db97417b3f](https://github.com/dotnet/efcore/tree/9e685c7a52d1a344d133a3d370e458db97417b3f) | MIT; SQLitePCLRaw/native assets have their own provenance |

The [official SDK download page](https://dotnet.microsoft.com/en-us/download/dotnet/11.0)
identifies .NET 11.0.0 and SDK 11.0.100 as the stable baseline. The
[language version table](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/language-versioning)
maps `net11.0` to C# 15. Pin the SDK and language version in product implementation;
do not use a floating `latest` value or enable preview features by default.

Important distinctions between release availability and compatibility evidence:

- Dapper.AOT 1.1.0's own [package pins](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/Directory.Packages.props)
  use Dapper 2.1.79. Dapper 2.1.100 is newer; the bounded probe below checked one
  combination with it, not complete compatibility with every call shape.
- Npgsql 11.0.0 targets `net10.0`; MySqlConnector 3.0.0 includes `net11.0`.
  Microsoft.Data.Sqlite 11.0.0 is a stable package targeting `net10.0`, compatible
  with a `net11.0` consumer. Framework compatibility is not proof of every feature's
  AOT behavior. See their pinned project files and the
  [SQLite package](https://www.nuget.org/packages/Microsoft.Data.Sqlite/11.0.0).
- The EF Core repository also contains an ORM. Referencing Microsoft.Data.Sqlite
  does not require adopting EF Core's runtime or query model. Its
  [packaging project](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite/Microsoft.Data.Sqlite.csproj)
  references the SQLite provider core and `SQLitePCLRaw.bundle_e_sqlite3`.
- A source repository's build SDK may be a prerelease even when its published
  package is stable. Product consumers use the verified stable SDK; building an
  entire upstream repository is a different workflow.

## 3. What Dapper.AOT actually contributes

The following source review determines the design, rather than a general claim
that generated SQL automatically receives compile-time optimization.

| Pinned source and symbols | Observed behavior | Korda consequence |
| --- | --- | --- |
| [Inspection.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/Internal/Inspection.cs), `IsDapperMethod` | Recognizes selected extension methods on `Dapper.SqlMapper`; marks unsupported API families | An ordinary `Korda` execution method is not intercepted merely because it eventually uses SQL |
| [DapperAnalyzer.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperAnalyzer.cs), `SharedGetParametersToInclude` | Constant SQL can filter known members during generation; unknown SQL or command type defers selection | Runtime SQL is compatible with generated binding when the relevant parameter types are statically known |
| [NonConstant.input.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/test/Dapper.AOT.Test/Interceptors/NonConstant.input.cs) and [expected generated output](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/test/Dapper.AOT.Test/Interceptors/NonConstant.output.cs) | A nonconstant SQL call generates member access and conditional parameter inclusion | Do not describe all runtime SQL as unsupported; distinguish dynamic SQL text from dynamic type discovery |
| [CommandFactory.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/CommandFactory.cs), `Include`, `AddParameters`, `UpdateParameters`, `TryRecycle` | The generic runtime can scan SQL for member names, create/update parameters, and optionally recycle commands | Korda already knows its layout and can avoid this rediscovery; command reuse needs explicit shape and ownership rules |
| [ParamPlan.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/Model/ParamPlan.cs), `Create` | Projects Roslyn types into an equatable data model; separately recognizes a dynamic parameter bag | Use a deterministic generation model and separate a runtime value layout from compiler symbols |
| [DapperInterceptorGenerator.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs), `WriteTokenizeMethod`, `WriteArgs` | Emits parameter setup and column-name/type tokenization followed by typed reads; list expansion changes binding shape | Reuse the two-phase mapping design; record variable-arity list expansion in layout identity |
| [RowFactory.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/RowFactory.cs) and [CommandT.Query.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/CommandT.Query.cs) | Tokenization happens per reader; typed reads process rows. Small synchronous token buffers use stack storage, while asynchronous paths lease storage | Separate result-shape validation from per-row materialization; pooling is a measured implementation choice, with exception-safe return |
| [ApiSurface.expected.txt](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/test/Dapper.AOT.Test/ApiSurface.expected.txt) and generator `Parse` | API recognition is not full call-site acceptance. `CommandDefinition` overloads are diagnosed; type-based mapping and other families are refused; some parameter-shape combinations still skip generation | A bridge needs negative tests and actual generated-code inspection, not just a warning-free build |

### 3.1 Dynamic parameters are not one capability

Dapper.AOT 1.1.0 can delegate compatible dynamic parameter bags to an identity-free
`AddParameters(IDbCommand)` method. It also delegates supported list expansion to
Dapper. These paths preserve useful upstream behavior, but do not prove all bag
construction paths AOT-safe.

In Dapper 2.1.100, [DynamicParameters.cs](https://github.com/DapperLib/Dapper/blob/188094784256da61d7a37c43ea54c64213c2ce7c/Dapper/DynamicParameters.cs)
still processes object templates through `CreateParamInfoGenerator`; the corresponding
[SqlMapper.cs](https://github.com/DapperLib/Dapper/blob/188094784256da61d7a37c43ea54c64213c2ce7c/Dapper/SqlMapper.cs)
uses `DynamicMethod` for general parameter readers and object materializers.
Explicit typed values, arbitrary object templates, and runtime-selected DTO types
are separate cases. Korda's supported path cannot fall back to the latter two.

### 3.2 Integration alternatives

| Alternative | Useful scope | Decision |
| --- | --- | --- |
| Direct Dapper calls plus Dapper.AOT | Application call sites with known argument/result types and supported overloads | Valid optional bridge candidate; prove each supported shape and diagnostic |
| Direct Dapper.AOT `Command<T>`, `CommandFactory<T>`, `RowFactory<T>` | Explicit generated factories without Dapper source syntax | Prototype candidate only behind an adapter; upstream [FAQ](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/docs/faq.md) states direct runtime use does not trigger generators and the API can change |
| Korda-generated binding/materialization over drivers | DSL-owned layouts, strict projections and dynamic query composition | Selected default; preserve the useful source patterns and port narrow code where justified and attributed |
| Reflection mapping or runtime IL emission | Arbitrary unregistered runtime shapes | Excluded from the AOT contract |

The selected default does not authorize a new connection pool, network protocol,
database scheduler, retry engine or SQL parser in execution. Code reuse decisions
must identify the exact borrowed symbols, modifications and upstream tests. Do not
copy Dapper.AOT's complete analyzer, SQL Server parser or runtime to obtain a small
binding primitive.

## 4. Execution input and ownership

Execution accepts the shared rendered-command contract, not a query builder. Its
invariants are:

1. SQL and layout are produced by the same successful render. A layout entry has
   stable slot identity, SQL type/nullability, parameter occurrence/order and any
   necessary precision, scale, size or provider type information.
2. Values are associated with slots through typed access. The driver adapter
   rejects missing required values, unknown explicitly supplied slots, incompatible
   types and unsupported provider mappings before sending SQL. A known `TArgs`
   type may contain members unused by an optional query shape; those members are
   neither errors nor bound parameters. `null` does not erase the declared type.
3. Repeated logical parameters follow the renderer's occurrence map. Positional
   reuse, duplicated occurrences and list expansion are never inferred from a
   dictionary's iteration order.
4. A result description states ordinal/alias, SQL and CLR representation,
   nullability and conversion policy. A renderer cannot silently change that
   description while retaining an old materializer.
5. Dialect/version/capability settings are part of the command's semantic identity.
   Driver transport capability is a separate check. The executor verifies the
   selected provider against that profile before execution.
6. The command carries no connection, transaction, active reader, provider object,
   callback into mutable builder state, or rented buffer whose lease has ended.

Immutable SQL and layout can be shared. Values and execution state are per
invocation. A caller-supplied mutable array, memory region or custom value must
remain unchanged until the invocation completes or its stream is disposed; the
API documents copy or borrow behavior. A convenience API may snapshot values, but
must report its allocation cost. No value may survive in a cache after its intended
lifetime merely because a SQL shape is cached.

## 5. Binding and reuse

### 5.1 Fixed and dynamic shape paths

Both paths use the same command contract and diagnostics.

- A fixed shape can reuse SQL, layout and generated typed access. Values change
  independently. A typed parameter binder writes directly to provider parameters.
- A dynamic query changes AST structure and can produce a new layout at runtime.
  The supported CLR types and converters remain statically registered. A bounded
  type dispatch or generated typed cell operation binds the resulting layout
  without `MakeGenericType`, reflection-based member discovery or runtime codegen.
  An expanded list's arity is a structural render input; binding rejects a different
  cardinality. A provider-native array can instead occupy one declared slot. A
  render-and-bind convenience operation snapshots the shape before rendering;
  execution never patches SQL to accommodate an unexpected value count.
- Dynamic projection means choosing among already representable results, not
  inventing a new CLR DTO after native compilation. Unstructured results, if added,
  require an explicit row/value model and separate allocation expectations.

Do not require a homogeneous `object[]` as the only parameter representation.
Preserve typed access until a driver genuinely requires `object`. Conversely, do
not promise zero boxing or zero GC for every provider: SQLite and MySQL's public
parameter values are object-based, and each driver has its own allocation behavior.

### 5.2 Cache and preparation boundaries

Reusable render plans are keyed by query shape, dialect/version/settings,
parameter structure and result contract. Raw hash equality is insufficient; verify
structural identity or use a collision-safe key. Cache entries do not retain user
values or connections, have a documented size bound, and can be disabled.
Explicit SQL literal constants participate in structural identity because changing
one changes the emitted SQL semantics; only bound request values are excluded.

Prepared statements and mutable commands belong to the connection/session domain
defined by the driver. Reuse cannot cross providers, incompatible layouts,
transactions, concurrent executions or an open reader. A parameter's size/type
change can invalidate preparation even when SQL text is unchanged. Start with
driver-owned pooling/preparation and measure before adding command recycling.

The Npgsql [positional path](https://github.com/npgsql/npgsql/blob/4d174200ed48e3e3ab16419dbf84dd655da59de6/src/Npgsql/NpgsqlCommand.cs)
avoids named-placeholder rewriting. Its
[generic parameter](https://github.com/npgsql/npgsql/blob/4d174200ed48e3e3ab16419dbf84dd655da59de6/src/Npgsql/NpgsqlParameter%60.cs)
supports `TypedValue` without boxing the value through `Value`. These are concrete
optimization candidates; they are not a measured Korda speedup.

## 6. Generated materialization

Keep a clear distinction between a source generator and a schema acquisition tool.
The compiler generator reads declared CLR types and deterministic metadata inputs;
it does not connect to a database. A separate local schema tool can acquire
metadata and emit a reproducible input. The core DSL remains usable with handwritten
typed schema declarations and explicit projectors.

Generation must support accessible constructors, records/DTOs and explicit
converter methods without invoking private members through reflection. Unsupported
construction, ambiguous names, inaccessible types, missing required members,
incompatible nullability and unsupported conversions produce stable diagnostics.
Do not generate code that silently leaves required data at its default value.

Use two stages:

1. Validate the actual reader shape once when schema information is available:
   required columns, duplicates, ordinals, nullability/conversion expectations and
   provider read types. An empty result does not excuse an invalid declared shape.
   Drivers with limited metadata require an explicit documented validation rule.
2. Read each row through known typed getters and construct the declared result.
   A NULL for a required non-null result is a mapping error. Numeric narrowing is
   checked unless a caller explicitly requests a different conversion contract.

Known projections prefer strict ordinal access. Mapping an external SQL result by
name is a separate mode, with one-time tokenization following the Dapper.AOT
pattern. Duplicate aliases require explicit ordinal binding or fail; permissive
name matching is not an implicit escape from the type contract.

Neutral advanced representations and static codec contracts are driver-free. They
specify SQL/CLR identity, NULL behavior, precision loss, timezone treatment and
exceptions, and can be validated before any provider is complete. JSON uses
source-generated serialization metadata or an explicit text/binary representation.
Provider adapters separately register transport/read mappings through AOT-visible
typed operations and earn support through real-database integration. A neutral
codec test does not accept its provider transport. Nested collections and
multi-result materialization require their own shape/lifetime contract; Dapper
multi-mapping support must not be assumed.

## 7. Async, streaming, resources and failures

Execution APIs expose cancellation tokens and separate buffered from streaming
results. A stream is pull-driven; it does not create a worker pool or eagerly buffer
all rows. A stream associated with a bound invocation has one active enumeration
and does not implicitly replay it. Re-execution creates a fresh invocation;
concurrent `MoveNextAsync` is rejected. The transaction and connection must outlive
any stream using them.

The executor disposes its command, reader, token buffers and any connection it
opened on normal completion, early enumeration break, mapping failure, cancellation
and driver failure. Caller-owned connections and transactions remain caller-owned.
A data-source-based convenience overload can open and close a connection; a
connection overload must document whether it opens a closed connection and restores
the original state. Prefer an explicit already-open connection contract initially.

Allow only the concurrency that the selected driver/connection contract permits.
Immutable queries can be rendered concurrently; a command, reader and transaction
are not thereby safe for concurrent use. Transactions are explicitly supplied,
associated with the same connection, and support only declared isolation and
savepoint capabilities. Do not introduce ambient transaction assumptions or
automatic retries around side effects. Connection loss around commit can leave an
unknown outcome and must be reported as such.

Errors have separate sources: invalid query/capability, binding, result mapping,
driver/database, cancellation and lifecycle misuse. Preserve provider exception
information and the original cause; a mapping error includes safe column/slot
context. Do not flatten a provider error into success, expose parameter values by
default, or classify every failure after token cancellation as cancellation.
Timeout and cancellation remain distinct signals where the provider supports them.

Cancellation is cooperative and provider-specific. Passing a token does not prove
an in-progress database command can be interrupted. The SQLite limitation below
must be visible in its capability profile, API guide and tests. Do not add hidden
`Task.Run` scheduling to make synchronous SQLite calls appear asynchronously
cancelable.

## 8. Provider contracts

| Provider | Initial binding/reading direction | Required limitations and gates |
| --- | --- | --- |
| PostgreSQL / Npgsql | Native `$1` positional placeholders; explicit PostgreSQL type where needed; typed parameters for known CLR types; typed reader getters | Validate NULL/arrays/enums/JSON independently; no mixed named/positional placeholders; prepared commands are session-bound |
| SQLite / Microsoft.Data.Sqlite | Named parameter layout accepted by the provider; explicit SQL-to-storage conversion; `SqliteType` where meaningful; strict result conversions | SQLite storage classes do not reproduce every SQL type. Input parameters only; asynchronous methods can execute synchronously; cancellation cannot promise interruption |
| MySQL and MariaDB / MySqlConnector | Provider parameters with declared `MySqlDbType` when inference is ambiguous; direct async I/O; typed reader getters | Separate MySQL and MariaDB dialect/version profiles; decimal precision, unsigned values, zero dates, timezone and connection settings need explicit mapping tests |

### 8.1 Npgsql AOT profile

Npgsql marks its library AOT-compatible and includes a
[native consumer](https://github.com/npgsql/npgsql/blob/4d174200ed48e3e3ab16419dbf84dd655da59de6/test/Npgsql.NativeAotTests/Program.cs).
That consumer only establishes a narrow upstream example; it does not certify all
Korda type mappings. The pinned
[NpgsqlSlimDataSourceBuilder](https://github.com/npgsql/npgsql/blob/4d174200ed48e3e3ab16419dbf84dd655da59de6/src/Npgsql/NpgsqlSlimDataSourceBuilder.cs)
has explicit opt-ins and annotations:

- Statically registered `MapEnum<TEnum>` and supported built-in mappings can be
  AOT candidates; retain required enum metadata.
- `EnableDynamicJson`, tuple-based records, unmapped types and `MapComposite<T>`
  have dynamic-code/trimming restrictions. Their availability under JIT must not
  cause Korda to advertise them in the default AOT profile.
- JSON text/bytes and supported `JsonDocument`/`JsonElement` mappings provide
  alternatives. Arbitrary POCO JSON requires an explicit static serialization path
  and validation; merely passing serializer options does not remove annotations.

Advanced SQL expressions can still render in the independent DSL even when a
particular driver representation is unavailable. Execution fails with a capability
diagnostic or uses an explicitly declared supported representation.

### 8.2 SQLite async and storage profile

The pinned [SqliteCommand](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteCommand.cs)
checks cancellation before synchronous execution in `ExecuteReaderAsync`, returns
the completed result as a task, and implements `Cancel()` without an interrupt.
The [official async guidance](https://learn.microsoft.com/en-us/dotnet/standard/data/sqlite/async)
agrees. Cancellation before execution and between application-level row reads can
be honored; interruption during a native step is not promised by this adapter.

[SqliteParameter](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteParameter.cs)
exposes SQLite storage typing and rejects non-input directions. Do not treat
`DbType` assignment as a complete conversion contract. Date/time, decimal, GUID,
boolean and unsigned values require an explicit storage policy and round-trip
tests. Required native assets remain the mature provider's package responsibility;
verify Linux x64 publish and independent package consumption.

### 8.3 MySQL and MariaDB profile

The pinned [project](https://github.com/mysql-net/MySqlConnector/blob/95875a195369f0dd804f63ded2f95da3fed59ec2/src/MySqlConnector/MySqlConnector.csproj)
enables AOT compatibility for supported modern targets.
[MySqlCommand](https://github.com/mysql-net/MySqlConnector/blob/95875a195369f0dd804f63ded2f95da3fed59ec2/src/MySqlConnector/MySqlCommand.cs)
has genuine async execution and cancellation integration; these semantics are not
interchangeable with SQLite's.
[MySqlParameter](https://github.com/mysql-net/MySqlConnector/blob/95875a195369f0dd804f63ded2f95da3fed59ec2/src/MySqlConnector/MySqlParameter.cs)
has an object-based value boundary, so boxed scalar values are not eliminated by
calling the framework strongly typed. The upstream
[AOT consumer](https://github.com/mysql-net/MySqlConnector/blob/95875a195369f0dd804f63ded2f95da3fed59ec2/tests/MySqlConnector.NativeAot.Tests/Program.cs)
checks a small query and schema; Korda must add its own value, cancellation,
transaction and result-shape tests against each supported server family.

## 9. Native AOT and local development requirements

The consumer can generate schema inputs, build, publish and run from a Linux x64
shell. GitHub CI is not required to use the library. The same maintained product
commands should later serve local and CI runs. Build tooling and analyzers do not
become runtime dependencies of the pure DSL.

Product validation must compile the actual generated consumer and execute its
native binary. Check trimming/dynamic-code warnings for the chosen package graph;
do not hide them with blanket suppression or root every consumer type. Treat
missing generation as an explicit diagnostic. Exercise both generator-enabled and
explicit hand-written binder/projector routes where those are advertised.

Generic expansion is a code-size budget: measure representative numbers of query,
argument, result and provider shapes. Avoid specializing every AST node combination
into a distinct generic execution pipeline. Dynamic SQL is ordinary runtime data;
it requires neither runtime IL generation nor a cross-language compiler.

The source review supports technical feasibility for this architecture. It does
not replace local publish/run evidence, provider integration results, or an API
compatibility baseline for the final assemblies and packages.

## 10. Validation and performance obligations

### 10.1 Observed bounded local probe

This task published and directly executed a Linux x64 native console consumer on
Debian 13 with SDK 11.0.100, C# 15, Dapper 2.1.100, Dapper.AOT 1.1.0 and
Microsoft.Data.Sqlite 11.0.0. The linked provider reported SQLite 3.53.4. Publishing
used GCC as the native linker; no JIT consumer execution was used.

| Check | Observed result | Limit |
| --- | --- | --- |
| Native execution | Published ELF x64 binary ran with `RuntimeFeature.IsDynamicCodeSupported == false` | One Linux environment; not a clean-machine or other-platform test |
| Runtime SQL shape | Optional `score > @threshold` predicate selected at runtime; otherwise identical `id >= @minId` query returned the expected 2 or 3 rows | Two finite shapes, not arbitrary SQL or parameter object types |
| Binding and mapping | Static anonymous `long` arguments mapped into a public DTO with `long`, `string`, `long?`; SQL NULL preserved; results matched direct `SqliteCommand` row by row | Buffered queries and one fixed single-row query; no throughput or cancellation claim |
| Generated implementation | Both call sites were intercepted; emitted binder tested parameter presence for runtime SQL; emitted row factory used typed getters and NULL handling | Inspection of this generated consumer, not all upstream generator paths |
| Unsupported overload | Replacing the single-row call with a `CommandDefinition` overload and making `DAP057` an error caused expected compilation failure | A deliberately enforced diagnostic, not proof all unsupported shapes are diagnosed |

Reproduce with a local `net11.0` console project containing the exact package
versions above, `[module: DapperAot]`, `InterceptorsNamespaces` including
`Dapper.AOT`, and emitted compiler-generated files. Create an in-memory SQLite
table `(id INTEGER PRIMARY KEY, name TEXT NOT NULL, score INTEGER NULL)` with
rows `(1, alpha, NULL)`, `(2, beta, 25)`, `(3, gamma, 50)`. A non-inlined helper
builds the SQL with and without the optional threshold predicate; bind `minId=1`
and `threshold=20`, select aliased DTO columns ordered by `id`, then compare with
the same SQL through direct driver calls. Publish Release for `linux-x64` with
`PublishAot=true`; this environment needed `CppCompilerAndLinker=gcc` and disabled
shared compilation/server startup. Run the published executable. For the negative
variant, change only the fixed call's overload and set `WarningsAsErrors` to
include `DAP057`; publishing must fail before native execution.

The positive publish completed without compiler, trimming or dynamic-code warnings.
This proves that runtime SQL, generated binding/materialization and this mature
driver can coexist under Native AOT for the stated cases. It is not Korda product
acceptance, a custom Korda generator test, PostgreSQL/MySQL validation, streaming
validation or evidence of Dapper.AOT performance parity.

### 10.2 Implementation acceptance

The implementation plan must include these independently runnable groups. Each
provider consumes fixed shared contract fixtures, so provider implementation can
start after contracts are established without waiting for the complete DSL.

| Group | Positive cases | Required negative or lifecycle cases |
| --- | --- | --- |
| Driver-free command contract | Dynamic optional predicates, repeated parameters, nulls and variable-length lists; render without provider assemblies | Missing/wrong value types; unsupported dialect operation; mismatched result/layout identity |
| Binder and projector | Known DTO and tuple shapes; constructor and converter paths; named and ordinal modes | Inaccessible construction, missing/duplicate columns, forbidden narrowing, NULL into required result, unsupported mapping |
| Native consumer | Fixed and runtime-composed SQL; generated and explicit factories; independent NuGet consumption | A deliberately ungenerated/missing mapping path fails clearly; no runtime IL fallback |
| Provider correctness | Scalars and relevant advanced types, preparation, transaction/savepoint behavior, buffered and streaming reads | Pre-cancel, supported in-flight cancel, timeout, rollback, early stream disposal, mapping failure, connection mismatch and reuse after failure |
| Optional Dapper bridge | Actual intercepted calls; supported nonconstant SQL and explicit parameter layout conversion | `CommandDefinition`, unsupported overloads, generic/type-erased DTOs, object-template bags and silently skipped generator shapes |

For performance, keep SQL, typed parameter values, result shape, driver version,
database data, preparation state, connection ownership and buffered/streaming mode
the same. Measure separately:

1. AST construction and rendering, including allocations and output length.
2. Binding and materialization over deterministic readers or local fixtures.
3. Direct driver, Dapper.AOT and Korda execution over the same provider.
4. Fixed render reuse and dynamic shape changes, including cache misses.
5. End-to-end latency, throughput, allocation/GC and published binary size.

Do not attribute network/database latency to DSL construction or subtract unrelated
benchmark means to claim a precise framework cost. Report distributions and
measurement uncertainty, with cold/warm boundaries. Define a concrete acceptance
budget after comparable baselines exist; no current source finding proves
Dapper.AOT parity. Java jOOQ rendering benchmarks have a different runtime and
remain a separate engineering comparison.

## 11. Provenance and evidence boundary

Only the source references, decisions and reproduction conditions belong here.
Local clones, generated output, runtime logs, binaries, packages and benchmark
samples stay outside the document repositories and are not uploaded elsewhere.

The source licenses were inspected in
[Dapper.AOT](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/License.txt),
[Dapper](https://github.com/DapperLib/Dapper/blob/188094784256da61d7a37c43ea54c64213c2ce7c/License.txt),
[Npgsql](https://github.com/npgsql/npgsql/blob/4d174200ed48e3e3ab16419dbf84dd655da59de6/LICENSE),
[MySqlConnector](https://github.com/mysql-net/MySqlConnector/blob/95875a195369f0dd804f63ded2f95da3fed59ec2/LICENSE)
and [EF Core](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/LICENSE.txt).
Future copied/translated code retains applicable copyright/license/NOTICE material,
identifies modifications and records its exact source symbols. Dependency and
native asset notices are verified from the shipped packages, including SQLitePCLRaw,
rather than inferred from the top-level provider license alone. No upstream product
name or logo is adopted as Korda branding.

The bounded probe above is the actual newly executed provider/generator evidence.
The task's validation record consolidates it with other experiments and limits.
Unexecuted tests in the acceptance matrix remain implementation obligations, not
completed acceptance items.
