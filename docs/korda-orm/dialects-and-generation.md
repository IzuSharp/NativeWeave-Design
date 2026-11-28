# Dialects, SQL semantics, schema generation, and validation

Status: researched design for `Korda-Orm-01`; no Korda.Orm product feature is
implemented or accepted by this document. The shared command and type boundaries
are owned by [the contracts](contracts.md). This direction does not inherit the
old native compiler or execution architecture.

## Source baseline and transfer method

The inspected upstream is jOOQ **3.21.10**, tag `version-3.21.10`, commit
`3c58109e7ab69772de75e640852935ee7e284177`. References below identify concrete
implementation symbols at that commit. They establish the basis for a semantic
rewrite, not a claim that every jOOQ class or dialect has been reviewed.

Preserve the query semantics, type relationships, dialect decisions, and known
edge cases in the available source. Rewrite Java/JDBC-specific mechanisms for
C#. Every implementation family must keep a compact mapping from the upstream
symbol to its C# owner, supported semantic cases, intentional differences, and
regression tests. Updating a source pin must review changed behavior in those
families; merely updating a version number is insufficient.

| Inspected source and symbols | Behavior to preserve or account for | C# implementation and verification responsibility |
| --- | --- | --- |
| [DefaultRenderContext][render]: constructor, `visit0`, `scopeEnd0`, `Rendered` | Rendering carries declaration/scope state; it collects bind occurrences and can insert SQL plus corresponding binds during scope resolution. | A render operation owns its context. Return SQL, parameter layout, and result description from one consistent snapshot; test aliases, nested scopes, repeated parameters, and rewrite-introduced occurrences. |
| [Val][val]: `accept`, `accept0`, `getBindVariable`; [ParamCollector][collector]: `bindInternal` | Parameters distinguish inlining, inferred/explicit types, named references, and repeated occurrences; Java binding participates in rendering. | Separate SQL type/placeholder decisions from driver binding. Preserve occurrence order and explicit type information; do not put an ADO.NET parameter in the AST. |
| [Identifiers][identifiers] and [DefaultRenderContext][render]: `literal` | Identifier delimiters and escaping are dialect-specific; qualification and case policies are contextual. | Use structured identifier segments. Test delimiters inside names, keywords, Unicode, qualification, aliases, and name-length policy. Values never become identifiers. |
| [SelectQueryImpl][select]: `accept`, `unionParensRequired`, `unionParenthesis`, `distinctOnEmulation` | Nested set operations require precedence-preserving parentheses or derived tables; SQLite cannot use the same parenthesized form as PostgreSQL. Some DISTINCT ON emulation is present in open source. | Port the supported rewrite with bag/order/limit semantics, not token substitution. Test EXCEPT non-associativity and ORDER BY/LIMIT on operands. |
| [CommonTableExpressionImpl][cte]: `accept`; [WithImpl][with] | A CTE has declaration versus reference modes and explicit field aliases; materialization hints have dialect gates. | Model CTE scope, result degree, recursive self-reference, and hints explicitly. Never silently remove a requested semantic capability. |
| [WindowSpecificationImpl][window]: `accept`, frame methods | Named windows, partition/order keys, ROWS/RANGE/GROUPS, boundaries, and exclusions are separate components. | Retain a typed window model. Validate boundary combinations and profile support; test NULL peers, empty frames, ties, and named-window refinement. |
| [SortFieldImpl][sort]: `accept` | Unsupported NULLS FIRST/LAST syntax is expressed through an additional null-ordering expression. | Preserve sort semantics and evaluation constraints. Test NULLs, ties, mixed directions, volatile expressions, and additional bind occurrences. |
| [AbstractInList][inlist]: `accept1` | Empty lists differ by dialect and can lower to constant conditions. | Specify empty IN and NOT IN, including NULL left operands; never generate a syntactically invalid empty list on profiles that reject it. |
| [InsertQueryImpl][insert]: `accept1`, conflict handling, excluded-value handling | PostgreSQL/SQLite ON CONFLICT and MySQL/MariaDB duplicate-key handling have different semantics. Rendering uses keys and version-specific excluded-value syntax. | Require explicit conflict intent. Validate missing/ambiguous key metadata, multiple unique constraints, partial indexes, WHERE conditions, defaults, and affected-row semantics. |
| [UpdateQueryImpl][update] and [DeleteQueryImpl][delete]: `accept1`, limit/from/using support sets | Joined modifications, limits, and target-table references differ; some cases require a subquery rewrite. | Implement only proven equivalents. Test multi-match joins, row identity, ordering, and self-reference restrictions before enabling a rewrite. |
| [AbstractDMLQuery][dml]: `toSQLReturning`, `prepare0`, `executeReturningGeneratedKeysFetchAdditionalRows` | Some RETURNING behavior needs JDBC generated keys and follow-up reads; it is absent from the SQL string. | A single SQL command supports native RETURNING only. A future multi-command feature needs a separate execution-plan contract and concurrency/transaction proof. |
| [JSONArray][jsonarray], [Multiset][multiset]: `accept0`, JSON/XML emulation helpers | JSON NULL/ABSENT behavior and nested collections involve type-preserving dialect rewrites, aggregation, ordering, and nested result representation. | Build advanced SQL families on the same AST. Define SQL NULL versus JSON null, empty collections, duplicates, ordering, and generated nested mapping together. |
| [Transformations][transforms]: `transform`; [SelectQueryImpl][select]: QUALIFY branch | Named configurable SQL transformations call `requireCommercial`; corresponding commercial bodies are absent from the open tree. | Do not claim those implementations were inherited. Unsupported transformations fail explicitly; independent future work must use permitted sources and its own semantic tests. |
| [ParserImpl.java][parser]: `ParserImpl` parse entry points and `DefaultParseContext.parseDialect/requireProEdition/requireUnsupportedSyntax` | A substantial parser is available, but dialect interpretation, metadata lookup, unsupported syntax, and commercial paths are distinct. | Keep parsing optional and downstream of the AST contract. It must not be required to interpret the framework's own Fluent output. |
| [Database][database], [GenerationTool][generation], [JavaGenerator][generator] | Metadata acquisition and source generation are modules; generator configuration can still open JDBC connections and instantiate Java classes reflectively. | Keep acquisition tooling, neutral schema metadata, Roslyn generation, and runtime DSL separate. Do not port reflective tool startup into the AOT runtime. |

