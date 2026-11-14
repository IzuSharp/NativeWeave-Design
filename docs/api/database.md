# Database, query and ORM public API specification

Version **0.4.0**; owns the C# surface refinement of **D14/C-DB-001,
D15/C-TX-001, D16/C-QUERY-001 and D17/C-QUERYGEN-001**. Implementation owners:
B01–B14; assembled conformance B21–B24; package/documentation integration A13/A16.
This is a design contract. None of its APIs is a released NativeWeave product.
The exact declaration fixture is
[`Database.cs`](../../experiments/public-api/NativeWeave.Api.Design/Database.cs);
it is the normative source of namespaces, accessibility, signatures, generic
constraints, nullability, overloads and defaults. Every behavioral fixture body
throws. The accompanying [consumer scenarios](../../experiments/public-api/NativeWeave.Api.Consumers/DatabaseExamples.cs)
are compile-only design consumers. A compiled declaration is not an implemented
native operation. Integration evidence records compilation/AOT separately.

Read the [coverage matrix](database-coverage.json) and
[source manifest](database-sources.json) with this document. Support classifications
mean designed scope, not completed implementation. Existing accepted versions,
finite Rust experiments and reviews retain their original identities.

## 1. Reference baseline and decisions

The research baseline is .NET **11.0.0 / SDK 11.0.100 / C# 15.0**, EF Core
**11.0.0**, Dapper **2.1.89**, and SqlSugarCore **5.1.4.221**. Full source commits, actual read ranges and
SHA-256 identities are in the source manifest. The official release page and
language-version table establish the stable baseline; no memory-safety preview or
`LangVersion=preview` feature is required. References are behavioral comparisons,
not dependencies or copied implementations. SqlSugar's current NuGet release and
fixed source project both identify 5.1.4.221; its repository has no matching release
tag, so the source manifest records a pinned snapshot with that project version,
not a claim of reproduced NuGet binary provenance.

The review covers `DbDataSource`, `DbConnection`, `DbCommand`, `DbParameter`,
`DbDataReader`, `DbTransaction`, `DbBatch`, `DbProviderFactory`; EF `DbContext`,
`DbSet<T>`, async query terminals, `Include`, no-tracking, set-based writes,
`IDbContextTransaction`, raw SQL and `IMigrator`; and Dapper command definitions,
buffered/unbuffered queries, multiple result sets and reader disposal. The matrix
also assesses familiar LINQ filtering, joins, projections, grouping, ordering,
cardinality, pagination and set operations against NativeWeave's deliberately
explicit SQL semantics.

Source findings that affect the design:

* BCL asynchronous provider base methods can call synchronous implementations.
  NativeWeave binds actual Rust futures; an `Async` suffix is never evidence that
  work is nonblocking. Synchronous network/query execution is not offered in v1.
* `DbDataSource` centralizes connection policy and owns connectionless command
  cleanup. NativeWeave similarly centralizes source/pool policy, but exposes an
  explicit `DataSession` when one physical connection/transaction is needed.
* EF `SaveChangesAsync` invokes change detection and reports concurrency when
  affected rows differ. NativeWeave keeps the useful explicit concurrency outcome
  and uses native compare-and-swap changesets without a managed state manager.
* EF11 `ExecuteUpdateAsync` accepts an ordinary `Action<UpdateSettersBuilder<T>>`
  but internally builds expression structures. NativeWeave's setters are ordinary
  calls that immediately append to a query-owned native builder; no C# SQL tree
  or expression compiler is introduced.
* Dapper's `QueryAsync(... buffered:false)` branch can return synchronous deferred
  enumeration, whereas `QueryUnbufferedAsync` uses actual asynchronous reads.
  NativeWeave exposes `IAsyncEnumerable<T>` explicitly, never an async-named
  method returning hidden synchronous database enumeration.
* EF11's inspected `IMigrator` methods retain trimming/dynamic-code annotations.
  NativeWeave uses explicit immutable SQL migration bundles through SQLx. This
  does not imply that all EF APIs lack AOT support, or that NativeWeave already
  implements a migration product.

### 1.1 SqlSugar usability comparison

The additional fixed-source review covers `ISugarQueryable<T>`'s conditional
`WhereIF`, typed joins, `Select`, paging and native-style aggregates,
`Expressionable<T>.And/Or/AndIF/OrIF`, and `IUpdateable<T>.SetColumns`, explicit
column selection and optimistic-lock execution. Those public families are mapped
in DB-089–DB-096 rather than assuming one happy-path CRUD sample covers them.
The inspected implementation's conditional filter returns without translating a
false predicate. NativeWeave preserves that useful behavior through `WhereIf`,
with an ordinary immediate builder delegate and no expression-tree capture.
`SqlPredicate.And/Or` composes native conditions; `Changes.Set/Unset` and typed
`UpdateSetters` make update intent visible without interpreting an entity lambda.
The comparison does not establish a blanket AOT verdict for every SqlSugar path.
The inspected source uses expression trees and its project declares a Reflection.Emit
dependency; NativeWeave does not copy those implementation mechanisms.

## 2. Installation, namespaces and assembly boundaries

| User package | What it brings | What it excludes |
| --- | --- | --- |
| `NativeWeave.Database.Sqlite` | Database facade, Data descriptors, generator/analyzers, matching SQLite native assets and Core dependencies | PostgreSQL, Server, gRPC, MCP |
| `NativeWeave.Database.PostgreSql` | Same facade and descriptors with PostgreSQL native assets | SQLite and Server |
| `NativeWeave.Database.DependencyInjection` | Optional Extensions 11 integration for the same builder and owners | A second host, pool or registration universe |
| `NativeWeave.Data` | BCL-only metadata, codecs' declarations, static mapping contracts and domain values | Runtime loading, sockets, a query evaluator |

`NativeWeave.Query` is a **namespace inside the NativeWeave.Database assembly** in
v1. It is not an extra NuGet/assembly: `DataSession.From` returns `Query<T>` and
query terminals consume sessions, so splitting those concrete surfaces would make
a package cycle or require unnecessary public abstractions. B09/B11/B12/B13 retain
distinct implementation/file ownership. Native Rust query code remains separate.
The source generator is a build-time dependency and may be excluded explicitly;
handwritten static descriptors use exactly the same runtime API.

The common path requires no global `Initialize`, catalog registration, native
handle, Cargo command or database model registration:

```csharp
using NativeWeave.Data;
using NativeWeave.Database.Sqlite;

[WeaveTable("students", DescriptorName = "Students")]
public sealed partial record Student(
    [property: WeaveKey, WeaveColumn("id")] long Id,
    [property: WeaveColumn("name")] string Name,
    [property: WeaveColumn("age")] int Age);

// Students is generated in the entity's namespace; this snippet is an expected
// product example, not a claim that the generator is implemented in the fixture.
await using var source = SqliteDataSource.Create("students.db");
await using var session = await source.OpenSessionAsync(cancellationToken);
using var query = session.From(Students.Table);
var adults = await query.WhereGreaterThanOrEqual(Students.Age, 18)
    .OrderBy(Students.Id).Take(100).SelectAll().ToListAsync(cancellationToken);
```

The fixture's corresponding consumer supplies the explicitly labelled handwritten
equivalent. Product Getting Started must be switched to a real generated consumer
only after B10/B24 runs it. Creating a source does not create tables or migrate a
database. A first-run tutorial must explicitly apply its migration bundle.

Advanced configuration keeps the same lifetime and query surface:

```csharp
using NativeWeave.Database;
using NativeWeave.Database.Sqlite;

await using var source = new DataSourceBuilder()
    .UseSqlite("students.db", o => o.BusyTimeout = TimeSpan.FromSeconds(2))
    .WithName("students")
    .ConfigureLimits(new DatabaseLimits { MaxConnections = 4 })
    .Build();
```

`Create` is equivalent to configuring the provider on a new builder and calling
`Build`. Callbacks run once synchronously; builders/options are not retained or
reread. `Build` snapshots and validates configuration, loads and negotiates the
package's native module and creates an engine-local pool owner without connecting.
Connections are established on `OpenSessionAsync`. Loading/ABI/RID errors therefore
appear at `Build`, and authentication/network/schema errors appear at the operation
that requires them. `CanConnectAsync` probes one connection and closes its session;
false means a provider connectivity failure, while cancellation, configuration and
ABI failures throw. It never creates a schema or suppresses a poison error.

Provider factories expose `Engine` for optional `EngineDescriptor.Inspect`
preflight. Normal `Create` performs the same negotiation automatically. The
engine identifiers are `database.sqlite` and `database.postgresql`, with unique
`nw_database_sqlite` / `nw_database_postgresql` asset basenames and corresponding
`*_get_abi_v1` bootstrap symbols. Independent sources have independent lifetimes;
shared module code stays resident under the existing Core contract.

Optional DI follows Extensions' discoverability convention:

```csharp
using Microsoft.Extensions.DependencyInjection;
using NativeWeave.Database;
using NativeWeave.Database.Sqlite;

services.AddNativeWeaveDatabase(b => b.UseSqlite("students.db"));
services.AddKeyedNativeWeaveDatabase("audit", b => b.UseSqlite("audit.db"));
// Resolve DataSource or standard GetRequiredKeyedService<DataSource>("audit").
```

The container owns each singleton source and disposes it asynchronously with the
host. No session is registered implicitly: a request can run concurrent work and
must open separate sessions explicitly. Duplicate unkeyed registration or duplicate
keys fail during registration rather than silently creating/overriding pools.
Configuration callbacks are evaluated once at owner construction; Options reload
never mutates an active native source. Applications explicitly construct a new
source for changed credentials or pool policy and drain the old owner.

## 3. Universal semantics for every database member

These rules apply to every member in the declaration fixture unless a subsection
below gives a stricter rule. They are part of each future reference entry; use XML
`inheritdoc`/shared conceptual links without omitting the member's specific facts.

* All reference parameters without `?` reject null. Names are nonempty strict UTF-8
  identifiers after managed UTF-16 validation; metadata names are quoted by Rust,
  never concatenated as trusted SQL values. Empty/duplicate keys, fields, aliases
  or parameter names fail before sending. Numeric lengths/counts must fit both the
  declared CLR type and the native checked capacity profile.
* `CancellationToken` is last and optional except deliberately named admission
  tokens. Task-returning APIs use a synchronous validation wrapper: known null,
  range, wrong-owner and already-closed errors throw before returning a Task.
  Following validation, an already canceled token returns a canceled Task carrying
  that token without business admission; CloseAsync still initiates close before
  canceling only its wait, and the stricter Commit/Rollback admission rules below
  take precedence. Provider/operation errors after admission fault the returned
  Task. StreamAsync/AsAsyncEnumerable validate and snapshot synchronously; their
  first MoveNext performs execution admission and reports asynchronous failures.
  A canceled wait never proves no database effect. No sync
  wrapper blocks on a native future. `ValueTask` is used only for standard disposal;
  public I/O operations return reusable `Task` objects without pooled-source
  single-await hazards. Async enumerators use their normal `ValueTask<bool>` API.
* No `Span`, row reader/writer or native borrow survives an await. Input scalar
  values and mutable byte arrays are snapshotted at the documented submission or
  builder call; results are ordinary owned CLR values. UTF-8/DTO copies are real
  costs and are counted. No `object[]` or runtime reflection mapping on typed paths.
* `DataSource` is safe for concurrent opens and independent sessions. A session
  admits at most one active command, cursor, bulk operation or transaction control
  call. Concurrent use throws `DatabaseException(ConcurrentUse)`; it is never queued
  behind an unknown transaction order. Builders and setters are single-writer and
  nonreentrant. Immutable metadata/projections/prepared shapes are shareable.
* `ArgumentException`/`ArgumentOutOfRangeException`/`ArgumentNullException` mean
  invalid caller inputs; `ObjectDisposedException` means closed admission;
  `InvalidOperationException` means invalid shape/cardinality or object state where
  documented. Native provider/shape/codec/resource/concurrency errors are
  `DatabaseException` with a `DatabaseErrorKind`. Unsupported operations use
  `DatabaseCapabilityException`. Panic/poison/core-protocol failures use
  `NativeWeave.Interop.NativeEngineException`, not a provider error retry hint.
