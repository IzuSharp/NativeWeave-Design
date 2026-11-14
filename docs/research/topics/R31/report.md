# R31 — Reference Application, Idempotent Recovery, and Equivalent-Workload Validation

Date: 2026-11-12 (America/Los_Angeles). Original task packets/baselines/hashes and SQLite execution records remain traceable. Current baselines are Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a` and Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`; current architecture and research supplements were integrated by `/root/database_research`, with independent acceptance review awaiting recording. Actual new PG response-loss/concurrent-snapshot probes are in the [completion fixture](../../../../experiments/database-completion/README.md); execution status is established by [task-status](../../../../verification/database-completion/task-status.json) and original manifests. No C#/Rust product was implemented, and research execution is not equated with product AOT/long-workload acceptance. See [D20](../../../verification/reference-application.md) for the detailed specification.

## 1. Selected Reference Scenario

A generic multitenant work-item service covers idempotent creation, typed-query pagination, attachment upload/download, a transactional outbox, and authorized status queries. REST is the required minimal entry point; optional gRPC/MCP reuse the same C# application service. It validates phase A interop/generation/packaging together with phase B database/ORM/server, rather than assigning only a few abstract future tasks to phase B. ArcForges is only a document-organization reference and does not affect business schemas or architecture.

The product baseline is **Rust Server + C# application/typed Fluent/DTO + Rust Database/ORM Engine**. Rust Server owns network I/O, protocols, connections, streams, and backpressure; C# owns business Handlers. Kestrel remains only a separate functional/cost/performance comparator. The ordinary database path selects maintainer-precompiled SeaQuery+SQLx; ordinary C# entities use runtime metadata and static DTOs without requiring generated Rust Entities or Cargo recompilation. SeaORM dynamic projections are reusable capabilities supported by actual execution evidence, while static Entity/ActiveModel form a separately maintained specialized profile; exact boundaries follow D14/D16 rather than redoing ORM selection in R31.

C# does not rebuild SQL ASTs/dialects/a complex LINQ Provider; an optional SG generates static metadata rather than capturing entire method bodies each time. Npgsql, Microsoft.Data.Sqlite, and EF Core serve only as independent comparators. Rust foundations for Database and Server are established project goals; performance experiments optimize implementations rather than reopening an established goal as a binary choice.

Non-goals: completing the entire product now; claiming distributed exactly-once behavior across databases and external messaging/filesystems; expanding the database requirement into mandatory Rust for every module; proving Rust drivers, AOT, or production durability through one Python experiment.

## 2. Candidates and Choices

| Candidate | Conclusion and rationale |
| --- | --- |
| Unconditionally retry the original write after timeout | Rejected; COMMIT may already have taken effect, and an unseen response does not mean no execution |
| Commit an idempotency record before the business write | Not this version's atomic protocol; it requires a separate durable InProgress/lease/recovery state machine and cannot be assumed inherently atomic |
| Single transaction with unique(scope,key)+requesthash+business+result+outbox | Selected; the unique key linearizes same-key races, confirmed results are replayable, and different payloads cannot overwrite them |
| Send external events directly inside a DB transaction | Rejected; external effects do not roll back with the DB, and long IO also holds connections/locks |
| transactional outbox + stable eventID + consumer deduplication | Selected; explicitly acknowledges at-least-once external delivery |
| Prove rollback from one GET that does not find the operation | Rejected; the original commit may still be in progress or the current read may not see the result |

Transaction-effect states are defined by database D15/`transactions-and-pooling.md`, with public names aligned with the database author: WeaveDataSource→DataSession→DataTransaction; CommitAsync's request token affects only admission before sending, with an independent commit deadline after commit admission; Unknown exceptions retain RecoveryKey/CorrelationId, and Dispose does not rewrite Unknown. TransactionOptions.Isolation defaults to null, using the provider's declared default: PG ReadCommitted and ordinary SQLite Serializable semantics, with BEGIN mode selected by the SQLite profile. A RecoveryKey-only example must not force a PG isolation level.

Bounded HTTP responses use the explicit D14/D15 `DataSession.CloseAsync(deadline)`: the Session closes new business admission and requests/joins existing transaction/cursor cleanup; waiting may stop on Pending/Quarantined, but the Engine retains all parent leases, roots, and budgets without claiming local release or rewriting Unknown. Background work is limited to existing termination/cleanup, without retaining an ended HttpContext/request DI scope or starting new business work. Successful `DisposeAsync` must establish actual local safety; it continues joining while native code is not quiescent, so await using cannot express a finite HTTP wait. This interface refinement is a design decision; the SQLite prototype in this round did not validate that C#/Rust shutdown implementation.

## 3. Official PostgreSQL Semantics and Concrete Counterexamples