This review covers the named symbols and relevant branches, not every method in
those files or every dialect/version path. Advanced window/recursive-query,
JSON/MULTISET, and metadata-acquisition conclusions are source-reviewed design
inputs, not executed C# implementations. No PostgreSQL, MySQL, or MariaDB server
was used for this review's metadata or rendering experiments. The bounded Java
probe and five SQLite semantic cases in [validation](validation.md) define the
actual execution coverage. Missing upstream tests and commercial bodies remain
explicit evidence gaps, not implicitly accepted behavior.

## Rendering and capability contracts

The logical pipeline is validate query and target profile, apply required proven
rewrites, render SQL and parameter occurrences, then seal the command description.
The internal representation may combine passes after measurement, provided the
observable contract remains the same. Rendering is synchronous and independent
of a connection, driver, network service, execution scheduler, or native compiler.

A target profile includes a dialect family, an explicitly supported version range,
and the semantic settings that affect generated SQL. Relevant examples include
extension availability, SQL modes, collation assumptions, and configured parameter
limits. A database adapter may check that a live server satisfies the supplied
profile; it must not make a renderer silently guess another profile. A disconnected
consumer supplies the profile directly. Placeholder layout is an explicit command
format choice validated against that profile and the eventual adapter.

Each implemented feature records one of four outcomes for a profile:

- **Native:** valid syntax and semantics are available directly.
- **Equivalent lowering:** a named, tested rule preserves the promised semantics
  under explicit, checked preconditions.
- **Unsupported:** a diagnostic identifies the feature, target profile, and reason.
- **Planned/unverified:** the feature is unavailable to product consumers until
  its implementation and declared profile have passed acceptance.