* All ordinary data APIs target the accepted Windows x64/Linux x64 engine assets.
  A .NET declaration compiling elsewhere is not an available native platform.
  Capabilities are checked in managed code for useful messages and independently
  in native code. Provider version/profile may narrow package capabilities after
  connection; silent clause dropping or managed-provider fallback is prohibited.
* Native owner destruction follows Core admission/retirement and the creating
  module's destructor. `Dispose` closes admission and transfers work to a bounded
  cleanup owner; it does not wait for I/O. `DisposeAsync` joins local safety and may
  wait beyond a policy deadline if native access remains. Repeated disposal is
  idempotent; disposal races linearize at admission. This is not physical module
  unload and does not decide a remote transaction outcome.
* Source, session and transaction `CloseAsync(waitBudget, token)` starts closure
  even for a canceled waiting token. `waitBudget >= TimeSpan.Zero` must be finite;
  zero requests closure and returns a current snapshot. Cancellation of the wait
  throws `OperationCanceledException` but leaves cleanup running and inspectable.
  Expiry returns `Pending`, `LocalResourcesReleased=false`, never false success.
  No permit/handle/root is released merely because a wait ended.

`DatabaseException.Kind`, ProviderCode and CorrelationId are immutable diagnostic
values. IsTransient is a provider classification of the cause, never permission to
retry a write: UnknownOutcome/commit-unknown is always false, and a transient
connection/serialization failure still requires an operation/outcome-specific
application retry policy. DatabaseCapabilityException adds the stable capability
name and provider identity. ConcurrencyConflictException fixes Kind=Constraint
and preserves expected/actual row counts. DatabaseCleanupException preserves the
independent cleanup snapshot and does not replace an already reported primary
failure. Standard TimeoutException represents expiry of a configured operation
budget; caller cancellation uses OperationCanceledException. Both still retain
native resources until the asynchronous retirement contract permits release.

The database reason codes in section 9.3 map to managed categories explicitly:
1=Provider, 2/16=Constraint, 3=Conversion, 4=ShapeMismatch,
5=UnsupportedCapability, 6/14=ResourceLimit, 7=ConcurrentUse,
8/11/12/13/15=InvalidState, 9=UnknownOutcome, and 10=Provider with a
DatabaseCleanupException/cleanup snapshot. A malformed managed argument is rejected
before an ABI call using standard argument exceptions instead of manufacturing a
provider error. Native panic/poison remains a Core NativeEngineException.

Defaults are design capacity choices, not measured performance claims. The
`DatabaseLimits` declaration is authoritative: 32 connections, 128 waiters, 15s
admission, 10,000 buffered rows/16 MiB, 256 rows/1 MiB per batch, 8 MiB general field,
4 MiB parameters, 999 parameters, 4,096 query nodes/depth 64, 128 prepared plans/
8 MiB and 30s command timeout. Effective maxima are the minimum of configured and
provider hard limits; setting an unsupported larger limit is rejected. Inline
fields must also fit a batch. Oversize fields fail `ResourceLimit` with the
`LargeValueRequiresStreaming` reason; v1 does not silently claim single-field
streaming that SQLx's ordinary row decoder does not supply. No logical-byte limit
is advertised as an RSS cap.

## 4. Metadata, codecs, entities and projections (B01/B07/B10/B12)

### 4.1 Exact type roles

| Types/members | Semantics, lifecycle and costs |
| --- | --- |
| `TableBuilder<TEntity>(name,schema)`, `Column`, `Build` | `TEntity:class`; record classes and ordinary classes work. Mutations are startup-only. Build validates one table identity, columns, codecs, key order and direct materializer/writer, then consumes the builder; reuse fails. It snapshots metadata and delegates. O(columns) startup managed allocation; no native load until first source registration. |
| `Table<TEntity>.Name/Schema/MetadataHash/Row` | Immutable strings/static row projection. Hash is canonical schema content, separate from ABI/version. No native handle exposed. |
| `Column<TEntity,T>.Name/Id/Codec` | Immutable entity/value typed token tied to exactly one table. Cross-table metadata and mixed sources are revalidated natively. Default/forged tokens are rejected. |
| `Table.Key`, `EntityKey.And` | Construct complete typed primary-key values; `And` returns a new immutable key so previously submitted snapshots cannot change. Reject missing, duplicate, nullable or nonkey components before traffic. Cost O(key components) and owned value snapshots. |
| `Table.TryGetColumn<T>` | Name must match registered metadata and requested native codec; returns false on absence/type mismatch, out null. This is the dynamic UI allowlist route, not reflection or arbitrary-column SQL. Only schemas/columns explicitly exposed by application policy may be searched. |
| `Projection<T>.Create`, `ResultField` | Static expert-SQL DTO mapping. ResultField.Create(name, typedCodec) preserves exact configured codec/nullability; ordered unique fields define exact shape; constructor delegate is AOT-visible. Fields are copied on creation. `T` may be a value type or reference type. No entities are required for scalar/DTO results. |
| `ProjectionBuilder<T>.Add/Build`, `ResultColumn<T>` | Query-scoped DTO projection, one ordered alias/token per native expression; Build freezes it. `ResultColumn` belongs to exactly that projection. O(projected columns) native/managed construction, constant-time ordinal access per field. |
| `RowReader.Get/Read/IsNull` | `ref struct`, only during materialization. Shape is validated before nullable decode. Get by typed column/result token or explicit ordinal; ordinal out of range is an argument error. Missing/duplicate columns are ShapeMismatch, never NULL. Strings/byte arrays are owned copies. |
| `EntityWriter<T>`, `RowWriter.Set` | Direct synchronous CLR extraction, only during an insert/bulk-row snapshot; no awaits, reflection, native callback or arbitrary property discovery. Repeated column assignment rejects. Generated fields are omitted by insert policy. Writer exception occurs before row dispatch. |
| `Changes<T>.Set/Unset` | Explicit changeset data, not a SQL expression tree. Set snapshots a typed value (including explicit null); Unset removes that assignment. Unset and null are different. Empty changes reject; keys/generated columns reject. Reuse snapshots independently at each call. |
| `ConcurrencyCheck<T>.Expect` | Expected typed token values, included in the same native WHERE as key and changes. All tokens required by the declared check are supplied; empty check rejects. No hidden identity map/version increment. Caller explicitly supplies a new version in Changes. |

Entity classes need not inherit a base type or implement a framework interface.
The generator opts in through `WeaveTableAttribute`, reads actual semantic symbols,
and emits `<EntityName>Mapping` by default or the explicit `DescriptorName` in the
entity namespace. Generated `Table`, typed property-name column fields and `Row`
are discovered naturally in IntelliSense. `WeaveColumn` selects a store name and
generated-value flag; `WeaveKey` and `WeaveVersion` mark keys/concurrency tokens;
`WeaveIgnore` excludes a property. Without `WeaveColumn`, the store column name is
the exact CLR property symbol name, including its original casing; the C# `@`
escape is syntax and is not part of that symbol name. There is no implicit
lowercasing, snake-case conversion or pluralization. `WeaveColumn("id")` changes
only the store name; the generated typed member remains `Id`. Examples using
lowercase SQL columns therefore declare those overrides explicitly. Handwritten
equivalence requires the same store names, key/concurrency flags, codecs,
nullability and constructor projection order, not merely the same CLR type.
Table/schema/member names and type nullability
are canonicalized identically to handwritten definitions. Entity getters are never
executed by the generator. An immutable record uses its unambiguous public primary
constructor; a class requires one unambiguous accessible constructor or public/init
assignments. Ambiguity is NWQ0103. Unsupported codec (including ambiguous decimal
policy) is NWQ0101 with a static handwritten-descriptor remedy, not reflection.

The generator does **not** duplicate registration: first use of its immutable
`Table` registers canonical metadata once per source. Registration cache has
bounded bytes/entries and source ownership. Generated source never calls Cargo,
changes the native library, contacts a database, requires `rd.xml`, or assumes it
can read another generator's output in the same pass. Ordinary changes add C# code
and descriptors. New native codecs/operators still require an engine/package
upgrade. Generator descriptors and the handwritten fallback have identical golden
metadata bytes and static constructor behavior.

### 4.2 Scalar codecs

`ValueCodec<T>` has an internal constructor. Applications cannot assert arbitrary
native codec IDs; `Id`/`Name` are logical inspection metadata, not configured per-source native registry handles. `Codecs` factories select a
precompiled supported native codec, not user-supplied Rust layout. The generator maps DateTimeOffset to UtcInstant and DateTime to UtcDateTime under this declared UTC-only policy; local wall-clock timestamp semantics require an explicit future profile. Nullable wrappers
preserve the native codec and add the explicit NULL flag; CLR generic types remain
statically visible. JSON uses a supplied `JsonTypeInfo<T>`, never a reflection
serializer. `EnumInt32<TEnum>` uses checked Int32 backing conversion; undefined
numeric values round-trip as enum values, so application validity is a separate
choice. Flags are not silently reinterpreted as strings.

| CLR surface | Exact ordinary mapping and restriction |
| --- | --- |
| Int16/Int32/Int64 | Signed checked widths; SQLx narrow conversion failures surface, never truncate. SQLite REAL is not accepted as an overflowed integer. |
| Boolean | PG bool; SQLite INTEGER 0/1 with schema expectation, reject other values. |
| String / nullable string | Strict UTF-8; SQL collation, not .NET culture/UTF-16 ordinal equivalence. |
| Bytes | bytea/BLOB; input copied at snapshot, output owned `byte[]`; no lifetime leak. |
| Guid | RFC 4122 network byte order, PG UUID or SQLite 16-byte BLOB; no mixed-endian CLR memory copy. |
| Date / Time | PG date/time; SQLite canonical ISO date/time text; microsecond time precision, reject submicrosecond loss. |
| UtcInstant | `DateTimeOffset` normalized to UTC, PG timestamptz/SQLite Unix microseconds; reject submicrosecond loss and provider range overflow. |
| UtcDateTime | `DateTime` with Kind=Utc only; same logical UTC-instant codec as UtcInstant, read returns Kind=Utc. Local/Unspecified, submicrosecond precision loss and range overflow reject; no timezone inference. |
| Single / Double | PG real/double, SQLite REAL with checked Single conversion; finite values only in ordinary profile. NaN/Infinity require a later explicit profile. |
| Decimal(p,s) | PG numeric with explicit precision 1..29 and scale 0..min(28,p); reject rounding/overflow. Unsupported on ordinary SQLite. |
| DecimalText | Exact SQLite text round-trip only; numeric arithmetic/range/order/aggregate rejected, not decimal SQL math. |
| FixedScaleMoney(scale) | Checked Int64 scaled representation, scale 0..18; exact fixed-scale arithmetic only within overflow-tested native profile. |
| Json<T> | Static JSON serialization/UTF-8; PG JSON/JSONB and enabled SQLite JSON storage profile. No automatic arbitrary CLR type discovery. |

`ResultField`'s native type compatibility is checked before materialization. A
nullable CLR declaration cannot make a missing column legal. Bound data do not
leak raw provider-private type objects. Provider-specific arrays, composite types,
range types, infinities and arbitrary native custom types are planned extensions,
not automatically supported by SQLx/SeaORM dependency presence.

## 5. Source, session, SQL and CRUD (B01–B04/B06–B08/B14)

`DataSource` owns an engine-local pool/runtime/admission budget. `OpenSessionAsync`
returns a caller-owned `DataSession` with one leased physical connection; failed
open publishes no session owner. `Source`, `Provider`, `Name`, `Limits`,
`Capabilities`, `Administration` and `Cleanup` are immutable/snapshot properties.
`DataSession.Transaction` is the currently admitted transaction or null, not an
invitation to replace transaction ownership. Source/session `Cleanup` remains
readable after disposal; other disposed operations reject.

