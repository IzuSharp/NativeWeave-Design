# R25 — Native ORM reuse without mandatory per-entity compilation

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Selection based on actual public and internal boundaries

The ordinary profile selects **SeaQuery + SQLx** for native query construction, dialect, execution, pool, transactions and codecs, with a small Rust metadata/ownership/capability layer. This is now a concrete design choice, subject to independent contract review. C# owns typed Fluent declarations and static DTO materialization. It does not own SQL semantics, relation-query execution, identity-map machinery or a hidden full ORM.

SeaORM is neither forced by its name nor dismissed as static-only. The preserved [SeaQuery investigation](source-driven-seaquery.md) and [dynamic-module correction](seaorm-dynamic-boundary.md) are supplemented by an executed SeaORM2.0.4 public dynamic-projection fixture. It constructs ModelType/FieldType for unrelated runtime tables and maps rows without a Rust EntityTrait declaration. This is positive evidence for a reusable native SeaORM capability with no entity recompilation.

## Native capability allocation

| Capability | Concrete owner and integration |
| --- | --- |
| SQL AST, expressions, CRUD, join/CTE/window/dialects | SeaQuery public dynamic APIs; native Adapter checks capability/ownership/budgets |
| Protocol, driver, physical pool, native transactions | SQLx; reuse directly, no managed replacement |
| Runtime projection metadata and native dynamic values | SeaORM public ModelType/FieldType/QueryResult is a supported comparison/optional integration; prevalidate actual row shape |
| Static ActiveModel hooks and typed relationship graph | SeaORM specialized native profile with explicit build/upgrade cost; not ordinary entity behavior |
| Explicit ordinary relation queries and CAS changesets | Rust applies declared metadata to native SeaQuery joins/updates and SQLx execution; C# only expresses typed intent |
| Batch eager loading with native grouping | Existing SeaORM loader source is the reuse candidate, but current ModelTrait/EntityTrait bounds require a controlled dynamic extension before promising arbitrary runtime metadata |
| CLR construction | Static C# projection reader/constructor; no reflection SQL/ORM engine |

## Deep relation-source finding

SeaORM LoaderTrait avoids N+1 by loading relation hops and regrouping results by ValueTuple. The inspected loader_impl remains generic over ModelTrait/EntityTrait, reads relation key metadata from static associated columns and uses all() to collect rows. The dynamic projection helper participates in many-to-many key extraction; it does not erase the outer static trait boundary. Duplicate-key reduction and ordered reconstruction are valuable existing native algorithms. A dynamic Entity constructor alone cannot automatically make this loader a complete runtime-metadata ORM.

Accordingly, the initial public ordinary surface supports explicit native joins, bounded relation result projections and explicit updates/CAS. Do not silently ship lazy loading/full graph persistence/change tracking. If batch eager-loading is admitted, prefer an upstream extraction/generalization of the existing native loader over reimplementing it in C#: descriptor access, bounded collection, key/tenant/arity validation and result regrouping form the reviewed extension boundary. Its conformance tests must use the upstream duplicate-key/empty/many-to-many cases plus arbitrary runtime schemas. No fork is currently required for the chosen baseline.

## New negative control and cost implications

SeaORM dynamic nullable decoding maps a missing column to None through Option<T>. The original failed fixture and corrected shape-preflight test are preserved. Every integration must validate unique names/ordinals/type shape before interpreting NULL. Public API availability alone was insufficient to establish correctness.

SeaQuery/SQLx direct row mapping avoids mandatory dynamic FieldValue objects when the requested C# projection can be encoded directly. That is a plausible allocation advantage, not measured superiority. Direct builder calls are the correctness route; batching is an optimization only after representative workloads justify transport/decoder costs. Static SeaORM hooks and optional dynamic projections remain separately measured alternatives. New native algorithms/codecs can require a maintainer module update; new ordinary supported entities cannot.

## Closure and future obligations

Source inspection, prior same-native-hash C# AOT evidence and the new dynamic projection/native join/changeset/codec/migration probes resolve the architecture questions. Existing report claims and source identities remain historical evidence below; schema-specific default decisions are explicitly superseded. Independent review decides research/design acceptance. B04/B09–B14 then implement the chosen scopes and both-OS AOT, semantic differential, race/fuzz and memory/performance tests. The existence of those future tests is not authorization to leave this architecture undecided forever.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## 固定源码入口与实际阅读

