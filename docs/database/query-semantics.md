# D16 — Native query semantics and typed Fluent contract

Contract: **C-QUERY-001@0.3.0**; design candidate. The registry records exact-content independent review and acceptance; product implementation/release gates remain in Delivery. Evidence: [R25](../research/topics/R25/source-driven-seaquery.md), [recovered AOT probe](../research/source-driven-evidence/README.md), existing R22/R24/R25 reports. This replaces full declaration-only LINQ capture, generic C# predicate compensation and required schema-specific SeaORM generation as the ordinary route. Historical SQL counterexamples remain valid; no arbitrary IQueryable compatibility is promised.

## 1. Semantic owner and scope

Rust SeaQuery owns query construction, native Expr/Condition state and SQL dialect generation. SQLx executes parameterized results. C# contributes typed descriptors, Fluent method calls, static projection construction and application logic. Its transport encoding is not a second SQL AST, rewrite engine or dialect emitter. Compiling C# does not imply compiling arbitrary C# lambdas into Rust.

The initial domain includes explicit CRUD, scalar typed values/null, filters, ordering, grouping/having/aggregates, inner/left joins, subqueries and backend-supported CTE/window constructs. Capability coverage is enumerated per operation/backend/profile; “SeaQuery supports it” is not sufficient to claim a stable C# binding exists. Additional operators are bound rather than replaced by a large general-purpose query compiler.

## 2. Typed facade and runtime metadata

A descriptor contains a stable metadata identifier, validated table/column name, codec, nullability and any explicit key/relation information. The C# type `Column<TEntity,TValue>` prevents accidental cross-entity/value use in supported APIs; joined scopes need explicit aliases and typed association, not a general unchecked string field. Dynamic external fields are resolved against an allowlist, and native code validates again. C# type safety alone is not a sandbox for raw ABI input.

Draft API, **not compiled**:
```csharp
using var q = session.From(Students.Table);
q.Select(Students.Row)
 .WhereGe(Students.Age, minAge)
 .WhereIsNotNull(Students.Email)
 .OrderBy(Students.Id, NullOrder.Last)
 .Take(100);
var rows = await q.ToListAsync(ct);
```

A more ergonomic `Where(s => s.Age.Ge(min).And(...))` may execute a normal C# builder delegate against native-backed expression proxies. It must not be marketed as arbitrary `Func<Student,bool>` translation. Expression proxies retain/query-match their native owner; cross-query reuse must either perform a documented native clone or reject, not borrow a dangling mutable object. The compiled research probe only establishes narrower typed-column composition and wrong-entity rejection.

## 3. Native builder and value lifecycle

Builder states: Mutable → Sealed → Submitted → Closed, with Poisoned on unsafe partial mutation failure. A logical single-writer gate precedes extracting the native handle; SafeHandle lifetime references alone cannot prevent Rust `&mut` aliasing. Sealing freezes the query shape/owned values. Parameter values are snapshotted at an explicit call/submission point, never reread from a mutable closure after await. A prepared reusable shape and per-execution parameter storage must be distinct objects with explicit cache ownership.

The Adapter maps operations to public SeaQuery methods and retains the resulting native Expr/Condition/statement. It validates sizes, nesting/operation limits, CTE shape, typed values and backend capabilities. A batched operation representation is optional and must have a versioned decoder and bounded allocation; partial failures either commit no builder change or poison the builder. That local property is unrelated to database transaction atomicity.

No function pointer, Rust trait object, Vec layout or native enum discriminant becomes a public wire value. ABI constants are explicitly versioned. Upstream non-exhaustive enums and Cargo feature-gated values are checked during adapter upgrades.

## 4. NULL and Boolean semantics

The default is **SQL three-valued logic**. Equality with a NULL operand yields UNKNOWN unless an explicitly named null-safe operation is requested; `IS NULL`/`IS NOT NULL` are distinct methods. WHERE retains TRUE only. NOT UNKNOWN remains UNKNOWN; FALSE AND UNKNOWN is FALSE; TRUE OR UNKNOWN is TRUE. For compatible totally ordered operands, SQL `NOT(x > y)` and `x <= y` both yield UNKNOWN on NULL; nullable data alone does not invalidate that equivalence. Do not silently replace these with C# two-valued null compensation, or generalize the equivalence to NaN/custom partial-order operators. The focused R24 SQLite integer truth-table fixture records this correction.