| Member family | Result, snapshot, errors and native behavior |
| --- | --- |
| `ExecuteAsync(SqlCommand)` | 64-bit affected rows; requires Mutation or explicitly SessionMutating. Reject a result-bearing query, never discard its rows silently. SQLx `execute`, fallible arguments and exact effect classification. |
| `ScalarAsync<T>` | Exactly one row/column decoded by explicit codec. Zero/multiple rows or columns is InvalidOperation/ShapeMismatch; nullable codec permits SQL NULL. No arbitrary first-column truncation. |
| `QueryAsync<T>` / `StreamAsync<T>` | Static exact projection; bounded owned list vs one-shot async stream. Stream starts at first MoveNext; command/values are already snapshotted when StreamAsync returns. Token plus enumerator token are linked; first enumeration owns one cursor, repeat enumeration rejects. |
| `FindAsync` | Native key SELECT; returns null on no row, throws on duplicate key-shaped result; no cached/attached entity. Includes every key component and application-supplied tenant key where required. |
| `InsertAsync` | Snapshots entity via writer before dispatch, omits generated columns; returns affected count, does not mutate input record or guess an identity. |
| `InsertReturningAsync<TEntity,T>` | Native INSERT RETURNING exact projection, exactly one row; immutable generated values come back through DTO/entity. Capability checked before write. |
| `UpdateAsync` / `DeleteAsync` | Key-bound native mutation; return 0/1 rows. Multirow result for a declared primary key is schema/constraint error. No read-before-write. |
| `UpdateCheckedAsync` / `DeleteCheckedAsync` | Key + explicit concurrency values in one native mutation; exactly one affected row required, otherwise `ConcurrencyConflictException` with expected/actual counts. Do not read client state or overwrite a changed row. |
| `UpsertAsync` | Explicit conflict target and changes, native `ON CONFLICT`; affected count is provider result. Target columns must identify an existing database primary/unique constraint; constraint-name target is PostgreSQL-only, columns are portable. No exists-then-write race, no SeaORM `save` equivalence. The typed `ConflictTarget.Columns(...).And(...)` declares the target; the provider validates its actual uniqueness atomically and reports a constraint error for missing/incompatible constraints. This does not require a second managed schema model. |
| `LoadRelatedAsync` | One parent's complete key plus explicit Relation maps to native FK SELECT/projection; bounded result list, no tracking or automatic recursive loading. Composite relation components are ordered and validated. CreateOptional/CreateOptionalReference and AndOptional variants explicitly lift the child foreign-key nullability; a NULL foreign key matches no parent. Relation.And variants return new immutable descriptors, so existing registered relations are not mutated. |
| `InsertManyAsync` | Pulls the input `IAsyncEnumerable` with cancellation; snapshots each entity before next MoveNext, bounds rows/bytes per native batch. `BulkAtomicity.All` default owns a transaction if none exists; inside a caller transaction it owns an internal savepoint and never commits the outer transaction. `PerBatch` is explicitly non-atomic across batches and is rejected inside an active caller transaction. No unbounded materialization or invisible COPY fast path. |

Bulk exceptions preserve the original error and transaction outcome; Unknown commit
is still `CommitOutcomeUnknownException`. `BulkResult.CommittedByOperation=false`
inside a caller transaction is not committed success. In caller-owned `All` mode,
create a tracked internal savepoint before consuming input, release it only after
all batches and input enumeration finish successfully, and roll back to/release it
on every input-enumerator, materializer, codec, native, cancellation or disposal
failure. Cleanup uses its independent finite cleanup budget, not an already canceled
business token. The outer transaction remains usable only after that rollback is
confirmed; otherwise mark it Failed, prohibit Commit and quarantine/discard the
connection until outer rollback/cleanup is proven. This rule applies equally to
SQLite and PostgreSQL and does not depend on a provider automatically aborting a
failed statement. Successful-batch progress is historical work, not a claim those
rows remain after savepoint rollback; preserve the original failure plus cleanup
snapshot and progress. Every post-admission bulk failure carries an immutable `BulkProgress` available
through `BulkFailure.TryGetProgress(exception, out progress)`. The adapter stores
it under the exact `Exception.Data` key `NativeWeave.Database.BulkProgress.v1`;
the helper reads only that key on the supplied exception and does not traverse
inner exceptions. This adds one error-path object and no success-path event stream.
RowsAffectedInCompletedBatches excludes a possibly partial current batch;
CompletedBatches counts fully acknowledged native batches. CompletedBatchesCommitted
is true only for confirmed preceding PerBatch commits, false inside a caller
transaction or an uncommitted All operation. CurrentTransactionOutcome preserves
InProgress/Committed/RolledBack/Unknown separately. The native kind15 progress
record accompanies the ordinary rich error payload. Cancellation remains an
OperationCanceledException, Unknown remains CommitOutcomeUnknownException, and a
user enumeration failure keeps its original exception rather than an ORM wrapper.
A `PerBatch` error never promises rollback of prior confirmed commits. Input enumeration/constructor errors stop admission and retire the
same native owner. The progress contract above is part of the current API, not an unspecified future diagnostic.

`SqlCommand.Create` is the explicit trusted SQL/typed-parameter route. Parameters
are named (`@name`) in the logical template and rewritten/bound by the Rust adapter
to the provider's placeholder syntax; names must exactly match, repeated names
refer to one typed value, missing/unused names reject. Literal SQL is trusted code;
external values are `SqlParameters.Add<T>`, never interpolation into a `string`.
No SQL parser/security guarantee is implied for arbitrary templates. The scanner distinguishes PostgreSQL operators such as `@>`/`@@` from named holes; ambiguous tokenization is rejected. The native
adapter's placeholder scanner recognizes quoted strings, escaped/doubled quotes,
PG dollar quotes, identifiers and comments; it does not rewrite occurrences inside
them. Ambiguous/malformed templates reject before send. Tests bind literal `@` and
provider cast/dollar cases. This scanner transports parameters, not SQL semantics.

`SqlCommand.Parameterized(FormattableString)` is the convenience path for built-in
scalars: a format-literal sequence plus typed values is sent to Rust, which chooses
placeholders. Alignment/format specifiers and untyped null arguments reject; use a
typed nullable `SqlParameters` entry for null. There are explicit boxing/object-array
costs on this opt-in path. `Create` with typed parameters avoids that convenience
cost. Names/identifiers are never treated as value holes. The command snapshots
arrays/strings and parameters on construction and is immutable/shareable.

`SessionMutating` requires no active framework transaction and an explicit command
category. It always retires/discards the session's connection on completion unless a
separately verified profile proves reset. Framework-owned transactions reject this
category and untrusted multistatement/transaction-control SQL. Merely selecting
`Query` cannot prove arbitrary SQL safe; expert SQL is an application-trust boundary,
not a sandbox. Ordinary Fluent APIs never fall back to it.

## 6. Transactions, savepoints and cleanup (B05)

`TransactionOptions` fixes `Isolation=null` as provider default (PG ReadCommitted,
SQLite ordinary Serializable plus provider BeginMode), optional RecoveryKey,
30s CommitTimeout, 5s CleanupTimeout and ReadOnly=false. ReadOnly is an enforced
provider transaction mode when supported; unsupported profiles reject, never ignore
it. Isolation requests are accepted exactly or rejected; no silent downgrade.
SQLite transaction BEGIN mode is explicitly Deferred/Immediate, separately from
`System.Data.IsolationLevel`. Nested BeginTransaction is rejected.

The four independent D15 state dimensions remain unchanged. `TransactionState`
uses Active/Failed/CommitInFlight/RollbackInFlight/Closed; `TransactionOutcome`
uses InProgress/Committed/RolledBack/Unknown. Local retirement and connection
reusability are represented by `DatabaseCloseResult`, not guessed from either enum.
`Outcome`, `State`, `CommitAttempted`, `RecoveryKey` and `Cleanup` survive disposal.

`CommitAsync(admissionToken)` observes the token **only before commit admission**.
Native admission atomically enters CommitInFlight and sets CommitAttempted; once
sending may have begun, the independent commit deadline drives a confirmed commit,
confirmed rollback/failure, or Unknown. Success means Committed. Request disconnect
never changes possible commit into Task.Canceled. `CommitOutcomeUnknownException`
contains inherited ProviderCode/CorrelationId, RecoveryKey and Outcome=Unknown;
application recovery uses that identity and an atomic idempotency protocol. No
transparent retry is permitted. A known Failed transaction cannot commit.

`RollbackAsync(admissionToken)` likewise cancels only before admitting rollback.
Once admitted it uses the independent cleanup policy. If rollback is unconfirmed
with CommitAttempted=false, state is Closed/InProgress with RollbackUnconfirmed;
it must not invent RolledBack or Unknown commit. Explicit rollback failure throws
`DatabaseCleanupException`; automatic cleanup records the failure without replacing
an already reported business/commit error. Cleanup never refines an Unknown outcome
without independent identity-bound evidence.

`CreateSavepointAsync` generates its own safe identifier and returns a transaction-
generation-bound `Savepoint`; names are not user SQL. Savepoints form a LIFO stack.
Only the top may Rollback/Release; wrong generation/order rejects before dispatch.
Rollback rolls back to the savepoint and keeps it active for later release.
Release does not commit the outer transaction. `DisposeAsync` rolls back to and
releases an unreleased top savepoint, then joins safety; it is not an implicit
commit of changes after the savepoint. If already released/outer closed it is
idempotent and never touches a reused connection. Non-top disposal cannot reorder
SQL; it records invalid-state cleanup and closes the outer transaction admission.
The initial policy uses SQLx's tracked same-connection nested transaction/savepoint
mechanism, not raw BEGIN that bypasses SQLx transaction depth.

For a response with a finite cleanup wait, use explicit CloseAsync control flow;
following a Pending snapshot immediately with unconditional `await using` disposal
would deliberately join indefinitely. Closing never frees callbacks/buffers or
returns a dirty/quarantined connection. The engine's bounded cleanup ledger remains
alive until SQLx futures, worker obligations and callbacks retire.

## 7. Native Fluent query semantics (B09/B11/B13)

### 7.1 Owner model and everyday expressions

`session.From(Table<T>)` creates one native SeaQuery SelectStatement arena and a
managed owner wrapper. `Query<T>`, all `SqlExpression<T>`, `SqlPredicate`,
`QueryRow<T>`, aliases, window definitions and query projections carry owner and
generation identity. Public value structs are opaque tokens, not native handles or
managed AST nodes; default instances are invalid. Operations call native builders
immediately. One synchronous mutation gate protects Rust mutable state; SafeHandle
pinning alone is insufficient.

`Where(Func<QueryRow<T>,SqlPredicate>)` executes the delegate synchronously once.
`WhereIf(condition, predicate)` validates the receiver/delegate but invokes the
same callback only when condition is true; false adds no native condition or
captured values. It never inspects C# IL/expression trees, compiles arbitrary `Func<TEntity,bool>`,
or rereads captured values after an await. Direct `WhereEqual`,
`WhereGreaterThanOrEqual`, `WhereIsNull`, `WhereIsNotNull` avoid delegate/closure
allocation on hot composition paths. Values are copied when their expression or
setter is created. Delegate exceptions do not attach an incomplete clause; query-
owned temporary expression nodes stay charged until disposal.

`Where(SqlPredicate)` appends with AND. `And`, `Or`, `Not` build native conditions.
`Equal`, `NotEqual`, comparisons and Between use SQL three-valued logic. `IsNull`
and `IsNotNull` are explicit. `NullSafeEqual` is capability/codec-bound, not a claim
that .NET equality/NaN/collations match every database. `In`/`NotIn` snapshot the
span immediately; empty sets deliberately yield FALSE/TRUE and this convenience is
specified separately from invalid empty SQL syntax. Sets containing NULL retain
SQL UNKNOWN semantics. Subquery `In` requires exactly one compatible projection.

Arithmetic extension methods constrain T to System.Numerics.INumber<T>, so adding
numbers to a string/Guid expression fails C# compilation. Same-owner expression
operands and nullable-value overloads are explicit. Nullable arithmetic propagates
SQL NULL and never coalesces implicitly. Relational operator value/expression
overloads preserve the same codec and owner checks. They remain native SQL operations with codec compatibility checks;
SQL integer overflow, decimal precision and divide-by-zero behavior remain explicit
provider semantics, not implied C# checked arithmetic. `ContainsLiteral`,
`StartsWithLiteral`, `EndsWithLiteral` escape wildcard/escape characters and bind
values. `Like` takes a raw SQL LIKE pattern. Nullable text uses explicitly named
`ContainsNullableLiteral` / `LikeNullable` so nullability is not erased by an
invariant generic wrapper. `Collate` only selects an allowlisted provider collation.
There is no culture-sensitive CLR fallback. `SqlFunctions.Coalesce` and
`CoalesceReference` explicitly choose a non-null result type.

