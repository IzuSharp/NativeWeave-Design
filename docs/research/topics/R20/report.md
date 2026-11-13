# R20 — SQLite native worker, cancellation and administrative serialization

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Current conclusion and reused work

The ordinary SQLite profile is SeaQuery + SQLx inside the same maintainer-precompiled Rust Engine as PostgreSQL. Optional SeaORM projection support can reuse that native boundary without generated Rust entities. Microsoft.Data.Sqlite/SQLitePCL.raw remain comparisons. SQLx's existing worker, SQLite VM and native transactions are reused; C# does not implement a database engine or create another worker pool.

The existing report/evidence already inspected worker commands, ExecuteIter, progress handlers, rollback/drop and shutdown. The preserved [retirement study](../../../database/sqlx-retirement-study.md) and `verification/source-lifecycle/results.json` contain actual Windows/Linux six-case evidence. They must no longer be described as wholly unexecuted merely because this task's graph was planned. They still do not establish a complete product adapter or SQLite VM audit.

## Lifetime and cancellation decision

Each SQLx SQLite connection has a dedicated worker thread. Both its command and row channels are bounded in items, not total bytes. Pool size bounds worker count; input/query/result/retirement bytes require separate budgets. Add no per-query Tokio runtime or extra asynchronous shim around every sqlite3 call.

Install a native-only progress handler under the connection handle lock before the operation. It reads an operation-owned atomic flag; request_cancel only signals that flag, never waits for the database mutex or sends to a full channel. Cleanup removes/retires the handler before another operation generation. This supports cooperative VM interruption and deliberately promises no hard interruption of every busy wait, filesystem call or extension.

Dropped futures/receivers, statement reset and worker shutdown are different events. A shutdown acknowledgment is not an OS JoinHandle observation. Finalizers/control entries transfer responsibility to a bounded cleanup owner; they do not invoke potentially blocking SQLx start_rollback/shutdown. All owners and budgets remain until the declared safe-retirement barrier. A permanently loaded module avoids unsound unloading while upstream work could still exist.

## SQL and transaction differences

The SQLite profile declares journal/WAL, synchronous, foreign_keys, busy_timeout, SQLite library version and compile options. Ordinary isolation is SQLite's serializable behavior with explicit DEFERRED/IMMEDIATE mode; unsupported PostgreSQL isolation settings fail before BEGIN. Constraint errors do not all have identical transaction effects. The new Rust fixture executes foreign-key failure, explicit rollback-to/release-savepoint and subsequent valid commit; the old six-case study handles lost COMMIT acknowledgment and pool/worker ownership.

New source inspection finds SQLx SQLite migration `lock` and `unlock` are no-ops. Calling Migrator on two unrelated application pool connections is therefore not a complete migration-serialization design. The administrative path owns a dedicated connection and obtains SQLite write admission with BEGIN IMMEDIATE before reading ledger/applying the supported transactional migration batch. SQLx's nested transaction/savepoint behavior can retain its existing apply/ledger mechanism under that outer transaction. Nontransactional maintenance is an explicit exclusive administrative operation; never silently enable no_tx inside this atomic profile. B08 must test concurrent processes and crash/recovery under the selected journal policy.



Independent review reproduced the exact public API chain in three real Linux Rust tests: `Connection::begin_with("BEGIN IMMEDIATE")` yields a depth-tracked `Transaction`; `Migrator::run(&mut *tx)` uses nested savepoints and preserves that outer transaction; explicit outer rollback undoes both schema and ledger, including a failing second migration. Reject every `m.no_tx` before acquiring the transaction. Raw `query("BEGIN IMMEDIATE")` is prohibited here: it leaves SQLx `is_in_transaction()` false and causes Migrator to fail with a nested-BEGIN error. Commit only on successful migration; rollback on error, and quarantine/close on cleanup failure. The [independent source and results](../../../../verification/interop-completion/db-review-migration/result.json) prove this finite public path, not cross-process crash/recovery or the future C# product.

## Evidence and acceptance boundary

[The completion fixture](../../../../experiments/database-completion/README.md) adds native foreign-key/savepoint behavior, migration checksum mismatch and atomic failed DDL, explicit joins and changesets. The common Linux run passed five tests; independent review and cross-platform evidence are separate records. Original Python SQLite probes remain SQL semantic counterexamples, not Rust execution.

The current research design resolves worker ownership, cooperative cancellation limits, safe pool reuse and the native administration mechanism. Future B03/B05/B08 must implement and validate busy/locked, filesystem failures, concurrent migration, late cancellation, C# AOT and long load. No “async” API claims that SQLite VM execution itself becomes nonblocking or instantaneously cancellable.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R20-C01 | [src/Microsoft.Data.Sqlite.Core/SqliteCommand.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteCommand.cs#L357-L439) | [[357, 439], [458, 543]]; source-observed; reader=database_design |
| R20-C02 | [src/Microsoft.Data.Sqlite.Core/SqliteDataReader.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteDataReader.cs#L118-L144) | [[118, 144], [154, 180], [182, 208], [243, 301]]; source-observed; reader=database_design |
| R20-C03 | [src/Microsoft.Data.Sqlite.Core/SqliteTransaction.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/Microsoft.Data.Sqlite.Core/SqliteTransaction.cs#L70-L243) | [[70, 243]]; source-observed; reader=database_design |
| R20-C04 | [test/Microsoft.Data.Sqlite.Tests/SqliteTransactionTest.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/Microsoft.Data.Sqlite.Tests/SqliteTransactionTest.cs#L14-L32) | [[14, 32], [310, 328], [359, 377], [379, 397]]; test-source-observed; reader=database_design |
| R20-C05 | [LICENSE.txt](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/LICENSE.txt#L1-L23) | [[1, 23]]; license-text-observed; reader=database_design |
| R20-C06 | https://www.sqlite.org/c3ref/interrupt.html | 定位见evidence; official-documentation-observed; reader=database_design |
| R20-V1 | [refs/tags/v11.0.0](https://api.github.com/repos/dotnet/efcore/git/refs/tags/v11.0.0) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R20-V2 | [refs/tags/v3.0.5](https://api.github.com/repos/ericsink/SQLitePCL.raw/git/refs/tags/v3.0.5) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R20-RU01 | [src/driver/sqlx_sqlite.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_sqlite.rs#L155-L254) | [[155, 254], [311, 337]]; source-observed; reader=/root/database_design |
| R20-SQ09-SQLITE-01 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 25-138;163-212;364-389; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-02 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 213-313;538-574; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-03 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 390-412;490-505;335-344; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-04 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 214-287; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-05 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 128-137;291-305;386-422;524-527;550-560; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-06 | [sqlx-sqlite/src/connection/execute.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/execute.rs) | 1-133; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-07 | [sqlx-sqlite/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/transaction.rs) | complete; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-08 | [tests/sqlite/sqlite.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/tests/sqlite/sqlite.rs) | 740-809; cross-task-source-evidence; reader=/root/interop_design |
| R20-SQ09-SQLITE-09 | [sqlx-sqlite/src/connection/executor.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/executor.rs) | 1-102; cross-task-source-evidence; reader=/root/interop_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
