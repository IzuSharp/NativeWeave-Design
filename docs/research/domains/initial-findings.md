> Historical checkpoint. Current product constraints and acceptance boundaries are in [ADR-0003](../../decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md). Any optional Rust Server/Kestrel product-host wording below describes the prior snapshot, not current authorization. Original evidence retains its recorded scope.

# Database, AOT ORM, and Server: Initial Source Investigation and Research Boundaries

- Record date: 2026-11-12 (user session date).
- Latest-version supplementary check: pinned EF Core / Kestrel v11 source was read separately; see [supplementary v11 source verification](v11-recheck.md). This report's v10 observations retain their status as historical evidence.
- Status: **preliminary research evidence; no accepted architecture decision has been established**.
- Executor: independent phase B research subagent.
- Inspection scope: 7 external projects and 20 specific source files or excerpts, plus official documentation and candidate directory inspection.
- Execution status: this topic did not compile, execute tests, publish Native AOT, or run performance tests. Upstream test definitions and CI files establish only the existence of relevant validation procedures, not passing results in this session.
- Version note: the pinned versions below support reproducible source reading; they are neither claimed to be the current latest versions nor selected as NativeWeave dependencies. Formal versions must be reverified with the toolchain and supply-chain topics.
- Basis: the user's NativeWeave task requirements and public primary sources. ArcForges design content, processes, and acceptance criteria were not used as a basis for this project.

## 1. Current Assessment and Decision Boundaries

Phase B should immediately open three experimental branches for comparison:

1. Pure C# Native AOT: database drivers, static mapping, server, and business code all in C#, as an essential baseline.
2. C# Native AOT + an independent Rust domain Engine: adopt only when complete workloads demonstrate benefits or when the Rust ecosystem supplies a necessary capability.
3. Equivalent pure-Rust workloads: separate native-engine costs from cross-language adaptation costs.

Existing evidence supports prioritizing Npgsql + generated mapping and Kestrel's AOT capabilities as research baselines; it is insufficient to accept final technology selections. SQLx, SeaQuery, SeaORM, and hyper/Tokio should undergo equally rigorous semantic, resource, and performance comparisons. Rust-side type safety must not automatically be equated with type safety at the C# call surface, nor may a .NET package's AOT declaration be extended to all its optional features.

## 2. Pinned Versions and Actual Reading Scope

Complete machine-readable records are in [sources.json](sources.json). All SHAs were returned by actual GitHub tag/ref requests, not inferred from version strings.

| Project | Pinned reference version | Commit SHA | Mechanisms actually researched in this round |
| --- | --- | --- | --- |
| Npgsql | v9.0.4 | `3b6c74c505c4dbc68a39b05e7440153b3bf511f4` | AOT feature boundaries, minimal query program, Native AOT CI |
| DapperAOT | 1.0.31 | `3bd350451f840b15a0894f4e8f2ed8a7ce95fb36` | Incremental generator filtering, interceptor output snapshots, packaging |
| EF Core | v10.0.0 | `12b8d44bf691d2e6933a6d1003647cce4f13c3d3` | Dynamic query compilation gate, precompilation entry point, code-generation entry point |
| SQLx | v0.8.6 | `bab1b022bd56a64f9a08b46b36b97c5cff19d77e` | Transaction ownership, Drop rollback, PostgreSQL implementation and tests |
| ASP.NET Core/Kestrel | v10.0.0 | `7387de91234d3ef751fa50b3d1bfede4130213ff` | Response-write state machine, tests of access after closure |
| Tokio | tokio-1.47.1 | `be8ee45b3fc2d107174e586141b1cb12c93e2ddf` | Bounded message-channel capacity and permits |
| hyper | v1.7.0 | `400bdfdace8b40e3bdb93c5c6647b6b98211d432` | HTTP/1 shutdown entry point, C API stability declaration |