### 7.2 Joins and projection

`InnerJoin` and `LeftJoin` use an explicit table, unique alias and synchronous ON
builder over `JoinPredicate<TLeft,TRight>`. The callback sees non-null declared
columns for ON evaluation. The returned aliases differ in type: `JoinedTable<T>`
allows ordinary Column reads; `LeftJoinedTable<T>` requires NullableValue or
NullableReference for projected/right-filtered columns. A non-null column cannot
silently become a non-null LEFT JOIN result. `HasMatch` uses a native explicit
match marker, separate from whether an arbitrary nullable field contains NULL.
ON predicates remain ON; moving them to WHERE is never an optimization.

Aliased self-joins are legal and must retain separate owner/alias identities.
Additional joins may reference an already joined alias captured by the callback;
all tokens must have the same arena. Cross-session/query tokens reject, even if
entity types happen to match. `SelectAll` selects only the root table and never
implicitly creates joined object graphs. Two-expression `Select` uses a static
factory for a compact DTO; arbitrary column counts use ProjectionBuilder and typed
ResultColumn ordinals. All projections validate count/order/names/type/nullability
before materialization. No hidden identity resolution, object graph fix-up or
reflection construction is performed.

### 7.3 Ordering, grouping, aggregate and advanced native operations

* `OrderBy` replaces the order list; `ThenBy` appends and requires a prior order.
  Expressions and column overloads specify Ascending and NullOrder.Last by default;
  both providers must render explicit null ordering. `Skip`/`Take` are nonnegative
  bounded offset/limit; offset paging requires an order whose final keys are known
  unique. `Take` without order is an explicitly nondeterministic limit, not paging.
* `SeekAfter` v1 requires one non-null unique ascending order key and no conflicting
  offset/order; it appends a native strict comparison and preserves all existing
  tenant/security predicates. It does not create an external cursor token or
  snapshot consistency. Composite/nullable/descending cursors remain planned;
  applications can build explicit native predicates now without a false turnkey
  cursor claim.
* `GroupBy` appends native grouping expressions; `Having` appends group conditions.
  Nonaggregated projection expressions must be grouping keys. `CountRows` is native
  COUNT(*); `Count(expr)` skips NULL and optionally uses DISTINCT. COUNT is Int64.
  Sum/Min/Max/Average return nullable on empty input. PG SUM(bigint) -> numeric is
  checked against the declared Int64 result; overflow is a conversion error. Decimal
  results retain the codec's precision/scale and may fail rather than round silently.
  There is no automatic zero for empty SUM. Nullable-input overloads skip NULL
  with the same empty-input result. SUM(Int32/Int64) returns checked Int64,
  SUM(Single/Double) returns Double, and SUM(Decimal) returns Decimal;
  AVG integral/Single/Double returns Double with explicitly permitted binary
  floating-point rounding, while AVG(Decimal) retains the explicit decimal profile.
  PostgreSQL numeric outputs are converted fallibly to those declared targets;
  SQLite DecimalText aggregates still reject. Nullable Min/Max preserve the
  original value codec; MinNullableText/MaxNullableText preserve SQL collation.
* `Distinct`, `Combine(Union/UnionAll/Intersect/Except)` are native set operations
  requiring exact compatible projection shapes and codecs. The right operand is
  cloned natively under read admission; it is not borrowed after its owner closes.
  Set duplicate/null/order semantics are SQL semantics. Different sources reject.
* `CommonTable<T>.Create` freezes/clones a native selection against an explicit
  declared table shape; `With` attaches it to a native query. Recursive=true requires
  a native recursive anchor/recursive-member UNION shape, one declared recursive
  self-reference and bounded construction depth. The adapter validates arity/types
  and supported clauses before SeaQuery rendering. Malformed/empty CTEs reject. The declared shape has a distinct logical table name:
  build the body from physical metadata, create CommonTable against the CTE shape,
  then `session.From(cteShape).With(cte)`. That name is scoped to WITH and requires
  no physical table. A recursive member references the same declared CTE shape;
  native validation distinguishes that single permitted self-reference from
  missing physical tables or accidental cycles. Names/column arity are explicit.
* `Window` returns query-owned native window state. PartitionBy/OrderBy append;
  RowsBetween accepts the three explicit FrameBoundary values and rejects invalid
  start/end combinations. Rank/RowNumber/aggregate Over are supported inline windows.
  Finite PRECEDING/FOLLOWING offsets, RANGE/GROUPS frames and arbitrary named-window
  registries are planned; the inspected SeaQuery named-window slot must not be
  marketed as an unbounded named-window list.
* `ForUpdate` is PostgreSQL-only and supports declared Update/Share/NoKeyUpdate/
  KeyShare plus Wait/NoWait/SkipLocked. SQLite rejects before sending; it cannot
  silently ignore a lock clause. Locks require an explicit active transaction.
* `Case`, typed parameters, native EXISTS/IN subqueries and explicit alias/projection
  composition provide common conditional/dynamic queries. LATERAL, provider custom
  functions, C# method translation and arbitrary expression trees are not assumed.

`CountAsync` counts the rows of the fully composed query, including Distinct,
grouping and paging, through a native subquery when needed. `AnyAsync` performs
native EXISTS respecting the same clauses. Neither fetches all DTOs into C#.
`UpdateAsync(Changes)` or setters and `DeleteAsync` perform set-based native writes;
no tracking and no automatic concurrency check. They require a WHERE clause by
default; explicit all-row operations are performed through audited expert SQL in
v1. Join/group/CTE/set/window mutations outside a provider-tested shape reject,
never discard clauses to manufacture an UPDATE/DELETE.

### 7.4 Terminal behavior, streaming and prepared shapes

Mutable query -> Sealed -> Submitted -> Closed is the single-execution path.
Selection is a borrowed managed view and owns no second native arena. The first
terminal snapshots/seals and admits one execution; another terminal, mutation or
parallel stream fails. `Clone` creates an explicit deep native mutable copy before
submission, charging its bytes. `ToSql` renders a bounded native clone for diagnostics
without executing/sealing; returned SQL contains placeholders and no parameter values.

`ToListAsync` returns bounded `IReadOnlyList<T>` (ordinary owned list), `ToArrayAsync`
returns an owned array, and neither silently switches to streaming when limits
are exceeded. First/Single return the appropriate row or throw on cardinality;
First reads at most one business row, Single at most two, then retires the cursor.
The `OrDefault` methods return default(T) on absence, following C# generic nullable
annotation rules: for value-type T this is the zero/default value, not a magically
wrapped `Nullable<T>`. Use SingleAsync when absence must be distinguished, or a
nullable scalar projection plus an explicit existence query when required.

`AsAsyncEnumerable` snapshots/seals synchronously and creates a one-shot sequence;
first MoveNext dispatches. The query/parent source remains rooted through the cursor.
Explicit query disposal closes admission and requests stop, so callers keep the
`using query` scope across enumeration. Enumerator disposal on break/exception
releases the current owned batch, stops/drains native work and joins its retirement.
No implicit prefetch; one batch, finite rows/bytes, at most one MoveNext in progress.
DTO values may outlive the cursor because they own their memory. RowReader cannot.

`Prepare` seals/transfers an immutable source-bound native shape to a new
`PreparedQuery<T>` and closes builder mutation/execution admission. It does not
promise one physical server prepared statement usable on every pooled connection.
SQLx owns per-connection statement caches; NativeWeave owns only bounded native
shape/metadata caches. Named typed QueryParameter values identify immutable parameters
in their source generation; each sealed shape fixes its exact allowed ID set.
QueryParameters snapshots at each execution, all parameters required exactly once.
Prepared shapes may execute concurrently **on separate sessions of the same source**.
Each execution has independent values/cursor/operation owners. Disposing a prepared
shape prevents new executions but retained in-flight executions complete safely.
Shape identity includes module ABI/profile, metadata hashes, projection and operators;
ordinary values are excluded. No uncontrolled global plan cache exists.

## 8. Administration and intentionally bounded scope (B08)

Migration bundles are immutable, provider-bound, strictly ascending positive
versions with canonical SQL bytes, description and transactional flag. Duplicate
versions or changed checksums reject. `MigrateAsync` only applies forward to the
optional target; no implicit destructive downgrade. `ValidateMigrationsAsync`
checks ledger/checksum/dirty state without changing schema. `GetMigrationStatusAsync`
returns bounded immutable state; missing/extra incompatible entries fail validation.
`GetTablesAsync(schema)` returns bounded table/column metadata using trusted native
provider catalog queries, with allowlisted schema scope and no reflection/DataTable.
It does not generate schema differences, automatically create models or expose
provider-private row objects.

Every migration operation owns a dedicated administrative connection. PG uses
SQLx Migrator/checksum/ledger and session advisory locking, with closure on error
rather than returning a possibly locked connection to the application pool. SQLite
rejects nontransactional entries first, uses tracked
`Connection::begin_with("BEGIN IMMEDIATE")`, runs Migrator against that transaction,
and explicitly commits/rolls back the outer batch. Raw BEGIN without SQLx depth
tracking is prohibited. Nontransactional PG migration is an explicit flag and
requires AllowNonTransactional; partial effects remain recorded and resumable.
No default runtime migration on source creation/DI activation.

The following are explicit v1 exclusions, not missing silent implementations:
ADO.NET inheritance/provider registration, DataSet/DataTable/designers,
TransactionScope/distributed transactions, MARS, automatic retries of writes,
transparent lazy loading, general change tracking/identity maps/graph SaveChanges,
reflection-created DTOs, arbitrary IQueryable/C# lambda translation, dynamic managed
plugin loading under Native AOT, MySQL/SQL Server/Oracle product providers,
automatic schema-diff/down-migration tools, right/full-outer-join convenience (including .NET11 FullJoin), multiple-result-grid processing,
stored-procedure output/ref-cursor abstractions, COPY/incremental BLOB streaming,
provider arrays/composites and unattended schema synchronization. Native functionality
may exist upstream; a future extension must specify/verify its own public API,
owners, ABI and task before claiming support. Explicit SQL handles ordinary
provider statements within the same trusted, bounded result/transaction rules.

## 9. Complete implementation boundary and C ABI v1

### 9.1 Cross-layer mapping and fixed wire conventions

C# facades call generated `DatabaseAdapter` operation methods with typed owners and
static descriptors. Those methods acquire logical admission before extracting a
safe native handle, encode immutable scalar/metadata payloads, invoke the creating
module's operation table and translate the existing Core status/error contract.
They do not retain a parallel managed SQL tree. Rust `DatabaseAdapter` validates
again, mutates the owned SeaQuery state or schedules a SQLx future on its own
executor. No SQLx/SeaQuery type or Rust enum discriminant crosses ABI.

The following are **normative internal signatures**, not public CLR methods or
already exported functions. Core `nw_status`, `nw_error_info_v1`, callback records,
opaque owners and byte views retain D02–D08 exact layouts. `nw_db_ref` is an opaque
creating-engine owner pointer validated by that module. `nw_db_token` is a u64
query-arena slot/generation token, never an address. Query token zero is invalid.
Every output pointer/token is zeroed before validation and is transferred only on
success. Input byte views are borrowed synchronously; persistent state is copied
before return. Query-arena tokens require no per-expression public release.