Metadata, version, or configuration conditions are preconditions on native or
equivalent support, not a fifth support category. They must be checked before a
command can be emitted successfully.

An unknown profile/feature combination is unsupported until reviewed. A failed
validation produces no executable command. Diagnostics must never be disguised by
omitting a clause, returning partly valid SQL, substituting a different conflict
policy, or automatically issuing additional statements.

Parameter layout distinguishes a logical typed slot from each occurrence emitted
in SQL. A rewrite may duplicate or relocate occurrences. Named, positional, and
numbered formats require an explicit mapping rather than assuming AST insertion
order equals bind order. Inlining is an explicit policy for valid syntax positions
or deliberately chosen literals; user values remain parameterized by default.
The rendered shape includes SQL type identity, nullability, facets, and output
column order. Runtime values are supplied through the binding boundary described
in the shared contracts; they are not global cache keys.

A single render context is not shared concurrently. Frozen query descriptions can
be rendered concurrently with independent contexts. Reusable shape caches include
profile, SQL options, parameter layout, result shape, and relevant schema identity.
They must be bounded or owned by an explicit lifetime. A cached command must not
retain credentials, connections, caller cancellation tokens, or mutable argument
objects. Pooling, AST structs, and render-buffer reuse remain internal experiments;
there is no zero-allocation claim for building a new AST and SQL string.

## Initial validation profiles and feature progression

The first product validation profiles are **PostgreSQL 18**, **SQLite 3.45 or later
with the exact runtime library recorded**, **MySQL 8.4**, and **MariaDB 11.8**.
PostgreSQL and SQLite form the first validation wave. MySQL and MariaDB are
independent provider/dialect tracks whose contract and pure rendering work can
start alongside the first two. This plan's final mandatory acceptance covers all
four profiles and the declared advanced/nested feature matrix; early validation
of one profile or package does not authorize a partial release. A narrower release
requires a separately reviewed scope and dependency-graph revision. These are
selected validation profiles,
not a claim of support for every newer or older release. Exact server patch
versions, extensions, modes, SQLite compile options, and driver versions must be
recorded by each implementation's acceptance tests.

The selection is compatible with the inspected open-source jOOQ dialect family
requirements, which identify PostgreSQL 18, SQLite 3.45, MySQL 8.0.31, and MariaDB
11.5 in [SQLDialect][dialect]. These are upstream assumptions, not automatic
Korda support. Later capabilities get explicit profiles. For example, MariaDB
13.0 added single-table UPDATE RETURNING according to the [vendor release
announcement][maria13]; it must not be projected backwards onto the 11.8 profile.

| Implementation family | Planned scope and admission gate |
| --- | --- |
| Foundational queries | Projection, predicates, expressions, joins, subqueries, aggregates, grouping, ordering, pagination, typed parameters, and aliases. Establish scope and NULL semantics before accepting convenience APIs. |
| Advanced relational queries | CTE/recursive CTE, UNION/INTERSECT/EXCEPT with duplicate semantics, window functions and frames, DISTINCT ON where native or proven equivalent, lateral/correlated queries where supported. These are explicit implementation tasks, not an unbounded CRUD backlog. |
| Modifications | INSERT/UPDATE/DELETE, multi-row values and insert-select, explicit conflict intent, native RETURNING, default/generated columns. Rewrites that need several commands are excluded from the single-command contract. |
| Advanced types | JSON/JSONB, arrays, enums, domain types, precision/time-zone-sensitive values. A profile's SQL capability and the driver's typed codec capability are both required. |
| Nested results | Row projections and MULTISET-style collections with a documented wire/result representation and generated decoder. JSON encoding is not automatically equivalent for every SQL value. |
| Optional language tools | Parser and translator, DDL/schema diff, richer schema acquisition, and additional dialects. Separate modules and acceptance gates; no dependency from ordinary Fluent query construction. |

This progression keeps the mature language model as the design reference while
making delivered support measurable. A family is not accepted because another
family's tests passed. The full feature inventory remains separate from the set
supported by a particular release.

## Intentional differences required by the new boundary

