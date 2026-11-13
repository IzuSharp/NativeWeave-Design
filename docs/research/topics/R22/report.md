# R22 — Typed native codecs, row shape, bounded results and migrations

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Current ownership

Rust metadata and SQLx codecs own database values; C# maps owned wire values into statically known CLR DTOs. The ordinary profile uses runtime metadata and precompiled codecs, not Rust Model/Projection code generated for each C# entity. Metadata content hashes describe table/column/key/codec/projection declarations and cache identity; they are not a per-schema native ABI version.

The preserved UUID/time/native binder and Python SQL counterexamples remain valid. This continuation adds fixed PG numeric source, concrete SeaORM dynamic mapping behavior, real Rust native migration tests and PG codec boundary probes. [The source manifest](../../../../verification/database-completion/source-inspection.json) distinguishes the executed crate checksum/VCS from older source-tag pins; selected files were compared by Git blob identity instead of assuming the entire package is identical.

## A new correctness failure: missing is not NULL

SeaORM2.0.4 exposes public ModelType/FieldType and can map unrelated runtime schemas with the same compiled native binary. The first experiment incorrectly expected a missing nullable field to fail. It failed: `TryGetable for Option<T>` maps SQLx ColumnNotFound to None. Original failing source/logs are preserved under `verification/database-completion/linux-attempt-1`; the corrected test contains this actual negative control.

Therefore validate the complete result shape before nullable decoding: exact expected count/unique alias or ordinal/type identity, no duplicate/missing/reordered fields, and codec compatibility. A nullable SQL NULL is allowed only for an existing declared column. The fixture uses public QueryResult.column_names and catches missing/duplicate metadata before dynamic projection. Direct SQLx `try_get` also retains type errors; no unchecked decode because the C# descriptor is typed.

## Numeric, time and streaming rules

UUID wire uses RFC4122 byte order and SQLite16-byte BLOB. Signed narrowing is checked. PostgreSQL numeric precision/scale and CLR decimal domain are explicit; SQLx rust_decimal rejects unrepresentable magnitudes and NaN but does not by itself implement every NativeWeave loss policy. A SQLx PG roundtrip fixture covers decimal, UUID, nullable integer and UTC microseconds; it observes loss for sub-microsecond input so the boundary must reject such values before encode when exactness is promised. SQLite exact decimal TEXT is roundtrip-only, not automatic numeric sorting/SUM; fixed-scale Int64 is a separate capability.

Native result batches have row and byte limits, checked multiplication/addition, exact tags/lengths and a creating-engine owner. A cursor retains its session until completion/retirement; taken batch owners outlive an operation notification independently. DTO constructor exceptions release exactly the owned batch and start normal cursor cleanup, preserving transaction outcome. Huge values can already be allocated inside an upstream row before export; advertised logical budgets are not whole-process or server-RSS limits. Provider large-field limits and measured peak memory remain necessary.

## Native migrations, not a second migration engine

Reuse SQLx Migrator's content checksum, dirty/applied-version validation and transactional apply/ledger operations through an explicit Rust administrative entry point. The executed SQLite fixture proves repeat idempotency, VersionMismatch after content drift, and rollback of DDL plus ledger on a failing migration. Metadata and production schema never change merely because an application opened a DataSource.

Source inspection finds PG migration errors may retain its session advisory lock; dedicated connection close is mandatory on error. SQLite's migration lock is a no-op, so the adapter must obtain write serialization before ledger inspection, with a dedicated connection/BEGIN IMMEDIATE transactional profile. Nontransactional DDL/maintenance requires a declared restart/repair protocol. Trusted ledger/schema identifiers must not accept raw external names because the native migrator renders these names into SQL.

B06/B07/B08/B12 now have concrete shape, range, cleanup and administrative oracles. Broad codecs, malformed wire fuzzing and product Windows/Linux AOT remain future implementation tests, not a reason to recreate native codecs in managed code.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R22-C01 | [src/Npgsql/Internal/Converters/Temporal/PgTimestamp.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Temporal/PgTimestamp.cs#L1-L44) | [[1, 44]]; source-observed; reader=database_design |
| R22-C02 | [src/Npgsql/Internal/Converters/Temporal/DateTimeConverterResolver.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Temporal/DateTimeConverterResolver.cs#L1-L120) | [[1, 120]]; source-observed; reader=database_design |
| R22-C03 | [src/Npgsql/Internal/Converters/Primitive/GuidUuidConverter.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/Converters/Primitive/GuidUuidConverter.cs#L1-L25) | [[1, 25]]; source-observed; reader=database_design |
| R22-C04 | [test/Npgsql.Tests/Types/DateTimeTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/Types/DateTimeTests.cs#L245-L281) | [[245, 281]]; test-source-observed; reader=database_design |
| R22-C05 | [src/Npgsql/NpgsqlDataReader.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataReader.cs#L238-L259) | [[238, 259], [357, 378], [500, 521], [593, 614], [952, 973], [1033, 1054], [1077, 1227]]; source-observed; reader=database_design |
| R22-C06 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R22-C07 | [src/Npgsql/NpgsqlDataSourceBuilder.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSourceBuilder.cs#L140-L225) | [[140, 225]]; source-observed; reader=database_design |
| R22-RU01 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |
| R22-RU02 | [src/driver/sqlx_postgres.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_postgres.rs#L180-L275) | [[180, 275], [828, 898], [328, 354]]; source-observed; reader=/root/database_design |
| R22-RU03 | [src/driver/sqlx_sqlite.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_sqlite.rs#L155-L254) | [[155, 254], [311, 337]]; source-observed; reader=/root/database_design |
| R22-RU04 | [sqlx-postgres/src/types/uuid.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/types/uuid.rs#L1-L38) | [[1, 38]]; source-observed; reader=/root/database_design |
| R22-RU05 | [sqlx-sqlite/src/types/uuid.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-sqlite/src/types/uuid.rs#L1-L86) | [[1, 86]]; source-observed; reader=/root/database_design |
| R22-RU06 | [sqlx-postgres/src/types/chrono/datetime.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/types/chrono/datetime.rs#L1-L112) | [[1, 112]]; source-observed; reader=/root/database_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.


Independent review reproduced the exact public API chain in three real Linux Rust tests: `Connection::begin_with("BEGIN IMMEDIATE")` yields a depth-tracked `Transaction`; `Migrator::run(&mut *tx)` uses nested savepoints and preserves that outer transaction; explicit outer rollback undoes both schema and ledger, including a failing second migration. Reject every `m.no_tx` before acquiring the transaction. Raw `query("BEGIN IMMEDIATE")` is prohibited here: it leaves SQLx `is_in_transaction()` false and causes Migrator to fail with a nested-BEGIN error. Commit only on successful migration; rollback on error, and quarantine/close on cleanup failure. The [independent source and results](../../../../verification/interop-completion/db-review-migration/result.json) prove this finite public path, not cross-process crash/recovery or the future C# product.