```c
typedef struct nw_db_owner* nw_db_ref;
typedef struct nw_db_buffer nw_db_buffer;
typedef uint64_t nw_db_token;
nw_status NW_CDECL nw_db_operation_start_v1(nw_db_ref op, const nw_operation_callbacks_v1* callbacks, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_request_cancel_v1(nw_db_ref op);
nw_status NW_CDECL nw_db_operation_take_owner_v1(nw_db_ref op, uint32_t expected_kind, nw_db_ref* owner, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_take_buffer_v1(nw_db_ref op, nw_db_buffer** buffer, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_take_count_v1(nw_db_ref op, int64_t* count, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_take_error_v1(nw_db_ref op, nw_db_buffer** error_payload, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_try_retire_v1(nw_db_ref op);
void NW_CDECL nw_db_operation_release_v1(nw_db_ref op);
nw_status NW_CDECL nw_db_source_create_v1(nw_bytes_view_v1 config, nw_db_ref* source, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_session_open_create_v1(nw_db_ref source, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_codec_register_v1(nw_db_ref source, uint32_t logical_codec, nw_bytes_view_v1 configuration, uint32_t* bound_codec_id, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_metadata_register_v1(nw_db_ref source, nw_bytes_view_v1 metadata, nw_db_ref* model, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_projection_register_v1(nw_db_ref source, nw_bytes_view_v1 projection, uint32_t* projection_id, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_create_v1(nw_db_ref session, nw_db_ref model, uint32_t table_id, nw_db_ref* query, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_column_v1(nw_db_ref query, nw_db_token alias, uint32_t column_id, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_value_v1(nw_db_ref query, nw_bytes_view_v1 one_cell, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_parameter_v1(nw_db_ref query, uint32_t parameter_id, nw_bytes_view_v1 name, uint32_t codec_id, uint32_t nullable, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_binary_v1(nw_db_ref query, uint32_t op_code, nw_db_token left, nw_db_token right, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_unary_v1(nw_db_ref query, uint32_t op_code, nw_db_token input, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_expr_list_v1(nw_db_ref query, uint32_t op_code, nw_db_token input, nw_bytes_view_v1 cells, nw_db_token* expr, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_import_v1(nw_db_ref query, nw_db_ref dependency, uint32_t kind, nw_db_token* token, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_clause_v1(nw_db_ref query, uint32_t clause, nw_bytes_view_v1 operands, nw_db_token* out_token, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_seal_v1(nw_db_ref query, uint32_t terminal, nw_db_ref* plan, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_clone_v1(nw_db_ref query, nw_db_ref* clone, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_render_v1(nw_db_ref query, nw_db_buffer** sql, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_cte_create_v1(nw_db_ref declared_model, uint32_t table_id, nw_db_ref body_query, uint32_t recursive, nw_db_ref* cte, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_execute_create_v1(nw_db_ref session, nw_db_ref plan, nw_bytes_view_v1 parameters, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_sql_create_v1(nw_db_ref session, nw_bytes_view_v1 template, nw_bytes_view_v1 parameters, nw_bytes_view_v1 command_options, nw_db_ref* plan, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_cursor_fetch_create_v1(nw_db_ref cursor, uint32_t max_rows, uint64_t max_bytes, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_tx_begin_create_v1(nw_db_ref session, nw_bytes_view_v1 options, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_tx_finish_create_v1(nw_db_ref tx, uint32_t action, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_savepoint_create_v1(nw_db_ref tx, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_savepoint_action_create_v1(nw_db_ref savepoint, uint32_t action, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_mutation_create_v1(nw_db_ref session, nw_db_ref model, uint32_t mutation, nw_bytes_view_v1 values_keys_checks, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_admin_create_v1(nw_db_ref source, uint32_t action, nw_bytes_view_v1 payload, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_close_create_v1(nw_db_ref owner, nw_db_ref* op, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_snapshot_v1(nw_db_ref owner, nw_bytes_view_v1 query, nw_db_buffer** snapshot, nw_error_info_v1* error);
void NW_CDECL nw_db_owner_release_v1(nw_db_ref owner);
nw_status NW_CDECL nw_db_buffer_view_v1(nw_db_buffer* buffer, nw_bytes_view_v1* view, nw_error_info_v1* error);
void NW_CDECL nw_db_buffer_release_v1(nw_db_buffer* buffer);
```

All `_create` async operations return a **Created** operation, not a completion.
They use Core create/start/notify/take_result/request_cancel/try_retire/release.
The typed take-result methods share one atomic result-taken flag. Owner kind
1=session, 2=cursor, 3=transaction, 4=savepoint; unknown/wrong kind is INVALID_STATE
without consuming the result. Count results use Int64. Buffer results carry their
validated db-wire/control kind. `start` copies the callback table and permits the
terminal callback to race with/before start returns after native admission;
registration/rooting therefore precedes start. `take_error` separately takes one
bounded rich diagnostic payload on terminal failure; it does not consume or change
the primary result/outcome. Only one corresponding take succeeds. Retirement of an
operation does not destroy a transferred result owner. `request_cancel` is a
nonblocking, idempotent atomic flag/notification returning OK; it has no diagnostic
out-parameter and does not itself certify a canceled terminal result. No callback
enters SQLx/SQLite blocking sends. `operation_try_retire` takes only the operation
owner and returns OK after the Core native-quiescence conditions hold, otherwise
PENDING; it neither returns diagnostics nor changes the business result.
`operation_release` has the exact Core void/no-error shape and is legal only for a
never-started Created operation or a proven Retired operation with no live managed
calls. It frees untaken results/inputs and the owner once, without callbacks, unwind
or blocking executor join. These three signatures specialize Core section6.2;
Database does not define a second cancellation/retirement/release protocol.
`owner_release` only requests close/joins an already quiescent owner or transfers
it to the bounded cleanup ledger; it is not blocking provider I/O in SafeHandle.
Both owner and immutable-buffer release have the void, nonfailing destructor shape.
The cleanup-ledger slot is reserved when the owner is created, so final release
cannot fail for lack of cleanup capacity. Every valid release consumes its owner
once and must not be retried; it has no diagnostic out-parameter, callback, blocking
join or unwind. Explicit Close supplies business/cleanup errors before final release.
An immutable buffer destructor is its creating module's Core-compatible free-threaded
release function; no status-returning alternative is passed to NativeBufferFactory.

Value/row arrays reuse **db-wire/1** D14's 96-byte header, 16-byte descriptors and
24-byte cells, checked nonoverlap, UTF-8, lengths and canonical codec tags. No second
cell encoding is introduced. Metadata uses D17's canonical table/column/key/
projection descriptor content; B01 owns both-side schema generation. For new command
control records the envelope is little-endian field serialization, never C struct
layout: `version:u16=1, kind:u16, size:u32, field_count:u32, reserved:u32=0`, followed
by sorted unique 16-byte entries `{field_id:u16,type:u16,length:u32,offset:u64}`.
Offsets start after the entire table, are bounds-checked, and nonempty ranges may
not overlap. Field types: 1=u32 (4 bytes), 2=u64 (8), 3=finite nonnegative timeout
nanoseconds (u64), 4=strict UTF-8, 5=binary bytes (nested records validated when that field requires one),
6=db-wire/1, 7=u32 vector, 8=u64 token vector. Unknown field/kind rejects;
missing required field rejects; no default inferred across an incompatible version.

| Control kind | Required field IDs (optional in parentheses) | Meaning |
| --- | --- | --- |
| 1 source config | 1 provider:u32, 2 connection/path:UTF8, 3 limits:record, 4 provider options:record, (5 name:UTF8) | Credentials are transient copied config and never included in errors/logs. Limits record fields 1..15 follow DatabaseLimits declaration order, each u64/count or timeout-ns; overflow rejects before narrowing. |
| 2 metadata | 1 canonical D17 descriptor:type5 raw UTF8 JSON bytes, 2 metadata hash:32 raw bytes encoded type5 | metadata_register receives the complete kind2 envelope; field1 is JSON, not a nested control-record envelope. Content hash recomputed natively; schema mismatch rejects. |
| 3 transaction options | 1 isolation:u32 (0 default,1 ReadCommitted,2 RepeatableRead,3 Serializable), 2 read_only:u32, 3 commit_ns, 4 cleanup_ns, (5 recovery_key:UTF8) | SQLite BEGIN mode comes from source profile, not isolation enum reinterpretation. Other BCL isolation values reject. |
| 4 mutation | 1 entity/table ID:u32, (2 insert/update values:db-wire), (3 key:db-wire), (4 checks:db-wire), (5 conflict columns:u32vector), (6 constraint:UTF8), (7 projection ID:u32), (8 upsert update values:db-wire) | The mutation table below fixes required/forbidden fields; insert values and upsert assignments have separate payloads. Duplicate set/key/check IDs reject. |
| 5 administration | 1 provider:u32, (2 bundle:record), (3 target:u64), (4 timeout_ns), (5 flags:u32), (6 schema:UTF8) | Immutable migration records contain version/description/SQL/mode and verified hashes. Schema list action has no bundle. |
| 6 clause operands | Operation-specific fields in table below | Tokens are query-owned; aliases/model IDs are validated. |
| 7 cleanup/outcome snapshot | 1 tx_state:u32, 2 outcome:u32, 3 commit_attempted:u32, 4 cleanup:u32, 5 disposition:u32, 6 released:u32, 7 deadline:u32, 8 correlation:u64, (9 provider_code:UTF8), (10 recovery_key:UTF8) | Raw codes explicitly map to the public enums in declaration order, with 0-based IDs. Snapshot preserves independent dimensions; absent tx fields for source/session are zero and ignored. |

Finite timeout units are nanoseconds checked against TimeSpan ticks/overflow;
C# TimeSpan ticks convert exactly by multiplication by 100. Optional null timeouts
select the source finite default, never unbounded zero.

The mutation code passed to `nw_db_mutation_create_v1` determines the complete
kind4 field set. Field1 is always required; every field not listed below is
forbidden, rather than ignored. Fields2/3/4/8 each contain an independent kind4
db-wire payload with that table's metadata hash and the ordered column IDs for
its own role. Key and concurrency values are never inferred from the insert row.

| Mutation code | Additional required fields | Validation and result |
| --- | --- | --- |
| 0 insert | 2 insert values | One entity row for InsertAsync; a bounded multirow payload for Bulk.Insert. Generated columns are omitted. Returns affected Int64 count. |
| 1 insert-returning | 2 insert values, 7 registered projection ID | Exactly one insert row and one returned row; resolve RETURNING columns against that table before writing. |
| 2 update | 2 assignment values, 3 complete key | Exactly one nonempty assignment row and one complete key row; returns 0/1 affected count. |
| 3 update-checked | 2 assignment values, 3 complete key, 4 expected concurrency values | Same update plus one nonempty expected-value row in its native WHERE; exactly one affected row or concurrency conflict. |
| 4 delete | 3 complete key | No assignment/insert payload; returns 0/1 affected count. |
| 5 delete-checked | 3 complete key, 4 expected concurrency values | No assignment/insert payload; exact key and nonempty expected values in one native WHERE. |
| 6 upsert | 2 insert values, 8 assignment values, exactly one of 5 conflict columns or 6 constraint name | Exactly one insert row plus an independent nonempty update row; native ON CONFLICT uses only the explicitly supplied update assignments. Returns provider affected count. |

All key/check/assignment payloads have exactly one record. A generated-only insert
may have zero descriptors in its one row and maps to native DEFAULT VALUES when
the provider profile supports it; zero rows are never an insert command.
Assignments reject key/generated columns, wrong-table IDs and duplicate IDs.
Upsert snapshots both the entity writer output and `Changes<TEntity>` before
admission. Field8 is not an implicit EXCLUDED-row update: values may differ from
field2, may contain an explicit SQL NULL, and may update only a subset of columns.
Native SeaQuery builds the insert and conflict assignment expressions from these
two separate value sets, with one fallible SQLx parameter binding and statement
execution. No exists-then-write query or managed SQL construction is introduced.

### 9.1.1 Canonical metadata and nested control records

Startup model metadata has one canonical UTF-8 JSON representation (bounded by
MaxParameterBytes, MaxQueryDepth and MaxQueryNodes). It is not a query AST. Keys
appear in exactly the order below, strings use JSON escaping without Unicode
normalization, numbers are unsigned decimal integers without leading zeroes,
booleans lowercase, and no insignificant whitespace is emitted. Absent optional
values are explicit null. JSON string encoding is fixed: quote and backslash use
`\"` and `\\`; U+0000..U+001F use exactly six ASCII bytes `\u00xx` with lowercase
hexadecimal digits (no short `\n`/`\t` forms). Slash is literal `/`; all remaining
Unicode scalar values are literal strict UTF8, including U+2028/U+2029. No optional
Unicode escapes, BOM or surrogate code points are allowed. A SHA-256 hash covers those canonical bytes. Native
validation rejects duplicate/unknown properties, invalid UTF-8, duplicate
IDs, column names equal under the provider identifier policy, inconsistent
nullability and missing codec/key references before caching. No runtime reflection
serializer is required; the generator emits canonical bytes, and the handwritten
builder uses the same bounded schema encoder.

