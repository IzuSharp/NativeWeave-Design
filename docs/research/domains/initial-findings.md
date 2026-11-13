> Historical checkpoint. Current product constraints and acceptance boundaries are in [ADR-0003](../../decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md). Any optional Rust Server/Kestrel product-host wording below describes the prior snapshot, not current authorization. Original evidence retains its recorded scope.

# Database, AOT ORM and Server: initial source investigation and research boundaries

- Record date: 2026-11-12 (user conversation date).
- Supplemental latest-version check: pinned EF Core / Kestrel v11 source has also been read; see [v11 supplemental source verification](v11-recheck.md). This report's v10 observations retain their status as historical evidence.
- Status: **preliminary research evidence; no accepted architectural decision has been established**.
- Executor: independent phase B research subagent.
- Inspection scope: 7 external projects and 20 scoped source files or excerpts, plus official documentation and candidate-directory inspection.
- Execution status: this topic did not compile, execute tests, publish Native AOT or perform performance tests. Upstream test definitions and CI files establish only that the corresponding validation procedures exist; they are not passing records from this conversation.
- Version note: the pinned versions below support reproducible source reading; they are not claimed to be the latest versions or selected NativeWeave dependencies. Production versions must be reverified with the toolchain and supply-chain topics.
- Basis: the user's NativeWeave task requirements and public primary sources. ArcForges design content, processes and acceptance criteria were not used as the basis for this project.

## 1. Current assessment and decision boundaries

Phase B should immediately begin three comparative experimental branches:

1. Pure C# Native AOT: database drivers, static mappings, server and business code all in C#, as an indispensable comparator.
2. C# Native AOT + independent Rust domain Engines: adopt only when complete workloads demonstrate benefits or the Rust ecosystem supplies a required capability.
3. Equivalent pure Rust workloads: separate the native engine's own costs from cross-language adaptation costs.

Existing evidence supports prioritizing Npgsql + generated mappings and Kestrel AOT capabilities as research baselines; it is insufficient to accept final technology selections. SQLx, SeaQuery, SeaORM and hyper/Tokio should undergo equally rigorous semantic, resource and performance comparisons. Type safety in the Rust version must not automatically be equated with type safety at the C# calling surface, and a .NET package's AOT declaration must not be extended to all of its optional features.

## 2. Pinned versions and actual reading scope

Complete machine-readable records are in [sources.json](sources.json). All SHAs were returned by actual GitHub tags/refs, rather than inferred from version strings.

| Project | Pinned reference version | Commit SHA | Mechanisms actually studied in this round |
| --- | --- | --- | --- |
| Npgsql | v9.0.4 | `3b6c74c505c4dbc68a39b05e7440153b3bf511f4` | AOT feature boundaries, minimal query program and Native AOT CI |
| DapperAOT | 1.0.31 | `3bd350451f840b15a0894f4e8f2ed8a7ce95fb36` | Incremental generator filtering, interceptor output snapshots and packaging |
| EF Core | v10.0.0 | `12b8d44bf691d2e6933a6d1003647cce4f13c3d3` | Dynamic query compilation prerequisites, precompilation entry points and code-generation entry points |
| SQLx | v0.8.6 | `bab1b022bd56a64f9a08b46b36b97c5cff19d77e` | Transaction ownership, rollback on Drop, PostgreSQL implementation and tests |
| ASP.NET Core/Kestrel | v10.0.0 | `7387de91234d3ef751fa50b3d1bfede4130213ff` | Response-writing state machine and tests of access after closure |
| Tokio | tokio-1.47.1 | `be8ee45b3fc2d107174e586141b1cb12c93e2ddf` | Bounded message-channel capacity and permits |
| hyper | v1.7.0 | `400bdfdace8b40e3bdb93c5c6647b6b98211d432` | HTTP/1 shutdown entry point and C API stability declaration |

SQLx's old address `launchbadge/sqlx` returned a redirect when actually called; repository ID 230595891 resolved to the current `transact-rs/sqlx`. Evidence links use the resolved repository so the pinned commit is not lost through an old address or an organization migration.

## 3. Source-level observations obtained

### DB-E001: Review Npgsql AOT capabilities feature by feature

