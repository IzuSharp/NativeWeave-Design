> Historical scoped investigation retained. Current selection, new SeaORM execution and shape/migration findings are consolidated in [report.md](report.md) and the [completion record](../../../../verification/database-completion/task-status.json). Historical statements of what was not yet executed refer to that original snapshot.

# R25 addendum — SeaORM's real dynamic boundary

Date: 2026-11-12. Author: recovery continuation. Status: source-inspected design analysis; independent review pending. This supplements [the existing SeaQuery comparison](source-driven-seaquery.md), not a second research plan or a replacement ADR. The precompiled ordinary-entity profile remains the product requirement; SeaQuery + SQLx remains a proposed recommendation, not an accepted production result.

## Finding SDI-DB-01: static EntityTrait is not the whole SeaORM API

At **SeaQL/sea-orm 2.0.4, commit `db40a19a7bde7be8e1c4b346b1b70d72e87f0245`**, the complete [src/dynamic/mod.rs](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/dynamic/mod.rs) explicitly exposes runtime-typed Entity, Column and Model APIs. It marks this module unstable across minor versions. Therefore, an argument that SeaORM is categorically static-only, or that all uses of SeaORM require recompiling Rust for each new C# entity, is too broad.

The narrower original claim remains true: a newly generated static `EntityTrait` implementation with new associated Model/ActiveModel/Column/Relation types must be compiled. That does not rule out a precompiled dynamic-metadata Adapter or a useful source extension. The new consumer requirement must be evaluated against the dynamic interfaces, not dismissed from the static trait alone.

## API → implementation → test inspection