```json
{"version":1,"logical_id":"Assembly:Namespace.Type","table_id":3828691529,"schema":null,"table":"students","columns":[{"id":4225434237,"name":"id","codec":3,"codec_config":null,"nullable":false,"key_ordinal":0,"generated":false,"concurrency":false,"collation":null,"max_length":null}],"projection":[4225434237],"relations":[]}
```

The sample codec 3 is Int64 in the registry below; actual codec IDs are generated
from that canonical registry, never inferred from CLR enum order. The logical_id is
the known closed entity type's assembly simple name, `:`, and CLR FullName. Both
generator output and handwritten TableBuilder use the same bounded known-type
identity helper (`typeof(TEntity)` only); this is not member reflection, assembly
scanning or dynamic construction. Null/empty type identity rejects. Closed generic
FullName content is retained exactly, so a changed encoded type identity changes
the metadata identity rather than pretending binary compatibility.

Table and column IDs are the first four SHA-256 digest bytes interpreted as a
little-endian u32 of these canonical JSON arrays respectively:
`["NWDB-TABLE-ID-v1",logical_id,schema,table]` and
`["NWDB-COLUMN-ID-v1",logical_id,schema,table,column_name]`.
Schema null is JSON null, not an empty string. Relation IDs hash
`["NWDB-RELATION-ID-v1",parent_logical_id,child_logical_id,parent_column_ids,child_column_ids]`
with the same rule and ordered numeric arrays. Zero IDs and different complete
identities with the same ID are rejected (generator NWQ0110; handwritten mapping
ArgumentException); never probe/reassign IDs according to registration order.
The native registry repeats full-identity/hash/collision validation. This fixes
stable nonzero u32 values without a platform-specific string hash; projection ordinals follow the ordered projection
array, not hash-map order. `key_ordinal` is null for nonkeys, otherwise contiguous
0-based primary-key component order; builder declaration order determines it.
`max_length` is a positive byte capacity or null. A relation record is
`{id,child_logical_id,parent_columns:[ids],child_columns:[ids]}` with equal positive
arity, and arrays of columns/relations are sorted by ID. Generated constructor
parameter order is recorded by projection, independently of descriptor ordering.

`Projection<T>.Create` serializes a descriptor with ordered
`{ordinal,name,codec,codec_config,nullable}` fields, owned materializer identity remaining managed.
Query projections add ordered arena-expression tokens separately through clause 6;
no managed function pointer is embedded in metadata. Generated and handwritten
projection hash bytes must match for the same declared shape. The exact logical
shape encoding is `{"version":1,"fields":[{"ordinal":0,"name":"id","codec":3,"codec_config":null,"nullable":false}]}`
with the same canonical JSON rules above, contiguous ordinals and fields in result
order. ShapeHash is lowercase hexadecimal SHA-256 of these bytes. Query tokens,
source-bound codec IDs and managed materializer identity are excluded from this hash.
After resolving configured codecs, kind13 carries the bound descriptor and this
logical hash; native reconstructs logical codecs/configurations and verifies it.
`projection_register` atomically interns that complete shape in the source and
returns a positive source-bound ID, reused only for byte-equivalent logical shapes.
The source owns it until close; the combined metadata/projection registry is bounded
by MaxQueryNodes entries and MaxParameterBytes encoded bytes. Registration that
would exceed either bound fails before publication, never evicts an in-use binding.
Raw Query/Stream and mutation returning register their projection before creating
the command/mutation. Scalar registers a one-field projection whose alias is the
empty string: this sentinel ignores only the provider column name, never its count,
codec or nullability. Empty aliases are otherwise invalid. Scalar shape and result
kind still require exactly one row and one column. Query/returning bindings require
exact nonempty aliases; native RETURNING resolves each alias to a declared table
column and validates its codec before any write.

Nested control records use the envelope already defined, with these exact kinds:

| Kind | Fields / validation |
| --- | --- |
| 8 PostgreSQL options | 1 TLS u32(0 VerifyFull/1 local-development disabled), 2 root-certificate path UTF8 optional, 3 application-name UTF8, 4 connect-timeout ns; unrecognized connection-string options reject and cannot override typed TLS policy |
| 9 SQLite options | 1 open-mode u32(0 rw-create/1 rw/2 ro/3 memory), 2 journal u32(0 WAL/1 DELETE/2 MEMORY), 3 synchronous u32(0 NORMAL/1 FULL), 4 begin-mode u32(0 DEFERRED/1 IMMEDIATE), 5 busy-timeout ns, 6 foreign-keys u32(0/1); impossible combinations reject before opening |
| 10 limits | Fifteen fields in DatabaseLimits declaration order; count/bytes u64, timeouts ns; mandatory, positive except valid zero buffered result demand, with native hard-limit validation |
| 11 migration entry | 1 version u64 positive, 2 description UTF8, 3 SQL UTF8, 4 mode u32(0 transactional/1 nontransactional), 5 SHA-256 binary32; checksum is SQLx's migration checksum algorithm in its own ledger, while bundle content hash remains separately identified |
| 12 migration bundle | 1 provider u32, 2 entries binary sequence (u32 count followed by repeated u32 length + kind11 record), 3 bundle SHA-256 binary32; strict ascending unique versions and total-byte/count caps |
| 13 projection | 1 ordered fields binary sequence (u32 count followed by u32 length + kind22 record),2 logical shape SHA-256 binary32; codec binding completed before this native record |
| 14 window-order entry | 1 expression token u64,2 direction u32,3 null-order u32; clause11 order list uses the same count/length record sequence |
| 15 bulk failure progress | 1 rows-affected-in-completed-batches u64 bounded Int64,2 completed-batches u32 bounded Int32,3 completed-commits u32(0/1),4 current-tx-outcome u32 matching TransactionOutcome; no inference from cancellation or row count |
| 16 migration status entry | 1 version u64 bounded positive Int64,2 description UTF8,3 checksum UTF8 (lowercase hexadecimal SQLx ledger checksum),4 applied u32(0/1) |
| 17 schema column | 1 name UTF8,2 provider store-type UTF8,3 nullable u32(0/1),4 primary-key u32(0/1) |
| 18 schema table | 1 schema UTF8 optional,2 name UTF8,3 columns binary count/length sequence of kind17 records |
| 19 administrative result | 1 action u32,2 entries binary sequence optional (kind16 for status/action1; kind18 for tables/action3),3 applied-count u32 optional,4 current-version u64 optional,5 completed u32 optional; action0 requires fields3/5, action1/3 requires field2, action2 returns empty success with only field1 |
| 20 raw command options | 1 command kind u32(0 Query,1 Mutation,2 SessionMutating),2 result kind u32(0 affected-count,1 scalar,2 buffered rows,3 stream),3 resolved finite timeout ns,4 registered projection ID u32(0 only for affected-count),5 parameter definitions binary count/length sequence of kind21,6 template kind u32(0 named SQL UTF8,1 interpolated segment sequence) |
| 21 named parameter definition | 1 parameter ID u32 positive,2 name UTF8 without @,3 bound-codec u32,4 nullable u32(0/1); definitions ordered by parameter ID, names/IDs unique and exactly matched to db-wire descriptors |
| 22 projection field | 1 ordinal u32,2 alias UTF8,3 bound-codec u32,4 nullable u32(0/1); optional5 arena expression token u64 only for inline query projection |


Migration entry field5 is the adapter's SHA-256 identity of immutable SQL bytes;
the SQLx ledger uses SQLx's actual checksum type/algorithm and is never overwritten
with that adapter hash. Both are tracked separately. Source config provider-options
field4 selects kind8/9; limits field3 selects kind10. Control kind5 bundle field2
selects kind12. Administrative results are owned buffers returned through operation_take_buffer;
the adapter materializes the exact MigrationStatus/MigrationReport/SchemaTable
records before releasing them. Record counts, strings and nested schema columns
are charged to MaxBufferedRows/MaxBufferedBytes and MaxFieldBytes. A failed migration
keeps its original error and ledger state, rather than returning Completed=false as
successful execution. The common sequence encoding has no padding and validates checked
sum lengths before allocating. Zero-length elements, extra bytes and repeated
mandatory field IDs reject.

Raw command options supply every public SqlCommand choice to `sql_create`:
command/effect class, finite deadline, result shape and parameter identity. A null
managed timeout resolves to source CommandTimeout before serialization; explicit
zero means expiration before dispatch. The operation converts it once to a
monotonic deadline at execution admission, covering provider execution and cursor
consumption. A buffered/stream/scalar result requires Query command kind; an
affected-count result requires Mutation or SessionMutating. These checks happen
before a provider statement is admitted. Native plans retain the registered shape
and parameter schema; raw SQL never has to guess its desired codec from a CLR type.

Prepared Query.Parameter IDs are nonzero u32 identities allocated monotonically by
the source-generation coordinator, never query-local indices and never recycled
before source disposal. Exhaustion fails with a resource-limit error. The exact
Expression.Parameter ABI above transmits ID/name/bound-codec/nullability, and native
rejects reuse of an ID with different metadata. Clone, Combine, subquery and CTE
creation/import preserve these IDs unchanged and union their parameter schemas.
Repeated occurrences of one ID bind one value. Two different IDs with the same
name in a composed shape reject atomically, so independently built queries cannot
silently alias their first parameters. QueryParameter is this immutable source/ID/
codec descriptor, distinct from an arena-owned SqlExpression token; it remains
usable after its original builder closes when a cloned/imported plan retains that
ID. ParameterValue only accepts an ID already declared/imported in that query;
QueryParameters.Set may prepare values freely, but execution rejects wrong-source,
missing, extra, duplicate or codec-mismatched IDs against the final sealed schema.
No implicit parameter remapping or accidental ID1 collision occurs across imports.
Raw command parameter IDs below are command-local because raw command plans cannot
be imported into Fluent builders; they never enter that source-generation ID domain.

Named parameter IDs are assigned 1..N in SqlParameters.Add order. Names are
case-sensitive ASCII `[A-Za-z_][A-Za-z0-9_]*`, at most128 bytes, without an `@` prefix;
missing/duplicate/unused names reject. The kind21 definitions transmit that exact
name-to-ID/codec/nullability map, and the native placeholder scanner binds `@name`
to the matching db-wire descriptor. Repeated holes reuse one ID/value. Interpolated
arguments use their zero-based argument index plus one as IDs and names `p0`, `p1`,
etc. For template-kind1, the template view is a binary u32 segment count followed
by `{kind:u32,length:u32,data[length]}` records: kind0 is strict UTF8 literal bytes;
kind1 has length4 and a little-endian parameter ID. Empty literal segments are
allowed; unknown kinds, adjacent unused arguments, formats/alignment and malformed
lengths reject. This is the parsed composite-format stream, never a managed SQL AST;
the Rust scanner verifies each hole is in a parameter position outside a quoted
string/comment/identifier before choosing provider placeholders. The named-template
path carries raw strict UTF8 bytes. Both paths are bounded by MaxParameterBytes and
MaxParameters and use the same static codec registry.

The initial scalar registry IDs are now fixed for B01/B07: 1 Int16, 2 Int32,
3 Int64, 4 Boolean, 5 UTF8 string, 6 bytes, 7 Guid RFC4122, 8 date, 9 time,
10 UTC instant, 11 double, 12 single, 13 decimal numeric, 14 decimal text,
15 fixed-scale money, 16 JSON UTF8, 17 enum Int32. Nullable is the existing wire
NULL capability/descriptor flag, not an invented per-entity codec. `ValueCodec<T>.Id` returns this logical ID. Decimal/fixed-money configurations are
canonical JSON objects in each column/result `codec_config` field: numeric uses
`{"precision":18,"scale":2}`, fixed money `{"scale":2}`, all other codecs null.
`codec_register` validates logical ID/configuration and returns a source-bound
codec_id (1..17 for unconfigured builtins; configured IDs start at 1024, IDs18..1023
reserved). The managed adapter caches that binding by logical ID/configuration
hash/source generation, before any value submission. The db-wire logical_tag is
1..17 above; codec_id is the bound source codec ID. Thus different decimal scales
cannot alias merely because their logical type is Decimal. Arbitrary native codec
implementations cannot be registered through this API; new logical types require
an engine upgrade. Parameter schema metadata includes the same configuration and
hash, even when a command has no entity descriptor. Registration rejects missing
or irrelevant configuration and hash/type disagreement. Builtin IDs above are
NativeWeave wire IDs, not SQLx/SeaQuery enum values.