An optional `NullSafeEqual` capability may use PostgreSQL `IS NOT DISTINCT FROM` or SQLite `IS` only within declared codec/collation domains and tests. It is not a promise that every .NET equality, NaN or mixed SQLite storage class has identical semantics. SQL `IN`/`NOT IN`, NULL-containing sets and empty sets have explicit operator behavior; do not label them LINQ `Contains` without an independently specified convenience rule. Empty-membership convenience may deliberately produce FALSE/TRUE, but must be named/documented and tested separately from native SQL rendering.

## 5. Values, arithmetic, strings and pagination

Every value is bound, never interpolated as SQL text. Identifiers are validated metadata, not values masquerading as identifier parameters. Collection length, total parameter count/bytes, query depth/node count and query result size have finite configurable limits from the selected backend profile. Reject or select an explicitly supported bulk-parameter mechanism when limits are exceeded; do not switch to literal concatenation.

Integer narrowing is checked. SQLite integer arithmetic can promote overflow to REAL; SQL arithmetic is not automatically C# checked arithmetic. Decimal PostgreSQL precision/scale/rounding are explicit. SQLite exact decimal-as-TEXT is a round-trip codec only, not automatic numeric SUM/order/range semantics. Fixed-scale checked Int64 is a separate money profile. NaN/Infinity, JSON/array/provider custom types and date/time precision need their own capability tests.

String comparison uses explicitly selected database collation. UTF-8 binary ordering is not arbitrary .NET UTF-16 ordinal or culture-sensitive equality. LIKE helpers that mean literal Contains/StartsWith/EndsWith escape `%`, `_` and the escape character before binding and state case/collation behavior. Raw SQL LIKE patterns remain a different API. No client-side filtering fallback.

Sort keys carry direction and explicit null order where promised. Paged business queries require a deterministic unique tie-breaker; native LIMIT without order may still exist as an explicitly nondeterministic low-level capability, not a guaranteed page API. Keyset cursor metadata binds query/profile/sort/codec and tenant scope, is tamper-resistant if exposed to clients and cannot remove authorization predicates. Keyset pagination alone does not give cross-request snapshot consistency; use an explicit snapshot/export policy when required. Offset/limit and export durations are bounded.

## 6. Join, aggregation, CTE and windows

Do not relocate a LEFT JOIN right-side predicate between ON and WHERE; that changes results. Use a non-null key or explicit match marker to distinguish an unmatched row from a matched nullable column. Projection nullability follows the selected join. Grouped projections contain declared keys/aggregates, not arbitrary in-memory groups. COUNT returns a checked documented integer width; SQL SUM on an empty set remains NULL unless the caller explicitly asks for a coalesced value. No hidden C# aggregate equivalence.

Expose native subqueries, CTEs and windows where the backend profile supports them. Validate empty/malformed CTEs before native renderer assertions. SQLite row locking, SELECT INTO and SEARCH/CYCLE must be rejected when requested because the inspected native paths can ignore them; unsupported ANY/SOME/ALL must return UnsupportedCapability before a panic or DB send. Multiple named-window definitions exceed the inspected SelectStatement's single optional slot: bind supported inline/single named windows now and require a source extension or revised upstream API before promising arbitrary named-window lists.

UNION/UNION ALL/EXCEPT/INTERSECT require compatible projection shapes and backend set/null/duplicate semantics. Unsupported clauses fail explicitly; do not synthesize another C# SQL dialect to fill the gap or silently drop a clause.

## 7. ORM policies: explicit, Rust-owned, not inherited by name

NativeWeave's ordinary profile specifies primary-key CRUD, explicit relationship joins, partial changesets, version-column compare-and-swap and migration integration. A changeset represents not-set versus explicitly-null versus value; updates always bind the intended key/tenant/version predicates. An affected-row mismatch is a concurrency result, not successful overwrite. Rust owns this policy over native query/execution capabilities; C# does not maintain a hidden query engine or identity map.

