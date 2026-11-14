# NativeWeave API composition guides

Version: 0.4.0. These guides explain the designed API. Exact signatures are in
[reference.md](reference.md); the domain specifications are normative for defaults,
errors, operation layouts and state transitions. All product implementation claims
remain false until the relevant Delivery evidence exists.

## 1. Database ownership, transactions and schema

A data source is the long-lived pool/configuration owner; a session owns one
admitted connection use. Open sessions for the operation that needs them and close
them with `await using`. A session is not a concurrently mutable request-global
object. Multiple independent sessions use the native pool's configured capacity.
Source construction does not silently create schema or execute migrations.

SQL commands have explicit operation kind, typed parameters and conversion policy.
Values are parameterized; identifiers come from validated metadata. User-provided
SQL is an explicit escape hatch whose shape and effects remain the caller's
responsibility. Large BLOB/CLOB content is not advertised as a general streaming
provider API merely because row streaming exists. PostgreSQL and SQLite codec,
NULL, precision, timezone and capability differences are listed in
[database.md](database.md#4-metadata-codecs-entities-and-projections-b01b07b10b12).

Transactions distinguish database outcome from cleanup. A known committed result,
a known rollback and an unknown remote outcome require different recovery actions.
Savepoints belong to their transaction; disposing a child does not manufacture
confirmation of a remote effect. Bounded close reports incomplete cleanup while
retaining reachable resources. It never frees callback context or a still-active
connection to satisfy a timeout. See the exact
[transaction rules](database.md#6-transactions-savepoints-and-cleanup-b05).

Migrations use ordered immutable SQL bundles and recorded checksums. An explicit
migration runner owns locking, ledger and provider transaction restrictions. No
automatic object-model diff engine or implicit destructive startup migration is
introduced. B08 implements this path; B21 exercises it in a real reference app.

## 2. ORM and Fluent composition

Static descriptors provide typed entity columns, keys, relationships and codecs.
The default generator emits them; advanced users can supply equivalent static
descriptors through the same API. A query owns native SeaQuery state. C# delegates
append native operations immediately; they are not captured expression trees.
Use ordinary `if` or `WhereIf` for optional conditions and typed predicate
composition for nested conditions. There is no hidden client-side SQL evaluation.

Joins explicitly distinguish required and nullable joined values. A left join does
not promise a non-null joined entity simply because the source column was non-null.
Projections materialize owned DTOs from bounded borrowed row batches. Mapping
failures retire the batch and cursor correctly. Aggregate NULL/empty-set behavior,
group rules, ordering, seek/page boundaries, set operations, windows and CTE scope
are specified in the native operation tables; a typed fluent spelling does not
erase database semantics.

Reusable prepared shapes retain native query state and bind typed parameters per
execution. They do not capture a session that has already closed. Query builders
are mutable and single-owner; prepared snapshots have their separately specified
sharing policy. Explicit relationship loads avoid hidden N+1 queries and lazy
proxies. Changesets distinguish unchanged fields from setting SQL NULL. Optimistic
updates carry expected concurrency tokens and inspect affected rows.

See [DatabaseExamples.cs](../../experiments/public-api/NativeWeave.Api.Consumers/DatabaseExamples.cs)
and [DatabaseAdvancedExamples.cs](../../experiments/public-api/NativeWeave.Api.Consumers/DatabaseAdvancedExamples.cs)
for compiler-checked dynamic conditions, joins/projections, nullable arithmetic,
prepared parameters, batching and concurrency shapes. Their database-facing bodies
are not executed against the throwing declaration assembly.

## 3. Server routing and business handlers

Configure listeners, limits, JSON metadata, services and diagnostics on the builder.
Build snapshots those host settings. Register routes, middleware and filters on the
application before Start/Run freezes route admission. Changing a live router is a
separate unsupported operation, not an accidental mutation of a captured list.
Request dispatch, HTTP flow control and TLS remain in the Rust host.

Typed routes use static handler/serializer binding. Raw routes expose explicit
request/response ownership for streaming and protocol work. Middleware and filters
execute in the documented order and at most once; calling the continuation twice
or mutating a committed response is an error. Authentication and authorization are
explicit application seams. They do not imply a built-in identity database, OAuth
provider, complete ASP.NET middleware compatibility or automatic security policy.

Routing precedence, query/path/header decoding, endpoint limits, binding failures,
status/trailers and error responses are defined in [server.md](server.md). Optional
gRPC exposes four cardinalities through Tonic on the same native host; optional MCP
has the finite modern stateless profile described there. Adding a protocol package
must not start another hidden listener/runtime.

## 4. Async and streaming

Ordinary asynchronous operations return Task. ValueTask is reserved for a defined
fast path or inherited BCL contract. Await a ValueTask once. An async enumerator
admits work at its documented first step, holds the required native lease and
accepts enumeration cancellation. Do not issue concurrent MoveNextAsync calls.
Early `break`, exceptions and mapper failures must join the cursor's retirement.

Owned rows/DTOs may escape enumeration. Borrowed row views, spans and request
contexts may not escape their stated scope. HTTP request and response streams obey
backpressure; body reads/writes account for managed and native retained bytes.
Write admission reserves capacity before accepting a copy or retained owner.
Cancelling a wait does not release data still reachable by native code.

A timeout uses a monotonic remaining budget. Caller cancellation, an expired
operation deadline and incomplete resource cleanup are distinct outcomes. See
the domain tables and C-ASYNC-001; no wrapper may infer quiescence from a completed
managed Task alone.

## 5. Engine extensions

Applications consume an engine's natural facade factory. Explicit engine catalogs,
descriptors and maintainer SPI are for diagnostics/integration, not mandatory
application initialization. Descriptor metadata identifies ABI, capabilities,
threading and supported asset identities. Preflight is not domain startup.

An extension composes with the small Core ownership/error/buffer/async contracts.
It owns its executor and domain algorithms. It must not introduce a default global
Tokio runtime, share unrelated engine state or require every engine to reference
Database/Server. Static managed references and descriptors are required for AOT;
arbitrary new managed plugin assemblies cannot be discovered after publication.
Native runtime loading, logical instance disposal, physical module unload and hot
replacement are distinct. The accepted design keeps validated native code resident
as needed; it does not promise hot unload/replacement of active callbacks.

New repositories explicitly adopt the
[standard and templates](../standards/csharp-public-api-and-documentation.md).
AGENTS.md in this repository does not automatically govern an independent project.

## 6. Native AOT and source generation

Entity metadata, DTO materializers, JSON contexts, typed handlers and closed generic
uses are compile-time inputs. Diagnostics identify unsupported model shapes at
source. The normal path uses no unbounded reflection binder, runtime expression
compiler, dynamic assembly, manual preservation list or per-entity Rust build.

The generator is delivered through verified NuGet build assets, including the
transitive path from a provider package. Duplicate references must not load two
copies of the analyzer. Generated identifiers, accessibility and nullable types
are part of the consumer contract. Advanced handwritten descriptors use the same
runtime surface and receive equivalent semantic/AOT tests.

Compilation, trimming analysis, Native AOT publication and execution are separate
evidence states. The current packaging probe executes a finite real generator and
precompiled native codec; the declaration probe roots and compiles the complete
surface and consumers. Neither proves an unimplemented ORM query or HTTP server
works. Existing Windows/Linux product obligations stay in A14/A15/A16/B21/B24.

## 7. Errors and recovery

Argument, cancellation and disposal errors follow familiar .NET conventions.
Domain exceptions preserve stable categories/provider codes and bounded diagnostic
context. Expected absence uses a Try/result shape where designed; SQL NULL is not
an exception. Invalid capability selection is detected before side effects when
the operation can be validated in advance.

Unknown transaction outcomes require application reconciliation with a stable
recovery identity. Bulk operations report actual completed progress according to
their atomicity mode; cancellation does not imply all earlier batches rolled back.
Panic containment maps unwind-capable failures and poison state; process abort,
native memory corruption and OOM abort are not recoverable facade exceptions.

Diagnostics redact secrets by default. Do not log connection strings, SQL parameter
values, authorization headers or request bodies just to make an error actionable.
Logs, ActivitySource and Meter identifiers are stable API surfaces with disabled
cost included in review.

## 8. Memory and resource management

Resource owners are reference types with explicit disposal. Small immutable value
types never copy ownership of an allocation. Sync borrowing ends before return;
async retention requires a copy, pin or explicit lease with a documented release
condition. A Span cannot cross an await or escape through a captured callback.

NativeBuffer scoped readers are the narrow synchronous borrow seam. Copy APIs
state their byte counts. Async copies use bounded staging and keep required leases
until the underlying work retires. Logical close prevents new admission; physical
release waits for all native dependencies. Repeated disposal follows the defined
idempotence rules, and use after logical close fails deterministically.

One pool, runtime, request scope or buffer is not automatically cheaper than a
small allocation; compare complete workload costs. Tables in the specifications
record known allocations/copies/FFI crossings and retained capacities as design
estimates. Measured claims require A21/B23 evidence.

## 9. Performance and diagnostics

Tune bounded pool capacity, query batching, retained-byte credits and endpoint
limits according to measured work. Avoid treating unlimited concurrency as a
performance feature. Keep disabled logging cheap, materialize only requested DTO
fields and use streaming when it actually limits memory for the workload.

Compare equivalent native and managed workloads with the same database, TLS,
payloads, data semantics and success/failure behavior. Record wall time, throughput,
tail latency, allocations, peak/retained memory, copy volume, FFI calls and startup
cost. A design declaration AOT executable is unsuitable as an ORM/server benchmark.
No near-Rust performance claim is accepted from API shape alone.

## 10. Compatibility and upgrades

Managed package/API, native ABI, source crates and domain semantics have separate
versions. Use one tested package closure and immutable assets. A changed default,
nullable contract, overload, disposal behavior or exception can break consumers
without removing a method. A22 defines the checks; each module runs them and owns
its XML/reference/example changes in the same implementation change.

Adding an ordinary model is an application rebuild. Adding a new engine capability
is a package/native adapter update. Rolling out a new native identity uses a new
process/deployment when the existing process has resident users of the old one.
Rollback selects a previously verified complete closure. No active-module hot
swap is implied by NativeLibrary loading support.

The implementation must generate reference documentation from actual product
assemblies plus XML, compile published samples, perform compatibility comparisons
and record actual target runs. The design reference and this guide remain clearly
labelled until those product gates pass.