### 9.1.2 Exact db-wire scalar and identity encoding

D14's96-byte header,16-byte descriptors and24-byte cells remain the container.
This refinement fixes its previously candidate scalar fields so independent managed
and Rust encoders produce identical bytes. Header flags are0. Descriptor flags
bit0 permits SQL NULL; cell flags bit0 means this value is SQL NULL. All other bits
are reserved0. A NULL cell retains its declared logical_tag/codec_id, requires a
nullable descriptor and has offset=length=0. Empty non-null string/bytes have
length0 and offset=payload_offset; they are not NULL. Tags/codecs match the
descriptor exactly even for NULL; readers reject disagreement before conversion.

| Logical ID | Non-null payload bytes and exact validation |
| --- | --- |
| 1 / 2 / 3 | Signed two's-complement Int16/Int32/Int64 in2/4/8 little-endian bytes. |
| 4 | One byte0 or1 only. |
| 5 | Raw strict UTF8 without BOM, terminator or normalization; unpaired CLR surrogates reject before encoding. |
| 6 | Raw bytes; no embedded length beyond the cell length. |
| 7 | Exactly16 RFC4122/network-order UUID bytes; no Guid mixed-endian memory reinterpretation. |
| 8 | Signed Int32 little-endian days since1970-01-01, range -719162..2932896 (DateOnly domain). |
| 9 | UInt64 little-endian microseconds since midnight,0..86399999999. CLR ticks must be divisible by10. |
| 10 | Signed Int64 little-endian microseconds since1970-01-01T00:00:00Z, range -62135596800000000..253402300799999999. Normalize DateTimeOffset to UTC; DateTime requires Kind=Utc; submicrosecond ticks reject. |
| 11 / 12 | IEEE754 binary64/binary32 bit patterns in8/4 little-endian bytes, finite only. Signed zero is preserved by the wire; provider round-trip semantics remain separately tested. |
| 13 / 14 | Exactly16 bytes: unsigned96-bit coefficient in12 little-endian bytes, scale:u8 in0..28, negative:u8 in0..1, reserved:u16=0. Canonicalize by removing coefficient trailing decimal zeroes while scale>0, and use scale=0/negative=0 for zero. Numeric codec13 additionally requires exact fit in its configured precision/scale without rounding. Codec14 writes canonical fixed-point decimal SQL text (optional minus, digits, optional decimal point; no exponent/grouping/positive sign); this is a provider encoding, not a different wire value. |
| 15 | Signed Int64 little-endian coefficient in8 bytes, numeric value=coefficient/10^configured_scale. CLR conversion must be exact and checked. |
| 16 | Strict UTF8 RFC8259 JSON text, no BOM; JSON null is non-null bytes `null`, distinct from a SQL NULL cell. Native syntax/size validation precedes provider admission. |
| 17 | Signed Int32 little-endian enum numeric value; undefined values are preserved, with no CLR enum layout on the wire. |

The semantic_profile_id is1 for the ordinary SQLite profile and2 for ordinary
PostgreSQL; it is not the public DatabaseProvider enum ordinal. Other profiles
require a versioned allocation before use. payload_kind1=execution parameters,
2=result row batch,3=homogeneous expression-value sequence,4=entity mutation
values/key/checks. Unknown kinds/profiles reject. Kind1 has one record and its
ordered IDs match kind21 (or the sealed prepared-parameter schema); kind2 has
zero or more rows with exact projection-ordinal descriptors; kind3 has one
descriptor with ID1 and zero or more records (exactly one for Expression.Value);
kind4 has one or more records and ordered table-column IDs. A zero-record result
batch is EOS, not an extra owned business row. Every consumer states its allowed
kind/count before decoding; collections cannot substitute an arbitrary row batch.

metadata_hash is the SHA-256 of canonical logical projection bytes for kind2 and
canonical model bytes for kind4. Kind1 hashes canonical UTF8
`{"version":1,"parameters":[{"id":1,"name":"p0","codec":3,"codec_config":null,"nullable":false}]}`
using kind21 order and the same key/string/number rules; prepared names follow the
same schema. Kind3 uses32 zero bytes because its one codec descriptor and admitted
query owner define its type. Native validates those hashes against the admitted
plan/model/schema rather than trusting the sender. entity_id is the declared table
ID for kind4 and0 otherwise; query_id is reserved0 in all v1 value payloads (query
identity stays in the opaque owner/token); projection_id is the source-bound
registration ID for registered result shapes,1 for a plan-local inline projection,
and0 for non-result kinds. The expected value is retained in the admitted native
plan and returned to its managed adapter at shape binding. A projection ID alone
never authorizes a pointer access or substitutes for the complete shape hash.

### 9.2 Operation tables: no inferred binding

| Managed adapter / ABI opcode | Exact operands and native entry | Output / failure |
| --- | --- | --- |
| `Source.Create` / source_create | config record -> SQLx PgPoolOptions/SqlitePoolOptions plus engine-local runtime | source owner; no connection yet |
| `Session.Open` / session_open_create | source -> bounded native admission then Pool::acquire | session handle; canceled admission no lease |
| `Codec.Register` | logical ID/config -> source-bound validated native codec | codec ID; no new native code accepted |
| `Metadata.Register` | canonical model -> runtime metadata registry and native codec profile | immutable model owner; all-or-nothing |
| `Projection.Register` | kind13 with kind22 fields -> source-bound exact logical shape/codec binding | positive projection ID; atomic bounded interning, no CLR delegate crosses ABI |
| `Expression.Column/Value/Parameter` | typed metadata ID or one db-wire cell; parameter ID/name/bound-codec/nullability | arena expr token -> SeaQuery Expr/Value; named prepared-parameter schema is retained natively; no CLR object pointer |
| `Expression.Binary` codes 1..6 | Equal,NotEqual,Greater,GreaterOrEqual,Less,LessOrEqual(left,right) | SeaQuery ExprTrait comparison methods |
| binary codes 7..14 | Add,Subtract,Multiply,Divide,And,Or,NullSafeEqual,Coalesce | ExprTrait arithmetic/Condition/native null operator; codec/backend gate |
| unary codes 1..3 | IsNull,IsNotNull,Not(input) | native unary condition |
| list codes 1..3 | In,NotIn,Between(input,cells); Between exactly 2 cells | SeaQuery is_in/is_not_in/between; empty membership explicit constants |
| clause 1/2 | WHERE/HAVING: field1 token:u64 | SelectStatement::and_where / having |
| clause 3 | ORDER: field1 token, field2 direction:u32(0 asc/1 desc), field3 null_order:u32(0 first/1 last), field4 replace:u32 | order_by_expr_with_nulls; no silent null order |
| clause 4 | GROUP: field1 token | add_group_by/expr group |
| clause 5 | LIMIT/OFFSET: field1 take:u64 or absent, field2 skip:u64 or absent | limit/offset; checked bounds |
| clause 6 | SELECT: field1 expr tokens:u64vector, field2 ordered projection descriptor:record | columns/expr_as and shape validation |
| clause 7 | JOIN COMMIT: field1 provisional alias token:u64, field2 ON expression token:u64 | atomically join_as/JoinType + Condition using clause18's reserved table/alias; promote the same alias token from provisional to committed |
| clause 8 | DISTINCT: no fields | SelectStatement::distinct |
| clause 9 | SET: field1 imported plan token:u64, field2 operation:u32(0 union,1 unionall,2 intersect,3 except) | union/intersect/except; native clone, exact shape |
| clause 10 | CTE ATTACH: field1 imported CTE token:u64 | CommonTableExpression/WithClause from the already validated, owned CTE snapshot; duplicate names reject |
| clause 11 | WINDOW: field1 action:u32(0 create,1 append partition,2 append order,3 set rows frame); field2 window token for actions1..3; field3 expression token for1/2; field4 direction:u32 and5 null_order:u32 for2; field6 start:u32 and7 end:u32 for3 | Native WindowStatement; action0 returns a new query-owned window token, other actions mutate it atomically and return zero; frame codes0 preceding,1 current,2 following |
| clause 12 | LOCK: field1 mode:u32(0 update,1 share,2 nokey,3 keyshare), field2 wait:u32(0 wait,1 nowait,2 skiplocked) | lock_with_behavior; PostgreSQL capability only |
| clause 13 | AGGREGATE: field1 function:u32(0 countrows,1 count,2 sum,3 avg,4 min,5 max,6 rownumber,7 rank), field2 input token optional, field3 distinct:u32, field4 window token optional, field5 result codec:u32 | SeaQuery Func/Expr; output native expression token |
| clause 14 | SUBQUERY: field1 imported plan token:u64, field2 op:u32(0 exists,1 in), field3 lhs token for IN | native Expr::exists / in_subquery; clone and shape checks |
| clause 15 | CASE: field1 condition, field2 true token, field3 false token | Expr::case; compatible codec |
| clause 16 | TEXT: field1 op:u32(0 contains,1 starts,2 ends,3 like,4 collate), field2 input token, field3 argument cell/UTF8, field4 escape Unicode scalar:u32 | literal helpers escape before native LIKE; collate requires allowlist |
| clause 17 | UPDATE SET: field1 root column_id:u32, field2 value/expression token:u64 | Builds native update assignment; key/generated columns and duplicate setter assignment reject. Changes.Set values become typed Expression.Value tokens, never a managed SQL fragment. |
| clause 18 | JOIN RESERVE: field1 imported model token:u64, field2 table_id:u32, field3 alias:UTF8, field4 kind:u32(0 inner/1 left) | Reserve a provisional native alias token before invoking the managed ON builder; expression_column can resolve its right columns, but no join is yet published |
| clause 19 | JOIN ABORT: field1 provisional alias token:u64 | Roll back an uncommitted join reservation and invalidate all expression tokens depending on that alias; no query clause was published |
| clause 20 | JOIN MATCH: field1 committed left-join alias token:u64 | Native boolean expression over a private non-null marker of the joined source; not a nullable user column test |
| clause 21 | OVER: field1 aggregate/window-capable expression token:u64, field2 window token:u64 | Clone the current WindowStatement into a new native expression; existing expression and window remain independent, return expression token |
| clause 22 | TIMEOUT: field1 finite timeout_ns | Set query's finite timeout override; source CommandTimeout was the initial value; snapshot at seal, convert once at execution admission |
| `Query.Seal` terminal 0..8 | 0 list,1 stream,2 first,3 single,4 count,5 exists,6 update,7 delete,8 immutable shape | freeze/validate native statement/values; plan owner; state Sealed; terminal8 supplies public Prepare and internal import snapshots without executing SQL |
| `Execute.Create` | sealed plan + execution values -> native renderer, fallible SQLx Arguments::add, query/query_as::fetch/execute | cursor or Int64 affected/count or scalar; no .unwrap parameter conversion |
| `Sql.Create` | named/segment template + kind1 values + kind20 options -> native placeholder binding and exact static result plan | plan retaining timeout, registered projection and kind21 parameter schema; no execution before Execute.Create |
| `CommonTable.Create` / cte_create | declared model/table ID + selected body-query owner + recursive0/1 -> native validated clone | independently owned immutable CTE; declaration/body source/profile/arity/codecs must match; input query remains unchanged |
| `Cursor.Fetch` | max rows/bytes -> SQLx stream.next into bounded db-wire batch | owned batch / EOS; one active fetch, early failure retires cursor |
| `Tx.Begin` | options -> SQLx begin_with/tracked transaction; provider isolation | tx owner only after begin confirmed |
| `Tx.Finish` action 0/1 | commit/rollback -> guarded SQLx Transaction operations | snapshot; possible send+no confirmation -> Unknown commit |
| `Savepoint.Action` 0/1 | rollback-to/release of top generation -> tracked native savepoint | snapshot; outer transaction never committed |
| mutation 0..6 | insert,insert-returning,update,update-checked,delete,delete-checked,upsert; record fields validated | native SeaQuery Insert/Update/Delete/OnConflict + SQLx; counts/row |
| admin 0..3 | migrate,status,validate,tables | SQLx Migrator or bounded native catalog query; owned static snapshot |
| `Relation.Load` | metadata relation expands native FK predicate and child projection, then ordinary Query.Seal/Execute | no separate C# relation algorithm or copied SeaORM state manager |
| `Entity.Find` | Query.Create; Expression.Column/Value and Binary.Equal for every ordered key component; WHERE; SELECT root projection; Seal terminal1(cursor); Execute/Fetch with max_rows2 | adapter returns null only for zero rows and fails on a second key-shaped row, then always retires cursor; no nonexistent Mutation.KeyQuery operation |
| `Bulk.Insert` | native bounded batch of mutation0 records; transaction ownership explicit | same execute/tx lifecycle; no extra universal batch ABI |

