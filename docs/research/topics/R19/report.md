# R19 — PostgreSQL native execution, recovery and managed comparison

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Current conclusion

The ordinary database profile uses maintainer-precompiled **SeaQuery 1.0.2 + SQLx 0.9.0**. Rust owns SQL rendering, connection/protocol, pool, transactions and database codecs. Npgsql remains source and workload comparison evidence. SeaORM is evaluated for specific reusable capabilities; it is not imposed as a schema-specific build dependency. The old DB-D004 selection of generated SeaORM models for every application is superseded.

C# supplies typed API, static metadata/DTO mapping and business code. An ordinary new entity does not change the Rust binary. A native Session holds one SQLx physical connection lease and admits one active operation; stream/transaction/cleanup retain that lease. A public Rust connection or trait object never crosses the ABI.

## Source to behavior

The additional fixed-source inspection is in [the ten-file source manifest](../../../../verification/database-completion/source-inspection.json). SQLx PG `run` checks the parameter count with `u16::try_from`, prepares/binds native arguments, sends Execute with `limit: 0`, closes the unnamed portal and waits through ReadyForQuery. Its connection tracks pending ReadyForQuery messages and updates server transaction status. Dropping a row stream stops application consumption; it does not itself prove that unread protocol bytes or server work vanished. Native cleanup must finish protocol synchronization or discard the connection before reuse.

`limit: 0` means the provider asks the server to execute the complete query. A bounded NativeWeave row batch is not a PostgreSQL portal fetch-size limit. SQL/result limits, large-field policy and admission bounds remain explicit. Whole RSS and server working memory cannot be guaranteed by counting exported batches. SQLx owns protocol implementation; NativeWeave must not create a second PostgreSQL wire driver.

The pin keeps backend process ID/secret private and has no demonstrated public immediate CancelRequest path. The accepted design behavior is cooperative cancellation before dispatch, configured native `statement_timeout` for ordinary long queries, and safe connection close/quarantine when required. An interruption request never implies rollback. A future public cancel extension must bind the backend identity and operation generation and drain before a later command; it is an optional engine capability, not an invented current API.

## TLS and unsupported behavior

The inspected TLS implementation allows `Prefer` to fall back to plaintext and `Require` does not validate certificate/hostname like `VerifyFull`. The production remote profile therefore selects VerifyFull with explicit trust configuration and rejects absent TLS support, invalid chains and hostname mismatch. Plaintext is allowed only through an explicitly named local/test configuration. The research fault proxy disables TLS to observe protocol frames; it proves nothing about TLS/auth interoperability. Credential/payload logging stays off by default.

Unknown types, incompatible result shapes, oversized parameter sets, encoding errors, failed transaction status and transport failure are distinct errors. Provider SQLSTATE is preserved without credentials. Identifiers come from validated metadata; parameter binding does not authorize table access. Administrative migration names are trusted constants or validated/quoted native identifiers.

## Concrete research and remaining implementation obligations

The new [fixture](../../../../experiments/database-completion/README.md) contains real PG timeout→failed transaction→rollback recovery, partial-row-stream drain, decimal/UUID/time boundary, COMMIT-response-loss, concurrent conflict-snapshot and migration-lock probes. Actual runs and source hashes are recorded separately in `verification/database-completion`; an ignored PG test is not a run. Prior Npgsql source findings remain comparative, not SQLx execution evidence.

B02 implements this native provider contract, TLS validation and actual Windows/Linux C# AOT consumption. B05 implements outcome/cleanup state and B06 the bounded output policy. B23 supplies like-for-like measured Npgsql/SQLx/native-versus-FFI workloads; this research does not claim Rust is faster. These product obligations do not reopen the fixed Rust ownership decision.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R19-C01 | [src/Npgsql/PoolingDataSource.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/PoolingDataSource.cs#L100-L356) | [[100, 356], [445, 455]]; source-observed; reader=database_design |
| R19-C02 | [src/Npgsql/Internal/NpgsqlConnector.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/Internal/NpgsqlConnector.cs#L2075-L2258) | [[2075, 2258], [2706, 2810], [2936, 2993]]; source-observed; reader=database_design |
| R19-C03 | [src/Npgsql/NpgsqlDataSourceBuilder.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/src/Npgsql/NpgsqlDataSourceBuilder.cs#L140-L225) | [[140, 225]]; source-observed; reader=database_design |
| R19-C04 | [test/Npgsql.NativeAotTests/Program.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.NativeAotTests/Program.cs#L1-L20) | [[1, 20]]; test-source-observed; reader=database_design |
| R19-C05 | [test/Npgsql.Tests/PoolTests.cs](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/test/Npgsql.Tests/PoolTests.cs#L47-L143) | [[47, 143]]; test-source-observed; reader=database_design |
| R19-C06 | [sqlx-core/src/pool/connection.rs](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/sqlx-core/src/pool/connection.rs#L130-L163) | [[130, 163], [195, 225], [271, 369]]; source-observed; reader=database_design |
| R19-C07 | [LICENSE](https://github.com/npgsql/npgsql/blob/d3768398c17877b3a916c3c4d87e8e11698991fc/LICENSE#L1-L18) | [[1, 18]]; license-text-observed; reader=database_design |
| R19-C08 | [LICENSE-MIT](https://github.com/transact-rs/sqlx/blob/bab1b022bd56a64f9a08b46b36b97c5cff19d77e/LICENSE-MIT) | 定位见evidence; license-text-observed; reader=database_design |
| R19-V1 | [refs/tags/v10.0.3](https://api.github.com/repos/npgsql/npgsql/git/refs/tags/v10.0.3) | 定位见evidence; release-tag-metadata-observed; reader=database_design |
| R19-RU01 | [Cargo.toml](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/Cargo.toml#L1-L195) | [[1, 195]]; source-observed; reader=/root/database_design |
| R19-RU02 | [src/database/connection.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/connection.rs#L1-L88) | [[1, 88], [167, 251]]; source-observed; reader=/root/database_design |
| R19-RU03 | [src/driver/sqlx_postgres.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/driver/sqlx_postgres.rs#L180-L275) | [[180, 275], [828, 898], [328, 354]]; source-observed; reader=/root/database_design |
| R19-RU04 | [sqlx-postgres/src/transaction.rs](https://github.com/transact-rs/sqlx/blob/75bc0487eb661da811bb7a3c5d158f1bd463fef4/sqlx-postgres/src/transaction.rs#L1-L102) | [[1, 102]]; source-observed; reader=/root/database_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
