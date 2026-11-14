# Transactions, connection pooling and uncertain-outcome recovery

- Task: D15; contract: C-TX-001@0.4.0; author: database_design / source-lifecycle continuation; 2026-11-12.
- Historical input packet: revision0.1.1, SHA-256 `cce4d00e3cc7983c2808cf7a5d47e4a08707885973c497ba5a929a78c5bd554c`, which matched the Plan graph at that time; see [database-completion](../../verification/database-completion/task-status.json) for the current revised inputs and hashes.
- Historical baseline: Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`.
- Status: **0.4.0 design candidate; the registry records exact-content independent review and acceptance, while product implementation/release acceptance remains in Delivery**; acceptance is determined by the matching content hash and independent Review in the registry. Contract code examples remain design-draft and uncompiled; full production adapters and C# AOT verification are not complete. See section 12 for historical finite Rust/SQLite reclamation experiments and section 13 for this round's actual PostgreSQL response-loss, protocol-recovery and migration-lock experiments.
- Inputs: [R19](../research/topics/R19/report.md), [R20](../research/topics/R20/report.md), [R21](../research/topics/R21/report.md); shares DataSource/DataSession naming with the [driver specification](drivers.md).

## Public API refinement 0.4.0

The exact public declarations and complete native operation inventory are now
[Database/ORM API 0.4.0](../api/database.md), its
[coverage matrix](../api/database-coverage.json), and
[Database.cs](../../experiments/public-api/NativeWeave.Api.Design/Database.cs).
They replace earlier provisional signature spellings; the lifecycle, native-source
findings and historical experiment identities below remain normative within that
explicit scope. Native AOT fixture compilation is separate from product execution.
Fresh exact-content review is required; prior accepted versions remain immutable.


> Old packets and Reviews provide historical provenance for the original versions only; they cannot accept this round's new content hashes.

## 1. Design decisions

TX-D001: A Rust transaction coordinator exclusively owns one native Session and its SQLx physical-connection lease; only one command/reader/COPY is permitted at a time. Transaction objects are not pooled. An Outcome snapshot retained by business code remains readable after Dispose and does not suffer ABA from internal connection reuse.

TX-D002: Maintain **transaction effects, application-operation results, protocol reusability state and local resource lifetime** separately. Cancellation, Task termination, Dispose or native quiescence alone never determines whether the database committed.

TX-D003: `CommitAsync(admissionToken)` accepts user cancellation only before commit is sent. After entering CommitInFlight, an independent commit deadline drives commit to confirmation or Unknown; a request-disconnection token is not allowed to overwrite effects that have already occurred. The caller may stop waiting, but cleanup responsibility remains with the transaction object/Session.

TX-D004: By default, do not automatically retry business writes or an entire transaction. Only operations proven unsent, explicitly rolled back or protected by business-level atomic idempotency enter an explicit retry policy. Unknown must enter the recovery branch.

These decisions resolve Q12's research/design question; network faults, actual scheduling, AOT and long-term resource verification remain B05/B22 acceptance conditions.

## 2. Source evidence and Rust adaptation boundary

The ordinary path is a precompiled SeaQuery + SQLx Rust Engine; the SQLx research pin is v0.9.0 `75bc0487eb661da811bb7a3c5d158f1bd463fef4`. Pinned SeaORM source remains evidence for the specialized static Entity profile; its trait/model compilation coupling is not an ordinary application prerequisite.

Rust SessionExecutor holds the physical-connection lease; B01 declares shared driver/session interfaces, B04 composes and owns the host, B02/B03 execute, and B05 coordinates transactions/cleanup. SeaQuery builds SQL, and a fallible binder propagates parameter-encoding errors. Borrowed transactions/streams remain within native asynchronous tasks owning the connection, without transmute across lifetimes. New ordinary C# entities are runtime metadata; SQLx pools/trait objects/allocator owners do not cross dynamic-library boundaries. See sections 12/13 for current actual native compilation and finite PG/SQLite fault evidence; formal product cross-language concurrency gates still require execution.

SQLx PoolConnection::close retains the pool permit until closure completes; close_on_drop only schedules closure, and Drop may spawn return-to-pool work, which executes after_release and ping and calls close_hard on failure. PG TransactionManager advances transaction depth through commands and ReadyForQuery; an error after invoking commit does not prove that no commit occurred. The SQLite worker handles successful BEGIN with lost ack differently from successful COMMIT with lost ack; start_rollback/shutdown may synchronously wait on a bounded channel and must not enter SafeHandle ReleaseHandle or non-blocking control functions. Detailed pinned files/line ranges and actual reader identities appear in R20/R21 evidence.

Npgsql v10.0.3's controlled deferred reset, removal of bad connections, and distinction between cancellation requests and terminal states remain **comparison evidence**, not new product dependencies. PostgreSQL18 [protocol flow](https://www.postgresql.org/docs/18/protocol-flow.html) defines Sync/ReadyForQuery boundaries. Cited upstream test source was read only, not executed; this round's independent experiments provide the finite PG fault evidence in section 13 without replacing production adapters or full AOT verification. PR5's finite Linux/SQLite query prototype cannot replace these verifications either.

## 3. Four state dimensions

| Dimension | States | Meaning |
| --- | --- | --- |
| TxLifecycle | Active / Failed / CommitInFlight / RollbackInFlight / Closed | Whether further operations in this transaction are permitted |
| TransactionOutcome | InProgress / Committed / RolledBack / Unknown | Knowledge of durable effects; only evidence-backed terminal states are permitted |
| ConnectionDisposition | Usable / ProviderResetPending / Quarantined / Discarded | Whether the next application operation receives clean protocol and session semantics |
| LocalLifetime | Live / Closing / Quiescent / Reclaimed | Obligations that may still access local objects, buffers or callbacks |

`ProviderResetPending` includes only provider-internal maintenance that is known, serialized and handled before the next user command. It does not permit arbitrary unread user results, unattributable protocol bytes, unconfirmed error recovery or unknown concurrent writes. Npgsql permits deferred reset, so “zero bytes pending transmission on every return to pool” is not required; the requirement is that the provider guarantees a new borrower cannot observe the previous user's transaction/session state.

Unknown is a knowledge state, not a reason to keep native memory alive. After resource quiescence, local handles may be released while separate managed/durable recovery identities remain. A connection with an untrusted protocol state cannot return to the pool even when native code is quiescent.

## 4. State machine and linearization points

| Input/event | Prior state | Subsequent state and result |
| --- | --- | --- |
| Successful Begin | Session has no transaction/active operation | Active, InProgress; acquire exclusive binding |
| Successful ordinary command | Active | Active; retain transaction |
| Command error invalidating the transaction | Active | Failed; permit only Rollback or supported RollbackToSavepoint |
| Token canceled before Commit | Active | Remain Active; commit was not initiated; throw cancellation; rollback/Dispose still required afterward |
| Commit admission | Active | CAS to CommitInFlight; prohibit new commands, a second commit and concurrent rollback |
| Trusted commit confirmation | CommitInFlight | Closed, Committed |
| Trusted rollback confirmation | CommitInFlight or RollbackInFlight | Closed, RolledBack; retain failure reason |
| Disconnect/deadline after possible sending, without a trusted terminal state | CommitInFlight | Closed, Unknown; clean up or discard connection; throw Unknown exception |
| Rollback confirmed successful with no prior commit | RollbackInFlight | Closed, RolledBack; local release still follows separate cleanup/retire barriers |
| Rollback unconfirmed, disconnect/deadline, and CommitInFlight never entered | RollbackInFlight | Closed, InProgress, CommitAttempted=false; Cleanup=RollbackUnconfirmed; prohibit further use; quarantine/discard connection |
| Cleanup rollback attempted after Unknown, or a “no transaction” response received | Closed, Unknown | Retain Unknown; this response cannot prove earlier COMMIT did not occur; update only Cleanup/ConnectionDisposition |
| Independent deadline reached while native call/SQLite worker still runs | Any completion flow | Application gate closed; LocalLifetime=Closing and Cleanup=Pending; retain connection, callbacks, buffers and budget without reporting successful safe cleanup |
| Dispose | Any Live state | Closing; close admission and join completion already started; do not blindly change Unknown to RolledBack |

`InProgress` means no confirmed knowledge of database transaction termination, not that local execution remains possible; it must be read together with TxLifecycle. RollbackUnconfirmed with CommitAttempted=false says only that this framework did not initiate COMMIT, not that server rollback has completed; it does not guarantee reversal of nontransactional external effects either. These judgments assume an exclusively held connection and prohibition of SessionMutating expert SQL within the transaction. Partial Begin success without confirmation likewise requires isolation and retained cleanup, without first publishing Active to the application.

Commit admission is the conservative local boundary “sending may have started,” not the server's durability point. Mark commit unsent only when it can be proven that provider commit was not called/not handed to the native executor. If the public provider API cannot report the exact send point, transport/timeout errors after invoking its commit method are classified as Unknown.

Commit is prohibited for a known Failed transaction: ending a failed PostgreSQL transaction must not be reported as successful commit. The adapter must maintain statement-error/savepoint-recovery state; an exception-free Task alone cannot justify ignoring an earlier failure. B05 must verify classification using actual failed transactions/deferred constraints.

## 5. Public API and exception paths

The following is a design composition example; WorkCommands/recovery are application placeholders. Exact framework signatures are compiled separately by the public API fixture.

```csharp
await using DataSession session = await source.OpenSessionAsync(requestToken);
await using DataTransaction tx = await session.BeginTransactionAsync(
    new TransactionOptions { RecoveryKey = operationId }, requestToken);