Result-bearing clauses 7/11(action0)/13/14/15/16/18/20/21 publish an arena token through
`out_token`; non-result clauses publish zero. Expr token zero is invalid; the
column function alone accepts alias zero to mean the root table. Join/window/
expression tokens carry arena identity and kind and cannot be interchanged.
`query_import` kinds 1=model, 2=sealed plan, 3=CTE take an admitted engine-private
opaque owner pointer directly, verify the same source/profile, and retain an
immutable native dependency or clone its state into the destination query arena.
Clause records then contain only query-local tokens, never encoded raw pointers
or a process-wide owner table. Import retains dependencies until destination query
retirement; closing the source wrapper cannot invalidate already imported state.

`Combine`, `Exists` and `In(QuerySelection<T>)` receive a selected mutable query,
not an already sealed plan. Their adapter sequence is explicit: validate source
and result shape, acquire source read admission, `query_clone(source)` into a
temporary owner, then end that read admission. Seal only the temporary clone with
terminal8, import its plan into the destination with `query_import(kind2)`, and
apply clause9 for Combine or clause14 for EXISTS/IN. The source query remains
mutable and its selection remains usable; changes after the clone do not alter
the imported snapshot. Clone preserves the selected shape, owned values and
source-bound parameter IDs. EXISTS ignores the result values but still validates
the selected native query; IN requires exactly one compatible result codec.

Public Prepare requires `db.prepared-shape.v1`; the internal nonexecuting snapshot
uses the same native shape representation under `db.query.v1` and does not create
a public prepared object or prepare a statement on a physical connection. Every
temporary plan/query owner is released in reverse order in a finally path after
the import has retained its dependency, or immediately on failure. If clause
application fails after import, its unused arena dependency remains bounded and
charged until destination-query disposal; no partial clause is published.
Source read admission is not held while acquiring destination mutation admission,
including self-composition, so the sequence cannot recursively acquire the same
query gate. Destination closure after cloning rejects admission and retires all
temporary owners. This uses existing clone/seal/import/release operations, not a
new managed query representation.

JOIN performs reserve18 -> synchronous ON expression construction -> commit7.
`JoinPredicate.Right` resolves columns against that provisional alias; Left uses
root alias0 and captured committed aliases remain legal. During the ON delegate,
only expression creation/read is allowed; reentrant query mutation/terminal work
rejects. A thrown delegate or failed commit invokes abort19 in a finally path;
the public alias is returned only after commit. Commit clones the validated ON
expression into private native JOIN state, then invalidates every public expression
token that depends on the provisional alias, just as abort does. A delegate that
captures `on.Right(nonnullableColumn)` therefore cannot use it for a later SELECT/
WHERE and bypass left-join nullable lifting. Fresh expressions from the committed
LeftJoinedTable alias carry native nullable result metadata. Provisional aliases cannot escape
as public joined-table values or enter another clause. Invalidated dependent tokens
fail before native extraction and can never become valid through ID reuse. Native
reservation/rollback is quota-bounded and cannot leave a half-published JOIN.
For left joins, the adapter creates a native derived source with a private
collision-free constant1 marker, then JOIN MATCH emits marker IS NOT NULL. This
works when all user columns are nullable and no declared key is available; the
marker is excluded from the user projection and consumes native query-node budget.

Window() is clause11/action0. PartitionBy and OrderBy issue actions1/2 immediately;
RowsBetween issues action3, with UnboundedPreceding0/CurrentRow1/UnboundedFollowing2.
Start cannot be Following, end cannot be Preceding, and start must not exceed end.
`Over` is clause21, not an unbound managed helper; it snapshots the window so later
window changes do not mutate previously built expressions. Rank/RowNumber use
clause13 then clause21. Every mutation uses the same single-writer admission gate.
WithTimeout is clause22; prepared/raw/query execution uses that retained deadline.

CommonTable.Create calls cte_create while holding read admission on its selected
body query and declared model. Native clones and validates the body including
projection without consuming/sealing the public source query. CTE owner release
uses owner_release; destination With first imports it using query_import kind3,
then clause10 attaches that immutable native dependency. The recursive flag and
declared self-reference belong to this CTE snapshot, not a later mutable C# object.

Buffer outputs are engine-private opaque owners, not an invented shared owned-byte
layout. `buffer_view` is called only while a managed logical read admission and
native owner lease span the whole synchronous copy; the returned view may not
survive that lease. `buffer_release` is creating-module-only. Buffer and operation
owner handles are distinct native kinds. Each released pointer is used at most
once by the generated owner wrapper; arbitrary stale pointer probing is outside
the ABI preconditions. Default or mismatched public expression tokens are rejected
safely before any native owner extraction.

This table is a finite method-binding transport. C# sends each operation directly;
it does not accumulate a new SQL AST or generic Core query IR. A future batched
transport is a separately measured optional optimization. Native mutation builds
candidate state and publishes on success; if unwinding/partial state cannot be
proved valid, poison the query and reject subsequent operations except cleanup.

Set-based update emits one clause17 per assignment, then Query.Seal terminal6.
The Rust adapter transforms the validated root-only query filter into a SeaQuery
UpdateStatement; it never drops join/group/paging clauses to make an unsupported
mutation appear valid. Delete uses terminal7 with the same shape validation.

`WhereIf` chooses whether to issue the same Expression/WHERE operations; it adds
no ABI opcode. Expression comparisons and numeric nullable overloads reuse the
binary opcode table with the existing descriptor NULL flag. Aggregate overloads
reuse clause13 and carry the declared result codec/configuration; no CLR numeric
operator is sent to Rust. ThenBy(expression) uses clause3 with replace=0. Bulk
failure progress reuses take_error's owned payload plus the exact kind15 record.
`SqlExpression.Over` accepts only native aggregate/window-capable expression kinds;
ordinary scalar expressions reject before render. This is a semantic check beyond
what its generic type can prove.

### 9.3 Capability allocation and error mapping

The database module's 64-bit capability mask is engine-local. Public
DatabaseCapabilities.Supports accepts the stable names below. The package mask is
intersected with provider/version/profile checks. Unknown names return false;
requesting an absent capability throws before dispatch. Merely seeing an upstream
method never sets a bit.

| Bit | Stable name | Provider condition |
| --- | --- | --- |
| 0 | db.metadata.v1 | both |
| 1 | db.query.v1 | both |
| 2 | db.transactions.v1 | both |
| 3 | db.savepoints.v1 | both |
| 4 | db.streaming.v1 | bounded row streaming, both |
| 5 | db.migrations.v1 | explicit administration, both |
| 6 | db.schema.read.v1 | bounded tables/columns, both |
| 7 | db.returning.v1 | native provider RETURNING supported |
| 8 | db.upsert.v1 | native conflict profile supported |
| 9 | db.cte.v1 | finite validated CTE shape |
| 10 | db.window.v1 | inline window subset |
| 11 | db.row-lock.v1 | PostgreSQL only |
| 12 | db.null-safe-equality.v1 | codec/collation profile tested |
| 13 | db.json.v1 | enabled provider JSON profile |
| 14 | db.decimal.numeric.v1 | PostgreSQL exact declared range |
| 15 | db.decimal.text.v1 | SQLite round-trip only |
| 16 | db.fixed-money.v1 | checked fixed scale |
| 17 | db.relationships.explicit.v1 | native explicit joins/FK loads |
| 18 | db.prepared-shape.v1 | bounded immutable native shapes |
| 19 | db.bulk-batches.v1 | bounded insert batches |
| 20 | db.dynamic-fields.v1 | registered metadata allowlist |
| 21 | db.recursive-cte.v1 | validated recursive subset |
| 22 | db.set-operations.v1 | exact compatible projections |
| 23 | db.scalar-codecs.v1 | ordinary scalar table above |
| 24 | db.sql.expert.v1 | trusted parameterized SQL boundary |

Bits 25..63 remain reserved/zero. These are required implementation capability
identities, not a claim that unimplemented packages currently advertise them.

Domain errors use the existing Core status and structured error domain; no second
Core `nw_status` enum is introduced. Required domain reason codes are fixed:
1 provider, 2 constraint, 3 conversion, 4 shape, 5 unsupported capability,
6 resource limit, 7 concurrent use, 8 invalid state, 9 commit outcome unknown,
10 rollback unconfirmed, 11 metadata mismatch, 12 missing parameter,
13 stale/mixed owner, 14 large value requires streaming, 15 migration checksum,
16 concurrency conflict. Native provider codes (PG SQLSTATE/SQLite extended code)
are preserved separately from reason/status. No credentials, parameter values,
arbitrary SQL, or native address is included by default. Mapping and retirement
run before completing the managed Task; errors cannot leave an unowned cursor or
mask Unknown through cleanup.

## 10. Required verification and documentation obligations

The declaration fixture and consumer scenarios validate C# rules only. The product
must implement and independently verify all matrix rows classified full/equivalent/
limited within their explicit limits. Rows planned/unsupported have no released API
claim. Static source read, prototype execution, signature compilation, Native AOT
publish, executing an AOT stub consumer, and executing a real database workload are
separate evidence levels.

| Owners | Required concrete cases |
| --- | --- |
| B01/B07 | Metadata/value/row golden bytes; malformed lengths/overlap; strict UTF-8; integer/date/decimal/NULL limits; missing nullable column vs actual NULL; no reflection fallback |
| B02/B03/B04 | PG TLS VerifyFull and bad-host/cert negatives; SQLite journal/busy/worker settings; bounded pool/waiters; source close while session opening; no cross-source handle use |
| B05 | Commit admission race, lost ack Unknown, failed-tx commit rejection, rollback unconfirmed, savepoint ordering, finite close retaining roots, no connection reentry before proven cleanup |
| B06/B12 | Actual async enumeration, early break, second enumeration, concurrent MoveNext rejection, constructor exception, first/single extra-row cleanup, memory limits across SQLx/wire/DTO layers |
| B08 | PG advisory-lock failure/close; SQLite tracked IMMEDIATE outer transaction; checksum and crash/restart; explicit nontransactional boundaries; no startup migration |
| B09/B11/B13 | Every operation table row paired with direct Rust SQL+ordered-parameter oracle and real PG/SQLite result/error oracle; cross-query alias/default-token/LEFT JOIN nullability; advanced clause rejection before panic/ignored SQL |
| B10 | Incremental stable output, unsupported codec/constructor diagnostics with spans, new entity no Cargo/no asset hash change, actual generated and handwritten parity |
| B14 | Key/tenant predicates, explicit null vs unset, CAS 0/1 row behavior, native conflict target, relationship key order, partial bulk outcome and caller-owned transaction |
| A13/A16/B21–B24 | Separate packages without cycles/unrelated engines, RID-free build/run and explicit RID AOT, clean no-Rust consumer, real application operations, allocation/copy/FFI measurements versus same Rust stack, source/API/XML-doc/example consistency |

Compile-negative consumers cover wrong entity/value, struct entity constraints,
raw handle access, unrelated alias generic types, nullable mapping, invalid numeric
operator types and missing generic constraints. Runtime negatives cover failures
that typing cannot prove (same TEntity but different tables/query owners, unknown
capabilities, changed schemas, default value structs). Signature-level checks must
not be substituted for these native tests.

Future XML reference entries link each member group above and provide its exact
parameter/return/error/lifetime/thread-safety/platform/cost facts. Examples link to
real compiling consumer files and carry evidence badges. B01 owns shared Data
reference, B02/B03 provider setup, B04 source/session lifetimes, B05 transactions,
B06 streaming, B07 codecs, B08 administration, B09 native seam, B10 generation,
B11 query semantics, B12 projections, B13 Fluent reference, B14 explicit ORM.
A16/B24 own end-to-end installation/build/publish examples. New operators require
matrix row + ABI mapping + native parity test + XML reference + compatibility
review in the same PR. A surface-wide API change cannot be accepted by changing
only a documentation example or old acceptance hash.
