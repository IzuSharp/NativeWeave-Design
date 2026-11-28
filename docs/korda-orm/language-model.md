# SQL language model and jOOQ semantic inheritance

Status: proposed Korda.Orm design for `Korda-Orm-01`; source review completed for
the paths below. This document does not claim an implemented DSL, exhaustive
jOOQ coverage, compiled public signatures, or product acceptance. Shared boundary
definitions are maintained in [contracts.md](contracts.md).

## Source baseline and design decision

The baseline is the public jOOQ **3.21.10** release, tag `version-3.21.10`, commit
[`3c58109e7ab69772de75e640852935ee7e284177`](https://github.com/jOOQ/jOOQ/tree/3c58109e7ab69772de75e640852935ee7e284177).
Its source files, rather than the complete commercial feature catalogue, define
the implementation material available to this study. The
[upstream policy](upstream-policy.md) governs reuse and future updates.

Inherit SQL concepts and their established lowering rules: typed fields,
relations, predicates, row expressions, composable queries, explicit parameter
nodes, SQL types, and dialect-specific semantics. Re-express these in C# while
separating SQL construction from driver binding and execution. Preserve a source
and semantic case link for each ported operation. A pleasant Fluent surface alone
does not satisfy this design.

## What the source actually does

All links below are fixed to the reviewed commit. Paths and symbols identify
reviewed evidence, not a claim that every method in each file was audited.

| Upstream source and symbol | Observed implementation | Korda.Orm decision and required check |
| --- | --- | --- |
| [QueryPart](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/QueryPart.java), [QueryPartInternal](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/QueryPartInternal.java) | Composition has a common node abstraction; internal visitation drives rendering/binding. | A common semantic node model supports independent validation and rendering. Core must build and render without a driver reference. |
| [Field](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Field.java), `Field<T>` | One scalar expression can participate in selection, grouping and ordering. Column, parameter, computed expression and scalar subquery are related expressions. | Preserve typed `Field<T>` composition, not entity-property-only querying. Exercise fields in SELECT, HAVING, ORDER BY and DML RETURNING. |
| [Table](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Table.java), `Table<R>` | Relations include physical tables, derived tables, joins, CTEs and table-valued expressions. Some legal-use restrictions are outside Java's type system. | Model relations independently of entity instances. Validate scope and query context before rendering; do not promise every SQL error is a compile error. |
| [Condition](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Condition.java), [AbstractCondition.acceptCase](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractCondition.java) | A condition is a boolean expression. The CASE fallback preserves UNKNOWN when the predicate is nullable. | `Condition` represents SQL truth, never an eagerly evaluated CLR `bool`. Test true/false/unknown in WHERE and in projections. |
| [Eq.accept](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Eq.java), [AbstractField.eq/isNull](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractField.java) | Equality and IS NULL are separate nodes; equal operands share `T`. | `.Eq()` retains SQL equality. A null value does not silently change the operator to IS NULL. Reject mismatched CLR expression types unless an explicit, valid conversion exists. |
| [IsDistinctFrom.accept](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/IsDistinctFrom.java) | MySQL/MariaDB use the null-safe `<=>` operator; SQLite uses `IS NOT`; other supported cases render or emulate distinctness. | Preserve explicit null-safe comparisons and verify the same truth table on each supported database. |
| [Row2](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Row2.java), [RowIsNull](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/RowIsNull.java), [RowIsNotNull](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/RowIsNotNull.java) | Rows preserve component types. Row IS NULL and IS NOT NULL emulations respectively require all components null and all components non-null. | Keep row degree/type checking and component semantics. For a mixed-null row, IS NOT NULL is not the negation of IS NULL. |
| [DataType](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/DataType.java), [DefaultDataType](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/DefaultDataType.java) | A SQL type includes much more than a Java class: dialect type, dimensions, nullability, collation, domain and conversion/binding information. | `SqlType<T>` keeps SQL identity and facets independent of provider codecs. Different SQL types sharing `T` must not collapse to one type. |
| [Nullability](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Nullability.java), [SQLDataType](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/SQLDataType.java) | Nullability includes a context-dependent default. JSON/JSONB and temporal types carry distinctions beyond the host representation. | Track storage declaration, inferred expression nullability and CLR mapping separately. Preserve JSON versus JSONB, time-zone policy, numeric width and decimal precision. |
| [Cast](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Cast.java), [Coerce.accept](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Coerce.java) | CAST changes SQL; coercion delegates rendering to the existing expression. | Expose SQL casts separately from checked client conversion. Do not offer unrestricted type relabelling that makes an unsafe read look type-safe. |
| [SelectImpl.select/where](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/SelectImpl.java), [SelectQueryImpl.copyBetween/addSelect](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/SelectQueryImpl.java) | Fluent steps mutate a delegated query. Copying has explicit handling for clause lists and lock state. | Public reusable queries must be immutable snapshots. A private builder may be mutable and single-owner, but freezing must detach mutable collections. Test shared subqueries and concurrent rendering. |
| [ConditionProviderImpl](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/ConditionProviderImpl.java), [NoCondition](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/NoCondition.java) | Optional-clause absence and a true predicate are handled differently in query composition, even though NoCondition can render TRUE in expression position. | Represent absent optional clauses explicitly. Do not confuse an omitted WHERE, FALSE and an UNKNOWN predicate. |
| [QOM](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/QOM.java), model contract and `Eq` accessors | Model operations return replacements; the API is explicitly experimental and documents remaining mutable elements and incomplete coverage. | Reuse its semantic decomposition. Keep implementation nodes internal; a stable inspection/extension contract needs its own version policy. |
| [AbstractQueryPart.equals/hashCode](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractQueryPart.java) | The fallback compares or hashes SQL rendered with inlined values. | Never use debug rendering as the command-cache identity. Query shape, render settings and parameter values have different lifetimes. |
| [TableAlias.initFieldAliases/accept](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/TableAlias.java), [FieldAlias](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/FieldAlias.java) | Aliasing reconstructs field ownership and cooperates with render scopes. | Relation identity and alias names are distinct. Test self-joins, alias shadowing, derived tables and legal/illegal correlation. |

## Deliberate separation from jOOQ execution internals

The source proves a useful render-only use case, not an internally isolated Java
DSL module. [AttachableQueryPart](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/AttachableQueryPart.java)
provides `getSQL()` and `getBindValues()`, while
[Query](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/Query.java)
also exposes execution. [AbstractQuery](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractQuery.java)
retains prepared-statement/rendered state, acquires connections and implements its
blocking-path `executeAsync` through an executor. These execution mechanisms are
not the C# rewrite template.

There is also a less obvious type/render coupling:
[Val.accept/accept0](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Val.java)
calls the type binding's SQL method during rendering. Korda must split that
responsibility: the pure SQL type/dialect layer decides the SQL cast and parameter
occurrence; the execution adapter chooses the concrete provider type, serializes
the value and reads results. A provider-specific SQL type can have a pure dialect
description without importing its driver into the DSL.

Similarly,
[DefaultDSLContext.extractBindValues/extractParams](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/DefaultDSLContext.java)
uses [ParamCollector](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/ParamCollector.java),
which keeps both an occurrence list and named maps. A name map alone is not an
ordered binding layout. Korda rendering produces SQL, ordered occurrences and
result metadata atomically. Rewrites can duplicate or remove occurrences; the
layout follows the rendered tree, with every occurrence referring to a typed
logical parameter. The execution layer may not infer order by scanning SQL text.

## C# semantic contracts

### Types and diagnostics

`Field<T>` describes the CLR result representation; `SqlType<T>` carries SQL
identity, domain and dimensions. SQL nullability is additional semantic metadata.
C# nullable annotations cannot alone model SQL UNKNOWN or make nullable database
values safe for non-nullable DTO members. Nullable value types and generated
nullable reference annotations should express known result nullability; the
mapper must still diagnose an unexpected database NULL.

Comparison overloads reject unrelated `T` values at compilation. SQL-compatible
numeric promotion is explicit and documented rather than inherited accidentally
from CLR operator overload resolution. Precision loss, unsigned values, domain
coercion, array element types and timestamp/time-zone changes require a declared
conversion policy. SQL `Cast` and client conversion are different operations.

Type-safe construction does not establish schema freshness, dialect support,
correct grouping, valid name resolution or database permissions. A pure semantic
validation pass handles the checks that depend on a query tree and dialect
profile. Diagnostics identify the operation, relevant type/scope, dialect and
failed precondition. Unsupported semantics fail before command execution. Raw SQL
extensions are explicit escape hatches with declared result types, parameter
layout and a documented loss of semantic guarantees.

Outer joins lift the optional side's effective result nullability. Generated
table metadata must not be mutated to achieve this. A typed optional relation or
projection provides nullable fields for that use site. Nested-row absence must
be distinguished from a present row containing nullable members; a declared
presence key is preferable to an unconditional all-fields-null heuristic.

### Composition and ownership

Queries, predicates, field references and parameter definitions are reusable
values. Modifying one query returns another query and must not affect a shared
subquery. The implementation can use immutable nodes, structural sharing or
private builders after measuring the alternatives. This is an observable
ownership contract, not a requirement to use a particular collection library.

`Param<T>` denotes a typed logical input, separate from a per-execution value set.
Execution values and mutable provider commands must not become state on a shared
query. Render contexts are per operation; caches are bounded and cannot retain
arbitrary request values. Owned query descriptions and SQL strings do not require
consumer disposal. Temporary pooled render buffers cannot escape through returned
commands. Buffer borrowing across asynchronous execution requires an explicit
lifetime contract in the execution layer.

Dynamic SQL composes the same nodes at runtime. It does not require emitting IL,
compiling expression trees or discovering DTO members through reflection. Fixed
queries may cache immutable rendered shapes; dynamic queries can cache bounded,
validated shapes when measurements justify it. Neither path promises zero
allocation: a newly returned SQL string has an allocation cost, and generic
specialization may increase Native AOT binary size.

### Public API candidates

The following **uncompiled design sketch** illustrates intended relationships.
It is not an API baseline and must be reconciled with `contracts.md`, compiled
examples and negative compilation cases before the implementation contract is
frozen. Names and overloads can change without changing the semantics above.

```csharp
SqlType<int> integer = SqlTypes.Int32;
var u = Tables.Users.As("u");
Field<int> id = u.Id;
Param<int> minimum = Sql.Param("minimum", integer);

Condition filter = id.Ge(minimum);
if (includeOnlyActive)
    filter = filter.And(u.IsActive.Eq(Sql.Literal(true)));

var query = Sql.Select(u.Id, u.Name)
    .From(u)
    .Where(filter)
    .OrderBy(u.Id.Asc());

var command = renderer.Render(query, dialectProfile);
// command exposes SQL, typed parameter layout and result description.
// A separate execution package consumes it with values and a known mapper.
```

Generated alias members must all belong to the aliased relation. This sketch's
generated `Tables.Users` API is illustrative rather than a prescribed generator
implementation.
Handwritten metadata must remain possible. Code generation supplies convenience,
schema fidelity and mapping code; it is not a precondition for constructing SQL.

Use explicit `.Eq()`, `.And()` and `.Or()` as the primary API so SQL composition
does not masquerade as CLR equality or short-circuit evaluation. Stable public
query types should support extension of optional clauses without consumers
storing a large family of grammar-step interfaces. jOOQ's
[SelectSelectStep guidance](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/SelectSelectStep.java)
specifically identifies mutability, composability and compatibility drawbacks
when clients retain step types. Selective C# grammar interfaces remain an
implementation option where they add useful compile-time guarantees.

Typed row/projection helpers preserve component types and arity for common
shapes. Arbitrary runtime projections require explicit runtime descriptors and
must not claim the same compile-time DTO guarantees. Measure generated overload
count and Native AOT size before choosing an arity expansion policy.

## Required semantic validation cases

The cases are maintained product test requirements, not tests executed by this
documentation change. The broader differential/database strategy is in
[validation.md](validation.md).

| Case family | Required positive and negative behavior |
| --- | --- |
| Type identity | `Field<int>` versus text fails compilation; same CLR type with incompatible SQL domain fails validation; an explicit approved cast succeeds. |
| Scalar NULL | Equality with NULL remains UNKNOWN; IS NULL and null-safe distinctness retain their respective truth tables. |
| Boolean projection | CASE emulation preserves UNKNOWN; WHERE removes rows whose predicate is FALSE or UNKNOWN. |
| Row NULL | All-null, mixed-null and all-non-null rows distinguish IS NULL, IS NOT NULL and NOT(IS NULL). |
| Membership | Empty IN/NOT IN, nullable members and nullable tested expressions preserve SQL semantics; cardinality changes cannot reuse an incompatible layout. |
| Binding | Repeated logical parameter, repeated names, reordered projection, nested subquery, inlined literal and rewrite-induced duplication produce exact occurrence/type order. |
| Identifiers | Quoted/reserved names, embedded quote characters, qualified names and parameter-like identifier text are not string-concatenation shortcuts. |
| Scope | Self-join aliases, nested aliases, correlated subqueries and CTE references bind to the intended relation; out-of-scope fields fail before execution. |
| Query ownership | Extending one query or changing one execution's values does not mutate another; simultaneous render operations are independent. |
| Projection | Outer-join nullability, duplicate names, tuple degree, selected column order and nested presence rules match the declared result shape. |
| Relational operations | Set-operation degree/type compatibility, aggregate/grouping rules, window frame validity and scalar-subquery cardinality have explicit enforcement boundaries. |
| Driver isolation | A consumer referencing only language/render assemblies builds and runs a dynamic query without a connection, provider package or native query compiler. |
| AOT | Generated and manual metadata/mappers compile and run as native consumers; invalid generic combinations fail; unknown runtime-only DTO construction is rejected. |

## Scope of this decision

This study settles the semantic and ownership direction, identifies concrete
upstream implementation anchors and specifies tests for the subsequent product
work. It does not equate jOOQ's full API with the first release scope. Advanced
query families, dialect lowerings, parser and schema generation require their
own source-linked implementation slices. An operation is complete only when its
semantic cases, AOT behavior and declared database profiles pass; adding a
Fluent method name alone is insufficient.
