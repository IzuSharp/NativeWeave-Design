# R19–R25 follow-up — source-driven SeaQuery integration

Date: 2026-11-12. Status: source-inspected, recovered finite experiment executed; **proposed architecture, independent review pending**. Existing report/evidence files remain historical records. This follow-up narrows and revises their default integration route rather than claiming all R19–R25 research is complete.

## 1. Fixed evidence and coverage

SeaQuery **1.0.2 / f2d5e04d30919c342da1f8845ff1fde46e3308fc**; SeaORM **2.0.4 / db40a19a7bde7be8e1c4b346b1b70d72e87f0245**; SQLx **0.9.0 / 75bc0487eb661da811bb7a3c5d158f1bd463fef4**, canonical repository `transact-rs/sqlx`. Paths/ranges and file hashes are in [source index](../../source-driven-evidence/source-inspection.json). The source snapshots were recovered, then selected mechanisms re-read in the recovery session. Upstream tests below were **read, not executed here**. Executed registry crates are identified separately by the recovered Cargo.lock; Git/crate byte identity has not been verified.

| Mechanism | Inspected source | Observed behavior / relevance |
|---|---|---|
| Dynamic SELECT state | `src/query/select.rs:40–64` | Native vectors of projections/from/join/groups/orders/unions, ConditionHolder and optional WithClause/window. Business entities are not Rust generic type parameters of SelectStatement. |
| Runtime identifiers | `src/types/iden/core.rs:1–139` | DynIden is `Cow<'static,str>` in this pin; Alias/String inputs become native identifier values. Do not carry an old Arc-based layout assumption across versions. |
| Expressions / conditions | `src/expr/enum.rs:1–37`; `src/query/condition.rs:1–74,120–143` | Native non-exhaustive Expr covers unary/binary/function/subquery/value/case; Condition stores nested native expressions. Rust must interpret native variants. |
| CRUD | insert `49–78,228–243,487–524`; update `35–64`; delete `40–62` | Dynamic columns/values/conditions/returning; checked insert shape errors exist. Use fallible values operations rather than `values_panic`. |
| Native rendering | `src/query/traits.rs:5–25,83–87`; backend query_builder `124–230` | Build creates SqlWriterValues, delegates dialect rendering, returns SQL and a separate ordered Values sequence. |
| CTE/window/aggregate/join | with `439–475`; window `75–104`; backend query_builder `886–944,1691–1728` | Reuse native structures and renderer. Empty/missing CTE data can assert/unwrap. SelectStatement has one optional named-window slot in this pin; arbitrary multiple named definitions are not assumed. |
| Backend mismatch | SQLite query `1–101`; PostgreSQL query `34–37,359–385` | SQLite ignores row locks/SELECT INTO/SEARCH/CYCLE in these paths, panics on unsupported subquery operators; PostgreSQL uses numbered `$` placeholders and native null-order/enum handling. |
| Value and driver adaptation | value `231–320`; sea-query-sqlx sqlx `1–28`; sqlx_sqlite `1–65,123–155` | Typed optional native Value variants depend on enabled features; SQLx bridge wraps built SQL/Values. Some SQLite conversions unwrap, unsupported variants panic, and add errors are discarded. |

Relevant tests read: `tests/error.rs:1–19` (column/value shape); PostgreSQL query `90–166` (group/aggregate/having/join), `921–998` (ordering/distinct), `1085–1114` (CTE); SQLite query `325–350` (nested conditions), `1013–1067` (LIKE, window and parameterized GLOB). These establish expected upstream examples, not universal SQL validity or executed adapter coverage.

## 2. Answer: can precompiled native code serve new C# entities?

**Yes within the dynamic metadata and enabled native capability profile.** A SELECT/INSERT/UPDATE/DELETE statement already accepts runtime identifiers, values and composition in native data structures. The adapter is compiled once against SeaQuery; it receives application-specific names/types/parameters through its stable boundary. Adding a Student or User with existing scalar codecs changes C# metadata/DTO code and the database schema, not the native engine's Rust generic type inventory.

This is supported both by the inspected dynamic structures and by the recovered Linux x64 experiment: local NuGet consumption, actual Native AOT SQLite queries, a second C# entity, native asset hash unchanged, and a wrong-entity column compile rejection. See [raw evidence and limits](../../source-driven-evidence/README.md). This does not mean an unknown Rust Value variant, new SQL operator, provider, aggregate extension or native algorithm can be created without updating the Engine.