Transparent lazy loading, general graph persistence, arbitrary hooks, identity maps and full change tracking are not supplied merely by depending on SeaQuery. Add only required, separately designed policies. Static SeaORM Entity/ActiveModel/Relation behavior is a specialized native profile, with its own model build dependency and tests, not the default consumer obligation. SeaORM `save` choosing insert/update by whether keys are set is not an exists-based upsert guarantee.

## 8. Boundary errors and expert escape hatch

Shape mismatch, unsupported codec/operator/backend, overflow, invalid UTF-8, stale/mixed owner, disposed/poisoned builder, capacity exhaustion and database errors are distinct categories. Preserve structured provider information without exposing credentials or unrestricted SQL parameter logging. Failed operations must release or quarantine every owned native value/batch and must not overwrite an Unknown transaction outcome.

Expert parameterized SQL is explicitly named and audited, requires declared static result mapping and budgets, and remains executed in Rust. `AssertSqlSafe` is only a provenance assertion at that boundary, not validation of arbitrary user text. Ordinary Fluent failure never automatically falls back to raw SQL, managed providers, client evaluation or reflection/dynamic code.

## 9. Costs and verification

Compare direct native methods versus batched native commands and generated static fast paths. Count FFI/UTF-8/value copies, native AST/condition clones, descriptor/shape cache memory, body allocations, result bytes and DTO allocations. Cache keys include Engine ABI/profile, metadata content and query shape; eviction bounds bytes as well as entries and keeps in-use owners alive. No zero-allocation or throughput claim is made.

B09/B11 require direct-Rust versus C# differential SQL+parameters and real PG/SQLite result/error oracles. B10/B12 require generated and handwritten static descriptor/DTO parity plus actual Windows/Linux AOT. B13 requires dynamic typed composition without expression compilation, wrong-entity/value negatives, advanced-clause coverage and unsupported-backend rejection. B14 requires tenant/relationship/CAS tests and no accidental full ORM scope. B05/B06/B22 retain unknown commit, cancellation, early stream stop, decoder exception, race/fuzz/soak and bounded-resource obligations. The recovered probe is only the documented feasibility slice, not acceptance of this full contract.

## 10. Source-inspected native ORM capability boundary and concrete relation cases

The chosen ordinary native route is SeaQuery + SQLx with runtime metadata. SeaORM
public dynamic ModelType/FieldType decoding is a valid optional native capability;
it has an actual unchanged-code runtime-schema fixture, not merely an inference
from the library name. It does **not** automatically expose static EntityTrait,
ActiveModel hooks or LoaderTrait relationships for unknown schemas.

The inspected SeaORM loader extracts keys, builds native relation queries, collects
results and groups them by ValueTuple while preserving parent order. Its outer APIs
remain bounded by ModelTrait/EntityTrait associated types. For future bounded eager
loading, prefer generalizing those native algorithms through a controlled upstream
metadata extension; do not build a C# relationship engine. The initial ordinary
surface supports explicit native joins/projections and CAS changesets, with no
transparent lazy loading, hidden tracking or arbitrary graph persistence.

`native_join_aggregate_matches_independent_sql_oracle` checks actual LEFT JOIN,
COUNT and SUM behavior against separately authored SQL. The changeset fixture
checks NotSet versus explicit NULL, tenant isolation and expected-version affected
rows. Existing R24 truth tables and native-slices negative controls remain separate
coverage. Every additional bound SeaQuery operation gets paired native-versus-ABI
SQL+ordered-values and PG/SQLite result/error tests; no complete upstream capability
coverage is claimed solely from these finite cases.

A native projection must validate exact shape before nullable decode. Missing or
duplicate columns are errors even when an upstream Option<T> decoder returns None.
This includes expert SQL, alias collisions, joined result nullability and descriptor
upgrade drift. Any poison/error cleanup follows the creating engine's owner rules;
transaction Unknown remains unchanged.

### Published research CI evidence

The [database CI confirmation](../../verification/database-completion/ci-confirmation.json) binds source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80` and run `43388468172` to actual Windows/Linux metadata/SQLite results (5/5 on each) and Linux PostgreSQL 18.0 results (6/6). Archived inputs/logs were checked byte-for-byte; Windows CRLF inputs remain separately identified. This confirms the finite native research oracles and leaves the specified C# product, TLS, concurrency, long-load and independent design-review obligations distinct.
