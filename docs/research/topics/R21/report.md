# R21 — Native transaction outcome, protocol reuse and cleanup

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Current design decision

Rust SQLx owns execution and the physical pool; the ordinary profile does not require a custom SeaORM TransactionTrait implementation. The native transaction coordinator wraps SQLx's public transaction/connection mechanisms. C# exposes immutable result/cleanup snapshots and async application APIs. Keep four independent facts: transaction lifecycle, known durable outcome, connection disposition and local resource lifetime, as specified by [D15](../../../database/transactions-and-pooling.md).

A COMMIT call crosses a conservative local dispatch boundary. Before that boundary cancellation can establish not-dispatched. After it, lack of a trustworthy response means Unknown unless independent evidence establishes the outcome. Dropping the wait, receiving a cancellation token, subsequent rollback cleanup and freeing local resources cannot establish that the previous COMMIT rolled back. A known failed PostgreSQL transaction cannot be reported as committed merely because a later COMMIT command returned without a transport exception.

## Source and real experiment chain

Historical Npgsql, SeaORM and SQLx source evidence is preserved below. The source-lifecycle study's SQLite commit-hook experiment already demonstrated a committed row after dropping the commit future. This continuation adds the SQLx PG `run`/ReadyForQuery path and a real protocol proxy fixture: forward COMMIT, consume server COMMIT plus idle ReadyForQuery, discard those bytes to the client, and query durable state through a separate connection. This distinguishes response loss from a synthetic exception after the client observed success.

The PG fixture separately tests statement timeout SQLSTATE57014, failed transaction SQLSTATE25P02, explicit ROLLBACK and same-backend reuse. Early row-stream cancellation is tested against actual unread rows and a subsequent query. These characterize the selected engine; they are not evidence that NativeWeave's future C# operation wrapper is already implemented.

## Disposal and pool invariant

Session admission closes first. Existing operation/reader/transaction work retains its parent connection; cleanup has a bounded reserved control path and can proceed after public closure. `DisposeAsync` joins local safety; `CloseAsync(deadline)` can return Pending without claiming resource release. Neither overwrites the primary business error or Unknown outcome. Unknown recovery identifiers outlive native handles without keeping every uncertain transaction's native memory indefinitely.

SQLx can queue known rollback maintenance before the next user command; this differs from unknown protocol bytes. Return to the pool requires trustworthy protocol and session state. `close_on_drop` is a requested disposition, not observed completion. Physical connection/worker/permit/retirement memory remain accounted until ownership actually transfers or is released.

The new migration inspection exposes another session-state hazard: PG Migrator acquires a session advisory lock and returns some errors before calling unlock. The design uses a dedicated administrative connection, closes it on any failure/timeout and never returns it to the application pool. The matching PG negative control observes the retained lock after checksum mismatch and its disappearance after connection close. SQLx owns locking implementation; NativeWeave owns safe administrative lifetime.

## Recovery and orchestration

Scoped idempotency key, normalized request hash, business mutation, response and outbox row share one database transaction. Same-key conflict is serialized by the unique constraint. In PG ReadCommitted, `ON CONFLICT DO NOTHING` may observe a row invisible to its statement snapshot. The new contention fixture synchronizes on a real `pg_locks` wait and verifies that a CTE fallback SELECT can return no row while a subsequent independent statement finds the committed operation. That is why D15/D20 use a second statement and never treat a single missing row as proof of rollback.

Retrying a transaction remains an explicit business decision; no transparent replay of arbitrary C# delegates. Savepoints are explicit and generation-bound. Recovery/tombstone retention is a business protocol, not another Core runtime. B05/B21/B22 implement the final coordinator and C# AOT tests; design acceptance is not blocked on completion of that future product code.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## Pinned Source Entry Points and Actual Reading

| Claim | Pinned file/source | Actual scope and evidence category |
| --- | --- | --- |
| R21-C01 | [src/Npgsql/NpgsqlTransaction.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlTransaction.cs#L120-L230) | [[120, 230], [290, 390]]; source-observed; reader=database_design |
| R21-C02 | [src/Npgsql/Internal/NpgsqlConnector.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/NpgsqlConnector.cs#L2075-L2258) | [[2075, 2258], [2706, 2810], [2936, 2993]]; source-observed; reader=database_design |
| R21-C03 | [src/Npgsql/NpgsqlDataReader.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataReader.cs#L238-L259) | [[238, 259], [357, 378], [500, 521], [593, 614], [952, 973], [1033, 1054], [1077, 1227]]; source-observed; reader=database_design |
| R21-C04 | [src/Npgsql/PoolingDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/PoolingDataSource.cs#L100-L356) | [[100, 356], [445, 455]]; source-observed; reader=database_design |
| R21-C05 | [src/Npgsql/NpgsqlDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSource.cs#L242-L257) | [[242, 257]]; source-observed; reader=database_design |
| R21-C06 | [test/Npgsql.Tests/TransactionTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/TransactionTests.cs#L36-L58) | [[36, 58], [65, 87], [94, 116], [123, 145]]; test-source-observed; reader=database_design |
| R21-C07 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/pool/connection.rs#L130-L163) | [[130, 163], [195, 225], [271, 369]]; source-observed; reader=database_design |
| R21-C08 | [sqlx-postgres/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-postgres/src/connection/mod.rs#L81-L108) | [[81, 108], [180, 207], [211, 258]]; source-observed; reader=database_design |
| R21-C09 | https://www.postgresql.org/docs/18/transaction-iso.html | See evidence for location; official-documentation-observed; reader=database_design |
| R21-C10 | https://www.postgresql.org/docs/18/sql-insert.html | See evidence for location; official-documentation-observed; reader=database_design |
| R21-C11 | [LICENSE-MIT](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/LICENSE-MIT) | See evidence for location; license-text-observed; reader=database_design |
| R21-RU01 | [src/database/transaction.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/transaction.rs#L1-L112) | [[1, 112], [238, 410]]; source-observed; reader=/root/database_design |
| R21-RU02 | [src/database/connection.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/connection.rs#L1-L88) | [[1, 88], [167, 251]]; source-observed; reader=/root/database_design |
| R21-RU03 | [sqlx-core/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/transaction.rs#L1-L150) | [[1, 150], [260, 292]]; source-observed; reader=/root/database_design |
| R21-RU04 | [sqlx-postgres/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/transaction.rs#L1-L102) | [[1, 102]]; source-observed; reader=/root/database_design |
| R21-RU05 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-core/src/pool/connection.rs#L50-L125) | [[50, 125], [195, 225], [280, 355]]; source-observed; reader=/root/database_design |
| R21-SQ09-SQLITE-02 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 213-313;538-574; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-03 | [sqlx-sqlite/src/connection/worker.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/worker.rs) | 390-412;490-505;335-344; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-04 | [sqlx-sqlite/src/connection/mod.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/connection/mod.rs) | 214-287; cross-task-source-evidence; reader=/root/interop_design |
| R21-SQ09-SQLITE-07 | [sqlx-sqlite/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/transaction.rs) | complete; cross-task-source-evidence; reader=/root/interop_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
