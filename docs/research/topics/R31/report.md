# R31 — Reference application, idempotent recovery and equivalent-load validation

Date: 2026-11-12 (America/Los_Angeles). Original packet/baseline/hash and SQLite execution records remain traceable. Current baselines are Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a` and Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`; current architecture and supplemental research are integrated by `/root/database_research`, with independent acceptance review awaiting recording. Actual new PG response-loss/concurrent-snapshot probes are in the [completion fixture](../../../../experiments/database-completion/README.md); [task-status](../../../../verification/database-completion/task-status.json) and raw manifests determine execution status. No C#/Rust product is implemented; research execution is not product AOT/sustained-load acceptance. See [D20](../../../verification/reference-application.md) for the detailed specification.

## 1. Selected reference scenario

A general-purpose multitenant work-item service covers idempotent creation, typed-query pagination, attachment upload/download, transactional outbox and authorized status queries. REST is the required minimum entry point; optional gRPC/MCP reuse the same C# application service. It validates phase A interop/generation/packaging and phase B database/ORM/server together, rather than assigning phase B only a few abstract future tasks. ArcForges is a document-organization reference only and does not affect business schemas or architecture.

The product baseline is **Rust Server + C# application/typed Fluent/DTO + Rust Database/ORM Engine**. Rust Server owns network I/O, protocols, connections, streams and backpressure; C# owns business Handlers. Kestrel remains only an independent feature/cost/performance comparator. The ordinary database path selects maintainer-precompiled SeaQuery+SQLx; ordinary C# entities use runtime metadata and static DTOs without generating Rust Entities or recompiling with Cargo. SeaORM dynamic projection is a reusable capability with actual execution evidence, while static Entity/ActiveModel is a separately maintained dedicated profile; concrete boundaries follow D14/D16, without rebuilding ORM selection in R31.

C# does not reimplement SQL ASTs/dialects/complex LINQ Providers; an optional SG generates static metadata instead of capturing complete method bodies each time. Npgsql, Microsoft.Data.Sqlite and EF Core are independent comparators only. Rust lower layers for databases and servers are established project goals; performance experiments optimize implementation rather than reopening settled goals as alternatives.

Non-goals: completing the entire product now; claiming distributed exactly-once behavior across databases and external messages/filesystems; extending the database requirement into mandatory Rust for every module; proving Rust drivers, AOT or production durability through one Python experiment.

## 2. Candidates and selection

| Candidate | Conclusion and rationale |
| --- | --- |
| Unconditionally retry the original write after timeout | Rejected; COMMIT may already have taken effect, and an invisible response does not mean non-execution |
| Commit the idempotency record before performing the business write | Not this version's atomic protocol; it requires a separate durable InProgress/lease/recovery state machine and must not be presented as inherently atomic |
| One transaction with unique (scope,key)+request hash+business+result+outbox | Selected; the unique key linearizes same-key races, acknowledged results can be replayed and differing payloads cannot overwrite them |
| Send external events directly inside the DB transaction | Rejected; external effects do not roll back with the DB, and long-running IO retains connections/locks |
| Transactional outbox+stable event ID+consumer deduplication | Selected; honestly acknowledges at-least-once external delivery |
| Use one GET that finds no operation as proof of rollback | Rejected; the original commit may still be in progress or the current read may not see its result |

Transaction effect states are defined by database D15/`transactions-and-pooling.md`. Public names align with the database author: WeaveDataSource→DataSession→DataTransaction; CommitAsync's request token affects only pre-send admission, followed by an independent commit deadline once on the wire. Unknown exceptions retain RecoveryKey/CorrelationId, and Dispose does not rewrite Unknown. TransactionOptions.Isolation defaults to null and uses the provider-declared default: ReadCommitted for PG and ordinary Serializable semantics for SQLite, with BEGIN mode selected by the SQLite profile. A RecoveryKey-only example must not impose a PostgreSQL isolation level.

Bounded HTTP responses use the explicit `DataSession.CloseAsync(deadline)` from D14/D15: the Session closes admission of new business work and requests/joins existing transaction/cursor cleanup. Waiting may stop in Pending/Quarantined, but the Engine retains all parent leases, roots and budgets; it must not claim local release or rewrite Unknown. Background work is limited to existing termination/cleanup, without retaining an ended HttpContext/request DI scope or introducing business work. Successful `DisposeAsync` requires actual local safety and continues joining while native work is not quiescent, so await using cannot express a finite HTTP wait. This interface refinement is a design decision; this round's SQLite prototype did not validate the C#/Rust shutdown implementation.

## 3. Official PostgreSQL semantics and concrete counterexamples