C# compile-time types protect ordinary application composition; the native boundary must still validate metadata, shape, backend capability, sizes and ownership. Quoting an identifier prevents syntax confusion, not unauthorized access to another table. Tenant/security policy must not trust unvalidated table identifiers supplied by untrusted input.

## 3. Capability allocation

**Bind directly through public Rust APIs:** CRUD, dynamic identifiers, expressions, all/any/negated conditions, order/group/having, joins, subqueries, supported CTE/window/aggregate constructs and backend rendering. This is deep reuse because the native AST and renderer perform the work, not because private fields cross the ABI.

**Light Adapter:** owned UTF-8/bytes and typed null values, fallible conversions, query/resource handles, capability rejection, panic quarantine, batched result transfer and async operation lifetime. New identifiers are data. Native dialect renderers remain upstream implementations.

**Metadata / optional C# generation:** entity table/column/codec descriptors, typed `Column<TEntity,TValue>`, projection ordinals/nullability, static DTO constructors, diagnostics and closed generic registrations. A generator is not needed to build native SQL; handwritten static metadata uses the same Engine.

**Potential source extension:** fallible parameter binding and multiple named-window definitions when required. An upstream extension or controlled patch may be appropriate; neither is implemented or necessary to claim the finite baseline. Record exact symbols/tests and maintenance cost before choosing a fork.

**Not SeaQuery responsibilities:** connections, network I/O, pools, transactions, cancellation and row execution (SQLx); typed Entity/ActiveModel lifecycle, relation traits and ORM-specific hooks (SeaORM); NativeWeave's managed DTO construction, stable ABI, authorization, cross-language retirement and whole-process budgets.

## 4. SeaORM versus SQLx, not a predetermined slogan

SeaORM's `EntityTrait` (`src/entity/base_entity.rs:57–140`) has associated Model/ActiveModel/Column/Relation/PrimaryKey types. Its ActiveModel insert/update path (`src/entity/active_model.rs:225–235,347–402`) invokes hooks and executes through the Entity's operations. This is valuable typed native ORM behavior, but the previous proposal compiled a new Rust Entity module for each application's model. That coupling belongs to that **chosen static profile**, not to every possible Rust-backed database abstraction.

SeaORM also offers ConnectionTrait/StreamTrait (`src/database/connection.rs:1–88`) and TransactionTrait (`181–216`). Passing raw Statements through those interfaces does not magically supply the static Entity's relationship/hook semantics. For the ordinary no-Cargo application path, SeaQuery + SQLx is therefore the better supported **default candidate** after this comparison. Retain static SeaORM as a specialized extension when its complete typed behavior is needed and a separately built module is acceptable.

SQLx owns actual execution and connection reuse. Inspected transaction `112–133,265–279` and pool connection `78–115,198–209,275–327` confirm distinctions between successful commit/rollback, queued rollback on Drop, asynchronous pool return/close and cleanup. None makes cancellation equivalent to a known rollback, nor local handle release equivalent to a known remote COMMIT result. Preserve D15's multidimensional state and quarantine rules.

## 5. Compare minimal boundaries

| Candidate | Benefit | Cost / limit | Disposition |
|---|---|---|---|
| Direct opaque native builder/expressions | Native AST is the semantic owner; no second SQL compiler; finite prototype exists | FFI calls, ownership transitions, expression handles, single-writer enforcement | Correctness/reference route |
| Batched operations applied to native builder | Amortizes boundary crossings and UTF-8 copies | Command bytes, validator/decoder, partial-error handling; must not become an independent SQL semantic IR | Compare with real workloads before selection |
| Generated static native calls | Known metadata/constructors, fewer repeated allocations possible | Generated code size, compiler compatibility, build complexity | Optional fast path / static mapping, not mandatory query capture |
| Full C# SQL AST/dialect/provider | Familiar LINQ provider machinery | Reimplements mature Rust work and adds broad translation semantics not requested | Reject as ordinary path |
| Export native Rust structures directly | Superficially fewer conversions | Unstable layouts, nested owners, enum changes, allocators, aliasing | Reject |
| Per-model SeaORM native generation | Full typed native Entity hooks/relations | Application Rust compilation/packaging coupling | Specialized opt-in, not ordinary consumer default |