try
{
    await WorkCommands.UpdateAsync(session, change, requestToken);
    await tx.CommitAsync(requestToken); // token controls admission only before commit is admitted.
}
catch (CommitOutcomeUnknownException ex)
{
    await recovery.RecordUncertainAsync(ex.RecoveryKey, ex.CorrelationId);
    // Query using the same idempotency key/operation_id; do not treat this failure as no write.
}
```

`CommitOutcomeUnknownException` contains Outcome=Unknown, optional RecoveryKey, ProviderCode and CorrelationId; it contains no connection passwords, SQL parameters or raw sensitive payloads. `DataTransaction.Outcome`, `CommitAttempted` and `Cleanup` remain readable after Dispose; successful CommitAsync means only Committed. Confirmed transaction rollback/failure returns the corresponding DatabaseException; an unknown outcome must not be downgraded to an ordinary OperationCanceledException.

Commit, Rollback and cleanup use configurable but finite independent deadlines, without inheriting an already-canceled request token. Default commit and cleanup deadlines are 30 seconds and 5 seconds respectively for initial implementation/counterexamples; these are operation policies, not guarantees of database completion time. When a provider cannot interrupt a synchronous call, record deadline exceeded while retaining worker/resource obligations rather than fabricate termination. Waiter timeout and executor stop are observed separately.

`DisposeAsync` closes application admission; it requests rollback if Active or joins an existing commit. Business failure and cleanup failure are latched separately: explicit RollbackAsync failure throws DatabaseCleanupException, while automatic Dispose does not overwrite an already-reported primary error with a cleanup exception. `tx.Cleanup` is an immutable snapshot with fields Status (NotStarted/Pending/Succeeded/RollbackUnconfirmed/Failed), CorrelationId, ProviderCode, LocalResourcesReleased, ConnectionDisposition and DeadlineExceeded; it contains no sensitive parameters. Diagnostic events use the same correlation ID as this snapshot.

Successful return from DisposeAsync requires LocalResourcesReleased=true; this expresses local safety only and does not guarantee Outcome=RolledBack. If native accessors remain when the deadline is reached, **DisposeAsync still joins and does not succeed early**; the Engine retains cleanup responsibility, roots and budget. Explicit `CloseAsync(waitBudget, cancellationToken)` for a bounded wait returns a DatabaseCloseResult snapshot (Status=Pending, ConnectionDisposition=Quarantined, LocalResourcesReleased=false), allowing the caller to stop waiting; that result does not masquerade as Disposed. Subsequent DisposeAsync/join waits for the same cleanup task without restarting rollback. Ordinary rollback/close errors are recorded in Cleanup and do not overwrite an already-reported CommitUnknown/business error through await using cleanup; explicit RollbackAsync still reports its own error. For bounded closure, use CloseAsync's explicit control flow rather than expecting await using to guarantee finite time.

DataSession/DataSource also provide CloseAsync(waitBudget, cancellationToken) with the same semantics: an Engine cleanup owner retains the session and its parent lease and joins existing transactions/cursors; a finite HTTP-response path does not additionally force waiting through await using. This API starts no new business work and does not prematurely return admission/connection budgets still in use.

Synchronous Dispose only requests closure and hands responsibility to a registered cleanup owner; it neither blocks finalizers nor promises a completed drain. Use DisposeAsync when local safety must be confirmed. Closed TxLifecycle may coexist with LocalLifetime=Closing and Cleanup=Pending; “the application may not continue using it” does not mean “the memory can already be released.”

SQLx/SeaORM object destruction occurs only on controlled executor paths permitted to block or await the runtime. Finalizers and ReleaseHandle only set closure/transfer responsibility to a budgeted retirement queue; they must not perform SQLite start_rollback/shutdown synchronous sends. Cleanup depending on a runtime must not be scheduled after that runtime is destroyed.

## 6. Returning, quarantining and discarding connections

Necessary conditions for return: no active SeaORM/SQLx stream/COPY/send Future; no cancellation/handler in flight accessing the connection; the transaction has ended or SQLx-controlled rollback maintenance can finish before the next command; session state is restored; no unknown protocol/concurrency damage. Application-operation terminal state, native retirement and eligibility for pool return are recorded separately.

Rust SessionExecutor retains PoolConnection until the decision is clear. Normal paths permit SQLx's own after_release/ping and serialized rollback; do not independently copy Npgsql's DISCARD ALL protocol or assume identical reset behavior. A profile may allow only fixed session settings that applications cannot change arbitrarily; validate/reset supported settings on each lease. If unknown or unsupported state must be cleaned up, invoke public `PoolConnection::close()` and join it rather than return to the pool.

`close_on_drop` expresses an intent to remove the connection and alone cannot establish LocalResourcesReleased=true; work scheduled by Drop remains in the Engine cleanup ledger. Using detach to release a permit early while excluding a still-live connection/SQLite thread from the budget is prohibited. The pool owns internal SQLx maintenance after pool return; DataSource closure must join pool closure and all cleanup owned by that Engine. The runtime must not be destroyed first, and D02 v1 modules are not unloaded. Do not infer cross-ABI owner retirement from private SQLx fields.

An Unknown remote effect alone does not force discard of a connection whose protocol/transaction state is proven clean; protocol and session state determine discard. Conversely, Task success or local quiescence does not permit a dirty connection to pass. An ignored SQLite statement reset() error does not prove reuse safety; if transaction/statement completion cannot be proven, close and join the worker. A deadline cannot force free.

## 7. Savepoints, isolation and session state

Reject nested BeginTransaction by default and explicitly expose Savepoint/Release/RollbackTo. Only a selected SeaORM integration profile needs to handle TransactionTrait's fixed-point constraint on the associated Transaction implementation; nested begin in that profile returns an explicit UnsupportedNestedTransaction error in v1. The trait requiring this method must not implicitly start a second top-level transaction. The ordinary SeaQuery+SQLx path does not require implementation of the SeaORM trait. NW explicit APIs map required savepoints to SQLx's same-connection savepoint mechanism, maintaining a stack and generation and rejecting out-of-order release/rollback. The framework generates safe savepoint identifiers rather than directly concatenating user strings; scope objects bind to the current transaction generation. Whether successful RollbackTo returns to Active depends on actual provider semantics. Disposing a savepoint does not commit the outer transaction.

PostgreSQL passes through requested ReadCommitted/RepeatableRead/Serializable capabilities; serialization failure/deadlock may indicate that “the whole transaction is retryable,” but does not automatically replay business delegates. SQLite's ordinary Serializable and BEGIN IMMEDIATE/DEFERRED options are expressed separately; SQLite must not be presented as having PostgreSQL's full isolation matrix. ReadUncommitted is supported only in an explicit profile that states prerequisites such as shared cache.

`TransactionOptions.Isolation=null` selects the default published by the provider profile: ReadCommitted for PostgreSQL; ordinary Serializable semantics for SQLite, with the SQLite profile explicitly selecting DEFERRED/IMMEDIATE BEGIN mode. Explicit requests for unsupported isolation levels must fail before start without silent downgrade. Thus a cross-provider application passing only RecoveryKey does not inadvertently require SQLite to implement PostgreSQL ReadCommitted.

Ordinary generated commands must not independently execute BEGIN/COMMIT/ROLLBACK or change transaction ownership. Expert-SQL entry points must be explicitly marked SessionMutating; reject that category and unaudited multi-statement/transaction-control SQL inside framework-owned Active transactions, without promising complete static auditing of arbitrary SQL. Nontransactional use reduces reuse guarantees and discards the connection on return by default. There is no public SQLx connection escape hatch that bypasses operation leases.

## 8. Atomic idempotency and Unknown recovery

The framework provides RecoveryKey propagation and Unknown outcomes without defining business idempotency identity. The reference application should use this implementable protocol:

1. Attempt to insert a unique `(scope,key)` record in the same transaction, containing request_hash, operation_id and status; scope includes tenant/principal/operation kind.
2. On conflict, read the existing record and compare request_hash. The same key with a different request returns conflict; do not replay an old result for a different request.
3. Perform business writes and record the canonical result and outbox events in the same transaction; report completion externally only after successful commit.
4. For an Unknown COMMIT outcome, query recovery by operation_id or the same key. One “not found” result cannot prove the old transaction will never commit, especially while its execution has not ended or when reading a replica or snapshot.
5. A same-key retry serializes with the old transaction through the unique constraint and same-transaction protocol; do not perform “check absent, then write” outside the transaction. Idempotency-record cleanup retention must cover the client's retry window; expired keys no longer promise the same duplicate-prevention semantics.

External email, object storage and other side effects that cannot share the transaction use an outbox and independently idempotent consumers; database transactions must not be claimed to make external systems exactly-once. Recovery reads should use a primary/explicit confirmation point meeting consistency requirements. D20 defines detailed HTTP and reference-service interfaces.

Concrete PostgreSQL18 branch: execute `INSERT ... ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id` in a ReadCommitted transaction; after 0 rows are returned, execute **the next, separate SELECT statement** to read the same scope/key and verify the hash. An INSERT DO NOTHING + SELECT combination inside one CTE must not be claimed to always read the conflicting record: the conflicting transaction's result may not yet be visible to the same statement's snapshot. The official [isolation rules §13.2.1](https://www.postgresql.org/docs/18/transaction-iso.html) and [INSERT RETURNING](https://www.postgresql.org/docs/18/sql-insert.html) describe this visibility and returning only actually inserted/updated rows, respectively. If the next read still finds no row (cleanup, expiry, timeout and so on), enter bounded recovery/retry without inferring rollback of the old transaction; early physical deletion within the retention period is prohibited, using an explicit retention/tombstone policy. B03/B21 must verify SQLite's atomic same-key protocol under the target journal/locking configuration, without extrapolating its concurrency behavior from PostgreSQL syntax.

## 9. Safety invariants

- `active_protocol_operations(session) <= 1`; no new operation lease may be acquired after admission closes.
- A transaction publishes at most one confirmed terminal state; Unknown can only be refined by subsequent identity-bound recovery evidence, not overwritten by local Dispose.
- Every connection returned to the pool satisfies the provider-defined isolated-reuse protocol; unknown damaged state cannot pass on the grounds that “it may reset later.”
- The operation continues to own the connection until cancellation registrations, readers and provider send tasks exit; DataSource closure does not transfer these responsibilities to a destroyed runtime.
- Committed business writes and idempotent results/outbox share the same transactional atomicity boundary; failure classification must not equate a “retryable exception” with “the business operation did not execute.”

These are implementation-acceptance obligations. State tables and source analysis support design decisions but do not yet prove that an actual scheduler satisfies them.

## 10. Costs and AOT

Rust reuses SQLx's physical pool, adding native Session objects, operation gates/leases, failure contexts and a bounded cleanup ledger. C# contains only native-handle wrappers and Outcome/Cleanup snapshots, without a second ORM transaction model or physical pool. Transaction objects are not pooled, avoiding reuse of disposed objects and ABA in recovery identities.

An Engine-local executor owns SQLx futures and SQLite-thread cleanup responsibilities; this does not force other Native Engines to share Tokio. Closure first stops new admission, stops streams/transactions, cleans connections and drains callbacks/control, then closes pool/runtime instances. D02 v1 native modules remain loaded until process exit, with no hot unload. Account for commit in flight, quarantined connections, pending rollback and waiters; background cleanup must not expand capacity without limit.

C# Outcome/exceptions and recovery DTOs are statically defined, and serializers use explicit metadata; PG/SQLite providers reside in Rust native assets. B23 compares pure Rust calls with C#→ABI calls using the same pinned native candidate stack: the ordinary candidate is SeaQuery+SQLx; SeaORM dynamic or static profiles are separate comparisons, without forcing the ordinary path through SeaORM. Managed drivers serve as independent benchmark comparisons; “Rust is required” is not an unsupported claim of performance superiority.

## 11. Verification / Delivery obligations

| ID / owner | Scenario | Observable acceptance condition |
| --- | --- | --- |
| TX-V01 / B05 | Cancellation before Commit, request disconnection during commit, lost commit response | Accurate distinction between unsent and Unknown; no automatic retry; recovery identifies committed business work |
| TX-V02 / B05,B22 | Unconfirmed rollback, disconnect, native cleanup timeout | Commit never attempted→Closed/InProgress/CommitAttempted=false/rollback unconfirmed; prior Unknown remains Unknown; connection cannot be leased; if still running, LocalResourcesReleased=false and budget does not reach zero; primary error and Cleanup are separately inspectable |
| TX-V03 / B05 | Commit of failed transaction, savepoint recovery, repeated termination | No false commit report; illegal transitions consistently rejected |
| TX-V04 / B02,B03 | Pool exhaustion/cancellation, reset failure, residual session settings | Admission slots restored; state isolated for next borrower; distinct paths for SQLx-controlled pending rollback and unknown protocol damage |
| TX-V05 / B21,B22 | Concurrent same key with same/different payloads, lost COMMIT response, expired records | One business effect or explicit conflict; record/result/outbox consistent; not-found does not falsely prove rollback |
| TX-V06 / B05,B22 | start/commit/Dispose/Cancel interleaving models and actual stress | Unique terminal state, no double return/deadlock, resource counts recover |

Inject actual-database faults through a controlled proxy cutting the COMMIT-response direction, server-terminated sessions, in-transaction constraints/deadlocks and similar methods; record the fault point, server observations and client classification. Execute separately with win-x64/linux-x64 Native AOT binaries; Python or model results cannot substitute. Long-term resource metrics include uncleaned Sessions, waiters, physical connections, workers, buffers and Unknown-recovery backlog.

## 12. Added finite SQLite reclamation and cancellation evidence

[The R20/R21/R25 continuation study](sqlx-retirement-study.md) and [actual research fixture](../../experiments/database-retirement/README.md) use pinned SQLx0.9, SeaQuery1.0.2, Tokio1.54.1 and Rust1.100. Six local Linux tests were executed: reuse of the same physical connection after transaction Drop, early stream termination, acquire cancellation without losing permits, dropping a Future after COMMIT dispatch but before ack delivery, progress-handler state isolation, and pool closure waiting for leased owners. Inputs and raw logs for each success/failure are preserved separately, with Windows/CI recorded through their actual executions.

The COMMIT test pauses in a controlled manner inside SQLite's native commit hook, drops the application's waiting Future, then releases the pause and ultimately observes committed rows. This counterexample supports TX-D002/TX-D003: stopping the wait cannot report RolledBack; unknown commit effects and local cleanup remain separately recorded. The fault-injection hook deliberately blocks for research only and must not be copied into production callbacks/finalizers.

The six independently read SQLx source files are byte-identical to the registry files actually compiled; the package's VCS declaration differs from the historical research Git pin, so equivalence of the entire package is not claimed. The SQLx worker Shutdown response occurs after its connection reference is released but before the thread closure returns; that response and Pool.size reaching zero are not equivalent to obtaining an OS JoinHandle. D02's initial module-residency constraint remains effective. The finite Rust evidence above does not accept production adapters, PostgreSQL response loss, cross-language retirement or the full AOT contract.

## 13. PostgreSQL response loss, protocol recovery and migration ownership

The database-completion research fixture adds explicit PostgreSQL18.0 probes with a
source/lock/OS/server identity manifest. Its COMMIT-loss proxy forwards the request,
consumes server COMMIT and idle ReadyForQuery, discards those replies to the client,
and checks durable state through another connection. A client error with a committed
row is the concrete oracle for Unknown; it does not implement the future C# exception.
The timeout case observes 57014, then 25P02 before rollback, then same-backend recovery.
The stream case drops consumption and verifies cleanup before the next query.

Migration lifetime is an administrative instance of the same rule. SQLx's PG
Migrator acquires a session advisory lock, checks ledger/checksums and unlocks on its
success path. Some errors return before unlock. A pooled application's connection
must never inherit this state. Use a dedicated migration connection, close it after
error/cancellation and preserve its cleanup owner until closure. A close failure
leaves the admin operation quarantined with resources counted; it is not proof of
remote lock release. The research negative control queries pg_locks after checksum
mismatch and after closing the dedicated connection. SQLite migration lock/unlock
are no-ops; the documented SQLite administrative profile owns write serialization
and rejects unsupported nontransactional migration inside its atomic batch.

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


These facts refine B05/B08/B22: distinct outcome/cleanup observables, zero advisory
locks after successful retirement, no pool reentry after unknown admin state, and
explicit finite deadlines that never free still-used native owners.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.