Official v18 [INSERT](https://www.postgresql.org/docs/18/sql-insert.html) and [TransactionIsolation](https://www.postgresql.org/docs/18/transaction-iso.html) §13.2.1 were read. The original evidence is versioned official documentation. New PG18.0 research executions separately pin source/binaries and run manifests; reading documentation itself is not execution.

On conflict, DO NOTHING can see a concurrent transaction that is not yet visible to the current statement snapshot; RETURNING yields only rows actually inserted/updated. A same-statement CTE INSERT DO NOTHING plus SELECT therefore cannot be claimed to always retrieve the original record.

Select READCOMMITTED with an initial INSERT ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id; on 0 rows, use the **next** SELECT to obtain a new snapshot, compare the hash and return the original response. Records are not physically deleted within the retention window; if no row is still visible or a timeout occurs, keep the outcome unconfirmed and perform bounded recovery under unique-key protection rather than asserting rollback from an empty result. Other isolation levels/cleanup strategies require separate validation. The SQLite path uses read-before-write inside a short BEGIN IMMEDIATE, explicitly serializing writers rather than mechanically transplanting PG locking semantics.

The hash comes from a validated business DTO and semantic version, and the scope comes from trusted tenant/principal/endpoint values; the same key with a different hash returns 409. request_key and response bytes have length bounds; status queries require authorization too. If HTTP can still respond, Unknown returns 503 with stable operation recovery information, without falsely claiming Created or a reliably queued 202. Even clients retaining only the original key may safely retry through the same-key/hash-protected flow.

## 4. Actual research prototype and execution records

[idempotency_experiment.py](idempotency_experiment.py) is an original minimal SQLite prototype from this round, using only the standard library and a temporary database cleaned up on exit. It is not a NativeWeave product API. `connect` enables foreign keys/synchronous FULL; setup uses WAL; every command uses a separate connection and BEGIN IMMEDIATE. Hash comparison occurs inside the write transaction, with operations/items/outbox in the same COMMIT.

Actual execution command:

```text
python docs/research/topics/R31/idempotency_experiment.py > docs/research/topics/R31/experiment-result.json
```

The main process exited 0 with empty stderr. Environment: Python3.12.14, SQLite3.53.1, Linux6.18.57x64/glibc2.41. To record D12 requirements completely, the final result was rerun through an instrumented wrapper; actual argv, UTC start/end times and raw stream hashes are in [run-manifest.json](run-manifest.json). The first run's times were not fabricated retrospectively. Script SHA256, stdout SHA256, expected child-process exit 17 and version/OS/configuration are in evidence.run_manifest; all [raw stdout](experiment-result.json) is retained.

| Actual assertion | Result |
| --- | --- |
| Same-key/hash replay | Same operation_id and response, with 1 row in each of the three tables |
| Same key, different hash | Conflict; no additional business or outbox record |
| Same key concurrently on 4 independent connections | Exactly 1 created and 3 replays; all share the same operation_id |
| Simulated response loss after actual COMMIT | Replay on a new connection retrieves the original durable result without a second business effect |
| Child process executes `os._exit(17)` before COMMIT | Actually bypasses finally/rollback; a new connection sees no additions in the three tables, then normal creation succeeds with the same key |

At the end, operations/items/outbox each contain 4 rows. The experiment checks atomic result relationships and does not measure throughput or latency; elapsed time is not a performance conclusion. Response loss is simulated by a program branch after COMMIT, not an actual dropped packet at a network proxy; process exit does not validate OS power loss/disk-controller fsync. SQLite writer locking makes this counterexample reproducible but does not prove PG's MVCC concurrency implementation. Product C#/Rust, AOT and cross-platform validation all remain not-run.

## 5. Concrete application implementation boundaries

Attachments first use disk credit to stream into temporary files, validate hash/length, persist and rename immutable blobs, then commit references/results/outbox in short DB transactions. Failures may leave bounded/collectible orphans but must not commit successful DB results pointing to half-written files. GC must protect active uploads and recovery and account for retention; directory fsync/rename and Windows/Linux differences require actual fault tests. Blob hashes are not credentials for cross-tenant reads.

Outbox workers claim bounded batches and mark after publication; crashes after publication cause duplicates, and consumer oracles durably deduplicate by event_id. Business transactions do not wait for client downloads or call external publishers; slow responses must not retain DB leases indefinitely. Pagination uses stable keyset(created_at,id), with no default promise of a consistent snapshot across pages; consistent exports have separate deadline/lease profiles.

Application developers write ordinary C# typed models, Fluent queries and async APIs, without Rust/FFI or per-entity Cargo requirements. Optional C# SGs generate static metadata/DTOs; ordinary Fluent calls reuse the native SeaQuery builder and SQLx execution. Dynamic filters first resolve allowed columns/operators, then Rust validates capability/parameter/tenant and resource boundaries. Business operation hashes/correlations do not become unbounded metric labels.

## 6. Fault and complete-workload evidence

B21 implements D20's complete minimal service, golden vectors, optional protocol facades and reference consumer; B22 implements independent oracles and controlled fault points: BEGIN/writes/before and after COMMIT/lost acknowledgements, PG restart, SQLite busy/disk full, pool reset, HTTP slow/abort, crash after outbox publication, crash between blob rename and DB commit, drain/retire and related cases.

Model/property validation checks at least: at most one business effect per scope/key; atomic item/result/outbox consistency; irreversible terminal states; Unknown does not become rollback through Dispose or an empty query; every owner is eventually released or explicitly isolated. Fuzzing targets lengths/inputs/query IR/ABI, and actual multithreaded tests control race windows rather than relying only on sleeps. Execute actual Windows/Linux AOT publications; 24h regressions and 72h release soaks examine long-term resource slopes, steady plateaus and fault recovery, rather than reporting only one peak RSS.

The B23 product baseline is Rust Server + C# business Handlers/typed Fluent/DTO + Rust ORM / PostgreSQL/SQLite Engine. Pure C# Kestrel + Npgsql/Microsoft.Data.Sqlite (EF Core where applicable) is an external managed benchmark only, and pure Rust implementations compare ecosystem and cross-language costs only; they must not be mislabeled as NativeWeave managed database product profiles. TLS/HTTP profiles, schema/index/isolation/pool, dataset/cache, error ratios, durability, hardware resources and sampling are identical. Use fixed arrival rates and record queueing, retaining p99/p99.9/raw histograms, CPU/op and GC/alloc/native/RSS/handles/copies/crossings. Mark absent/untested combinations not-run and do not infer actual benefits from microbenchmarks; performance thresholds follow frozen baselines and product goals, with no invented percentages now. Evidence improves Rust DB and must not silently remove product constraints; the Rust Server lower layer is an established goal, and end-to-end evidence selects and optimizes concrete Rust compositions.

B24 accepts independent packages/RIDs/profiles, clean-machine execution, version rejection, upgrade/rollback and SBOM/LICENSE. Every NativeWeave Server example must validate the Rust Server native library; applications with databases also validate the Rust DB native library and relevant phase A interop/AOT gates. Pure managed examples may only be independent external comparators and must not be labeled NativeWeave Server product profiles. Database/Server cores must support independent acceptance before composition validation; the reference application must not force every independent task to run serially.

## 7. Closure recommendation and cross-review

The reference scenario, transaction idempotency, Unknown recovery and equivalent-performance methodology have explicit designs; all implementation/production validation obligations belong to B21–B24, without making research await release of the entire product. R31's current research/design results are complete and entering independent acceptance review: new Rust/SQLx PostgreSQL 18.0 actual-database counterexamples have executed, including lost COMMIT acknowledgement and concurrent snapshots. The author cannot self-declare accepted status; the complete product, other candidate features and long-term validation remain explicit Delivery obligations and no longer justify marking completed research planned/partially_evidenced.

Cross-review: database R21 checks Commit states and PG snapshots, and R20 checks SQLite writer semantics; R26/R29 check request-abort/stream budgets; R28 checks distinct gRPC/MCP terminal states; R17 checks workload equivalence; R34 checks tenant/auth/hash/retention and error disclosure. Potential counterexamples and affected files map concretely to D20 and relevant Delivery tasks without adding a metaplanning layer.

## 8. Newly completed research verification and explicit subsequent phases

`database-completion/tests/postgres.rs` pins two decisive counterexamples: a network proxy drops a COMMIT response while a new connection sees committed results; for a concurrent unique-key conflict synchronized through an actual pg_locks wait, a same-statement CTE SELECT can return empty while the next statement retrieves the original operation. Original results from R31's SQLite experiment—simulated response loss, actual process exit and four-connection contention—are retained without double counting. Other new PG/SQLite research in this round also covers protocol recovery, type loss, shape omissions and migration locks, all with actual execution scope traceable through designated manifests.

D20/B21 connect the two native Engines through the same business-operation definition; ownership still composes each Engine's local runtime with the Core ABI without a monolithic global scheduler. B22/B23 retain product fault-injection, actual C# AOT, sustained-load, performance and disk-durability obligations; these neither block research-level acceptance of idempotency/outbox/Unknown/interface designs nor authorize formal product development now.

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