Actual call chain: `NpgsqlDataSourceBuilder.EnableDynamicJson` → internal builder; additional switches cover tuple records and unmapped enums/ranges. Explicit `RequiresDynamicCode` and `RequiresUnreferencedCode` annotations were read on the public APIs. The minimal Native AOT program uses `NpgsqlSlimDataSourceBuilder`, asynchronously opens a connection, executes a query and reads strings; CI separately performs whole-library analysis and actual execution after publication.

Sources: [pinned builder source](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/src/Npgsql/NpgsqlDataSourceBuilder.cs), [AOT test program](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/test/Npgsql.NativeAotTests/Program.cs), [CI definition](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/.github/workflows/native-aot.yml).

**Implications for NativeWeave (inference)**: the database capability inventory must be granular enough to cover data types, mapping modes and feature switches, rather than a single "PostgreSQL driver supports AOT" cell. Pregenerated JSON metadata or serialization to bytes before binding are alternative paths requiring validation; experiments are required before claiming that all POCO mapping can be solved at zero cost.

**Not covered**: connection pooling, authentication plugins, fault recovery, cancellation protocols, COPY, complex types and the complete Windows AOT path. This round did not execute upstream CI or verify whether its historical runs passed.

### ORM-E001: DapperAOT provides an actual compile-time mapping reference and exposes silent-fallback risks

Actual path: `Initialize` establishes a Roslyn incremental syntax pipeline → `PreFilter` selects candidate calls → `Parse` obtains semantic operations and checks enablement/support flags → generates interceptors. The snapshots read show how `Query`/`QueryAsync` calls redirect to static `CommandFactory` and `RowFactory`. Meanwhile, `Parse` returns an empty result immediately for `NotAotSupported`, `DoNotGenerate` or disabled cases.