| Claim | 固定文件/来源 | 实际范围与证据类别 |
| --- | --- | --- |
| R25-C01 | [src/EFCore/ChangeTracking/Internal/StateManager.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/ChangeTracking/Internal/StateManager.cs#L324-L365) | [[324, 365], [1423, 1490]]; source-observed; reader=database_design |
| R25-C02 | [src/EFCore/ChangeTracking/Internal/ChangeDetector.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/ChangeTracking/Internal/ChangeDetector.cs#L130-L179) | [[130, 179], [242, 317]]; source-observed; reader=database_design |
| R25-C03 | [src/EFCore.Relational/Update/AffectedCountModificationCommandBatch.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore.Relational/Update/AffectedCountModificationCommandBatch.cs#L410-L437) | [[410, 437], [526, 590]]; source-observed; reader=database_design |
| R25-C04 | [test/EFCore.Specification.Tests/OptimisticConcurrencyTestBase.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/EFCore.Specification.Tests/OptimisticConcurrencyTestBase.cs#L28-L63) | [[28, 63], [351, 407]]; test-source-observed; reader=database_design |
| R25-C05 | [src/EFCore/Query/Internal/QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs#L60-L115) | [[60, 115], [134, 156]]; source-observed; reader=database_design |
| R25-C06 | [src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs#L53-L74) | [[53, 74], [207, 236], [515, 543]]; source-observed; reader=database_design |
| R25-C07 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R25-RU01 | [Cargo.toml](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/Cargo.toml#L1-L195) | [[1, 195]]; source-observed; reader=/root/database_design |
| R25-RU02 | [src/entity/base_entity.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/base_entity.rs#L65-L135) | [[65, 135]]; source-observed; reader=/root/database_design |
| R25-RU03 | [src/entity/active_model.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/active_model.rs#L1-L100) | [[1, 100], [215, 240], [340, 405], [440, 465]]; source-observed; reader=/root/database_design |
| R25-RU04 | [src/entity/relation.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/relation.rs#L1-L145) | [[1, 145], [301, 326]]; source-observed; reader=/root/database_design |
| R25-RU05 | [src/executor/update.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/update.rs#L1-L220) | [[1, 220]]; source-observed; reader=/root/database_design |
| R25-RU06 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |
| R25-RU07 | [tests/relational_tests.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/tests/relational_tests.rs#L619-L710) | [[619, 710], [711, 784]]; test-source-observed; reader=/root/database_design |
| R25-RU08 | [tests/transaction_tests.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/tests/transaction_tests.rs#L142-L169) | [[142, 169], [206, 235], [272, 300], [994, 1027], [373, 455]]; test-source-observed; reader=/root/database_design |
| R25-RU09 | [sea-orm-codegen/src/entity/writer/compact.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/src/entity/writer/compact.rs#L1-L159) | [[1, 159]]; source-observed; reader=/root/database_design |
| R25-RU10 | [sea-orm-codegen/tests/compact/fruit.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/tests/compact/fruit.rs#L1-L39) | [[1, 39]]; test-source-observed; reader=/root/database_design |
| R25-RU11 | [LICENSE-MIT](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/LICENSE-MIT#L1-L25) | [[1, 25]]; source-observed; reader=/root/database_design |
| R25-ROOT04 | [diesel_dynamic_schema/src/lib.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel_dynamic_schema/src/lib.rs) | whole_file; cross-task-source-evidence; reader=/root |
| R25-ROOT05 | [diesel/src/query_builder/select_statement/boxed.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel/src/query_builder/select_statement/boxed.rs) | [[1, 190]]; cross-task-source-evidence; reader=/root |
| R25-ROOT06 | [diesel_dynamic_schema/tests/dynamic_values.rs](https://github.com/diesel-rs/diesel/blob/4007d771b1e808839f771a693f6bae9f821f0e64/diesel_dynamic_schema/tests/dynamic_values.rs) | [[1, 140]]; cross-task-source-evidence; reader=/root |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
