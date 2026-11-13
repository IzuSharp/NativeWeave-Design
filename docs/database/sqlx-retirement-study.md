# R20/R21/R25 continuation — SQLx cancellation, pool return and SQLite retirement

Observation: 2026-11-12 America/Los_Angeles. Author: `/root/design_source_review`.
Baseline: Design `c7e123a74405a92dc3de1ef450355b08d1c05ceb`, after the already
merged PR1 research-asset migration. This is a new, finite research slice under
the existing tasks; it does not implement a NativeWeave product Engine or
accept C-TX-001. The author of these new experiments cannot independently approve them.

## 1. What this adds to the recovered work

The existing native database fixture already demonstrates checked scalar binding,
explicit SQLite rollback, dynamic table names, CRUD and rejection of a silently
omitted SQLite row lock. The recovered C# query probe already demonstrates a
second ordinary entity using an unchanged native asset. Neither result should be
repeated or relabelled as new work.

The missing execution evidence addressed here is narrower: what happens when a
transaction or stream is dropped, an acquire waiter disappears, cancellation
state is replaced, or a COMMIT executes without the application receiving its
acknowledgment. The six new tests use actual SQLx/SQLite worker and pool code.
They do not replace PostgreSQL faults, C# Native AOT or the cross-language
retirement implementation.

The proposed ordinary path remains C# typed Fluent/static metadata -> native
SeaQuery -> SQLx. The new stream test builds its SELECT using SeaQuery itself.
No C# SQL AST, new ORM, mandatory per-entity Rust build, shared Core runtime or
private upstream layout is introduced.

## 2. Fixed source identity and the compiled package relationship