Sources: [generator](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs), [input snapshot](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.input.cs), [output snapshot](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.output.cs). The [project FAQ](https://aot.dapperlib.dev/faq.html) also explains the importance of support coverage and actual AOT publication tests.

**Implications for NativeWeave (candidate requirements)**: production AOT APIs must produce actionable compilation diagnostics or explicit alternative APIs for unsupported usage; they must not silently retain a path that depends on dynamic runtime generation. Whether interceptors may be adopted depends on actual support in the selected stable C# toolchain; a reference project's adoption does not establish compliance with NativeWeave's stable Core requirements.

**Not covered**: all Dapper overloads, private types, dynamic parameters, generator diagnostic coverage, resource release on early streaming exit and every runtime execution path. Snapshots are upstream expected output only and were not regenerated in this conversation.

### ORM-E002: EF Core ordinary query compilation and precompilation are different execution paths

In the pinned version, `QueryCompiler.ExecuteCore` first extracts parameters and then searches the compiled-query cache; when new compilation is needed, it checks `RuntimeFeature.IsDynamicCodeSupported`, otherwise throwing `QueryNotPrecompiled`. `PrecompileQuery` in the same source has an experimental annotation. The design-time generation entry point connects `QueryLocator`, C#-to-expression-tree conversion and precompiled output.

Sources: [QueryCompiler](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore/Query/Internal/QueryCompiler.cs), [PrecompiledQueryCodeGenerator](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore.Design/Query/Internal/PrecompiledQueryCodeGenerator.cs), [official Native AOT documentation](https://learn.microsoft.com/ef/core/performance/nativeaot-and-precompiled-queries).

**Implications for NativeWeave**: separately compare direct use of a mature provider's stable subset, generated predefined query methods, a compile-time LINQ subset and a controlled runtime query IR. Neither "LINQ cannot work with AOT" nor "adding a Source Generator supports arbitrary IQueryable" is a valid claim. The EF documentation read still labels Native AOT/precompilation experimental; this judgment is limited to the materials read and the pinned versions and needs rechecking by the latest-version topic.

**Not covered**: the complete SQL translator, null compensation, differences in provider precompilation, relationship fixup, tracking, compiled models and the EF test pipeline. This round confirms only entry points and failure branches.

### DB-E002: SQLx rollback on Drop does not mean server-acknowledged rollback

Actual path: `Transaction::commit/rollback` awaits the database transaction manager and sets `open` to false only after success; `Drop` calls `start_rollback` if the transaction remains open. The PostgreSQL implementation of `start_rollback` queues rollback SQL on the connection and adjusts the local transaction depth; it does not wait for server acknowledgement inside Drop.

Relevant tests include explicit rollback, commit, nested savepoints, reuse of the same connection after consecutive transaction drops and recovery through explicit rollback after statement timeout. Test intent in source does not mean successful execution in the current environment.

Sources: [generic transactions](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/transaction.rs), [PostgreSQL transactions](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/transaction.rs), [relevant tests, lines 423–620 read](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/tests/postgres/postgres.rs#L423-L620).

**Implications for NativeWeave (candidate contract)**: distinguish "rollback requested," "connection cleanup completed," "server outcome acknowledged" and "connection discarded." Specify the promises made by C# synchronous Dispose, asynchronous DisposeAsync, Engine shutdown and final resource reclamation separately. When a commit request has arrived but its response is lost, cancellation or disconnection must not automatically mean "not committed," and non-idempotent business operations must not be retried automatically.

**Not covered**: the complete pool return/cleanup path, protocol synchronization during cancellation, classification of uncertain COMMIT outcomes, the SQLite worker model and draining during Rust executor shutdown. This round did not quantify FFI, conversion or pool-layer costs.

### SRV-E001: Kestrel response states should not be replaced by a simple disposed boolean

The response PipeWriter in the pinned source distinguishes Open, Closed and Aborted. Writes/flushes check state first; after writes are no longer accepted, the relevant APIs reject access, with tests for each. Aborted also has a branch that throws on a write only when the corresponding cancellation token requests cancellation.

Sources: [response PipeWriter](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs), [corresponding tests](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs).

**Implications for NativeWeave (inference)**: if a Rust HTTP Engine is introduced, its adapter must preserve the distinct semantics of request completion, connection interruption, stopping response writes, asynchronous flush and callback cessation; `Handle.Dispose()` alone is insufficient.

The [official ASP.NET Core AOT support matrix](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/native-aot?view=aspnetcore-10.0) and [gRPC AOT documentation](https://learn.microsoft.com/en-us/aspnet/core/grpc/native-aot?view=aspnetcore-10.0) are inputs to baseline selection; they do not establish compatibility of every middleware, MVC or arbitrary plugin.

**Not covered**: HTTP/2/3, TLS, connection-level shutdown, request queues, actual memory upper bounds and the complete mutual-exclusion relationships of synchronous/asynchronous writing. A state class and unit tests are insufficient to prove concurrency correctness of the entire server.

### SRV-E002: hyper's bundled FFI cannot directly become NativeWeave's stable contract

The pinned `Cargo.toml` marks the C API feature unstable and provides no semver guarantee. HTTP/1 `graceful_shutdown` calls `disable_keep_alive`, and its documentation requires continued polling of the connection Future until shutdown completes.

Sources: [hyper Cargo features](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/Cargo.toml), [HTTP/1 connection shutdown](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/src/server/conn/http1.rs#L120-L155).

**Implications for NativeWeave (inference)**: even when reusing hyper, a separately versioned Adapter boundary is needed, or an explicitly experimental status that follows unstable upstream APIs. Stopping polling, releasing the C# context and graceful shutdown are different events and must not be blurred into a single completion callback.

**Not covered**: the complete hyper FFI implementation, h2/HTTP/3, hyper-util, TLS integration, shutdown concurrency tests and latest-version status.

### SRV-E003: A bounded message channel does not automatically bound total memory

The Tokio `mpsc::channel` source read establishes message capacity using a semaphore, and `send` waits for a permit before sending. This supports only the narrow conclusion that the number of messages in the queue is constrained by capacity.

Source: [Tokio bounded channel](https://github.com/tokio-rs/tokio/blob/be8ee45b3fc2d107174e586141b1cb12c93e2ddf/tokio/src/sync/mpsc/bounded.rs).

**Additional inference**: if every producer allocates a large message before waiting for a permit, or new waiting tasks are continuously created, message capacity alone cannot constrain total RSS. NativeWeave backpressure budgets should separately cover accepted request counts, queued bytes, active tasks and external in-flight resources. Semaphore, shutdown and cancellation tests must still be read before establishing memory bounds with explicit assumptions.

## 4. Candidate comparison: what can be concluded

| Route | Existing evidence | Potential reuse | Commitments that cannot be made in advance |
| --- | --- | --- | --- |
| Npgsql + C# static mappings | Core AOT tests and feature opt-in annotations | ADO.NET connections, parameters and result reading; avoids DB FFI | All data types, plugins and arbitrary JSON POCOs are AOT-safe |
| DapperAOT | Incremental generation and mapping snapshots | Command factories, mapping generation, diagnostics and API coverage testing approaches | Arbitrary existing Dapper code works with AOT without modification |
| EF Core | Separate query compilation and precompilation paths | SQL semantics, relations/projections, parameter extraction and test references | The pinned version's Native AOT support is fully production-ready |
| linq2db | Only repository/official discussions checked; target implementation not yet read | LINQ translation and multi-provider semantic references | A maintainer-supported individual user's AOT success implies whole-library support |
| SQLx Engine | Transaction and rollback source | Rust drivers, transaction/pool/streaming capabilities | Wrapping SQLx automatically gives C# queries the compile-time checking of Rust macros |
| SeaQuery | Official generated documentation and source directories located | SQL AST, parameter numbering and multi-dialect serialization | A Rust query builder directly becomes a natural C# API |
| SeaORM | Official generated documentation and database directories located | Entity/relation and transaction/streaming interfaces | Rust macro-generated models can be reused directly as C# entities without an additional contract |
| Kestrel + C# handlers | Official AOT matrix and scoped response-state source | Primary application networking and managed async stack | Arbitrary ASP.NET modules support AOT; every workload outperforms Rust |
| hyper/Tokio Engine | Scoped shutdown, channel and feature source | Rust HTTP, flow control and optional executors | The hyper C API is stable; introducing Tokio necessarily reduces RSS or latency |

### Four AOT ORM questions that must remain separate

- **Query expression**: ordinary LINQ to Objects, IQueryable expression trees, compile-time syntax analysis and controlled Fluent IR are different entry points.
- **SQL translation**: interpreting a finite expression tree does not itself generate machine code; however, available metadata, generic instances, dynamic member access and result materializers still require AOT design.
- **Result mapping**: pregenerated mappers can reduce dynamic generation; they must cover nullable values, conversion exceptions, constructor/setter accessibility, relational projections and early streaming exit.
- **Call substitution**: a Source Generator adding code is not equivalent to arbitrarily rewriting existing methods. Compare explicitly generated partial methods/APIs with interception mechanisms whose stability has been verified.

Dynamic filters may be composed at runtime as a finite, strongly typed, parameterized query IR, requiring static definitions for fields, operations, type mappings and allowed methods. This does not execute arbitrary user C# and should not silently fall back to raw SQL concatenation or full client-side filtering. Whether to expose IQueryable requires API usability experiments and review of the translation-capability contract.

## 5. Domain questions and output interfaces that must be completed

These are independent research boundaries and may start in parallel; formal IDs are assigned by Plan's research graph. Each first produces evidence and candidate contracts, after which the corresponding owner in the documentation graph prepares specifications and development tasks.

| Question key | Research question | Evidence/experiments | Output to Design / Plan |
| --- | --- | --- | --- |
| DB-Q01 | Equivalent Npgsql/SQLx features and cross-language costs | Pinned-version call chains for connection, pooling, execution, cancellation, parameters, reading and release | Provider support matrix; decision on Rust adoption and budgets to measure |
| DB-Q02 | Threading and cancellation semantics of SQLite routes | Microsoft.Data.Sqlite, SQLitePCL.raw, rusqlite, SQLx SQLite worker and SQLite C API | Thread-affinity, busy-lock, interrupt, WAL and checkpoint contracts |
| DB-Q03 | When transactions and savepoints permit connection return | Complete commit/rollback/drop/pool/reset/disconnection state machine | State transitions, unknown commit outcomes and synchronous/asynchronous cleanup tasks |
| DB-Q04 | How batched and streaming reads avoid per-cell FFI | Row/batch/columnar candidates and experiments with actual data distributions | Buffer/row lifetimes, copy counts and batch ABI; do not mandate Arrow in advance |
| DB-Q05 | How schemas and migrations are deployed independently | Transactional DDL, migration locks, checksums, failure recovery and permissions | Version compatibility, reentrant migrations and rollback/roll-forward rules |
| ORM-Q01 | A natural C# query surface and a rejectable syntax set | Compile-time LINQ subset, explicitly generated methods and Fluent IR user examples | Supported/rejected syntax table, diagnostic codes and fallback entry points without dynamic code |
| ORM-Q02 | How SQL semantics are validated | Differences in null/empty sets/join/aggregation/pagination/collation/time/numeric behavior | Provider-difference table, SQL goldens + differential tests against actual databases |
| ORM-Q03 | Metadata/mapping and result lifetimes | Nullable values, projections, value conversions, concurrent enumeration and midstream exceptions | Static descriptors, materializers and release contracts |
| ORM-Q04 | How caching and precompilation are versioned | Schema, provider, parameter-shape, generic-combination and generated-size experiments | Cache keys, invalidation, build incrementality and grounding for size limits |
| SRV-Q01 | Which requirements Kestrel satisfies and when an additional Engine has value | Benchmarks with identical TLS, connection reuse, payloads, business logic and database access | Server capability boundaries, equivalent experiments and selection ADR |
| SRV-Q02 | How Rust request adaptation and streaming backpressure form a complete feedback loop | Complete request/response buffer, header, cancellation, thread-callback and shutdown paths | Request tokens, consumption acknowledgements, budgets and drain state machines |
| SRV-Q03 | How gRPC/MCP compose without entering Core | Official SDKs, serialization, streaming methods and tool-registration AOT experiments | Independent protocol adapters, version matrices and diagnostics |
| SRV-Q04 | Who owns TLS, authentication and observability | Kestrel/.NET and native Rust TLS, trace contexts and logging models | Ownership, certificate updates, disabling sensitive parameters and sampling overhead |
| E2E-Q01 | Whether databases and servers can preserve end-to-end resource boundaries | A bookkeeping/order-style transactional reference workload without business dependencies | Reference application design, fault matrix and three-route benchmarks |

The recommended reference application uses a small, verifiable resource-booking or inventory transaction model: record creation, idempotency keys, conditional updates and paginated/streaming queries, covering write conflicts and commit uncertainty. The model serves validation only and introduces no downstream business protocol into the framework.

## 6. Domain invariants and validation obligations

The following requirements are independent of candidate implementations and await formalization; they do not represent completed proofs:

1. **Exclusive connection use**: a connection used for one protocol interaction must not simultaneously be reused by incompatible transactions/readers; if a provider supports multiplexing, specify its compatibility boundaries with transactions, streaming and session state.
2. **Transaction terminal state**: a transaction records at most one acknowledged terminal state. Unknown must not masquerade as RolledBack; without protocol acknowledgement, do not claim either committed or uncommitted.
3. **Result validity window**: every read requires valid leases for its backing buffer and parent reader. Early enumeration exit, exceptions and cancellation all eventually release the leases.
4. **SQL parameter isolation**: user data may enter only value parameters; identifiers and syntax fragments come from verified static or controlled sets. Parameter order, types and null markers must agree.
5. **Query equivalence**: require `GeneratedQuery(D, p) = ReferenceSQL(D, p)` only within the declared semantic domain; that domain must state assumptions about collation, timezone, null, overflow, floating-point NaN, ordering tie-breaks and related behavior.
6. **Completion uniqueness**: each cross-language request/query operation reaches final completion at most once; races between cancellation requests and arriving results must not consume results or release contexts twice.
7. **Resource bounds**: if active request counts, queued bytes, concurrent materializers and native pool sizes are bounded, specify the components and calculation of the memory budget; limiting channel item counts alone does not prove a whole-system bound.
8. **Shutdown quiescence**: after shutdown/drain completion is declared, no callback may enter with a reference to a released context, and no cleanup operation may remain that requires an already-stopped executor.

Commit/cancellation/cleanup state transitions and callback-stop protocols suit model checking; SQL semantics better suit property tests and differential tests against actual PostgreSQL/SQLite; native memory boundaries suit fuzzing, sanitizers and the corresponding Rust tools. SQL golden text snapshots cannot substitute for actual execution semantics, and a stress test without failures cannot substitute for proof of all races.

## 7. Minimum experimental matrix (proposed, not yet executed)

| Scenario | Required observations | Comparison/fault |
| --- | --- | --- |
| AOT connection and mapping | Actually published binaries connect, bind, read and close successfully | Execute separately on Windows/Linux; record each RID independently |
| Unsupported query expressions | Explicit compilation errors or explicit alternative paths | Private types, captured state, arbitrary method calls and dynamic members |
| SQL semantics | Consistent results in pinned test databases | Null, empty sets, left joins, aggregation, decimal, time zones and collation |
| Connection pool exhaustion | Bounded waiting and capacity restoration after cancellation | Holding connections without release, authentication failure and network refusal |
| Query cancellation races | Exactly one completion result, with a connection that can be cleaned up or discarded | cancel before send / during read / after completion |
| Transaction failures | No erroneous commit and no treatment of Unknown as rollback | Statement timeout, deadlock, disconnection and lost COMMIT response |
| Early streaming exit | Reader, connection, native buffer and GCHandle return to baseline | Break after consuming one row, materializer throws and client disconnects |
| Batched reads/writes | Explainable throughput and copy/allocation accounting | Small/large rows, binary large objects, UTF-8 and nullable values |
| Migrations | Schema results agree with the version ledger | Concurrent startup, interrupted execution, insufficient privileges and nontransactional DDL |
| HTTP flow control | Slow clients cannot cause unbounded memory growth | Slow reads/writes, oversized headers/bodies and multiple HTTP/2 streams |
| Server shutdown | After accepting stops, drain terminates and resources reach zero or the agreed state | Active transactions, delayed callbacks, pending flushes and long-lived connections |
| Protocol adapters | Actual AOT execution of gRPC/MCP paths | Serialization, stream cancellation, error mapping and version differences |
| End-to-end workloads | Reproducible CPU/RSS/allocation/throughput/P95/P99/error rates | Identical protocols, data, indexes, TLS, features and machines across the three routes |

Performance thresholds must follow baselines and application goals. This round sets no arbitrary figures such as "30% faster" or "RSS below 50 MB." Test records should also include concurrency and queueing states corresponding to throughput, cold/warm startup, duration, repetitions, confidence-interval methodology, load-generator saturation checks and error rates; otherwise latency percentiles can mislead.

## 8. Extended source inventory and priorities

"Read" applies only to the scope declared in sections 2 and 3 and sources.json. The unpinned candidate paths below are research entry points only, not evidence of having been read.

| Priority | Project/primary entry point | Question to resolve | Next-round source entry points and status |
| --- | --- | --- | --- |
| P0 | [Npgsql](https://github.com/npgsql/npgsql) | Pure C# PostgreSQL baseline | `NpgsqlCommand`, `NpgsqlConnector`, `PoolingDataSource`, type resolvers; directories/filenames located, implementation bodies not read |
| P0 | [SQLx](https://github.com/transact-rs/sqlx) | Optional Rust driver engine | `sqlx-core/src/pool/`, postgres executor/connection, `sqlx-sqlite` worker; transactions partially read |
| P0 | [DapperAOT](https://github.com/DapperLib/DapperAOT) | Static parameter and mapping generation | Generation entry points/snapshots read; continue with `CommandT.Query`, `AsyncQueryState` and negative diagnostic tests |
| P0 | [EF Core](https://github.com/dotnet/efcore) | Query semantics and precompilation | Entry points read; continue with relational query translators, SQL nullability, compiled models and provider tests |
| P0 | [ASP.NET Core](https://github.com/dotnet/aspnetcore) | C# Native AOT server baseline | Kestrel, RequestDelegateGenerator, Pipelines, connection management and stream tests |
| P0 | [Tokio](https://github.com/tokio-rs/tokio), [hyper](https://github.com/hyperium/hyper), [hyper-util](https://github.com/hyperium/hyper-util) | Rust server/runtime costs and shutdown | Some source read; continue with body flow control, connection tasks, executors, TLS adapters and shutdown tests |
| P1 | [linq2db](https://github.com/linq2db/linq2db) | Multi-database SQL translation and diagnostics | Internal LINQ builders, expression compilation and mappers; this round only inspected the repository/official discussions |
| P1 | [SeaQuery](https://github.com/SeaQL/sea-query) | Parameterizable query IR and dialects | `src/backend`, `src/query`, `src/value` directories actually located; contents not read |
| P1 | [SeaORM](https://github.com/SeaQL/sea-orm) | Rust ORM layer responsibilities and transactions/streaming | `src/database/transaction.rs`, `stream`, `statement.rs` paths located; contents not read |
| P1 | [Microsoft.Data.Sqlite](https://github.com/dotnet/efcore/tree/main/src/Microsoft.Data.Sqlite.Core), [SQLitePCL.raw](https://github.com/ericsink/SQLitePCL.raw) | Minimal C# SQLite native-binding baseline | Connection/command/reader and native library loading; version pinning and reading pending |
| P1 | [rusqlite](https://github.com/rusqlite/rusqlite), [SQLite C API](https://www.sqlite.org/c3ref/intro.html) | Synchronous SQLite engines and thread/interrupt | Connection, statement, transaction and unlock/interrupt; investigation pending |
| P1 | [official PostgreSQL protocol](https://www.postgresql.org/docs/current/protocol.html) | Cancellation, Sync, transaction states and error recovery | Extended query, CancelRequest and ReadyForQuery; pinning by server version pending |
| P1 | [grpc-dotnet](https://github.com/grpc/grpc-dotnet), [MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) | Protocol adapters, AOT generated registration and serialization | Server binding/streaming/serialization/transport; source pinning pending |
| P1 | [System.Text.Json/runtime](https://github.com/dotnet/runtime), [OpenTelemetry .NET](https://github.com/open-telemetry/opentelemetry-dotnet) | Static serialization and observability overhead | Source generation, diagnostics, metrics/traces AOT; reading pending |
| P2 | [Apache Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) | Whether large-batch data exchange merits standardization | Evaluate lifetime, columnar conversion and dependency costs; do not presuppose it as the database ABI |
| P2 | [Testcontainers .NET](https://github.com/testcontainers/testcontainers-dotnet), [Toxiproxy](https://github.com/Shopify/toxiproxy) | Reproducible database/network faults | Test-tool candidates only, excluded from the product runtime; Windows/Linux capability adaptation pending |

Every added project must explain which custom development work it replaces and the dependencies/licenses and update costs it introduces. A longer candidate list must not itself expand production modules.

## 9. License and reuse records

- Npgsql: pinned LICENSE actually read; obligations to retain copyright and license text pass to the supply-chain topic.
- DapperAOT: pinned `License.txt` actually read; the tool declares Apache 2.0 and additional name/logo usage restrictions. GitHub metadata returns only NOASSERTION, so automatic classification alone is insufficient.
- SQLx: pinned Cargo.toml declares MIT OR Apache-2.0; both licenses exist in the repository. The dependency tree still requires independent investigation.
- ASP.NET Core, EF Core: files read contain MIT headers; auditing of all transitive dependencies and embedded third-party code is incomplete.
- hyper: pinned Cargo.toml declares MIT; Tokio's license was not read in this round and remains pending verification.

This deliverable retains only research summaries and links; it copies no substantial external product source and makes no decision about which code to bring into NativeWeave.

## 10. Current evidence gaps and cross-review questions

1. The latest-version topic must confirm the selected stable language features and framework versions; in particular, do not treat the old pinned EF/Dapper implementations read as facts about future versions.
2. The ABI/ownership topic should review SQLx deferred rollback and release ordering for streaming readers and parent connections; if Core does not support the required leases/draining, revise the scoped contract instead of adding a global runtime.
3. The generator topic should demonstrate a complete diagnostic path for unsupported queries, incremental-build consistency and public strongly typed APIs; referencing a generator is not a shortcut to AOT-safety acceptance.
4. The concurrency topic should examine interactions among callback completion, cancellation-registration release, executor shutdown and .NET continuations; arbitrary C# user code must not execute while native locks are held.
5. The server topic needs complete Kestrel and Rust request paths; the single PipeWriter or hyper method examined this round must not serve as a complete architectural comparison.
6. The performance topic must provide complete workload experiments; without performance data, maintainability benefits must still be evaluated from actual code/configuration differences.
7. The release topic must examine NuGet/RID/native dependencies, TLS backends, OS ABIs, configurations and database-version combinations; all formally supported platforms require actual builds and execution.
8. Independent reviewers should spot-check whether evidence at pinned SHAs supports each conclusion, explicitly separating test source read from actual successful execution.

**Deliverable status for this round**: research boundaries, candidate comparisons and 7 scoped source-evidence items have been established; phase B's production public APIs, database selection, ORM query subset, server engine selection and performance commitments remain unaccepted. They are concrete inputs to the next round of parallel research and documentation, rather than vaguely deferred future work.

