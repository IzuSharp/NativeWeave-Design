# D14 — Rust Database Engine and precompiled application boundary

Contract: **C-DB-001@0.4.0**. Status: design candidate; the registry records exact-content independent review and acceptance; product implementation/release gates remain in Delivery. Supersedes DB-D004/DB-D005/DB-D006's ordinary SeaORM model-build assumptions, not the historical source facts. Evidence: [R25](../research/topics/R25/source-driven-seaquery.md), [recovered prototype](../research/source-driven-evidence/README.md), existing R19–R22. Transaction safety remains [D15](transactions-and-pooling.md).

## Public API refinement 0.4.0

The exact public declarations and complete native operation inventory are now
[Database/ORM API 0.4.0](../api/database.md), its
[coverage matrix](../api/database-coverage.json), and
[Database.cs](../../experiments/public-api/NativeWeave.Api.Design/Database.cs).
They replace earlier provisional signature spellings; the lifecycle, native-source
findings and historical experiment identities below remain normative within that
explicit scope. Native AOT fixture compilation is separate from product execution.
Fresh exact-content review is required; prior accepted versions remain immutable.


## 1. Architecture and selection

Database lower layers are mandatory Rust. After comparing SeaQuery, SQLx, SeaORM static entities and its actual public dynamic projection/loader boundaries, the selected ordinary design is a maintainer-precompiled **SeaQuery 1.0.2 + SQLx 0.9.0** Engine. SeaQuery owns native query construction and dialects; SQLx owns execution, connections, pools and protocol. NativeWeave's Rust Adapter supplies bounded admission, fallible codecs, capability checks, transaction/cleanup coordination and explicit ORM policies. C# supplies business types, typed Fluent calls, static metadata/DTO code and interop; no C# SQL dialect engine or managed-provider fallback.

SeaORM public ModelType/FieldType/QueryResult dynamic projections are a real no-per-entity-build integration, demonstrated by the database-completion fixture. Their result shape must be checked before nullable decoding. Static SeaORM Entity/ActiveModel/Relation integration remains a specialized profile with a separately compiled model package. Its build coupling is not a universal property of Rust database access. Ordinary Student/User entities using supported codecs/operators vary as runtime metadata and C# code, not generated Rust. No Cargo or CI-built application Engine is required on that path. New native codecs/operators/providers can require a new maintainer Engine version.

Core has no SQL AST, pool or mandatory global Tokio runtime. Managed drivers remain external comparisons. Source reuse and consumer experience justify this design. Formal research/design acceptance is recorded by the independent review and registry; no product execution or performance superiority follows from that acceptance.

## 2. Modules and implementation boundaries

B01 owns domain interfaces/descriptors/limits/errors and the typed C# facade, never a managed product provider. B02/B03 implement Rust PostgreSQL/SQLite adapters. B04 is the required native host, resource admission and runtime/session/pool ownership. B05/B06/B07 own native transactions, bounded streams and fallible codecs. B08 owns Rust migration execution with a C# administration surface. B09/B10 own thin binding metadata and optional static C# generation. B11/B12/B13/B14 own native query/binding, DTO materialization, runtime Fluent composition and explicit Rust relation/CAS policies.

Use disjoint implementation scopes and versioned driver fixtures. Do not create a host/provider cycle or wait for the entire ORM before implementing independent codecs. B21/B22 verify the actual combined implementation.

## 3. Public API and ownership

Design consumer shape, with exact declarations in the public API fixture:
```csharp
await using DataSource source = PostgreSqlDataSource.Create(connectionString);
await using DataSession session = await source.OpenSessionAsync(ct);
using var query = session.From(Students.Table);
IReadOnlyList<Student> rows = await query
    .WhereGreaterThanOrEqual(Students.Age, minAge).Take(100)
    .SelectAll().ToListAsync(ct);
```
The recovered experiment executed a narrower synchronous static-descriptor API. DataSource owns its Engine-local runtime/pool; Session holds one physical connection lease. Transactions/cursors/operations retain parent owners. A Session admits at most one user command/reader/COPY at a time, rejecting concurrency rather than silently changing transaction order. Cleanup admission is independent of the closed public gate.

