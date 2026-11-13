# Transactions, connection pools and recovery from indeterminate outcomes

- Task: D15; contract: C-TX-001@0.3.0; author: database_design / source-lifecycle continuation; 2026-11-12.
- Historical input packet: revision 0.1.1, SHA-256 `cce4d00e3cc7983c2808cf7a5d47e4a08707885973c497ba5a929a78c5bd554c`, which matched the Plan graph at that time; see [database-completion](../../verification/database-completion/task-status.json) for current revision inputs and hashes.
- Historical baseline: Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`.
- Status: **0.3.0 design candidate; the registry records independent review and acceptance of exact content, while product implementation/release acceptance remains in Delivery**; acceptance is determined by the registry entry with the same content hash and independent Review. Contract code examples remain design-draft and uncompiled; the complete production adapter and C# AOT validation are unfinished. Historical limited Rust/SQLite reclamation experiments appear in §12; this round's actual PostgreSQL response-loss, protocol-recovery and migration-lock experiments appear in §13.
- Inputs: [R19](../research/topics/R19/report.md), [R20](../research/topics/R20/report.md), [R21](../research/topics/R21/report.md); shares WeaveDataSource/DataSession naming with the [driver specification](drivers.md).

> Old packets and Reviews provide historical provenance only for their original versions and cannot accept this round's new content hash.

## 1. Design decisions

TX-D001: The Rust transaction coordinator exclusively owns a native Session and its SQLx physical-connection lease; only one command/reader/COPY is permitted at a time. Transaction objects are not pooled. An Outcome snapshot retained by business code remains readable after Dispose and does not suffer ABA from internal connection reuse.

TX-D002: Maintain **transaction effects, application-operation results, protocol reusability and local resource lifetime** separately. Cancellation, Task termination, Dispose or native quiescence alone never determines whether a database commit occurred.

TX-D003: `CommitAsync(admissionToken)` accepts user cancellation only before commit is sent. After entering CommitInFlight, an independent commit deadline drives the commit to acknowledgment or Unknown; a request-disconnection token must not overwrite an effect that has already occurred. The caller may stop waiting, but cleanup responsibility remains with the transaction object/Session.

TX-D004: Do not automatically retry business writes or whole transactions by default. Only operations proven unsent, explicitly rolled back, or protected by business-level atomic idempotency enter an explicit retry policy. Unknown must enter a recovery branch.

These decisions resolve Q12's research-design question; network faults, actual scheduling, AOT and long-running resource validation remain B05/B22 acceptance conditions.

## 2. Source evidence and Rust adapter boundaries

The ordinary path is a precompiled SeaQuery + SQLx Rust Engine; the SQLx research pin is v0.9.0 `75bc0487eb661da811bb7a3c5d158f1bd463fef4`. Pinned SeaORM source remains evidence for the specialized static Entity profile; its trait/model compilation coupling is not a prerequisite for ordinary applications.

Rust SessionExecutor holds the physical-connection lease; B01 declares shared driver/session interfaces, B04 composes and owns the host, B02/B03 execute, and B05 coordinates transactions/cleanup. SeaQuery builds SQL, and the fallible binder propagates parameter-encoding errors. Borrowed transactions/streams stay within the native async task that owns the connection; no transmute crosses lifetime boundaries. Adding ordinary C# entities is runtime metadata; SQLx pools/trait objects/allocator owners do not cross dynamic-library boundaries. Actual native compilation and limited PG/SQLite fault evidence appear in §12/13; formal product cross-language concurrency gates must still run.

SQLx PoolConnection::close retains the pool permit until closure ends; close_on_drop only schedules closure, and Drop may spawn pool-return work; returning to the pool executes after_release and ping, with close_hard on failure. The PG TransactionManager advances transaction depth through commands and ReadyForQuery; an error after calling commit does not prove no commit occurred. The SQLite worker treats successful BEGIN with lost acknowledgment differently from successful COMMIT with lost acknowledgment; start_rollback/shutdown may synchronously wait for a bounded channel and must not enter SafeHandle ReleaseHandle or nonblocking control functions. Detailed pinned files/line ranges and actual reader identities are in R20/R21 evidence.

Npgsql v10.0.3 controlled deferred reset, broken-connection eviction and the distinction between cancellation request and terminal state remain **comparison evidence**, not new product dependencies. PostgreSQL 18 [protocol flow](https://www.postgresql.org/docs/18/protocol-flow.html) defines Sync/ReadyForQuery boundaries. Referenced upstream test source was read only, not executed; this round's independent experiments obtained the limited PG fault evidence in §13, which cannot replace production-adapter and complete AOT validation; the PR5 limited Linux/SQLite query prototype cannot replace them either.

## 3. Four state dimensions

| Dimension | States | Meaning |
| --- | --- | --- |
| TxLifecycle | Active / Failed / CommitInFlight / RollbackInFlight / Closed | Whether further operations in this transaction are permitted |
| TransactionOutcome | InProgress / Committed / RolledBack / Unknown | Knowledge of persistence effects; only evidence-backed terminal states are permitted |
| ConnectionDisposition | Usable / ProviderResetPending / Quarantined / Discarded | Whether the next application operation receives clean protocol and session semantics |
| LocalLifetime | Live / Closing / Quiescent / Reclaimed | Obligations that may still access local objects, buffers or callbacks |

`ProviderResetPending` includes only provider-internal maintenance that is known, ordered and handled before the next user command. It does not permit arbitrary unread user results, unattributable protocol bytes, unconfirmed error recovery or unknown concurrent writes. Npgsql allows deferred reset, so “zero pending-send bytes on every pool return” is not required; what is required is the provider's guarantee that the next borrower cannot observe the previous user's transaction/session state.

Unknown is a knowledge state, not a reason to keep native memory alive. Once resources are quiescent, local handles may be released while retaining a separate managed/durable recovery identifier. A connection with untrustworthy protocol state cannot return to the pool even if native code is quiescent.

## 4. State machine and linearization points

| Input/event | Previous state | Next state and outcome |
| --- | --- | --- |
| Begin succeeds | Session has no transaction/active operation | Active, InProgress; acquire exclusive binding |
| Ordinary command succeeds | Active | Active; retain transaction |
| Command error invalidates the transaction | Active | Failed; permit only Rollback or supported RollbackToSavepoint |
| Token already cancelled before Commit | Active | Remain Active; commit not initiated; throw cancellation; rollback/Dispose still required afterward |
| Commit dispatch admission | Active | CAS to CommitInFlight; prohibit new commands, a second commit and concurrent rollback |
| Trustworthy commit acknowledgment | CommitInFlight | Closed, Committed |
| Trustworthy rollback acknowledgment | CommitInFlight or RollbackInFlight | Closed, RolledBack; retain failure reason |
| Disconnection/deadline after possible send with no trustworthy terminal state | CommitInFlight | Closed, Unknown; clean up or discard connection; throw Unknown exception |
| Rollback acknowledged successfully and commit never attempted | RollbackInFlight | Closed, RolledBack; local release still follows independent cleanup/retire barriers |
| Rollback unacknowledged, disconnection/deadline, and never entered CommitInFlight | RollbackInFlight | Closed, InProgress, CommitAttempted=false; Cleanup=RollbackUnconfirmed; further use prohibited; connection quarantined/discarded |
| Cleanup rollback attempted or “no transaction” received after Unknown | Closed, Unknown | Retain Unknown; this response cannot prove an earlier COMMIT did not occur; update only Cleanup/ConnectionDisposition |
| Independent deadline reached while native call/SQLite worker still runs | Any completion flow | Application gate closed; LocalLifetime=Closing and Cleanup=Pending; retain connection, callbacks, buffers and budget; do not report safe-cleanup success |
| Dispose | Any Live state | Closing; close admission and join any completion flow already started; do not blindly change Unknown to RolledBack |

`InProgress` means there is no confirmed knowledge of database-transaction termination; it does not guarantee local execution remains possible and must be read together with TxLifecycle. RollbackUnconfirmed with CommitAttempted=false states only that this framework did not initiate COMMIT, not that server rollback has completed; it also does not guarantee reversal of nontransactional external side effects. These judgments assume an exclusive connection and prohibition of SessionMutating expert SQL inside the transaction. A partially successful Begin without acknowledgment likewise requires isolation and retained cleanup, without first publishing Active to the application.

Commit dispatch admission is the conservative local boundary at which “sending may have begun”; it must not be equated with the server's persistence point. Commit may be marked unsent only when it is provable that provider commit was not called or work was not handed to the native executor. If the public provider API cannot report the exact send position, transport/timeout errors after calling its commit method are classified as Unknown.

A known Failed transaction must not Commit: ending a failed PostgreSQL transaction must not be reported as a successful commit. The adapter must maintain statement-error/savepoint-recovery state rather than ignore earlier failure merely because a Task completes without exception. B05 must validate classification with actual failed transactions/deferred constraints.

## 5. Public API and exception paths

The following code is **design-draft and uncompiled**. This section defines the interface's strict semantics.

```csharp
public enum TransactionOutcome { InProgress, Committed, RolledBack, Unknown }
public sealed record TransactionOptions(
    IsolationLevel? Isolation = null,
    string? RecoveryKey = null);