The old SQLx address `launchbadge/sqlx` returned a redirect in the actual request; repository ID 230595891 resolved to the current `transact-rs/sqlx`. Evidence links use the resolved repository, preserving the pinned commit despite the old address or organization migration.

## 3. Source-Level Observations Obtained

### DB-E001: Npgsql AOT Capabilities Must Be Reviewed Feature by Feature

Actual call chain: `NpgsqlDataSourceBuilder.EnableDynamicJson` → internal builder; there are separate feature switches for tuple records and unmapped enums/ranges. Explicit `RequiresDynamicCode` and `RequiresUnreferencedCode` annotations were read on public APIs. The minimal Native AOT program uses `NpgsqlSlimDataSourceBuilder`, opens a connection asynchronously, executes a query, and reads a string; CI separately performs whole-library analysis and execution after actual publication.

Sources: [pinned builder source](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/src/Npgsql/NpgsqlDataSourceBuilder.cs), [AOT test program](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/test/Npgsql.NativeAotTests/Program.cs), [CI definition](https://github.com/npgsql/npgsql/blob/3b6c74c505c4dbc68a39b05e7440153b3bf511f4/.github/workflows/native-aot.yml).

**Implication for NativeWeave (inference)**: the database capability inventory must be granular down to data types, mapping approaches, and feature switches; a single "PostgreSQL driver supports AOT" cell is insufficient. Pregenerated JSON metadata or serialization to bytes before binding are alternative paths that require validation; experiments are required before claiming that all POCO mapping can be solved at zero cost.

**Not covered**: complete paths for connection pooling, authentication plugins, failure recovery, the cancellation protocol, COPY, complex types, and Windows AOT. This round neither executed upstream CI nor checked whether its historical runs passed.

### ORM-E001: DapperAOT Provides a Real Compile-Time Mapping Reference and Reveals Silent Fallback Risks

Actual chain: `Initialize` establishes a Roslyn incremental syntax pipeline → `PreFilter` selects candidate calls → `Parse` obtains semantic operations and checks enablement and support flags → interceptors are generated. The snapshots read show how `Query`/`QueryAsync` calls are redirected to static `CommandFactory` and `RowFactory`. At the same time, `Parse` directly returns an empty result for `NotAotSupported`, `DoNotGenerate`, or disabled cases.

Sources: [generator](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs), [input snapshot](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.input.cs), [output snapshot](https://github.com/DapperLib/DapperAOT/blob/3bd350451f840b15a0894f4e8f2ed8a7ce95fb36/test/Dapper.AOT.Test/Interceptors/Query.output.cs). The [project FAQ](https://aot.dapperlib.dev/faq.html) also explains the importance of support coverage and actual AOT publication testing.

**Implication for NativeWeave (candidate requirement)**: production AOT APIs must produce actionable compilation diagnostics or explicit alternative APIs for unsupported usage, rather than silently retaining a path that depends on runtime dynamic generation. Whether interceptors may be used depends on actual support in the selected stable C# toolchain; a reference project's use of the feature does not establish that it meets NativeWeave's stable-Core requirements.

**Not covered**: all Dapper overloads, private types, dynamic parameters, generator diagnostic coverage, resource release on early streaming exit, and all runtime execution paths. The snapshots are only upstream expected output and were not regenerated in this session.

### ORM-E002: EF Core's Normal Query Compilation and Precompilation Are Distinct Execution Paths

In the pinned version, `QueryCompiler.ExecuteCore` first extracts parameters and then looks up the compiled-query cache; when new compilation is required, it checks `RuntimeFeature.IsDynamicCodeSupported`, otherwise throwing `QueryNotPrecompiled`. `PrecompileQuery` in the same source carries an experimental annotation. The design-time generation entry point connects `QueryLocator`, C#-to-expression-tree conversion, and precompiled output.

Sources: [QueryCompiler](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore/Query/Internal/QueryCompiler.cs), [PrecompiledQueryCodeGenerator](https://github.com/dotnet/efcore/blob/12b8d44bf691d2e6933a6d1003647cce4f13c3d3/src/EFCore.Design/Query/Internal/PrecompiledQueryCodeGenerator.cs), [official Native AOT documentation](https://learn.microsoft.com/ef/core/performance/nativeaot-and-precompiled-queries).

**Implication for NativeWeave**: directly adopting stable subsets of mature providers, generating predefined query methods, a compile-time LINQ subset, and controlled runtime query IR must be compared separately. Neither "LINQ cannot use AOT" nor "adding a Source Generator supports arbitrary IQueryable" is justified. The EF documentation read still marks Native AOT/precompilation as experimental; that assessment is limited to the materials read and pinned versions and requires rechecking in the latest-version topic.

**Not covered**: the complete SQL translator, null compensation, provider precompilation differences, relationship fixup, trackers, compiled models, and EF test chains. This round confirms only entry points and failure branches.

### DB-E002: SQLx Drop Rollback Does Not Mean the Server Has Confirmed Rollback

Actual chain: `Transaction::commit/rollback` awaits the database transaction manager and sets `open` to false only after success; `Drop` calls `start_rollback` if the transaction remains open. The PostgreSQL `start_rollback` implementation queues rollback SQL on the connection and adjusts the local transaction depth; it does not wait for server acknowledgment in Drop.

Related tests include explicit rollback, commit, nested savepoints, reuse of the same connection after successive transaction drops, and recovery through explicit rollback after a statement timeout. Test intent in source code is not evidence of successful execution in the current environment.

Sources: [generic transactions](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/transaction.rs), [PostgreSQL transactions](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/transaction.rs), [related tests, lines 423–620 read](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/tests/postgres/postgres.rs#L423-L620).

**Implication for NativeWeave (candidate contract)**: "rollback requested," "connection cleanup complete," "server outcome confirmed," and "connection discarded" must be distinguished. The guarantees of C# synchronous Dispose, asynchronous DisposeAsync, Engine shutdown, and eventual resource reclamation must each be explicit. When a commit request reaches the server but its response is lost, cancellation or disconnection must not automatically be interpreted as "not committed," and non-idempotent business operations must not be retried automatically.

**Not covered**: the complete pool-return/cleanup chain, protocol synchronization during cancellation, classification of uncertain COMMIT outcomes, the SQLite worker model, and drain during Rust executor shutdown. This round did not quantify FFI, conversion, or pool-layer costs.

### SRV-E001: Kestrel Response States Should Not Be Replaced by a Simple disposed Boolean

The response PipeWriter in the pinned source distinguishes Open, Closed, and Aborted. Writes/flushes check state first; after writes stop being accepted, the relevant APIs reject access and have individual tests. Aborted also includes a branch that throws during writes only when the corresponding cancellation token requests cancellation.

Sources: [response PipeWriter](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs), [corresponding tests](https://github.com/dotnet/aspnetcore/blob/7387de91234d3ef751fa50b3d1bfede4130213ff/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs).

**Implication for NativeWeave (inference)**: if a Rust HTTP Engine is introduced, the adapter must preserve the distinct semantics of request completion, connection abort, stopping response writes, asynchronous flush, and callback cessation; `Handle.Dispose()` alone is insufficient.

The [official ASP.NET Core AOT support matrix](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/native-aot?view=aspnetcore-10.0) and [gRPC AOT documentation](https://learn.microsoft.com/en-us/aspnet/core/grpc/native-aot?view=aspnetcore-10.0) are inputs for baseline selection; they do not establish compatibility for every middleware component, MVC, or arbitrary plugin.

**Not covered**: HTTP/2/3, TLS, connection-level shutdown, request queues, actual memory limits, and the complete mutual-exclusion relationships between synchronous/asynchronous writes. One state class and its unit tests cannot prove concurrency correctness of an entire server.

### SRV-E002: hyper's Own FFI Cannot Be Promoted Directly to a Stable NativeWeave Contract

The pinned `Cargo.toml` labels the C API feature unstable and makes no semver commitment. HTTP/1 `graceful_shutdown` calls `disable_keep_alive`; its documentation requires continued polling of the connection Future until shutdown completes.

Sources: [hyper Cargo features](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/Cargo.toml), [HTTP/1 connection shutdown](https://github.com/hyperium/hyper/blob/400bdfdace8b40e3bdb93c5c6647b6b98211d432/src/server/conn/http1.rs#L120-L155).

**Implication for NativeWeave (inference)**: even when reusing hyper, an independently versioned Adapter boundary is needed, or the implementation must explicitly remain experimental while following unstable upstream APIs. Stopping polling, releasing the C# context, and graceful shutdown are different events and must not be blurred into one completion callback.

**Not covered**: hyper's complete FFI implementation chain, h2/HTTP/3, hyper-util, TLS integration, concurrent shutdown tests, and latest-version status.

### SRV-E003: A Bounded Message Channel Does Not Automatically Bound Total Memory

The Tokio `mpsc::channel` code read establishes message capacity with a semaphore, and `send` sends after waiting for a permit. The source supports only the narrow conclusion that the number of queued messages is constrained by capacity.

Source: [Tokio bounded channel](https://github.com/tokio-rs/tokio/blob/be8ee45b3fc2d107174e586141b1cb12c93e2ddf/tokio/src/sync/mpsc/bounded.rs).

**Additional inference**: if every producer allocates a large message before waiting for a permit, or continually creates waiting tasks, message capacity alone cannot bound total RSS. NativeWeave backpressure budgets should separately cover accepted request counts, queued bytes, active task counts, and external in-flight resources. Semaphore, shutdown, and cancellation tests still need to be read before establishing a memory bound with explicit assumptions.

## 4. Candidate Comparison: What Can Be Concluded

| Approach | Existing evidence | Potential reuse points | Commitments that cannot be made in advance |
| --- | --- | --- | --- |
| Npgsql + C# static mapping | Core AOT tests, feature opt-in annotations | ADO.NET connections, parameters, result reading; avoid DB FFI | All data types, plugins, and arbitrary JSON POCOs are AOT-safe |
| DapperAOT | Incremental generation and mapping snapshots | Command factories, mapping generation, diagnostics, and API coverage testing methods | Any existing Dapper code can use AOT without modification |
| EF Core | Separation of query compilation and precompilation | References for SQL semantics, relationships/projections, parameter extraction, and tests | Native AOT in the pinned version is fully production-ready |
| linq2db | Only repository/official discussions checked; target implementation not yet read | Reference for LINQ translation and multi-provider semantics | A maintainer-assisted successful AOT case for one user establishes support for the entire library |
| SQLx Engine | Transaction and rollback source | Rust drivers, transaction/pool/streaming capabilities | Wrapping SQLx automatically gives C# queries Rust macro compile-time checks |
| SeaQuery | Official generated documentation and source directories located | SQL AST, parameter numbering, multi-dialect serialization | A Rust query builder directly becomes a natural C# API |
| SeaORM | Official generated documentation and database directories located | Entity/relationship, transaction/streaming interfaces | Rust macro-generated models can be reused directly as C# entities without additional contracts |
| Kestrel + C# handlers | Official AOT matrix and selected response-state source | Main-application networking and managed async stack | Every ASP.NET module supports AOT; every workload outperforms Rust |
| hyper/Tokio Engine | Selected shutdown, channel, and feature source | Rust HTTP, flow control, optional executor | hyper's C API is stable; introducing Tokio necessarily lowers RSS or latency |

### Four AOT ORM Questions That Must Be Kept Separate

- **Query expression**: ordinary LINQ to Objects, IQueryable expression trees, compile-time syntax analysis, and controlled Fluent IR are distinct entry points.
- **SQL translation**: interpreting a finite expression tree is not itself machine-code generation; available metadata, generic instantiations, dynamic member access, and result materializers still require AOT design.
- **Result mapping**: pregenerated mappers can reduce dynamic generation; they must cover nullable values, conversion exceptions, constructor/setter accessibility, relationship projections, and early exit from streaming.
- **Call replacement**: adding code with a Source Generator cannot be equated directly with arbitrarily rewriting existing methods. Explicitly generated partial methods/APIs must be compared with interception mechanisms whose stability has been verified.

Dynamic filters can be assembled at runtime as a finite, strongly typed, parameterized query IR, provided fields, operations, type mappings, and allowed methods all have static definitions. This does not execute arbitrary user C#, and must not silently fall back to raw SQL concatenation or full client-side filtering. Exposing IQueryable requires API usability experiments and review of the translation-capability contract.

## 5. Domain Questions and Output Interfaces That Must Be Completed

These are independent research boundaries that may start in parallel; formal IDs are assigned by Plan's research graph. Each first produces evidence and candidate contracts, after which the corresponding owner in the documentation graph prepares specifications and development tasks.

| Question key | Research question | Evidence/experiments | Output to Design / Plan |
| --- | --- | --- | --- |
| DB-Q01 | Equivalent Npgsql and SQLx features and cross-language costs | Pinned-version connection, pool, execution, cancellation, parameter, read, and release call chains | Provider support matrix; decision on introducing Rust and budgets awaiting measurement |
| DB-Q02 | Threading and cancellation semantics of SQLite approaches | Microsoft.Data.Sqlite, SQLitePCL.raw, rusqlite, SQLx SQLite worker, and SQLite C API | Thread affinity, busy locking, interrupt, WAL, checkpoint contracts |
| DB-Q03 | When transactions and savepoints permit a connection to return to the pool | Complete commit/rollback/drop/pool/reset/disconnection state machine | State transitions, unknown commit outcomes, synchronous/asynchronous cleanup tasks |
| DB-Q04 | How bulk and streaming reads avoid per-element FFI | Row/batch/columnar candidates and experiments with real data distributions | Buffer/row lifetime, copy counts, bulk ABI; do not mandate Arrow in advance |
| DB-Q05 | How schema and migrations deploy independently | Transactional DDL, migration locks, checksums, failure recovery, and permissions | Version compatibility, reentrant migrations, rollback/roll-forward rules |
| ORM-Q01 | Natural C# query surface and syntax that can be rejected | User examples of a compile-time LINQ subset, explicit generated methods, and Fluent IR | Supported/rejected syntax table, diagnostic codes, alternative entry points without dynamic code |
| ORM-Q02 | How to validate SQL semantics | Differences in null/empty sets/joins/aggregation/pagination/collation/time/numbers | Provider differences table, SQL golden tests + real-database differential tests |
| ORM-Q03 | Metadata/mapping and result lifetimes | Nullable values, projections, value conversions, concurrent enumeration, exceptions midway | Static descriptors, materializers, release contracts |
| ORM-Q04 | How caching and precompilation are versioned | Experiments with schema, provider, parameter shapes, generic combinations, and generated code size | Cache keys, invalidation, build incrementality, and basis for size limits |
| SRV-Q01 | Which requirements Kestrel meets and when an additional Engine adds value | Benchmarks with identical TLS, connection reuse, payloads, business logic, and database access | Server capability boundaries, equivalent experiments, and selection ADR |
| SRV-Q02 | How Rust request adaptation and streaming backpressure form a complete protocol | Complete request/response buffer, header, cancellation, thread callback, and shutdown chains | Request tokens, consumption acknowledgment, budgets, drain state machine |
| SRV-Q03 | How gRPC/MCP compose without entering Core | Official SDKs, serialization, streaming methods, tool-registration AOT experiments | Separate protocol adapters, version matrices, and diagnostics |
| SRV-Q04 | Who owns TLS, authentication, and observability | Kestrel/.NET and Rust native TLS, trace context, logging models | Ownership, certificate updates, disabling sensitive parameters, sampling overhead |
| E2E-Q01 | Whether database and server can maintain end-to-end resource boundaries | Accounting/order-style transactional reference workloads without business dependencies | Reference application design, failure matrix, and three-approach benchmarks |

The recommended reference application uses a small, verifiable resource-reservation or inventory-transaction model: record creation, idempotency keys, conditional updates, pagination/streaming queries, covering write conflicts and commit uncertainty. This model serves validation only and introduces no downstream business protocol into the framework.

## 6. Domain Invariants and Validation Obligations

The following requirements are independent of candidate implementations and await formalization; they do not indicate completed proofs:

1. **Exclusive connection use**: a connection used by one protocol interaction must not simultaneously be reused by an incompatible transaction/reader; if a provider supports multiplexing, its compatibility boundaries with transactions, streaming, and session state must be explicit.
2. **Transaction terminal state**: a transaction records at most one confirmed terminal state. Unknown must not masquerade as RolledBack; without protocol confirmation, neither committed nor uncommitted may be claimed.
3. **Result validity period**: every read requires valid leases for its backing buffer and parent reader. Early enumeration exit, exceptions, and cancellation all eventually release the leases.
4. **SQL parameter isolation**: user data may enter only value parameters; identifiers and syntax fragments come from validated static or controlled sets. Parameter order, types, and null markers must agree.
5. **Query equivalence**: require `GeneratedQuery(D, p) = ReferenceSQL(D, p)` only within a declared semantic domain; that domain must state assumptions about collation, timezone, null, overflow, floating-point NaN, ordering tie-breaks, and similar factors.
6. **Unique completion**: each cross-language request/query operation reaches final completion at most once; races between cancellation requests and result arrival must not consume a result or release a context twice.
7. **Resource bounds**: if active request counts, queued bytes, concurrent materializers, and native pool sizes are bounded, provide the composition and calculation of the memory budget; limiting channel item counts alone is not a proof for the entire system.
8. **Shutdown quiescence**: after shutdown/drain is declared complete, no callback may enter referencing a released context, and no cleanup operation may remain that requires an already-stopped executor to complete.

Commit/cancellation/cleanup state transitions and callback cessation protocols are suitable for model checking; SQL semantics are better suited to property tests and real PostgreSQL/SQLite differential tests; native memory boundaries suit fuzzing, sanitizers, and corresponding Rust tools. SQL golden text snapshots cannot replace actual execution semantics, and a stress test with no failures cannot prove that all races have been resolved.

## 7. Minimum Experiment Matrix (Proposed, Not Yet Executed)

| Scenario | Results that must be observed | Baselines/failures |
| --- | --- | --- |
| AOT connections and mapping | Actually published binaries successfully connect, bind, read, and close | Separate Windows/Linux execution; each RID recorded independently |
| Unsupported query expressions | Explicit compilation error or explicit alternative path | Private types, captured state, arbitrary method calls, dynamic members |
| SQL semantics | Consistent results in fixed test databases | null, empty sets, left join, aggregation, decimal, timezones, collation |
| Connection pool exhaustion | Bounded waiting and restored capacity after cancellation | Connections held without release, authentication failure, network rejection |
| Query cancellation races | Exactly one completion result; connection can be cleaned up or discarded | cancel before send / during read / after completion |
| Transaction failure | No incorrect commit; Unknown not treated as rollback | statement timeout, deadlock, disconnection, lost COMMIT response |
| Early exit from streaming | Reader, connection, native buffer, and GCHandle return to baseline | break after one row, materializer throws, client disconnects |
| Bulk reads/writes | Explainable throughput and copy/allocation accounting | Small/large rows, binary large objects, UTF-8, nullable values |
| Migration | Schema results agree with the version ledger | Concurrent startup, interrupted execution, insufficient permissions, nontransactional DDL |
| HTTP flow control | Slow clients cannot cause unbounded memory growth | Slow reads, slow writes, oversized headers/bodies, HTTP/2 multiple streams |
| Server shutdown | Drain terminates after admission stops; resources reach zero or the agreed state | Active transactions, delayed callbacks, pending flush, long-lived connections |
| Protocol adapters | gRPC/MCP paths actually run under AOT | Serialization, stream cancellation, error mapping, and version differences |
| End-to-end workloads | Reproducible CPU/RSS/allocations/throughput/P95/P99/error rates | Identical protocols, data, indexes, TLS, features, and machines for all three approaches |

Performance thresholds must be determined by baselines and application goals. This round sets no arbitrary numbers such as "30% faster" or "RSS below 50 MB." Test records should also include the concurrency and queueing state corresponding to throughput, cold/warm starts, duration, repetition count, confidence-interval method, load-generator saturation checks, and error rates; otherwise latency percentiles can be misleading.

## 8. Expanded Source Inventory and Priorities

"Read" applies only to the scope declared in sections 2 and 3 and sources.json. Candidate paths below without pinned versions are research entry points, not evidence of completed reading.

| Priority | Project/primary entry point | Problem to solve | Next source entry points and status |
| --- | --- | --- | --- |
| P0 | [Npgsql](https://github.com/npgsql/npgsql) | Pure-C# PostgreSQL baseline | `NpgsqlCommand`, `NpgsqlConnector`, `PoolingDataSource`, type resolvers; directories/file names located, implementation bodies unread |
| P0 | [SQLx](https://github.com/transact-rs/sqlx) | Optional Rust driver engine | `sqlx-core/src/pool/`, postgres executor/connection, `sqlx-sqlite` worker; transactions partially read |
| P0 | [DapperAOT](https://github.com/DapperLib/DapperAOT) | Static parameter and mapping generation | Generation entry points/snapshots read; continue with `CommandT.Query`, `AsyncQueryState`, and negative diagnostic tests |
| P0 | [EF Core](https://github.com/dotnet/efcore) | Query semantics and precompilation | Entry points read; continue with relational query translator, SQL nullability, compiled models, and provider tests |
| P0 | [ASP.NET Core](https://github.com/dotnet/aspnetcore) | C# Native AOT server baseline | Kestrel, RequestDelegateGenerator, Pipelines, connection management, and stream tests |
| P0 | [Tokio](https://github.com/tokio-rs/tokio), [hyper](https://github.com/hyperium/hyper), [hyper-util](https://github.com/hyperium/hyper-util) | Rust server/runtime costs and shutdown | Some source read; continue with body flow control, connection tasks, executors, TLS adapters, and shutdown tests |
| P1 | [linq2db](https://github.com/linq2db/linq2db) | Multi-database SQL translation and diagnostics | Internal LINQ builders, expression compilation, and mappers; only repository/official discussion inspection in this round |
| P1 | [SeaQuery](https://github.com/SeaQL/sea-query) | Parameterizable query IR and dialects | `src/backend`, `src/query`, `src/value` directories actually located; contents unread |
| P1 | [SeaORM](https://github.com/SeaQL/sea-orm) | Rust ORM-layer responsibilities and transactions/streaming | `src/database/transaction.rs`, `stream`, `statement.rs` paths located; contents unread |
| P1 | [Microsoft.Data.Sqlite](https://github.com/dotnet/efcore/tree/main/src/Microsoft.Data.Sqlite.Core), [SQLitePCL.raw](https://github.com/ericsink/SQLitePCL.raw) | Minimal C# native SQLite binding baseline | connection/command/reader, native library loading; version pinning and reading pending |
| P1 | [rusqlite](https://github.com/rusqlite/rusqlite), [SQLite C API](https://www.sqlite.org/c3ref/intro.html) | Synchronous SQLite engines and thread/interrupt behavior | connection, statement, transaction, unlock/interrupt; investigation pending |
| P1 | [official PostgreSQL protocol](https://www.postgresql.org/docs/current/protocol.html) | cancellation, Sync, transaction state, and error recovery | extended query, CancelRequest, ReadyForQuery; server-version pinning pending |
| P1 | [grpc-dotnet](https://github.com/grpc/grpc-dotnet), [MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) | Protocol adapters, AOT-generated registration, and serialization | server binding/streaming/serialization/transport; source pinning pending |
| P1 | [System.Text.Json/runtime](https://github.com/dotnet/runtime), [OpenTelemetry .NET](https://github.com/open-telemetry/opentelemetry-dotnet) | Static serialization and observability overhead | source generation, diagnostics, metrics/traces AOT; reading pending |
| P2 | [Apache Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) | Whether bulk data exchange is worth standardizing | Evaluate lifetime, columnar conversion, and dependency costs; do not presuppose it as the database ABI |
| P2 | [Testcontainers .NET](https://github.com/testcontainers/testcontainers-dotnet), [Toxiproxy](https://github.com/Shopify/toxiproxy) | Reproducible database/network failures | Test-tool candidates only, outside the product runtime; Windows/Linux capability adaptation pending |

Every added project must explain which custom development work it replaces and what dependency/license and update costs it introduces. A longer candidate list must not by itself increase the number of formal product modules.

## 9. License and Reuse Records

- Npgsql: the pinned LICENSE was actually read; obligations to retain its copyright and license text enter the supply-chain topic.
- DapperAOT: the pinned `License.txt` was actually read; the tool declares Apache 2.0, with additional restrictions on name/logo use. GitHub metadata returns only NOASSERTION, so automatic classification alone is insufficient.
- SQLx: the pinned Cargo.toml declares MIT OR Apache-2.0; both licenses are present in the repository. The dependency tree still requires separate investigation.
- ASP.NET Core, EF Core: the files read contain MIT headers; the audit of all transitive dependencies and embedded third-party code is incomplete.
- hyper: the pinned Cargo.toml declares MIT; Tokio's license was not read in this round and remains pending verification.

This delivery stores only research summaries and links; it neither copies large passages of external product source code nor decides which code to bring into NativeWeave.

## 10. Current Evidence Gaps and Cross-Review Questions

1. The latest-version topic should confirm the selected stable language features and framework versions; in particular, older pinned EF/Dapper implementations read here must not be treated as facts about future versions.
2. The ABI/ownership topic should review release ordering for SQLx deferred rollback, streaming readers, and parent connections; if Core does not support the required lease/drain behavior, revise the scoped contract rather than adding a global runtime.
3. The generator topic should demonstrate complete diagnostics for unsupported queries, incremental-build consistency, and public strongly typed APIs; there is no acceptance shortcut equating a generator reference with AOT safety.
4. The concurrency topic should examine interactions between callback completion, cancellation registration disposal, executor shutdown, and .NET continuations; arbitrary C# user code must not execute while native locks are held.
5. The server topic needs complete Kestrel and Rust request paths; this round's single PipeWriter class or hyper method must not serve as the conclusion of a complete architecture comparison.
6. The performance topic must provide complete-workload experiments; without performance data, maintainability benefits must still be assessed from actual code/configuration differences.
7. The release topic must inspect combinations of NuGet/RID/native dependencies, TLS backends, OS ABIs, configurations, and database versions; every formally supported platform requires actual builds and execution.
8. An independent reviewer should sample the pinned-SHA evidence to check that it supports each conclusion, explicitly distinguishing "test source read" from "executed and passed."

**Deliverable status for this round**: research boundaries, candidate comparisons, and 7 pieces of partial source evidence have been established; phase B's formal public API, database choices, ORM query subset, server-engine selection, and performance commitments remain unaccepted. They are explicit inputs to the next round of parallel research and documentation, rather than being deferred as vague future matters.

