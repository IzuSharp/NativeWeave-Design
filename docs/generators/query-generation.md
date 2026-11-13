# D17 — Static metadata and DTO generation, not a second SQL compiler

Contract: **C-QUERYGEN-001@0.3.0**; design candidate. The registry records exact-content independent review and acceptance; product implementation/release gates remain in Delivery. Existing task D17 and B09/B10/B12/B13 are retained. Source evidence and executed scope: [R25](../research/topics/R25/source-driven-seaquery.md), [recovered probe](../research/source-driven-evidence/README.md). The previous declaration-only LINQ plus generated per-application Rust Entity/dispatcher pipeline is superseded as the ordinary route.

## 1. Required application experience

An application references NativeWeave's managed facade and a maintainer-precompiled Rust database NuGet. It defines ordinary C# entities and projections, uses typed Fluent APIs, restores/builds/runs locally, and publishes as Native AOT. Adding an entity using existing supported native codecs/operators must not invoke Rust compilation or wait for CI. This is a required product experience; the recovered explicit-RID Linux prototype demonstrates only part of it.

No IQueryable provider, runtime expression compilation, Reflection.Emit, dynamic proxy mapper, runtime generic construction or broad reflective setter path is required. Full C# predicate/LINQ semantics are not the query contract. C# business code remains ordinary compiled code; database semantics are those explicitly documented in D16 and performed by native SeaQuery/SQLx.

## 2. What is generated and what is not

Generate typed table/column/projection descriptors, static constructor/reader code, explicit nullable/value codec tables, optional immutable changeset descriptors, AOT-visible closed generic registrations and compile diagnostics. Handwritten static equivalents use exactly the same native Engine, supported API and verification path. A generator is a productivity tool, not the only way to express runtime-native queries.

Do not generate C# SQL dialects, a query optimizer, hidden client evaluation or application-specific Rust Entity/ActiveModel code in the normal profile. Do not contact a database/network, launch Cargo, alter native libraries or execute user model property getters during generation. A separate explicit maintainer/custom profile may generate a specialized SeaORM native model package; it is not a transitive requirement for ordinary Fluent data access.

## 3. Incremental pipeline and deterministic inputs

Use syntax filtering followed by semantic symbols for explicitly opted-in model/projection declarations. Resolve property type/nullability, declared table/column names, keys, codecs, allowed constructor/member assignment and explicit relationship metadata. Diagnostics bind to source spans. Output names and ordering derive from stable fully qualified metadata identities, not dictionary iteration, timestamps or random GUIDs.

Generate directly into the consumer compilation; do not expect to read another generator's generated syntax in the same pass. Shared declarations belong in an explicit schema input or reusable generator model, with a versioned schema and tests. Build integration owns any explicit multi-stage maintainer work. Analyzer/generator host compatibility is tested independently of application target framework version.

A minimal descriptor declaration (draft, not compiled product API):
```csharp
[WeaveTable("students")]
public sealed partial record Student(
    [property: WeaveKey] long Id,
    string Name,
    int Age);
```

Generated shape (illustrative, not executed):
```csharp
public static class Students
{
    public static readonly Table<Student> Table = /* validated static descriptor */;
    public static readonly Column<Student, long> Id = /* column and codec id */;
    public static readonly Projection<Student> Row = /* static constructor mapping */;
}
```
C# code and model metadata vary; the native binary does not. The exact attribute/API names are provisional. The recovered probe used handwritten static descriptors and DTO constructors, so it is evidence for that path, not for this generator's implementation.

## 4. Static materialization and errors

Projection descriptors contain ordered column/codec IDs, nullability and expected result shape. Rust validates and emits the bounded typed batch; C# checks the matching shape and invokes direct typed readers/constructors. Database conversions and provider semantics remain Rust-owned; converting an owned wire value to a CLR DTO is boundary materialization, not a second ORM engine.

A mapping failure or user constructor exception stops iteration, releases the batch in finally, closes/drains the cursor according to D15/D06 and preserves any transaction outcome. No reflection or stringification fallback. Non-null targets receiving SQL NULL, integer narrowing/precision loss, invalid UTF-8 and unknown codec IDs produce explicit failures. Ordinary DTO strings/bytes own a managed copy; zero-copy views are separate lifetime-scoped APIs and cannot escape by default.

Runtime JSON mapping uses explicitly supplied static JsonTypeInfo where relevant. Closed generics must be AOT-visible; an application cannot invent an arbitrary result type from an untrusted runtime name. Boxing, descriptor startup allocation and generated code-size costs are measured rather than presumed zero.

## 5. Fluent binding without method-body capture

Calls to typed native-backed operators are ordinary C# calls. A convenience lambda over expression proxies is a normal builder delegate, not an arbitrary domain-object predicate interpreted later. No source generator rewrites every method invocation or assumes it can intercept any call. Unknown C# methods are simply not part of the query API. Feature-gated operations resolve against the selected native profile and are also validated natively at execution.

