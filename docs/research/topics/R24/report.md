# R24 — Native SQL semantics, parameters and explicit relations

Research consolidation: 2026-11-12 (America/Los_Angeles); author `/root/database_research`. Baselines Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan `5b346ebb5acdb387077d0faae16b00bbc77cb299`. **Independent acceptance review pending; no product implementation or performance acceptance claimed.** Current evidence and explicit stage obligations are in [evidence.json](evidence.json), [coverage.json](coverage.json), and [completion record](../../../../verification/database-completion/task-status.json).


## Current design

SeaQuery is the SQL semantic constructor and renderer, SQLx the execution/codec authority. C# typing limits invalid composition but does not impose complete LINQ/CLR semantics on SQL. The source-driven contract covers explicit CRUD, comparisons, SQL3VL/null tests, join/group/aggregate/order, supported subquery/CTE/window/set operations and backend capability rejection. Native engine capability is exposed through versioned bindings; unsupported semantics fail before database send.

The previous managed AST/provider and compulsory static SeaORM model assumptions are superseded. Existing SQLite semantic results remain valid. R24's native engine evidence now also includes an executed SeaQuery LEFT JOIN/group/count/sum query compared with separately written SQL over the same actual SQLx SQLite connection. It preserves the distinction between an unmatched row, a matched nullable amount, COUNT(column)=0 and SUM=NULL. The test is finite, not universal relational equivalence.

## Parameters and identifiers

Values are native bound parameters. Identifier quoting prevents syntax confusion but does not authorize table/tenant access; metadata IDs and raw identifier imports require allowlists and native validation. SQLx's AssertSqlSafe is a provenance assertion only. Typed fallible binding propagates encoding errors and rejects overflow, invalid UTF8, mismatched null/type/codec and excess counts before dispatch; no string concatenation fallback.

The existing native-slices fixture already demonstrates the SQLite silent-row-lock negative control and explicit rejection, unsigned overflow before send, encoder rollback and runtime tables. Do not repeat it or promote only a renderer result into real execution. Each native backend/operator pair needs a declared capability and test oracle; SQLite's ignored FOR UPDATE/SELECT INTO/SEARCH/CYCLE and unsupported subquery operators cannot be accepted silently.

## Relational and mutation semantics

SQL3VL is normative. WHERE retains TRUE; NOT UNKNOWN stays UNKNOWN. NULL-safe comparison is a named operator; nullable integer NOT(x>y) versus x<=y equivalence does not justify NaN/custom-order rewrites. LIKE literal conveniences escape wildcard and escape bytes and declare collation; raw patterns are a separate API. LEFT JOIN ON predicates cannot be moved to WHERE. Paging with semantic guarantees requires a unique tie-breaker and explicit snapshot policy.

Rust changesets distinguish NotSet, Null and Value. Native UPDATE predicates always include the declared key, tenant and expected version; affected-row mismatch becomes an explicit concurrency conflict. A real SeaQuery/SQLx fixture performs a nullable update, preserves omitted fields and the other tenant, and observes 1 then 0 affected rows for repeated expected-version writes. This is a native capability binding, not managed tracking.

## Advanced native capabilities and limits

Validate CTE shape before native assertions. The pinned SelectStatement has one optional named-window slot; bind native inline/single-window capability and fail explicit unsupported multi-named-window requests until an upstream extension is adopted. Do not produce SQL in C# to fill gaps. Multiple statement/query features can be bound independently against the same native metadata without new Rust entity types.

Budget the operation count/depth/values before building and parameters before binding; output-length checks after allocating a SQL string are not allocation protection. SeaQuery uses clones/infallible allocations in inspected paths; a bounded operation envelope and conservative admission can limit requested work, not guarantee recovery from every allocator failure. Process-level availability and measured whole-memory limits remain R34/B22/B23 responsibilities.

D16 records the native method/lifetime boundary, supported semantics and explicit rejection table. B11/B13 implement differential SQL+ordered-values+actual-result cases for both PG/SQLite, not only text goldens. No performance superiority, complete EF compatibility or full arbitrary SQL validation is claimed.