SQLx 0.9.0 is inspected at
[`75bc0487eb661da811bb7a3c5d158f1bd463fef4`](https://github.com/transact-rs/sqlx/tree/75bc0487eb661da811bb7a3c5d158f1bd463fef4).
The research crate retains SeaQuery 1.0.2, SQLx 0.9.0 and Tokio 1.54.1 and pins
Rust 1.100.0. Its complete Cargo.lock starts from the migrated fixture's resolved
closure; the root package is renamed, without resolving newer dependency versions.

[source-inspection.json](../../experiments/database-retirement/source-inspection.json)
records the exact Git blob and SHA256, inspected ranges/symbols, package checksum
and comparison result. All six selected Git files match the actual downloaded
registry files byte-for-byte. Five downloaded `.crate` archives—sqlx, sqlx-core,
sqlx-sqlite, sea-query and tokio—match the SHA256 values in Cargo.lock.

The published SQLx crates identify packaging commit
`003b698e99e024f3621b8043a2426fde5b741171` in `.cargo_vcs_info.json`, which is not
the historical study pin above. **The six matching files establish only those
file identities.** This report does not claim whole-package equivalence, a
verified release signature, or a complete upstream audit.

| Selected source at the fixed SQLx commit | Read mechanism | Consequence |
| --- | --- | --- |
| [sqlx-core/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/transaction.rs), begin/commit/rollback and Drop | `open` is true before awaiting begin; commit/rollback clear it only after successful await; Drop invokes `start_rollback` | Dropping a Future is not a database outcome. Failed or abandoned acknowledgment can leave Drop compensation to execute later. |
| [sqlx-sqlite/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/transaction.rs) | TransactionManager delegates to the connection worker; `start_rollback().ok()` discards its enqueue error | Drop does not provide a fallible rollback acknowledgment to the application. |
| [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs), Execute/Begin/Commit/Rollback | The worker runs SQLite and sends rows/results; a failed row send ends the iterator; BEGIN and COMMIT have different lost-ack compensation | A stopped receiver can stop further production at a send boundary, but does not interrupt arbitrary work already inside `sqlite3_step`. |
| Same worker, `rendezvous_oneshot` | Worker send completes only after receiver acknowledgment | Successful SQLite execution and successful application observation are separate events with a real cancellation window. |
| [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/pool/connection.rs), close/Drop/return | Explicit close retains its pool permit; Drop schedules return/close; return runs `after_release` and ping, with close paths on failure | Connection owner release, pool cleanliness and capacity return require distinct observations. Detach is not a way to hide still-live connections from the budget. |
| [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs), lock/progress/hook removal/close | Locked handle excludes worker access; replacing/removing a hook releases its stored closure; close sends Shutdown and awaits its response | A native hook's lifetime can be controlled, but this does not drain a separate managed cancellation registration. |
| [sqlx-sqlite/src/options/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/options/mod.rs), channel sizes | Command and row channels are independently bounded by item count | These limits are not byte budgets or limits on a row's largest value. |

Relevant upstream progress-handler tests were read at the same source pin,
`tests/sqlite/sqlite.rs` around lines 740–809; those upstream tests were not run.
The new tests below are independently authored fixtures with their own inputs
and execution records.

## 3. Actual call and cleanup chains

### Transaction and COMMIT

`Transaction::commit(self)` -> SQLite TransactionManager ->
`ConnectionWorker::commit` -> bounded command channel -> `Command::Commit` ->
SQLite commit -> worker transaction-depth update -> rendezvous result ->
application acknowledgment -> `open = false`.

If the commit future disappears before its final successful await, the
Transaction destructor sees an open transaction and requests rollback. The
worker separately detects a successful but unacknowledged COMMIT and ignores
the next Drop-generated rollback. This is necessary compensation for a result
delivery failure, not a promise that the application knows the commit outcome.

The new controlled witness is:

1. A real transaction inserts a row on a real SQLite connection.
2. Polling the commit future dispatches COMMIT to the worker.
3. SQLite enters a public commit hook. A test-only gate pauses the worker there.
4. The application drops its pending commit future before any success is returned.
5. The test releases the hook and allows SQLite to commit.
6. A subsequent query observes the inserted row. A later ordinary transaction
   can roll back without removing the committed row.

Therefore `drop(commit_future)` cannot be translated to `RolledBack`. A real
adapter with no trustworthy terminal acknowledgment must retain Unknown until
an identity-bound recovery observation supplies more information. The fixture's
follow-up SELECT is that observation for this controlled, same-connection test;
it is not a general recovery algorithm for arbitrary remote transactions.

The blocking hook is deliberate fault injection. It must not be copied into
production FFI callbacks, progress callbacks or finalizers. Dropping its release
sender on a test-error path also unblocks the worker, and the runner applies a
process-level deadline independently of Tokio timeouts.

### Early result-stream termination

SeaQuery native SELECT -> SQLx `fetch` -> worker `Command::Execute` -> row iterator
-> bounded row channel -> application row. Dropping the stream closes the
consumer side; the worker breaks when sending a row fails. A later command on
the same connection can advance after the iterator cleans up.

The new fixture uses a row-channel capacity of one and a 1,000-row result. It
consumes one row, drops the stream, and successfully executes a count and a
connection-local marker lookup. This is finite evidence for the exercised
ordinary SELECT, not a hard interruption guarantee for busy handlers, I/O,
extensions or an arbitrarily expensive `sqlite3_step` before its next row.

### Pool return and close

Dropping a pooled owner may spawn asynchronous return work. A canceled acquire
waiter must not steal capacity, and a closed pool must reject new acquisition
while its outstanding owners retire. The tests distinguish physical connection
reuse with a TEMP-table marker: an accidentally substituted clean connection
cannot pass the marker check.

Explicit `PoolConnection::close()` retains the pool permit during its awaited
close. `close_on_drop` is an intent; its fallback path contains a timeout and
does not itself give the caller a completion acknowledgment. Do not report
`LocalResourcesReleased = true` merely because a drop request was issued.

## 4. Shutdown acknowledgment is a narrower claim than OS thread join

The inspected worker spawns an OS thread without retaining a public JoinHandle.
For `Command::Shutdown`, it drops its connection references, sends the response,
and then returns from the thread closure. `SqliteConnection::close` awaits that
response; `close_hard` instead drops the connection and returns.

The source comment near `close` describes thread termination, but the observable
implementation is the shutdown response, sent before the closure has returned.
This distinction matters to native-module unloading and strict OS-thread-count
accounting. The current D02 profile keeps the module loaded to process exit.
NativeWeave can separately prove that its resource/callback obligations are
retired; it must not invent an OS JoinHandle acknowledgment from that evidence.

If a future requirement demands exact worker-thread join or hot unload, evaluate
a narrow upstream-supported seam/extension with its own pin and tests. That
requirement does not justify replacing SQLx's network/database machinery or
creating an unconditional global NativeWeave runtime.

Both `start_rollback` and `shutdown` can perform synchronous sends to the bounded
worker channel. A cooperative runtime timeout cannot preempt a synchronous send
that is currently blocking its thread. Their destructors/cleanup paths must be
owned by an execution context explicitly allowed to perform that work; an
arbitrary `tokio::spawn` or SafeHandle finalizer is not such a proof.

## 5. Implications for the proposed C# / native contract

The following findings retain their finite evidence and open product gates.
They do not independently accept the affected contracts.

| Finding | Impact and evidence | Disposition |
| --- | --- | --- |
| DB-LIFE-001 | A dropped COMMIT future can leave a committed row; the commit-hook witness in section 3 and the corresponding executed test distinguish database effect from result observation. | Preserve D15 TX-D002/TX-D003 Unknown/outcome semantics; actual provider recovery and C# adapter classification remain B05/B22 gates. |
| DB-LIFE-002 | SQLx worker Shutdown response precedes closure return; the fixed `Command::Shutdown` source supports resource release ordering but does not expose OS thread join. | Retain D02 module residency; do not infer exact worker-thread retirement from pool size or shutdown response. A stricter requirement needs separate upstream-supported evidence. |
| DB-LIFE-003 | `start_rollback` and `shutdown` synchronously enqueue to a bounded worker channel. Cooperative timeout alone cannot establish a hard cleanup deadline. | B03/B04 must assign cleanup to an allowed execution context and retain outstanding work in resource accounting; this fixture does not validate saturated-channel shutdown. |
| DB-LIFE-004 | D15 previously required SeaORM TransactionTrait and a SeaORM benchmark for the ordinary candidate, conflicting with the existing direct SeaQuery/SQLx profile. | D15 now conditions the trait on the selected SeaORM profile and compares equivalent native stacks. Full SeaORM profile behavior remains separately unverified. |

| Boundary action | Required behavior | Must not imply |
| --- | --- | --- |
| Cancel ordinary query | Record operation-local cancellation intent; continue owning the executing connection and any worker-visible state | Statement stopped, rollback confirmed, or pool reusable |
| Cancel commit admission | Reject before handing COMMIT to the native executor, if that precondition is actually established | Ability to retract a COMMIT already dispatched |
| Stop waiting after dispatch | Keep the native completion/cleanup owner and expose uncertain outcome if no trustworthy acknowledgment arrives | `OperationCanceledException` is a confirmed database rollback |
| Remove progress callback | Exclude worker access with the public lock protocol; remove the exact old handler before reusing the connection | Managed CancellationTokenRegistration callbacks are also drained |
| Dispose stream/session | Close logical admission, stop further consumption and complete provider cleanup before reuse | Every intermediate row/string allocation was byte-bounded |
| Close datasource with deadline | Stop new admission, retain charged outstanding cleanup and report Pending when obligations remain | Timeout frees callback roots, memory or live worker capacity |

The native session owns the real SQLx connection and transaction work. C# owns
its typed facade and immutable Outcome/Cleanup snapshots; it does not duplicate
the provider's pool or transaction protocol. Separate operation-local cancel
state prevents a late cancel from a previous query becoming a cancel for the
next query. The new sequential replacement fixture is not a proof of all races,
memory orderings or managed cancellation-registration retirement.

SeaORM remains a separately evaluated native integration profile. Its dynamic
metadata constructor and ActiveModel/relationship boundaries have their existing
R25 analysis; they do not become prerequisites for this direct SQLx profile.
Equivalent benchmarks compare pure native calls and C# -> ABI calls through the
**same selected native stack**, rather than forcing the ordinary SQLx candidate
through SeaORM simply because an older task assumed that choice.

## 6. New executable verification

Entry point: [experiments/database-retirement](../../experiments/database-retirement/README.md).
The execution summary and raw command/source evidence are retained there.

| Test | Observable oracle | Scope limit |
| --- | --- | --- |
| `dropped_transaction_rolls_back_before_same_connection_reuse` | Uncommitted row absent; connection-local TEMP marker survives reacquisition | One SQLite pool/connection and ordinary insert |
| `early_stream_drop_unblocks_bounded_row_queue_and_reuses_connection` | One consumed row, then later count/marker succeeds after early drop | No arbitrary expensive step or decoder exception injection |
| `canceled_acquire_waiter_does_not_lose_the_only_pool_permit` | Pending waiter dropped; same sole connection can be acquired again | Does not exhaustively test cancellation during fresh connection creation |
| `dropping_dispatched_commit_before_ack_can_still_commit` | Real committed row after loss of application acknowledgment; later rollback leaves it intact | Local SQLite gate, not PostgreSQL wire-response fault injection |
| `progress_cancel_state_is_removed_before_next_operation` | Interrupted old operation; old capture released; next operation uses its own state successfully | Sequential replacement, no managed callback or weak-memory proof |
| `pool_close_waits_for_checked_out_owner_and_rejects_new_acquire` | Close is initially pending; new acquire rejected; size reaches zero after owner release | Pool state, not OS thread join or whole-process memory bounds |

Local Linux execution passed all six tests with Rust 1.100.0 and `cargo test
--locked`. The first attempt failed Cargo's unused-dependencies check because a
test-only crate initially declared ordinary dependencies. The correction moves
those dependencies to `dev-dependencies`; it does not disable the lint. Failed
and successful inputs/stdout/stderr remain separate. CI runs, when performed,
must retain their own OS, commit, run and artifact identities; local success
must never be relabelled as a Windows or Native AOT result.

No new throughput, latency, hard-timeout, PostgreSQL, C# AOT, full ORM or accepted
production-contract result is claimed.

## 7. Existing tasks advanced and remaining gates

R20/R21 gain independently inspected source-to-package identity and real finite
SQLite cancellation/cleanup evidence. R25 retains the dynamic metadata/native
reuse architecture without repeating the already successful entity experiment.
D15 receives these precise observations and corrects stale mandatory-SeaORM
benchmark/trait language. These changes do not change the status of any formal
Delivery task to implemented or complete.

| Existing task | Concrete next output |
| --- | --- |
| B03 / R20 | Busy/locked/file-I/O and long-step cancellation; worker cleanup under channel pressure; operation-specific progress-handler replacement races |
| B04 / R21 | Engine-local completion/cleanup owner with bounded pending work and a provider-independent close result; distinguish local retirement from pool return |
| B05 / R21 | Actual native adapter classification of lost COMMIT/ROLLBACK acknowledgments, failed transactions and savepoint sequences; preserve Outcome/Cleanup after Dispose |
| B06 / R22 | Decoder exception/early stream stop with bounded row bytes and oversized-field policy; same-session cleanup before reuse |
| B22 / R31 | PostgreSQL response-direction COMMIT fault injection, durable recovery identity and cross-platform C# AOT races/soak |
| B23 / R17 | Same-backend pure-Rust versus C#-bound workload comparison; separate SeaORM dynamic/static alternatives when exercised |

The next proof is the cross-language adapter and real backend faults, not a new
task graph or another copy of the original six database tests.