Do not announce a batched wire format as final before comparison. A small domain-specific operation encoding, if selected, is a transport to native methods, not a Core universal AST, SQL optimizer or dialect system.

## 6. C# API and native semantics

A typed Fluent API can execute builder delegates as normal C# code; it does not require `Expression<T>.Compile`, IQueryable or arbitrary method-body translation. Start from the actually demonstrated typed descriptor approach and add ergonomic expression proxies only with explicit owner scopes and compile fixtures. Fluent operators preserve SQL three-valued logic; `IS NULL` and null-safe comparison are named operations. Do not silently apply C# two-valued null compensation to all expressions.

Draft example (not compiled product API):
```csharp
using var q = db.From(Students.Table);
q.Select(Students.Row)
 .WhereGe(Students.Age, minAge)
 .OrderBy(Students.Id)
 .Take(100);
var rows = await q.ToListAsync(cancellationToken);
```
The recovered probe compiled a narrower synchronous API, not this async contract. The production constructor/decoder is static; anonymous arbitrary runtime types do not gain automatic AOT mapping. Entity changes with supported codecs must leave the native asset unchanged. Arbitrary SQL remains a separately named expert API with bound values, declared result shape and no claimed semantic validation of user SQL.

## 7. Necessary safety work discovered in source

SQLite SeaQuery row-lock rendering is a no-op and SEARCH/CYCLE options are ignored. Passing such a requested semantic operation through without error is unacceptable for a strong contract. Validate backend capabilities before DB submission; **catch_unwind does not detect a silently omitted clause**. CTE shape and typed value ranges require checks before rendering/binding. Preserve upstream error categories where meaningful and add an explicit UnsupportedCapability result rather than inventing successful emulation.

The inspected sea-query-sqlx SQLite binder uses `try_from(u64).unwrap()` and ignores some `args.add` results. Choose a small fallible value-to-Arguments adapter using supported public APIs (or a reviewed upstream fallible extension), propagate every encoding error and reject unsupported values. Do not infer parameter safety from `AssertSqlSafe`: it asserts provenance, it does not sanitize arbitrary concatenated SQL. Bind parameters separately and only assert the output of the trusted validated native builder.

Native mutable builders are single-writer. SafeHandle refcounting prevents a physical free during a call but does not make simultaneous mutable Rust references legal. Reject overlapping mutations, mixed-owner expressions, mutation after sealing and stale handles. If a mutation panics after partial state change, poison/destroy the builder under a safe cleanup protocol; do not assume it can resume. Values retained by a query are native-owned or explicitly leased, never temporary managed pins surviving an async await.

## 8. ORM scope and cost

The default candidate is a native query/execution and metadata-driven CRUD/relationship surface, not all SeaORM/EF ORM behavior. Rust implements explicitly specified primary-key CRUD, joins/relations, affected-row CAS, transactions and migrations. Lazy loading, transparent identity maps, arbitrary graph persistence and change tracking are not inherited from SeaQuery. Evaluate each needed capability rather than quietly creating a new full ORM in C#.

Measure direct versus batched calls, expression allocations/clones, UTF-8 conversion, repeated metadata, native/managed caches, result column/row encoding and DTO allocation. SeaQuery condition rendering in the inspected backend clones a Condition, so even direct reuse is not “zero-copy/zero-allocation.” Production uses persistent bounded pools/runtime and streaming batches; do not benchmark the per-call-runtime JSON prototype as the final product.

## 9. Verification and disposition

The old requirement that every ordinary C# entity must trigger Rust compilation is **design-answered negatively for this dynamic profile**. Full native capability coverage, performance and production safety remain unverified. B09/B10/B11/B12/B13 now separate binding metadata, optional static generation, native builder/binder, DTO materialization and runtime Fluent composition. B02/B03/B04 are Rust provider/host work; managed drivers are comparisons only.

Required tests: native-versus-C# SQL+parameter golden and real PG/SQLite result/error differential suites; every promised CRUD/join/CTE/window/aggregate capability and backend rejection; wrong-entity/value/null/projection compile cases; huge values/overflow/malformed and mixed-owner handles; sanitizer/race/close/cancel tests; unknown COMMIT and connection quarantine; Native AOT on Windows/Linux; clean no-Rust/RID-free consumer runs; same native hash after adding supported entities; long load/RSS and full-workload comparisons. No independent approval of this amendment has yet occurred.