Official v18 [INSERT](https://www.postgresql.org/docs/18/sql-insert.html) and [TransactionIsolation](https://www.postgresql.org/docs/18/transaction-iso.html) §13.2.1 were read. The original evidence is versioned official documentation. Added PG18.0 research execution separately pins source/binaries and run manifests; document reading itself is not treated as execution.

On conflict, DO NOTHING may observe a concurrent transaction invisible to the current statement snapshot; RETURNING yields only rows actually inserted/updated. A same-statement CTE INSERT DO NOTHING plus SELECT therefore cannot be declared to always obtain the original record.

Under READCOMMITTED, the chosen first statement is INSERT ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id; if it returns 0 rows, a **subsequent** SELECT obtains a new snapshot, then compares the hash and returns the original response. Records are not physically deleted within the retention window; if the row is still absent or a timeout occurs, the outcome remains unconfirmed and bounded recovery proceeds under unique-key protection, without asserting rollback from an empty result. Other isolation levels/cleanup policies require separate validation. The SQLite path uses read-before-write under a short BEGIN IMMEDIATE, explicitly serializing writers rather than mechanically importing PG locking semantics.

The hash comes from a validated business DTO and semantic version, while scope comes from trusted tenant/principal/endpoint identities; the same key with a different hash returns 409. request_key and responsebytes have length bounds, and status queries also require authorization. While HTTP can still respond, Unknown returns 503 with stable operation-recovery information, rather than falsely reporting Created or a reliably queued 202. A client retaining only the original key can still safely retry the same-key/hash-protected flow.

## 4. Actual Research Prototype and Execution Records

[idempotency_experiment.py](idempotency_experiment.py) is an original minimal SQLite prototype from this round, using only the standard library and a temporary database cleaned up after exit. It is not a NativeWeave product API. `connect` enables foreign keys/synchronous FULL; setup uses WAL; every command uses a separate connection and BEGIN IMMEDIATE; hash comparison occurs inside the write transaction; operations/items/outbox share one COMMIT.

Actual execution command:

```text
python docs/research/topics/R31/idempotency_experiment.py > docs/research/topics/R31/experiment-result.json
```

The main process exited 0, with empty stderr. Environment: Python3.12.14, SQLite3.53.1, Linux6.18.57 x64/glibc2.41. To fully record D12 requirements, the final result was rerun through an instrumented wrapper; actual argv, UTC start/end times, and raw-stream hashes are in [run-manifest.json](run-manifest.json), without fabricating the first run's timing. Script SHA256 and stdout SHA256, expected subprocess exit17, and versions/OS/configuration are in evidence.run_manifest; the [original stdout](experiment-result.json) is retained in full.

| Actual assertion | Result |
| --- | --- |
| Replay with identical key/hash | Same operation_id and response; 1 row in each of the three tables |
| Same key, different hash | conflict; no additional business or outbox row |
| 4 independent connections concurrently using the same key | Exactly 1 created and 3 replay; all have the same operation_id |
| Simulated response loss after actual COMMIT | Replay through a new connection obtains the original durable result, without a second business effect |
| Subprocess `os._exit(17)` before COMMIT | Actually skips finally/rollback; a new connection sees no additions to the three tables, and subsequent creation with the same key succeeds normally |

At completion, operations/items/outbox each contain 4 rows. The experiment checks atomic result relationships, not throughput or latency; elapsed time is not a performance conclusion. Response loss is simulated by a program branch after COMMIT, not actual packet loss through a network proxy; process exit is not OS power loss or disk-controller fsync validation. The SQLite writer lock makes this counterexample reproducible but does not prove PG's MVCC concurrency implementation. Product C#/Rust, AOT, and cross-platform execution all remain not-run.

## 5. Concrete Application Implementation Boundaries

Attachments first stream to temporary files using disk credit, undergo hash/length validation and persistence, and are renamed as immutable blobs; a short DB transaction then commits references/results/outbox entries. Failure may leave bounded, garbage-collectable orphans, but must not commit a DB success pointing to a partially written file. GC must protect active uploads and recovery and account for retention; directory fsync/rename and Windows/Linux differences need actual fault tests. A blob hash is not a cross-tenant read credential.

The Outbox worker claims bounded batches and marks them after publication; a crash after publication causes duplicates, so the consumer oracle persistently deduplicates by event_id. Business transactions neither wait for client downloads nor call external publishers; slow responses must not hold DB leases indefinitely either. Pagination uses stable keyset(created_at,id) and does not promise consistent cross-page snapshots by default; consistent exports have separate deadline/lease profiles.

Application developers write ordinary C# typed models, Fluent queries, and async APIs, with no Rust/FFI or per-entity Cargo requirements. An optional C# SG generates static metadata/DTOs; ordinary Fluent calls reuse the native SeaQuery builder and SQLx execution. Dynamic filters first resolve allowed columns/operators; Rust then validates capabilities/parameters/tenant and resource boundaries. Business operation hashes/correlation values do not become unbounded metric labels.

## 6. Failure and Complete-Workload Evidence

B21 implements D20's complete minimal service, golden vectors, optional protocol facades, and reference consumer; B22 implements an independent oracle and controlled fault points: BEGIN/writes/before and after COMMIT/lost acknowledgment, PG restart, SQLite busy/disk full, pool reset, HTTP slow/abort, crash after outbox publication, crash between blob rename and DB commit, drain/retire, and others.

Model/property validation checks at least: at most one business effect per scope/key; atomic consistency of item/result/outbox; irreversible terminal states; Unknown does not become rollback through Dispose or an empty query; every owner is eventually released or explicitly quarantined. Fuzzing targets lengths/inputs/query IR/ABI, and actual multithreaded tests control race windows rather than relying only on sleep. Execute actual Windows/Linux AOT publications; 24h regressions and 72h release soaks check long-term resource slopes, steady plateaus, and failure recovery rather than reporting a single peak RSS.

The B23 product baseline is Rust Server + C# business Handlers/typed Fluent/DTO + Rust ORM / PostgreSQL/SQLite Engine. Pure C# Kestrel + Npgsql/Microsoft.Data.Sqlite (EF Core where applicable) is only an external managed baseline; a pure-Rust implementation is only an ecosystem/cross-language-cost comparator. Neither may be mislabeled as a NativeWeave managed-database product profile. TLS/HTTP profiles, schema/indexes/isolation/pools, datasets/caches, error ratios, durability, hardware resources, and sampling are identical. Use fixed arrival rates and record queueing, retaining p99/p99.9/raw histograms, CPU/op, GC/alloc/native/RSS/handles/copies/crossings. Mark nonexistent/untested combinations not-run rather than inferring actual benefits from microbenchmarks; performance thresholds depend on frozen baselines and product goals, with no invented percentages now. Evidence improves Rust DB and cannot silently remove product constraints; Rust Server foundations are established, and end-to-end evidence selects and optimizes concrete Rust combinations.

B24 accepts independent packages/RIDs/profiles, clean-machine execution, version rejection, upgrade/rollback, and SBOM/LICENSE. Every NativeWeave Server example must validate the Rust Server native library; database applications also validate the Rust DB native library and relevant phase A interop/AOT gates. Pure managed examples may only be separate external comparators and must not be labeled NativeWeave Server product profiles. Database/Server cores must be independently acceptable before combined validation; the reference application does not force all independent tasks to run serially.

## 7. Completion Recommendation and Cross-Review

The reference application scenario, transactional idempotency, Unknown recovery, and equivalent-performance methodology now have concrete designs; all implementation/production-validation obligations go to B21–B24, rather than keeping research open until the entire product ships. Current R31 research/design outputs are complete and have entered independent acceptance review: added Rust/SQLx PostgreSQL 18.0 real-database counterexamples were executed, including lost COMMIT acknowledgment and concurrent snapshots. Authors cannot declare accepted status themselves; the complete product, other candidate features, and long-term validation remain explicit Delivery obligations, rather than reasons to label completed research planned/partially_evidenced.

Cross-Review: database R21 checks Commit states and PG snapshots, R20 checks SQLite writer semantics; R26/R29 check request abort/stream budgets; R28 checks differing gRPC/MCP terminal states; R17 checks workload equivalence; R34 checks tenant/auth/hash/retention and error leakage. Potential counterexamples and affected files map concretely to D20 and related Delivery tasks, without adding a new meta-planning layer.

## 8. Added Research Closure and Explicit Subsequent Phases

`database-completion/tests/postgres.rs` captures two decisive counterexamples: a COMMIT response is discarded by a network proxy while a new connection observes the committed result; after synchronizing a concurrent unique-key conflict through actual pg_locks waiting, a same-statement CTE SELECT may return empty while the next statement obtains the original operation. The original R31 SQLite experiment's simulated response loss, actual process exit, and four-connection race results remain retained without double-counting. Other new PG/SQLite research in this round also covers protocol recovery, type loss, shape omissions, and migration locks, with actual execution scope traced through designated manifests.

D20/B21 connect both native Engines through one business-operation definition; ownership still composes each Engine's local runtime with the Core ABI, without building a giant global scheduler. B22/B23 retain obligations for product fault injection, actual C# AOT, long workloads, performance, and disk durability; these neither block research-level acceptance of idempotency/outbox/Unknown/interface design nor authorize formal product development now.

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