SafeHandle lifetime protection is separate from the mutable builder's single-writer gate. Sealing freezes query shape and parameter snapshots. Native streams remain inside native async operations that hold connection ownership; do not transmute lifetimes to manufacture a self-referential FFI cursor. Disposal cannot invalidate in-flight callbacks/results.

CloseAsync(deadline) stops admission and waits for retirement up to the deadline. Pending cleanup retains roots, owners and budgets; DisposeAsync joins actual safety. A bounded HTTP path must not follow Pending close with an unconditional indefinite await-using join. Public task outcome, native retirement, connection reuse and remote transaction effect remain separate.

## 4. ABI and operation lifecycle

Consume existing lifetime/callback/async/error contracts and the eventual accepted ABI/buffer layouts. Do not export Rust Vec/String/Expr/Value/traits or CLR layouts. Native modules remain alive while objects/operations/callbacks/buffers can use them. Instance close is not module unload.

Operations cover datasource/session open, builder create/mutate/seal, execute, cursor fetch, transaction begin/commit/rollback and close/drain. Async operations retain create→start, terminal notification, exactly-once take_result and separate retirement. Cancellation requests cannot block on a SQLite lock, channel send or network action. SafeHandle release is not an I/O join.

Direct native-builder calls are the reference route. Batched native operations are a measured optimization candidate requiring bounded validation and partial-mutation failure semantics, not a predetermined universal IR. Expert raw SQL is a separate parameterized capability; never silently fall back to it.

Metadata hashes identify runtime table/column/projection declarations and cache content, not entities compiled into a schema-specific library. Validate enabled native codecs/operators and actual metadata/database compatibility. New application metadata does not by itself change the native Engine binary.

### 4.1 db-wire/1 result and parameter transport