## Historical source citations retained

The following original source observations are retained with their original reader identities. They do not restore superseded integration decisions or claim that this author reread every old range.

## Pinned Source Entry Points and Actual Reading

| Claim | Pinned file/source | Actual scope and evidence category |
| --- | --- | --- |
| R24-C01 | [src/EFCore.Relational/Query/SqlNullabilityProcessor.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore.Relational/Query/SqlNullabilityProcessor.cs#L38-L79) | [[38, 79], [728, 751], [856, 879], [1118, 1141], [1398, 1421], [1875, 2015]]; source-observed; reader=database_design |
| R24-C02 | [test/EFCore.Relational.Specification.Tests/Query/NullSemanticsQueryTestBase.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/test/EFCore.Relational.Specification.Tests/Query/NullSemanticsQueryTestBase.cs#L1628-L1656) | [[1628, 1656], [2081, 2113]]; test-source-observed; reader=database_design |
| R24-C03 | [src/prepare.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/prepare.rs#L1-L196) | [[1, 196]]; source-observed; reader=database_design |
| R24-C04 | [src/query/traits.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/query/traits.rs#L1-L131) | [[1, 131]]; source-observed; reader=database_design |
| R24-C05 | [src/backend/query_builder.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/backend/query_builder.rs#L678-L701) | [[678, 701], [715, 738], [825, 848], [1070, 1101], [1108, 1131], [1909, 1932]]; source-observed; reader=database_design |
| R24-C06 | [src/backend/sqlite/query.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/src/backend/sqlite/query.rs#L21-L47) | [[21, 47], [65, 86]]; source-observed; reader=database_design |
| R24-C07 | [tests/postgres/query.rs](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/tests/postgres/query.rs#L5-L48) | [[5, 48], [166, 184]]; test-source-observed; reader=database_design |
| R24-C08 | [LICENSE-MIT](https://github.com/SeaQL/sea-query/blob/f2d5e04d30919c342da1f8845ff1fde46e3308fc/LICENSE-MIT#L1-L25) | [[1, 25]]; license-text-observed; reader=database_design |
| R24-C09 | https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-value-types | See evidence for location; official-documentation-observed; reader=database_design |
| R24-C10 | https://www.sqlite.org/lang_expr.html | See evidence for location; official-documentation-observed; reader=database_design |
| R24-C11 | [sqlite_semantics_probe.py](sqlite_semantics_probe.py) | actual script SHA-256 `f78a340af85a34b16464531b0ad6c3249f33aeda1d8d11e9dff4e8e51570b455`; result/logs in [evidence.json](evidence.json); executed-reference-experiment; reader=database_design |
| R24-V1 | [refs/tags/1.0.2](https://api.github.com/repos/SeaQL/sea-query/git/refs/tags/1.0.2) | See evidence for location; release-tag-metadata-observed; reader=database_design |
| R24-RU01 | [src/query/helper.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/query/helper.rs#L625-L810) | [[625, 810], [811, 838]]; source-observed; reader=/root/database_design |
| R24-RU02 | [src/entity/relation.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/relation.rs#L1-L145) | [[1, 145], [301, 326]]; source-observed; reader=/root/database_design |
| R24-RU03 | [src/executor/select.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/executor/select.rs#L266-L324) | [[266, 324], [869, 925]]; source-observed; reader=/root/database_design |

## CI confirmation at the published fixture commit

GitHub run `43388468172`, source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, independently executed the same five metadata/SQLite cases on Windows and Linux and all six PostgreSQL cases on Linux PostgreSQL 18.0. The author read raw suite logs and verified every archived file, input snapshot and stream hash; the [confirmation](../../../../verification/database-completion/ci-confirmation.json) records exact artifact identities, image digest and CRLF/LF differences. These are 11 unique native research cases with 16 CI executions, not new product/AOT tests or a second technical reviewer. This task claims only its mapped cases above.