Dynamic UI filtering uses validated table/field/operator metadata and parameters, retaining finite node/depth/byte limits. It does not require a serializable full C# expression tree or a universal Core query IR. B09 may define compact transport operations if batching wins; semantic evaluation stays in native SeaQuery.

## 6. Diagnostics and compatibility

Do not silently reuse old diagnostic meanings. The prior declaration-only NWQ0001–NWQ0016 family remains associated with the superseded experimental profile. Proposed new static-metadata diagnostics:

| ID | Error and remedy |
|---|---|
| NWQ0101 | Model member has no enabled native codec; select an explicit supported mapping/profile |
| NWQ0102 | Nullable database column mapped to non-null target without an explicit policy |
| NWQ0103 | Ambiguous constructor/member mapping; declare the intended static constructor |
| NWQ0104 | Duplicate or inconsistent metadata/alias/key declaration |
| NWQ0105 | Required capability absent from the selected package's compile-time profile; native runtime validation remains mandatory |
| NWQ0106 | Unsupported generator input/dependency shape; use explicit shared input or handwritten static descriptors |
| NWQ0107 | AOT mapping would require dynamic code or unbounded reflective discovery; supply static mapping |

Cross-entity/type mismatch should primarily fail through ordinary C# typing, as the recovered negative fixture demonstrates. Dynamic runtime profile failures remain structured domain errors, not fake compile diagnostics. Version changes to metadata schema/native capabilities require explicit generator/package compatibility checks; a business model hash is not an ABI version.

## 7. Build/package and verification

See D10. The normal consumer command path is restore → C# compilation/generation → local run; publication adds Native AOT and supported native linkage, not application Cargo. Test on a machine without Rust, with no network after allowed restore, both RID-free local commands and explicit-RID publish. Rebuild the C# app after adding a second entity/projection/query while checking the native asset hash is unchanged.

B10 owns incremental stability, deterministic output, compiler-version fixtures, diagnostic spans and negative unsupported types. B12 owns static DTO decoding and exception cleanup. B13 owns runtime Fluent binding and compile-time type rejection; B11 owns native query/binding behavior. A13/A16/B24 own package and platform matrices. They can start using versioned interface fixtures rather than waiting for full domains.

Required evidence: generated-source golden files, incremental cache behavior when unrelated/model files change, wrong entity/value/nullability/constructor negatives, handwritten-versus-generated parity, no dynamic-code/trimming suppression, real Windows/Linux AOT execution, constructor exception and cursor/buffer cleanup, native profile mismatch, schema drift, large field/batch budgets and complete query semantic differential tests. A generator unit test is not an AOT consumer test. No production generator execution is claimed in this research revision.

## 8. Fixed descriptor and operation rules for Codex

A descriptor's canonical content includes schema-format version, logical metadata
ID, validated names, scalar codec and nullability, primary/foreign keys, relation
alias/arity and ordered projection fields. Native capability/ABI versions are
separate from that business metadata hash. A second supported C# entity registers a
second descriptor; it does not manufacture a new Rust type, rewrite Cargo.lock or
change native assets. Runtime dynamic filters resolve only declared descriptors.

| Phase | Exact obligation | Owner |
| --- | --- | --- |
| Generator input | Stable syntax/semantic equality, no timestamps/order instability; errors point to source spans | B10 |
| Build | Emit static descriptors/readers; generated and handwritten forms use same API; no Cargo or database call | B10/A13 |
| Query call | Entity/value types checked by C#; native owner/generation/profile checked at entry | B13/B11 |
| Seal/submission | Snapshot mutable parameters and freeze native query; reuse shape with independent execution values | B11/B13 |
| First result | Match complete ordered shape and reject duplicates/missing/type mismatches before NULL interpretation | B06/B12 |
| DTO creation | Direct typed constructor; exception releases owned batch and closes cursor through async contract | B12 |
| Compatibility | Unknown metadata schema or required codec fails early, with no reflection/provider fallback | B09/B24 |

New research found a concrete reason for the first-result rule: SeaORM dynamic
nullable decoding can map a missing column to None. The native preflight is therefore
mandatory even for generated DTOs. Application static typing cannot validate a
malformed or schema-drifted native result.

Acceptance examples must include compile failures for wrong entity/value types,
runtime mixed-query aliases, Dispose/seal races, unknown dynamic field/operator,
missing/duplicate result columns, constructor failure, schema hash drift, and a
new entity in a no-Rust consumer with unchanged native binary hash. These are final
implementation instructions; their product execution is recorded in Delivery, not
fabricated as already completed Documentation work.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.


The optional SeaORM profile can inspect actual provider shape through public `QueryResult::try_as_pg_row` / `try_as_sqlite_row`, then SQLx `Row::columns` / `Column::type_info`. These borrowed views remain inside the row owner lifetime; no private field or fork is needed. Validate provider type compatibility rather than assuming a declared nullable field proves the result column exists; SQLite NULL/dynamic affinity still follows the explicit codec/null policy. The missing-column negative control remains part of the research fixture.