The public API refinement fixes the scalar bytes, NULL/nullable bits, payload/profile
IDs, parameter names and shape hashes in [API section9.1.2](../api/database.md#912-exact-db-wire-scalar-and-identity-encoding).
Those rules specialize the retained container below; B01/B07 must generate and
round-trip the same canonical bytes independently on both sides. They do not freeze
a general query-operation IR: query operations remain the typed native builder calls.


The following is a field serialization format, **not C struct memory layout**; integers are little-endian, with no implicit padding. B01 generates codecs for both sides, and D07 owns the outer bytes. The fixed header is 96 bytes: magic `NWDB`(4), version u16, payload_kind u16, header_bytes u32, flags u32, total_bytes u64, metadata_hash[32], record_count u32, descriptor_count u32, entity_id u32, query_id u32, projection_id u32, semantic_profile_id u32, descriptor_offset u64, payload_offset u64. All reserved flags are 0; unknown required versions are rejected. descriptor_offset must be 96 (8-byte aligned); the descriptor table immediately follows the header.

Ordinary parameter/row-batch payloads use a row-major cell table. `cell_table_offset = descriptor_offset + 16*descriptor_count`, `cell_count = record_count*descriptor_count`, and the cell table occupies `24*cell_count` contiguous bytes; `payload_offset = cell_table_offset + 24*cell_count`. All these values are checked and 8-byte aligned. The header, descriptor table and cell table are each contiguous and mutually non-overlapping; cell data may appear only at or beyond the payload start, and total_bytes must not be less than payload_offset. A column descriptor is 16 bytes: column_or_parameter_id u32, logical_tag u16, flags u16, codec_id u32, reserved u32. Each cell is 24 bytes: logical_tag u16, flags u16, codec_id u32, absolute_data_offset u64, byte_length u64; with the NULL flag, offset/length must be 0. Fixed-width value lengths must match the codec exactly; UTF-8 is strictly validated, and variable payloads must not point into the header/descriptor/cell tables. cell_count=`record_count*descriptor_count`, table lengths, offset+length and alignment are all checked. Every nonempty cell-data range is non-overlapping; aliases into the header/descriptor/cell tables or another nonempty cell are rejected. Payloads may be tightly packed without natural alignment per value; codecs read bytes rather than dereference unaligned typed pointers. Row-batch column IDs/shape must match the generated projection. Static parameters use record_count=1; with no parameters, descriptor_count=0.



This retained header is the versioned value/result transport refined by API section9.1.2, not a general query-operation protocol. Its metadata_hash meaning supersedes compiled-entity inventory semantics and requires explicit compatibility versioning. Native builders may use direct typed ABI methods instead. Reject unknown required versions/tags, oversized allocation, overlapping payload regions, malformed UTF-8 and profile mismatch before submission. B09 compares representations without reimplementing SQL semantics.

## 5. Type semantics and Rust database codecs


C# codecs convert only between CLR values and db-wire values; Rust metadata/drivers determine the interpretation of database SQL types, parameter types and rows→explicit result projections. Corresponding mismatches fail before sending or on the first result-shape validation; there is no fallback to `object[]`, reflection setters or automatic string conversion.

| Logical value | PostgreSQL | SQLite and portable limitations |
| --- | --- | --- |
| signed integers | int2/int4/int8, checked narrowing | INTEGER; reject overflowed REAL values masquerading as integers |
| bool | boolean | INTEGER0/1 + schema CHECK; reject other values |
| string | text/varchar; UTF-8 parameters | TEXT; explicit collation, without claiming all .NET string semantics |
| Guid | UUID, wire 16 bytes in RFC4122 order | 16-byte BLOB in the same order; historical mixed endianness prohibited |
| DateOnly | date | Fixed ISO date TEXT, with explicit range/calendar |
| UTC instant | timestamptz | Unix microseconds INTEGER; reject sub-microsecond precision loss by default |
| decimal | Explicit numeric(p,s), range/rounding policy | Exact TEXT for round trips only; comparable money uses fixed-scale checked Int64 |
| bytes | bytea | BLOB; ordinary DTOs own copies |
| JSON | Rust metadata maps JSON columns; wire UTF-8 text | SQLite JSON capability profile; C# typed DTOs require explicit static JsonTypeInfo |
| enum/custom | Explicit integer/text mapping within precompiled capabilities; new native codecs require another Engine version | Explicit integer/text mapping; unknown types rejected |

Npgsql date/UUID source is comparison evidence only and does not directly prove equivalence of SQLx / the NativeWeave Rust adapter; R22 retains the original evidence, and B07 must actually test the Rust route for each type. nullable means SQL NULL; empty strings/default(T)/empty arrays are not substitutes. NaN/Infinity, timezone infinity values, wide-range numeric, arrays and composite types are listed as separate provider-specific capabilities; they do not automatically enter the cross-provider equivalence domain.

## 6. Bounded resources, streams and costs

The following values are configurable design starting points, not measured capacity or performance conclusions: per DataSource, at most 32 leased Sessions, 128 waiters and a 15-second admission timeout; buffered results are limited to 10,000 rows/16MiB of charged data; each fetch to 256 rows/1MiB; the general field limit is 8MiB, but an inline cell must also fit within the current max-batch-bytes. Oversized values return LargeValueRequiresStreaming rather than silently exceeding the batch limit. Single-field incremental BLOB streaming is an explicit future capability; v1 rejects oversized inline fields and does not pretend ordinary SQLx row decoding supplies it. Every limit is finite, configurable and checked; D16/D17 separately limit total parameter bytes/collection elements.

A Rust cursor permits at most one fetch at a time and one owned batch not yet taken; each batch's byte permit transfers with its actual owner and is returned after C# mapping completes. Prefetch is off by default; enabling it requires explicit total-page and byte budgets. Backpressure stops producer progress; cancellation/consumer break/decoder exceptions stop admission, request stop, join the stream, perform protocol cleanup and then retire under D06. A result owner must not leak because the user does not await the Task.

SQLx rows, the wire buffer and C# DTOs may coexist; budgets must cover logical bytes in use at every layer and record copy/FFI counts. SQLx internal buffers, allocator overhead, thread stacks and GC costs are measured separately; a logical budget is not a strict RSS upper bound. Result conversion and necessary asynchronous adaptation have costs; zero allocation must not be promised without evidence. The initial version prioritizes provable correctness; B23 measures throughput, P95/P99, CPU, native/managed allocations/RSS, build time, codegen size and the amount of developer-written code.

## 7. SQLite execution and cancellation

The ordinary route uses the Rust SQLx SQLite adapter and no longer ships a Microsoft.Data.Sqlite adapter. SQLx0.9 already has a dedicated OS thread, bounded command channel and row channel per connection; do not unconditionally wrap it in Task.Run or an unlimited thread pool. Connection limits also bound thread counts, and queues with finite item counts additionally need byte budgets. WAL, foreign_keys, busy_timeout, synchronous, journal mode and threading build options enter the profile.

Cancellation: rejection is possible before dispatch; once execution starts, a native-only progress handler installed before execution reads an independent operation atomic flag. request_cancel only stores the flag and does not acquire the SQLite handle lock; the handler does not call managed code, allocate or panic. After completion/cleanup is confirmed, remove the handler or safely change its generation before assigning the same connection to the next operation. Verify SQLx public lock_handle/progress APIs against the pinned version; do not wait for a lock to install the handler only when cancellation is requested.

Progress interruption is cooperative and does not promise a hard deadline for arbitrary sqlite3_step, busy waits, filesystem or extension code. Dropping a future/row receiver is not evidence that an arbitrary step has terminated. SQLx worker `start_rollback` / `shutdown` contains synchronous bounded-channel sends, which must run on dedicated cleanup/coordinator paths and not in ReleaseHandle/non-blocking request_stop/try_retire. Drop/reset/close_hard alone does not prove worker exit; if execution continues at the deadline, retain the worker, buffers and budget, mark CleanupPending, and do not fabricate safe release.

SQLx rolls back when BEGIN succeeds but its ack is lost; when COMMIT/ROLLBACK succeeds but its ack is lost, state suppresses duplicate Drop rollback. NativeWeave still classifies outcomes according to its own commit admission and observations, without mistaking these internal compensations for confirmation received by the business caller. See R20/R21 for concrete proofs and counterexamples; the related upstream tests were read only, not executed.

## 8. PostgreSQL execution and session recovery

Rust SQLx PgPool/connections execute parameterized statements built by SeaQuery. Generated SQL and the explicit fallible parameter binder follow the same ownership path; Arguments::add errors must not be discarded, nor may unsigned narrowing use unwrap. SQLx0.9 AssertSqlSafe may be used only on capability/type-checked Rust SeaQuery output or at an explicitly audited expert-SQL boundary; it is not SQL sanitization.

Ordinary cancellation is a request rather than an early Task.Canceled result; the SQLx public paths inspected have not been proven to provide an equivalent to Npgsql's cancellation token, so v1 does not promise immediate remote CancelRequest. Check the flag before starting; during execution, request stop through a fixed session/transaction statement_timeout and controlled transport-termination policy, with final state and cleanup determined by provider results. Any future protocol CancelRequest requires separate proofs for backend keys/generations/new-connection races; do not invent an API. This decision does not prevent design completion; B02 verifies cancellation, timeout, long-statement and cleanup boundaries.

SessionExecutor retains the connection until the stream and transaction actually end; reuse requires explicit absence of unconsumed results/in-flight cancellation, a terminated transaction and restored session state. SQLx's return-to-pool ping may flush pending rollback; known deferred cleanup differs from unknown protocol damage. Unknown damage is removed through public PoolConnection::close/close_on_drop; close_on_drop only schedules the action, and cleanup completion still requires tracking. `detach` releases the pool permit and must not conceal connections still being cleaned up or exceed the total budget. See D15 for complete states.



## 9. Migration, precompiled packages and compatibility

The Engine manifest binds ABI, capability/codec profile, RID, toolchain, locked dependencies and native asset hash. Application metadata, query shape and migration history are separately versioned; see D10. Ordinary entity changes require at most static C# metadata/DTO regeneration, never default Cargo. Registry crates and source commits retain separate provenance until checked.

Migrations are explicit Rust administrative operations, not speculative startup schema-sync. Immutable ID/content hash/provider/from-to version/transaction mode enter the ledger. PostgreSQL advisory locking or SQLite explicit writer/deployment admission serializes migration owners. Transactional DDL and ledger commit together; nontransactional DDL uses staged resumable checks. Same ID/different hash, missing migration, inadequate permission and incompatible schema fail explicitly. Destructive down-migration is not the production default.



An atomic SQLite migration batch must use SQLx's public `Connection::begin_with("BEGIN IMMEDIATE")` to create a tracked `Transaction`, then call `Migrator::run(&mut *tx)`. First reject unsupported nontransactional entries using `migrator.iter().any(|m| m.no_tx)`, then admit the operation and acquire the writer lock. On success, only `tx.commit().await` ends the outer batch; on migration error, explicitly call `tx.rollback().await`, and isolate and close the dedicated connection if rollback fails. Do not first call `query("BEGIN IMMEDIATE").execute(&mut conn)`: raw SQL does not update SQLx transaction depth, so a subsequent BEGIN inside Migrator will fail.

```rust
// Illustrative public SQLx 0.9.0 chain; domain error/cleanup mapping remains B08.
use sqlx::Connection;
if migrator.iter().any(|m| m.no_tx) {
    return Err(UnsupportedNonTransactionalMigration);
}
let mut tx = conn.begin_with("BEGIN IMMEDIATE").await?;
match migrator.run(&mut *tx).await {
    Ok(()) => tx.commit().await?,
    Err(error) => {
        // If rollback fails, retain both errors and retire this dedicated connection.
        let rollback = tx.rollback().await;
        return Err(map_migration_failure(error, rollback));
    }
}
```

The independent reviewer actually ran three Linux Rust regressions: the raw BEGIN counterexample, tracked outer rollback/commit, and whole-batch rollback after the second migration fails. Schema and migration ledger are rolled back together, and inner savepoints do not commit the outer transaction. See [independent three-case regression](../../verification/interop-completion/db-review-migration/result.json). This proves the public call chain and finite atomicity, without replacing B08's cross-process contention, Windows, crash/restart and product AOT verification; the example error names and map_migration_failure illustrate domain mapping and are not released APIs. That mapping must preserve both the original migration error and rollback error and require isolation/closure of a connection that has not been safely cleaned up.

## 10. Source-driven failure gates and acceptance

Reject SQLite row-lock/SELECT INTO/SEARCH-CYCLE requests that the pinned renderer silently ignores. Catching panic cannot detect omitted semantics. Check CTE shape and values before native rendering. A fallible argument binder propagates every encoding error and checks narrowing; do not use discarded add errors or unsigned unwrap. Poison unsafe partial builder mutations and retain all live owners.

B01/B04 verify malformed metadata/length/shape fuzzing, ABI/RID/capability rejection and no managed product provider. B02/B03 verify actual Rust PG/SQLite into typed batches/DTOs, schema errors, cancellation, stream early stop and pool/worker cleanup. B05/B06 verify Unknown COMMIT, unconfirmed rollback, reuse versus retirement, decoder exceptions and huge fields. B07/B08 cover every codec negative and migration interruption. B09–B14 cover typed native query parity, metadata/DTO generation and bounded relation/CAS scope. B21–B24 cover Windows/Linux AOT, faults/soak, clean no-Rust and RID-free consumers, unchanged native hash after entity changes, and full-workload costs.

The recovered Linux SQLite AOT experiment is real but finite. Its JSON/fetch_all/per-call-runtime/raw-handle shortcuts are not the production streaming/pool/concurrency design. That recovered probe did not cover Windows or PostgreSQL faults; the later native PostgreSQL fault cases are recorded below. Production generator, cross-language async lifetime and hard resource bounds remain product verification obligations. Never suppress IL2026/IL3050 indiscriminately to manufacture acceptance.

## 11. Concrete native boundary and binding obligations

The following historical signature sketch explains the domain boundary; API 0.4.0 section 9 now supplies the exact versioned operation signatures. `nw_status`, opaque creating-engine pointers and `nw_bytes_view_v1` reuse D02/D07/D08; they do not introduce a second Core status enum or a universal SQL IR. The shown declarations are **design examples, not compiled product exports**. Operation create/start/take_result/retire/release follows D06.

```c
nw_status NW_CDECL nw_db_metadata_register(nw_db_source* source,
    nw_bytes_view_v1 descriptor, nw_db_metadata** out_metadata, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_create(nw_db_session* session,
    nw_db_metadata* metadata, uint32_t table_id, nw_db_query** out_query, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_query_seal(nw_db_query* query, nw_db_plan** out_plan, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_execute_create(nw_db_session* session,
    nw_db_plan* plan, nw_db_operation** out_operation, nw_error_info_v1* error);
nw_status NW_CDECL nw_db_operation_take_cursor(nw_db_operation* operation,
    nw_db_cursor** out_cursor, nw_error_info_v1* error);
```

Each output pointer is initialized to null; ownership transfers only on success.
Metadata input is borrowed for the call and copied/validated into bounded native
metadata before return. Registration is all-or-nothing and checks duplicate IDs,
names, codec/null/key/relation shape and capability profile. Query creation retains
metadata and its logical parent. A sealed plan is immutable; mutation cannot race
sealing. Execution owns a parameter snapshot and a session lease. The cursor returned
by successful take_result is an independent result owner; operation retirement may
not free it. Cursor fetch has one active native operation and returns owned batches.
Each release goes to the engine that created that owner. No caller can reinterpret
Rust Vec/Expr/Value or a managed object pointer as one of these exported structures.

| Entry family | Native work | Managed obligation | Failure rule |
| --- | --- | --- | --- |
| Metadata registration | Validate/copy descriptors and native codec registry | Supply generated or handwritten immutable descriptors | Reject missing/duplicate fields and unsupported codec; no partial registration |
| Typed query/expr calls | SeaQuery native methods under one-writer admission | Enforce entity/value typing and matching query/alias owner | Reject mixed owner, disposed/sealed/poisoned builder; never emulate in C# |
| Seal/execute | Freeze values, render natively, fallibly bind, submit SQLx future | Capture inputs before await; keep owner/control leases | Pre-dispatch errors have no DB effect; dispatched failures use D15 |
| Cursor/batch | SQLx stream, bounded transport and retirement | Static shape-checked DTO construction and finally release | No borrowed row across MoveNext; constructor errors close cursor safely |
| Administrative migration | SQLx Migrator and native DB transaction/lock | Explicit invocation, trusted migration bundle | Never auto-migrate on open; close dedicated connection on error |

Rust enums, memory layout and non-exhaustive upstream variants remain private. The
binding manifest enumerates each exported operation/version/capability and both-side
conformance tests. Typed direct calls are the baseline; a compact batching envelope
can be added when measured, without becoming a second query-semantic authority.

## 12. Source-confirmed shape, security and administration corrections

The completion study verified that SeaORM's `Option<T>` decoder treats SQLx
ColumnNotFound as None. Validate result count, unique aliases/ordinals and type shape
before any nullable mapping; missing and SQL NULL are separate facts. This rule
also applies to hand-written descriptors and expert SQL projections.

Remote PostgreSQL defaults to VerifyFull with declared root trust/hostname checks.
SQLx Prefer permits plaintext fallback and Require alone does not enforce the same
identity checks. A local/test plaintext profile is explicit and never silently
selected after TLS failure. Native driver features and TLS backend belong in the
package capability manifest and SBOM.

SQLx's migration engine already supplies applied-version/checksum/dirty detection
and transactional DDL/ledger work. Reuse it. PG migration locks are session advisory
locks and an early error may leave them held; use a dedicated administrative
connection and close it on error or timeout. SQLite migration lock/unlock are no-ops;
obtain native write serialization before ledger inspection and hold it through the
supported transactional batch, rather than assuming `Migrator::run(&pool)` serializes
all processes. Nontransactional maintenance is a separate explicit admin capability.

## 13. Research-design acceptance versus product verification

[R19–R25](../research/topics/R25/report.md), the exact [source manifest](../../verification/database-completion/source-inspection.json),
and the [finite native fixture](../../experiments/database-completion/README.md)
resolve the ordinary no-per-entity-Cargo architecture and expose concrete error cases.
Independent acceptance can approve these interfaces and constraints before Codex
implements them. B01–B14/B22–B24 still must pass their actual C# AOT, Windows/Linux,
TLS/auth, malformed-input, concurrency, fault, memory and performance obligations.
No successful native-only experiment is relabeled as completed product validation.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.


The optional SeaORM profile can inspect actual provider shape through public `QueryResult::try_as_pg_row` / `try_as_sqlite_row`, then SQLx `Row::columns` / `Column::type_info`. These borrowed views remain inside the row owner lifetime; no private field or fork is needed. Validate provider type compatibility rather than assuming a declared nullable field proves the result column exists; SQLite NULL/dynamic affinity still follows the explicit codec/null policy. The missing-column negative control remains part of the research fixture.