1. **RETURNING is not always pure rendering.** The jOOQ source deliberately omits
   the SQL clause where JDBC execution emulates it. Korda's disconnected command
   cannot promise that emulation. On MySQL 8.4 it rejects arbitrary RETURNING;
   generated-key retrieval, if added, is a separately named adapter operation with
   its own result contract. PostgreSQL RETURNING and SQLite RETURNING also have
   different details. SQLite buffers RETURNING output internally, does not promise
   row order, and excludes later trigger changes; streaming the reader cannot
   remove those engine-level properties. See the [SQLite reference][sqlite-returning]
   and [PostgreSQL 18 reference][pg-returning].
2. **Explicit clauses cannot disappear silently.** `CommonTableExpressionImpl`
   only renders materialization modifiers for selected dialects. Korda validates
   an explicitly requested modifier and reports an unsupported profile instead of
   silently dropping it. Any future advisory-only hint API must say so in its
   name/contract and expose ignored-hint diagnostics.
3. **Unknown conflict metadata is a diagnostic.** `InsertQueryImpl` contains
   fallback text such as `[unknown primary key]`. Korda must reject unresolved
   keys before emitting a command. ON CONFLICT and duplicate-key update are not
   unconditional aliases: multiple unique keys, conditions, triggers, and affected
   rows require explicit tests. MySQL's current syntax and semantics are documented
   in its [8.4 reference][mysql-upsert].
4. **A parameter limit does not silently change binding policy.** jOOQ's execution
   rendering can catch a force-inline signal and rerender with literal values.
   Korda reports a capacity failure unless an explicit, independently tested
   lowering policy has been selected. Parameter budgets belong to the target
   profile, not an unversioned constant copied from upstream.
5. **Commercial transformation bodies are not available implementations.** The
   open-source QUALIFY gate can throw before producing SQL for PostgreSQL. A
   future Korda equivalent needs independent permitted evidence and proof. This
   does not prohibit copying eligible open-source dialect rewrites that actually
   exist in `accept` implementations; the source/license review distinguishes them.
6. **SQL equivalence includes evaluation behavior.** A rewrite that duplicates a
   volatile expression, changes NULL handling, changes a bag to a set, or reads
   rows in an additional statement can change results. Such rewrites need a
   restricted precondition or an unsupported diagnostic, even if simple examples
   return the same rows.

## Schema acquisition and C# generation

The upstream dependency direction is useful: `jooq-codegen` consumes `jooq-meta`
and `jooq`; `jooq-meta` consumes `jooq`. It does not establish that all metadata
work is disconnected. `GenerationTool.run0` configures/opens a connection and
instantiates providers; `Database` exposes connection ownership. Provider classes
query catalogs and preserve details rather than infer all types from CLR/Java
names. The C# design keeps the semantic model but makes this boundary explicit.

| Upstream evidence | Required schema information and C# responsibility |
| --- | --- |
| [PostgresDatabase][pgmeta]: `getEnums0`, `loadForeignKeys`, table/domain queries | Preserve schema-qualified type identity, enum label order, domains, identity/generated columns, and ordered key/foreign-key columns. Use a PostgreSQL acquisition adapter outside the runtime DSL. |
| [SQLiteTableDefinition][sqlitemeta]: `getElements0` | Inspect `pragma_table_xinfo`, declaration text, affinity, generated/hidden columns, and INTEGER PRIMARY KEY/WITHOUT ROWID distinctions. Do not infer identity solely from whether `sqlite_sequence` currently contains a row. |
| [MySQLDatabase][mysqlmeta]: key and foreign-key queries; [MariaDBDatabase][mariameta] | Capture catalog/schema conventions, ordered constraints, enums, unsigned values, generated columns, and provider/version differences. Shared driver use does not erase dialect differences. |
| [JavaGenerator][generator]: `generate0`, table/record/POJO/relation generation | Generate relation/type descriptors independently from materialized DTOs and tracking/CRUD record behavior. Korda does not inherit Java UpdatableRecord/JDBC coupling. |
| [DDLDatabase][ddlmeta]: `export`, `load` | This upstream DDL path parses and executes statements through a database context; it is not proof of a database-free metadata parser. An offline Korda schema format is independently specified. |