| Fixed file/range | Actual observation | Consequence |
| --- | --- | --- |
| [dynamic/entity.rs L1–205](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/dynamic/entity.rs#L1-L205) | Entity stores schema/table/column metadata privately. In this inspected file, the exposed construction path is `from_entity<E: EntityTrait>`. Column comparison methods construct SeaQuery expressions. | A runtime representation exists, but the inspected public constructor does not demonstrate importing arbitrary C# metadata. A metadata constructor is a plausible narrow extension, not an impossible task. |
| [dynamic/execute.rs L1–106](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/dynamic/execute.rs#L1-L106) | Dynamic selector construction starts from `Select<E>::select_also_dyn_model`; `one/all` execute through ConnectionTrait. | This is useful runtime projection support, not proof of a complete unknown-schema CRUD/relationship/change-tracking subsystem. |
| [dynamic/model.rs L1–204](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/dynamic/model.rs#L1-L204) | `ModelType` exposes fields; `FieldType::new` supplies a field/type descriptor; `from_query_result` maps using explicit ArrayType tags. Model access looks up fields. The module includes unsupported char decoding and feature-gated type branches. | Runtime projection decoding is available independently of inventing a new CLR or Rust type at runtime. Codec coverage, allocation and error behavior still require tests. |
| Same file L156–204 | The included test constructs a mock cake row and derives metadata from a statically declared Entity. | The test was read, not run here; it does not establish external-schema construction or a C# AOT integration result. |
| [database/connection.rs L1–95](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/database/connection.rs#L1-L95) | Public connection methods can execute builders/statements and return QueryResult; StreamTrait defines streaming interfaces. | SeaQuery + SeaORM connection/dynamic projection is a real comparison route without a per-query static business Entity. |
| [entity/base_entity.rs L65–110](https://github.com/SeaQL/sea-orm/blob/db40a19a7bde7be8e1c4b346b1b70d72e87f0245/src/entity/base_entity.rs#L65-L110) | Static entity APIs retain associated model/column/relation types. | A dynamic constructor alone must not be advertised as automatically unlocking every static ActiveModel/Relation/hook behavior. |

These ranges were inspected in this continuation. No upstream SeaORM tests or SeaORM integration binary were executed in this continuation. Git source and the independently downloaded Cargo registry package are separate identities until their relationship is verified.

## Comparison adjustment, not a predetermined library choice

Three native paths must now be compared explicitly:

**Public dynamic connection/projection path:** reuse SeaQuery to build runtime statements, SeaORM ConnectionTrait/QueryResult and ModelType to execute/decode. This can avoid a per-entity Rust build for the demonstrated API shape, but fixed-session ownership and the desired CRUD/relationship coverage need a complete fixture. Do not call statement execution the complete static ORM.

**Controlled dynamic-model extension:** add validated metadata construction in the owning SeaORM crate, then determine which existing mutation/relationship routines can be reused without a parallel ORM. A constructor patch is narrower than a full dynamic ActiveModel system. Enumerate those separately, with tests, upstream contribution, patch ownership and minor-version upgrade burden. Private fields and an unstable module justify controls, not automatic rejection. No such patch is adopted or implemented here.

**SeaQuery + SQLx:** retain the native AST/renderer and direct native execution/row conversion. For the user's explicit Fluent/CRUD/relations scope, this removes mandatory static-model code generation and the mandatory custom SeaORM transaction-trait bridge. It still requires a small checked native metadata/codec/CRUD policy layer. Rust-side field decoding into owned row batches may avoid an extra dynamic Model/FieldValue intermediate, but that is a cost hypothesis, not a benchmark result.

The existing recovered Linux/SQLite C# Native AOT probe directly supports only the third path's narrow subset. It cannot prove that the first or second path is inferior. The provisional recommendation remains the third path because its ordinary-entity feasibility has actual execution evidence and its required semantic scope is smaller; a broader ORM requirement or measured advantage may justify the SeaORM dynamic route. No user decision is needed for this ordinary technical comparison. Formal acceptance still needs an independent review of the final specification and remaining validation obligations.

## Additional source-derived constraints

The dynamic Column string helpers in entity.rs construct LIKE patterns by adding wildcard characters. They must not be silently exposed as literal .NET Contains/StartsWith/EndsWith semantics without escaping and a declared collation policy. D16's distinction between raw LIKE patterns and literal matching remains necessary.

SQLx 0.9 `Row::try_get` (`sqlx-core/src/row.rs` L112–133 at `75bc0487eb661da811bb7a3c5d158f1bd463fef4`) checks compatible types before decoding. The direct Adapter should preserve that error path, not replace it with unchecked decoding because a C# descriptor is typed. `AssertSqlSafe` is an assertion of SQL provenance, not a sanitizer. Its owned-String conversion can avoid the borrowed-str conversion's extra owned-string creation; this is an implementation opportunity, not a zero-copy claim.

The recovered query probe's managed result-size check happens after native `fetch_all` and JSON allocation. It therefore cannot establish a native intermediate-memory bound. A checked final SQL length is similarly insufficient if rendering already allocated an unbounded string. B06/B09/B11 must reserve or conservatively bound input/render/result work before allocation, or justify a fallible source extension; existing formatting unwrap paths must be included in that review.

## Existing task impact and acceptance obligations

R25 compares all three paths using this actual dynamic module. R22 checks its enabled type/NULL/precision/error coverage. D14/D16/D17 and D27/D28 retain ordinary metadata-based consumption; they do not restore mandatory per-entity Cargo. B04's normal host owns SQLx connection/runtime/lifetime; a SeaORM-specific executor is conditional on adopting that optional integration, not a prerequisite for every DB feature. B11 performs direct-native versus Adapter SQL/parameter/result differential testing; B14 retains explicit Rust CRUD, relationships, not-set/null/value updates, tenant/version predicates and Unknown recovery without silently expanding to a full tracking ORM.

Required focused fixtures: construct projection metadata from runtime field names; execute and decode a second schema with an unchanged native binary; unsupported type/null/duplicate-column/missing-field negatives; fixed-connection transaction/stream ownership; direct SQLx versus SeaORM dynamic projection allocation/copy behavior; a narrow constructor-extension compile/test if that route is pursued. Preserve real Windows/Linux AOT, clean no-Rust consumer, PostgreSQL/SQLite fault, streaming, race/fuzz and workload gates. Design choice, implementation verification and production acceptance remain distinct.