await using DataSession session = await source.OpenSessionAsync(requestToken);
await using DataTransaction tx = await session.BeginTransactionAsync(
    new TransactionOptions(RecoveryKey: operationId), requestToken);
try
{
    await WorkCommands.UpdateAsync(session, change, requestToken);
    await tx.CommitAsync(requestToken); // token controls admission only before commit dispatch.
}
catch (CommitOutcomeUnknownException ex)
{
    await recovery.RecordUncertainAsync(ex.RecoveryKey, ex.CorrelationId);
    // Query by the same idempotency key/operation_id; do not treat this failure as proof that no write occurred.
}
```

`CommitOutcomeUnknownException` contains Outcome=Unknown, an optional RecoveryKey, ProviderCode and CorrelationId; it contains no connection password, SQL parameters or raw sensitive payload. `DataTransaction.Outcome`, `CommitAttempted` and `Cleanup` remain readable after Dispose; successful CommitAsync means only Committed. Explicit transaction rollback/failure returns the corresponding DataException; an unknown outcome must not be downgraded to an ordinary OperationCanceledException.

Commit, Rollback and cleanup use configurable but finite independent deadlines rather than inherit an already cancelled request token. The default commit deadline is 30 seconds and cleanup deadline 5 seconds for initial implementation/counterexamples; these are operation policies, not database completion-time guarantees. If a provider cannot interrupt a synchronous call, record deadline exceeded while retaining worker/resource obligations rather than fabricate termination. Waiter timeout and executor stop are observed separately.

`DisposeAsync` closes application admission; if Active, it requests rollback, and if commit already exists, it joins it. Business failure and cleanup failure are latched separately: explicit RollbackAsync failure throws DataCleanupException, whereas automatic Dispose does not overwrite an already reported primary error with a cleanup exception. `tx.Cleanup` is an immutable snapshot with fields Status (NotStarted/Pending/Succeeded/RollbackUnconfirmed/Failed), CorrelationId, ProviderCode, LocalResourcesReleased, ConnectionDisposition and DeadlineExceeded; it contains no sensitive parameters. Diagnostic events use the same correlation ID as this snapshot.

Successful return from DisposeAsync requires LocalResourcesReleased=true; this indicates local safety only, not Outcome=RolledBack. If native accessors remain at the deadline, **DisposeAsync continues to join and does not succeed early**, while the Engine retains cleanup responsibility, roots and budget. Explicit `CloseAsync(deadline)` for bounded waiting returns a CleanupResult snapshot (Status=Pending, ConnectionDisposition=Quarantined, LocalResourcesReleased=false), allowing the caller to decide to stop waiting; this result does not pretend the object is already Disposed. Subsequent DisposeAsync/join waits for the same cleanup task without another rollback. Ordinary rollback/close errors are recorded in Cleanup and do not overwrite an already reported CommitUnknown/business error through the await using cleanup path; explicit RollbackAsync still reports its own error. For bounded shutdown, use the explicit CloseAsync control flow rather than expect await using to guarantee a finite duration.

DataSession/DataSource also provide CloseAsync(deadline) with the same semantics: the Engine cleanup owner retains the session and its parent lease and joins existing tx/cursors; bounded HTTP response paths do not additionally force waiting through await using. This API starts no new business work and does not prematurely return admission/connection budget still in use.

Synchronous Dispose only requests closure and transfers responsibility to an already registered cleanup owner; it neither blocks a finalizer nor promises completed drain. Use DisposeAsync when confirmation of local safety is needed. Closed TxLifecycle may coexist with LocalLifetime=Closing and Cleanup=Pending; “application use prohibited” does not mean “memory may already be released.”

SQLx/SeaORM objects are destroyed only on controlled executor paths where blocking or waiting for the runtime is permitted. Finalizers and ReleaseHandle only mark closure/transfer to a budgeted retirement queue and must not execute SQLite start_rollback/shutdown synchronous send. Cleanup dependent on a runtime must not be scheduled after that runtime is destroyed.

## 6. Connection return, quarantine and discard

Necessary conditions for return: no active SeaORM/SQLx stream/COPY/send Future; no in-flight cancellation/handler accessing the connection; the transaction has ended or SQLx-controlled rollback maintenance can complete before the next command; session state is restored; no unknown protocol/concurrency damage. Application-operation terminal state, native retirement and pool-return eligibility are recorded separately.

Rust SessionExecutor retains PoolConnection until the decision is explicit. The normal path permits SQLx's own after_release/ping and ordered rollback; do not independently copy Npgsql's DISCARD ALL protocol or assume identical reset behavior. A selected profile may permit only fixed session settings that the application cannot change arbitrarily; validate/reset supported settings on each lease. If unknown or unsupported state must be cleaned up, call public `PoolConnection::close()` and join rather than return to the pool.

`close_on_drop` expresses eviction intent and cannot alone establish LocalResourcesReleased=true; work scheduled by Drop remains in the Engine cleanup ledger. Using detach to release a permit early while excluding a still-live connection/SQLite thread from budget is prohibited. The pool owns internal SQLx maintenance after pool return; DataSource shutdown joins pool closure and all cleanup for this Engine. The runtime must not be destroyed first, and D02 v1 modules are not unloaded. Whether an owner crossing the ABI has retired is not guessed from private SQLx fields.

An Unknown remote effect alone does not require discarding a connection whose protocol/transaction state is proven clean; discard is based on protocol and session state. Conversely, Task success or local quiescence does not permit a dirty connection to pass. An ignored SQLite statement reset() error does not prove safe reuse; if transaction/statement termination cannot be proven, close and join the worker, without forcing a free at the deadline.

## 7. Savepoints, isolation and session state

Reject nested BeginTransaction by default and explicitly provide Savepoint/Release/RollbackTo. Only a selected SeaORM integration profile needs to handle the associated Transaction implementation fixed-point constraint of its TransactionTrait; nested begin in that profile returns an explicit UnsupportedNestedTransaction error in v1 rather than implicitly start a second top-level transaction merely because the trait requires that method. The ordinary SeaQuery+SQLx path does not require implementing SeaORM traits. Required savepoints map from explicit NW APIs to SQLx savepoints on the same connection, maintaining a stack and generation and rejecting out-of-order release/rollback. The framework generates safe savepoint identifiers rather than directly concatenate user strings; scope objects bind to the current transaction generation. Whether successful RollbackTo returns to Active depends on actual provider semantics. Disposing a savepoint does not commit the outer transaction.

PostgreSQL conveys requested ReadCommitted/RepeatableRead/Serializable capabilities; serialization failure/deadlock may indicate “the whole transaction may be retried” but does not automatically replay the business delegate. SQLite's ordinary Serializable and BEGIN IMMEDIATE/DEFERRED options are expressed separately rather than pretending SQLite has PostgreSQL's complete isolation matrix; ReadUncommitted is supported only in an explicit profile with prerequisites such as shared cache stated.

`TransactionOptions.Isolation=null` uses the default published by the provider profile: ReadCommitted for PostgreSQL; ordinary Serializable semantics for SQLite, whose profile explicitly selects DEFERRED/IMMEDIATE BEGIN mode. An explicit unsupported isolation request must be rejected before start without silent downgrade. Thus a cross-provider application specifying only RecoveryKey does not accidentally require SQLite to implement PostgreSQL ReadCommitted.

Ordinary generated commands must not independently execute BEGIN/COMMIT/ROLLBACK or modify transaction ownership. An expert-SQL entry point requires an explicit SessionMutating marker; that category and unaudited multistatement/transaction-control SQL are rejected inside a framework-owned Active transaction, without promising complete static auditing of arbitrary SQL. Nontransactional use reduces reuse guarantees and discards the connection on return by default. There is no public SQLx connection escape hatch that bypasses operation leases.

## 8. Atomic idempotency and Unknown recovery

The framework provides RecoveryKey propagation and Unknown outcomes without defining business idempotency identities. The reference application should use the following implementable protocol:

1. Within the same transaction, attempt to insert a unique `(scope,key)` record containing request_hash, operation_id and state; scope includes tenant/principal/operation kind.
2. On conflict, read the existing record and compare request_hash. The same key with a different request returns a conflict; an old result must not be replayed for a different request.
3. Perform business writes and record the normalized result and outbox event in the same transaction; report completion externally only after commit succeeds.
4. When the COMMIT outcome is Unknown, query for recovery using operation_id or the same key. One “not found” result cannot prove the old transaction will never commit, especially while old execution is unfinished, when reading a replica or when reading a snapshot.
5. A retry with the same key serializes with the old transaction through a uniqueness constraint and the same-transaction protocol; do not “check absence, then write” outside the transaction. Idempotency-record cleanup retention must cover the client retry window; expired keys no longer promise the same deduplication semantics.

External email, object storage or other effects that cannot join the same transaction use an outbox and independently idempotent consumers; a database transaction must not be claimed to make external systems exactly-once. Recovery reads should use a primary database/explicit acknowledgment point meeting consistency requirements. D20 defines detailed HTTP and reference-service interfaces.

PostgreSQL 18's concrete branch: execute `INSERT ... ON CONFLICT(scope,key) DO NOTHING RETURNING operation_id` in a ReadCommitted transaction; after 0 rows return, execute **the next, separate SELECT statement** to read the same scope/key and verify the hash. Do not claim that INSERT DO NOTHING + SELECT combined in one CTE always reads the conflicting record: the conflicting transaction's result may not yet be visible in the same statement's snapshot. Official [isolation rules §13.2.1](https://www.postgresql.org/docs/18/transaction-iso.html) and [INSERT RETURNING](https://www.postgresql.org/docs/18/sql-insert.html) explain this visibility and the fact that only actually inserted/updated rows are returned, respectively. If the next read still finds no row (cleanup, expiry, timeout, etc.), enter bounded recovery/retry rather than infer rollback of the old transaction; prohibit early physical deletion during retention and use an explicit retention/tombstone policy. B03/B21 must verify the SQLite same-key atomic protocol under the target journal/locking configuration rather than infer concurrency behavior from PostgreSQL syntax.

## 9. Safety invariants

- `active_protocol_operations(session) <= 1`; no new operation lease may be acquired after admission closes.
- A transaction publishes at most one confirmed terminal state; only subsequent identity-bound recovery evidence may refine Unknown, which local Dispose cannot overwrite.
- Every returned connection satisfies the provider-defined protocol for isolated reuse; unknown damage cannot pass on the assumption that it “might reset later.”
- The operation continues to own the connection until cancellation registration, readers and provider send tasks exit; DataSource shutdown does not transfer those responsibilities to a destroyed runtime.
- Committed business writes and idempotency results/outbox share the same transaction-atomicity boundary; failure classification does not equate a “retryable exception” with “business work did not execute.”

These are implementation-acceptance obligations. State tables and source analysis support the design decisions but do not yet prove that actual schedulers satisfy them.

## 10. Cost and AOT

Rust reuses the SQLx physical pool, adding native Session objects, operation gates/leases, failure contexts and a bounded cleanup ledger. C# has only native-handle wrappers and Outcome/Cleanup snapshots, without maintaining a second ORM transaction model or physical pool. Transaction objects are not pooled, avoiding disposed-object reuse and ABA of recovery identities.

An Engine-local executor owns SQLx futures and SQLite-thread cleanup responsibilities; this does not force other Native Engines to share Tokio. Shutdown first stops new admission, stops streams/transactions, cleans connections, drains callbacks/control calls, and finally closes pool/runtime instances. Under D02 v1, native modules remain loaded until process exit without hot unloading. Budgets include commit in flight, quarantined connections, pending rollback and waiters; background cleanup must not expand capacity without bound.

C# Outcome/exception and recovery DTO types are statically defined, and serializers use explicit metadata; both PG/SQLite providers reside in Rust native assets. B23 compares pure Rust calls with C#→ABI calls against the same pinned native candidate stack: the ordinary candidate is SeaQuery+SQLx, while dynamic or static SeaORM profiles are separate comparisons and SeaORM is not mandatory on the ordinary path. Managed drivers are independent benchmark comparators; “Rust is mandatory” is not an evidence-free claim of superior performance.

## 11. Verification / Delivery obligations

| ID / owner | Scenario | Observable acceptance condition |
| --- | --- | --- |
| TX-V01 / B05 | Cancellation before Commit, request disconnection during commit, lost commit response | Correct distinction between unsent and Unknown; no automatic retry; recovery can identify committed business work |
| TX-V02 / B05,B22 | Unconfirmed rollback, disconnection, native cleanup timeout | Never committed→Closed/InProgress/CommitAttempted=false/unconfirmed rollback; previous Unknown remains Unknown; connection cannot be leased; while work runs, LocalResourcesReleased=false and budget does not reach zero; primary error and Cleanup are separately queryable |
| TX-V03 / B05 | Commit on a failed transaction, savepoint recovery, repeated termination | No false report of commit; stable rejection of illegal transitions |
| TX-V04 / B02,B03 | Pool exhaustion/cancellation, reset failure, leftover session settings | Admission slots restored; next borrower's state isolated; include distinct SQLx-controlled pending-rollback and unknown-protocol-damage paths |
| TX-V05 / B21,B22 | Concurrent same-key requests with same/different payloads, lost COMMIT return, expired records | One business effect or explicit conflict; record/result/outbox consistent; not found is not false proof of rollback |
| TX-V06 / B05,B22 | start/commit/Dispose/Cancel interleaving models and actual stress | Single terminal state, no double return/deadlock, restored resource counts |

Inject real-database faults through a controllable proxy cutting the COMMIT response direction, server-initiated session termination, constraints/deadlocks inside transactions, and similar means; record fault location, server observations and client classification. Execute separately with win-x64/linux-x64 Native AOT binaries; Python or model results cannot substitute. Long-running resource metrics include uncleaned Sessions, waiters, physical connections, workers, buffers and the Unknown recovery backlog.

## 12. Added limited SQLite reclamation and cancellation evidence

The [R20/R21/R25 continuation study](sqlx-retirement-study.md) and [actual research fixture](../../experiments/database-retirement/README.md) use pinned SQLx 0.9, SeaQuery 1.0.2, Tokio 1.54.1 and Rust 1.100. Six local Linux tests were executed: reuse of the same physical connection after transaction Drop, early stream stop, cancellation of acquire without losing a permit, dropping a Future after COMMIT dispatch but before acknowledgment delivery, progress-handler state isolation, and Pool closure waiting for a leased owner. Successful/failed inputs and raw logs for each run are separately retained; Windows/CI evidence is recorded separately from its actual runs.

The COMMIT test pauses execution under control inside SQLite's native commit hook, drops the application's waiting Future, then resumes execution and ultimately observes committed rows. This counterexample supports TX-D002/TX-D003: stopping the wait must not report RolledBack; unknown commit effects and local cleanup continue to be recorded separately. The fault-injection hook deliberately blocks for research only and must not be copied into production callbacks/finalizers.

The six independently read SQLx source files are byte-for-byte identical to the registry files actually compiled; the package's VCS declaration differs from the historical research Git pin, so the entire package is not claimed equivalent. The SQLx worker Shutdown response occurs after its connection reference is released but before its thread closure returns; that response and Pool.size reaching zero do not mean an OS JoinHandle has been obtained. D02's initial module-residency constraint remains effective. This limited Rust evidence does not accept the production adapter, PostgreSQL response loss, cross-language retirement or the complete AOT contract.

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

An atomic SQLite migration batch must use the public SQLx `Connection::begin_with("BEGIN IMMEDIATE")` to create a tracked `Transaction`, then call `Migrator::run(&mut *tx)`. First reject unsupported nontransactional entries with `migrator.iter().any(|m| m.no_tx)`, then admit the operation and acquire the writer lock. On success, only `tx.commit().await` ends the outer batch; on a migration error, explicitly call `tx.rollback().await`, and if rollback fails, isolate and close the dedicated connection. Do not first call `query("BEGIN IMMEDIATE").execute(&mut conn)`: raw SQL does not update SQLx transaction depth, so the subsequent BEGIN inside Migrator would fail.

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

The independent reviewer actually ran three Linux Rust regressions: the raw BEGIN counterexample, tracked outer rollback/commit, and whole-batch rollback after the second migration failed; schema changes and the migration ledger were rolled back together, and inner savepoints did not commit the outer transaction. See the [independent three-case regression](../../verification/interop-completion/db-review-migration/result.json). This proves the public call chain and limited atomicity; it does not replace B08 cross-process contention, Windows, crash/restart or product AOT validation. Example error names and map_migration_failure only illustrate domain mapping and are not published APIs; that mapping must preserve the original migration error and rollback error, and require isolation/closure of connections not yet safely cleaned up.


These facts refine B05/B08/B22: distinct outcome/cleanup observables, zero advisory
locks after successful retirement, no pool reentry after unknown admin state, and
explicit finite deadlines that never free still-used native owners.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.