The maintained schema model contains catalog/schema/table identities, stable
column order, SQL type identities and facets, nullability, defaults versus computed
expressions, ordered keys and relationships, and source-profile/version metadata.
It contains no connection string, credentials, driver object, or live connection.
Unknown types carry an explicit unresolved/custom-codec requirement; they do not
silently become strings or `object` mappings. Identifier-to-C# naming is
deterministic and reversible through metadata, including keyword escapes,
collisions, duplicate casing, and Unicode.

The normal local workflow has distinct stages:

1. An explicitly invoked schema tool connects through an acquisition adapter, or
   reads an existing maintained schema snapshot. It produces a deterministic
   neutral schema document with a format version and diagnostics.
2. The developer reviews that document and any naming/type overrides. Schema
   drift is visible as a normal diff. It is a maintained input in a consumer or
   product project, not a raw database dump in this design repository.
3. A Roslyn incremental generator consumes supplied schema inputs and explicit C#
   declarations to emit `Table`, `Field<T>`, `SqlType<T>`, key descriptors, and
   opted-in parameter/result mapping code. It performs no database I/O or network
   access during compilation and emits no reflection-based runtime fallback.
4. A local `dotnet build` or `dotnet publish` validates generated and handwritten
   code together. A Native AOT consumer runs directly. GitHub CI repeats the same
   entry points when requested by changed inputs; CI is not required to develop.

Handwritten typed descriptors are an equally supported DSL input. Schema
generation is a convenience and scale feature, not a prerequisite for rendering
a query. Adding an entity or DTO requires ordinary C# generation/compilation and
no Rust/C++ compiler. A generator cannot infer an arbitrary runtime-selected
projection into an unrelated DTO. The API therefore distinguishes a known typed
projection and generated mapping from a genuinely dynamic row shape, with an
explicit typed accessor or row representation for the latter.

Generator diagnostics cover missing codecs, invalid nullability, duplicate column
identity, name collisions, unresolved foreign keys, incompatible mapping types,
and unsupported schema format versions. Snapshot ordering and generated output
must be deterministic. Public declarations, XML documentation, examples, and
diagnostic identifiers change together. The existing API standard's general C#
clarity, naming, ownership, and AOT obligations apply; its historical native ABI
and execution requirements do not apply to this independent managed direction.

## Verification layers and current evidence

### Available upstream evidence

The pinned public Git tree contains no `src/test/` paths and no `jOOQ-test` module.
The root POM lists test-related dependencies, but that does not make the upstream
regression corpus available. This was checked from the actual tracked tree.
There is no claim to have imported or run a hidden/commercial test suite.
Available evidence comprises inspected implementation, public bug references in
that implementation, documented SQL behavior, and independently authored cases.

Use the published open-source Java runtime as a SQL-only reference where it
supports the feature. Differential tests compare query semantics, parameter types
and occurrence order, qualification, and profile-specific behavior. SQL whitespace,
alias spelling, quoting style, or placeholder spelling may differ legitimately.
Do not compare parameterized SQL by string equality alone or assume jOOQ output
is correct in a target database without executing representative cases.

### Required semantic corpus

| Family | Positive cases | Negative or boundary cases |
| --- | --- | --- |
| Parameters and identifiers | Repeated slots, nested subqueries, typed NULL, explicit casts, unusual names | Wrong type/facet, missing values, excessive parameter count, illegal identifiers, injection-shaped strings remaining values |
| Predicates and joins | Three-valued logic, EXISTS, correlated joins, empty lists | NULL inside NOT IN, outer-join predicate placement, ambiguous aliases, out-of-scope fields |
| Set operations and CTEs | Nested UNION/INTERSECT/EXCEPT, duplicates, recursive CTE | Wrong projection degree/type, different associativity, operand LIMIT/ORDER BY, illegal recursive references |
| Windows and aggregation | ROWS/RANGE/GROUPS, ties, empty partitions, named windows | Invalid frame endpoints, unsupported exclusions, NULL peers, aggregate/window placement |
| DML and conflict policy | Multi-row INSERT, explicit conflicts, native RETURNING | Multiple unique keys, missing key metadata, unsupported returning, trigger behavior, conditional updates |
| JSON and nested results | SQL NULL/JSON null/absent, empty/duplicate nested rows | Precision loss, ambiguous field names, unstable ordering, unsupported value codecs or JSON functions |
| Schema and generation | Deterministic snapshots, composite keys, generated columns, enums | Stale schema, naming collisions, unknown type, incompatible DTO, no database reachable during compilation |

