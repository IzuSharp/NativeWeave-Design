# R23 — Ordinary typed Fluent over the native query engine

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Resolved architecture correction

C# queries are ordinary typed calls to a precompiled Rust SeaQuery/SQLx Engine. Handwritten static descriptors and optional Roslyn-generated equivalents are equal paths. No arbitrary IQueryable translation, Expression.Compile, managed SQL AST/dialect, mandatory source-captured query body or schema-specific Rust build is required. The former two-stage C# capture→Rust Entity generation→C# manifest pipeline is superseded as the ordinary application path.

The user's requirement is stronger than “developers do not handwrite Rust”: adding a supported entity must not require Rust compilation at all. Existing recovered C# Native AOT evidence already compiled a second typed entity with an unchanged native asset and rejected a wrong-entity column at compile time. The new Rust study also constructs unrelated SeaORM dynamic projection metadata without any EntityTrait declarations. Neither observation establishes a complete product Fluent implementation, but both directly invalidate the old universal per-entity build assumption.

## Why the source supports this choice

SeaQuery Select/Insert/Update/Delete statements store native runtime identifiers, expressions and values. SeaORM static EntityTrait has associated Model/Column/Relation types; that is a valid optional specialized profile, not the entire library. Its public dynamic ModelType/FieldType can decode named runtime projections. Static LoaderTrait bounds remain real and must not be waved away by the word dynamic. See [R25](../R25/report.md) and its preserved detailed addenda.

Earlier EF QueryCompiler and DapperAOT interceptor observations remain scoped comparisons. They do not force NativeWeave to build another full LINQ provider or prove that either whole library is AOT-incompatible. Roslyn generation is additive and cannot assume another generator's current-pass output is a new source input; D17 emits its own static helpers from stable explicit model inputs.

## Concrete public semantics

`Table<TEntity>`, `Column<TEntity,TValue>`, typed aliases and `Projection<TResult>` carry static metadata. Query creation binds a native owner and capability profile. Each operation invokes a typed native method or bounded command envelope interpreted solely by the native builder. A convenience lambda executes as a normal C# delegate over expression proxies, not over materialized domain objects or an arbitrary expression interpreter. Unsupported methods are outside that API; no hidden client evaluation or fallback provider.

Parameter values snapshot at the documented mutation/seal/submission boundary. Native mutation has one writer, independent of SafeHandle physical lifetime. Query/alias/expression owners must match; poisoned/sealed/disposed objects reject further mutation. Immutable execution shapes and per-execution parameter storage are separate so an await cannot observe a later mutation of an unrelated C# closure.

## AOT, errors and verification

Generation covers descriptors, stable IDs/content hashes, declared codecs, constructor/reader code, closed generic registrations and useful diagnostics. It never runs Cargo, calls a database, discovers arbitrary runtime types or executes user property getters. DTO failures preserve error and owner cleanup; result-shape validation occurs before nullable decoding, including SeaORM's missing-column-as-null negative control.

D17 now provides distinct ABI responsibilities and diagnostic/compatibility matrices. B10 tests incremental generation and static parity; B11 owns native builder/binder; B12 owns safe CLR materialization; B13 owns typed runtime Fluent. The product no-Rust consumer test requires RID-free dotnet build/run and explicit-RID Native AOT with unchanged native hash after a new entity. Existing finite AOT evidence is reused, not inflated into completed Windows/Linux product acceptance.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## Pinned Source Entry Points and Actual Reading

| Claim | Pinned file/source | Actual scope and evidence category |
| --- | --- | --- |
| R23-C01 | [src/EFCore/Query/Internal/QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs#L60-L115) | [[60, 115], [134, 156]]; source-observed; reader=database_design |
| R23-C02 | [src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT.Analyzers/CodeAnalysis/DapperInterceptorGenerator.cs#L53-L74) | [[53, 74], [207, 236], [515, 543]]; source-observed; reader=database_design |
| R23-C03 | [src/Dapper.AOT/Internal/AsyncQueryState.cs](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/src/Dapper.AOT/Internal/AsyncQueryState.cs#L15-L54) | [[15, 54], [76, 116]]; source-observed; reader=database_design |
| R23-C04 | [License.txt](https://github.com/DapperLib/DapperAOT/blob/0e071bf05e54caecfa98c885b075fa3e247f3ecc/License.txt#L1-L10) | [[1, 10]]; license-text-observed; reader=database_design |
| R23-C05 | [docs/features/incremental-generators.cookbook.md](https://github.com/dotnet/roslyn/blob/b907b90240f9f22873227aa510794dd280d61f57/docs/features/incremental-generators.cookbook.md) | [[1, 230]]; cross-task-source-evidence; reader=/root; source task=R06 |
| R23-V1 | [refs/tags/1.1.0](https://api.github.com/repos/DapperLib/DapperAOT/git/refs/tags/1.1.0) | See evidence for location; release-tag-metadata-observed; reader=database_design |
| R23-RU01 | [src/entity/base_entity.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/base_entity.rs#L65-L135) | [[65, 135]]; source-observed; reader=/root/database_design |
| R23-RU02 | [sea-orm-codegen/src/entity/writer/compact.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/src/entity/writer/compact.rs#L1-L159) | [[1, 159]]; source-observed; reader=/root/database_design |
| R23-RU03 | [sea-orm-codegen/tests/compact/fruit.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/sea-orm-codegen/tests/compact/fruit.rs#L1-L39) | [[1, 39]]; test-source-observed; reader=/root/database_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