Each family first has database-free AST/render/diagnostic tests. A separately
selected database integration layer executes supported semantics and rejects
unsupported ones against an explicit profile. Generated descriptors and mappings
also have compile-success, compile-failure, and Native AOT execution consumers.
Direct-driver results are an execution control, not a substitute for language
semantics. Profiling and long performance campaigns remain outside ordinary CI.

The local Java reference probe and the independent C# experiments are reported
separately in [validation](validation.md). No Java run establishes C# AOT
compatibility or product feature acceptance. No rendering-only run establishes
server correctness, result mapping, or query performance.

## Parallel implementation boundaries

After shared type, query-node, render-result, diagnostic, schema-format, and
provider-binding contracts are fixed, the PostgreSQL/SQLite renderers, the
MySQL/MariaDB renderers, schema acquisition adapters, generator, execution adapters,
and reference-case harness can proceed in separate worktrees. A renderer should
depend on stable node/type contracts and its own capability profile; it does not
wait for a working execution adapter. A schema acquisition adapter does not wait
for the full Fluent language. A generator can use hand-authored schema fixtures
before acquisition adapters are ready.

Cross-family rewrites need an owner and explicit prerequisites: nested collections
need both advanced type semantics and result-layout contracts; joined DML needs
key/scope semantics; fixed-query specialization needs a stable render layout.
These are genuine integration dependencies. They do not justify making every
provider wait for every SQL feature. Shared node registration, diagnostic IDs,
public API baselines, module registration, and the schema format have one owner
per integration change. Provider-local sources and tests retain independent CI
selection; shared contract changes select actual consumers.

[render]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/DefaultRenderContext.java
[val]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Val.java
[collector]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/ParamCollector.java
[identifiers]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Identifiers.java
[select]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/SelectQueryImpl.java
[cte]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/CommonTableExpressionImpl.java
[with]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/WithImpl.java
[window]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/WindowSpecificationImpl.java
[sort]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/SortFieldImpl.java
[inlist]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractInList.java
[insert]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/InsertQueryImpl.java
[update]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/UpdateQueryImpl.java
[delete]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/DeleteQueryImpl.java
[dml]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/AbstractDMLQuery.java
[jsonarray]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/JSONArray.java
[multiset]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Multiset.java
[transforms]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Transformations.java
[parser]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/ParserImpl.java
[database]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/src/main/java/org/jooq/meta/Database.java
[generation]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-codegen/src/main/java/org/jooq/codegen/GenerationTool.java
[generator]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-codegen/src/main/java/org/jooq/codegen/JavaGenerator.java
[pgmeta]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/src/main/java/org/jooq/meta/postgres/PostgresDatabase.java
[sqlitemeta]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/src/main/java/org/jooq/meta/sqlite/SQLiteTableDefinition.java
[mysqlmeta]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/src/main/java/org/jooq/meta/mysql/MySQLDatabase.java
[mariameta]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/src/main/java/org/jooq/meta/mariadb/MariaDBDatabase.java
[ddlmeta]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta-extensions/src/main/java/org/jooq/meta/extensions/ddl/DDLDatabase.java
[dialect]: https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/SQLDialect.java
[sqlite-returning]: https://www.sqlite.org/lang_returning.html
[pg-returning]: https://www.postgresql.org/docs/18/dml-returning.html
[mysql-upsert]: https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html
[maria13]: https://mariadb.com/resources/blog/announcing-mariadb-community-server-13-0-ga/
