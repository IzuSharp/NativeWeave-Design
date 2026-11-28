# Shared contracts for parallel implementation

Version: **0.1.0**. Status: **proposed; user review pending**. None of these
contracts inherits an accepted historical Korda contract or authorizes product
implementation. The Plan graph pins the immutable Design revision containing
them. Changes to a shared semantic invariant update its version and all affected
task inputs before integration.

These are normative semantic and module contracts. Candidate C# names below are
not a compiled public API baseline. `ORM-FOUNDATION` must compile the shared surface,
positive/negative consumers and test doubles before independent tasks begin.
Internal allocation strategy, node representation and renderer visitor dispatch
remain implementation choices unless a measured result requires a decision.

| ID | Owner family | Depends on | Stable responsibility |
| --- | --- | --- | --- |
| ORM-C01 | Types/language | None | SQL/CLR types, logical query and parameter identity, scope and snapshot ownership |
| ORM-C02 | Rendering/dialects | ORM-C01 | Capability validation and semantics-preserving rendering |
| ORM-C03 | Command boundary | ORM-C01, ORM-C02 | Atomic SQL/layout/result template and per-invocation typed arguments |
| ORM-C04 | Execution/providers | ORM-C03 | Binding, row mapping, lifetime, cancellation, transactions and errors |
| ORM-C05 | Schema/generation | ORM-C01, ORM-C03, ORM-C04 | Offline schema/model generation and statically reachable mapping |
| ORM-C06 | Verification/packages | ORM-C01–ORM-C05 | Feature evidence, independent module checks and package/API compatibility |

The dependency table describes semantic inputs, not a requirement that the full
implementation of each contract finish before another task starts.

## ORM-C01: SQL language and type identity

`SqlType<T>` contains a stable SQL type identity, CLR representation `T`, SQL
nullability and relevant facets: length, precision/scale, array element type,
domain/enum identity and temporal policy. Driver type objects are forbidden.
Reference-nullability annotations are not the sole SQL-nullability representation.
Domain types that happen to share a CLR representation remain distinguishable.

`Field<T>` represents a typed scalar expression; `Condition` represents SQL truth
including UNKNOWN. A relation has identity independent of its alias text, and its
fields retain that identity. Typed rows/projections preserve degree and component
types. The model supports physical/derived tables, joins, CTE references and
correlation without requiring an entity class per intermediate query.

`Param<T>` identifies a logical typed slot. Names aid diagnostics but do not define
binding order or permit two incompatible slots to collide. Distinct slot identities
are never merged merely because their names and SQL types match. Query descriptions
can be shared across invocations; request values belong to invocation state.
Literal expressions are explicit and distinct from bound slots.

Reusable query objects are immutable snapshots. Builders, if used, have single
ownership, and `Build` freezes collections. Extending a query cannot modify another
query that shares a subexpression. Execution cannot mutate a query to attach a
connection, command or cached request. Render contexts are invocation-local.

Compile-time validation rejects unrelated generic operands, invalid known row
degree and unsupported generated DTO members where expressible. A pure validation
pass handles scope, grouping, dialect/version and runtime-composed layout rules.
Database constraints, permissions, actual cardinality and stale schema may still
fail at execution. Diagnostics must state that boundary honestly.

SQL equality with a NULL parameter remains SQL equality. `IsNull`, null-safe
distinctness, missing optional predicates and TRUE/FALSE/UNKNOWN are separate
operations. Empty membership, row NULL, outer-join nullability and set-operation
coercion follow the source-linked cases in [language-model.md](language-model.md).

## ORM-C02: rendering and capabilities

Input: immutable query snapshot, explicit database/version profile, render options,
placeholder mode and structural collection cardinalities where expansion is
required. Output: a complete C03 template or a deterministic failure.
No connection, driver, task scheduler or external process is required.

The profile states tested version ranges and relevant extensions/settings rather
than a single universal database capability bitset. Each operation/context is:

- **Native:** the selected profile preserves the required semantics directly.
- **Equivalent lowering:** a documented rule preserves semantics under checked
  preconditions, including NULL, collation, ordering and evaluation behavior.
- **Unsupported:** reject before execution with operation/profile/precondition.
- **Planned/unverified:** unavailable to product consumers until separately accepted.

Do not silently omit locks, RETURNING, materialization requests, conflict targets,
NULL ordering or other requested semantics. Hints that are intentionally advisory
need an explicitly named advisory API with documented behavior; they cannot weaken
a strict semantic API. Rewrites may not duplicate volatile expressions or change
row cardinality without proof that the supported case is equivalent.

Alias resolution and quoting operate on identifier segments, not caller-composed
SQL. Bound values never become string-concatenated SQL. Raw SQL extensions require
explicit typed/parameter/result declarations and are marked as escaping some
static validation; placeholders cannot be discovered by a naive text scan.

Driver-neutral type/dialect code decides casts and SQL declarations. Providers
decide wire encodings and reader conversions. Limits on parameters, nesting or SQL
size fail explicitly; an oversized list is not silently truncated.

Initial execution is one database command. Native RETURNING is allowed only in
profiles that support the requested operation. Generated-key and follow-up SELECT
emulations are excluded until an explicit execution-plan contract is added.

## ORM-C03: rendered template and bound command

The selected names make ownership explicit:

| Value | Required content | Ownership |
| --- | --- | --- |
| `RenderedTemplate<TArgs, TRow>` or equivalent typed handle | SQL text; profile/placeholder identity; ordered binding occurrences; typed logical slots; result descriptor; validated lowering requirements | Immutable and reusable; contains no request values, driver objects, connection, active reader or mutable builder callbacks |
| Binding occurrence | Logical slot identity; parameter ordinal/name required by placeholder mode; SQL type/facets; conversion identity | Ordered by the final rendered tree, including duplicated or removed occurrences |
| Result descriptor | Ordered projection identity/aliases; SQL/CLR type; nullability; conversion; nested presence policy where applicable | Describes the actual emitted SELECT/RETURNING shape |
| `BoundCommand<TArgs, TRow>` / invocation | Template plus typed per-invocation argument access and mapping identity | Single execution ownership; values retained only until completion or stream disposal |

Generics are an implementation candidate; a bounded typed-cell layout may support
heterogeneous dynamic slots. Do not make `object[]`, reflection or unbounded
runtime generic construction the mandatory path. Supported scalar types and
custom codecs must be statically reachable. Handwritten static binders/projectors
are valid alternatives to generation.

SQL, occurrence map and result descriptor must come from one successful render.
The exporter cannot publish separately updated arrays. Repeated logical slots may
map to repeated occurrences or intentional positional reuse according to the
placeholder policy; adapters follow the recorded map exactly. A typed NULL keeps
its declared SQL type. Missing required slots, unknown explicitly supplied slots
and incompatible values are errors. A statically known `TArgs` may be a superset
of the members used by one optional query shape; unused members are not errors
and are not bound. An `Eq(T)` convenience overload, if introduced, must specify
whether it captures an invocation value or creates an explicit literal. It may
not silently retain request values inside a reusable template.

Expanded `IN` lists declare their cardinality as structural render input; `Bind`
rejects a different length. A native-array parameter may instead be a single
typed slot where the profile supports its semantics. A `RenderAndBind` convenience
path may snapshot a collection and its arity before rendering; the executor may
not rewrite SQL or append placeholders after validation.

Cache identity includes query shape, explicit SQL literal constants,
profile/version/settings, placeholder policy, SQL type facets, expanded-list
cardinalities, conversion and result shape. Bound request values are excluded;
`Literal(1)` and `Literal(2)` are different shapes. Debug/inlined rendering is not
the cache-key algorithm. No global unbounded shape cache is
required; caching is opt-in or bounded with an eviction policy justified by data.
Pooled render memory cannot escape in the returned string/layout.

A representative **uncompiled** composition sketch is:

```csharp
var minimum = Sql.Param<int>("minimum", SqlTypes.Int32);
var predicate = users.Id.Ge(minimum);
if (onlyActive)
    predicate = predicate.And(users.IsActive.Eq(Sql.Literal(true)));

var query = Sql.Select(users.Id, users.Name).From(users).Where(predicate);
var template = renderer.Render(query, postgresProfile);
var command = template.Bind(arguments); // generated or manual typed argument access
// Rendering above requires no execution package or database driver.
await foreach (var row in session.StreamAsync(command, userProjection, cancellationToken))
    Consume(row);
```

The foundation task resolves exact signatures and overloads, including typed
`arguments` and `userProjection`, before this becomes a compilable example.
It must not replace these semantics with untyped dictionaries for convenience.

## ORM-C04: execution and resource lifecycle

Execution preflight verifies template/provider compatibility, codecs, arguments,
result mapping and caller cancellation before sending SQL. It binds explicit
layout entries through generated/manual typed access and never reparses SQL to
rediscover them. Validate reader shape once, then use typed per-row access. Strict
ordinal mapping must reject a mismatched result layout before silently assigning
wrong members; name-based compatibility is an explicit alternate policy.

For buffered results, owned records/DTOs outlive reader disposal. A streaming
sequence starts execution on enumeration, has one active enumerator, rejects
concurrent `MoveNextAsync`, and holds command/reader/owned connection until EOF,
failure, cancellation or `DisposeAsync`. Early break returns those resources.
Rows are owned by default; a future borrowed-row API must use a separate explicit
lifetime. Re-execution requires creating a new invocation, not reusing a live one.

The API distinguishes an owned connection/session from an externally supplied
connection/transaction. It disposes only resources it owns. User-owned resources
must not be shared concurrently unless the driver contract explicitly allows it.
Request scalars may be copied; mutable arrays/memory and custom reference values
are either snapshotted or borrowed under a documented no-mutation-until-completion
rule. A `Span` cannot cross an asynchronous retention boundary.

Use `CancellationToken` last with the usual default and `Async` naming. Cancellation
before admission prevents sending; later cancellation requests the driver's
behavior and does not prove a transaction had no effect. SQLite async methods may
perform synchronous work and cannot promise in-flight `Cancel` interruption.
Do not manufacture cancellation support by dispatching to a private thread pool.
Timeouts, caller cancellation and provider errors retain their distinct meaning.

Transactions remain driver transactions. State explicitly who begins/commits/
rolls back, whether nested savepoints are supported, and what happens on disposal.
A failure during commit can have an unknown outcome; no automatic retry is implied.
Korda adds no implicit cross-provider transaction or retry engine.

Argument/type/scope/capability errors are deterministic domain/argument errors;
conversion and unexpected NULL failures identify the column and expected type.
Preserve provider exceptions/codes or wrap them with a retained inner exception
and stable category. Do not include credentials or parameter values by default.
Logging/DI/hosting are optional outward integrations. Session/transaction state is
not globally mutable, while immutable templates can be shared.

## ORM-C05: schema and generation

A deterministic schema snapshot records source provider/profile, object identities,
qualified names, SQL types/facets/nullability, keys/constraints and unsupported
metadata. Discovery is an explicit local CLI action using the appropriate driver.
Roslyn consumes versioned offline input and source symbols, without opening a
database or contacting a service during compilation.

Schema types generate typed tables/columns/keys, not runtime database objects.
DTO/projection generation emits explicit constructors/member assignments and
statically registered conversions; no reflection fallback or runtime IL is allowed.
Incremental generator inputs must be deterministic and diagnostics actionable.
Public record constructors and accessible `init` members are supported through
generated constructors/object initializers. Unknown schema types, ambiguous names,
inaccessible or otherwise unexpressible assignments and missing codecs fail
compilation/configuration rather than silently becoming `object`.

Handwritten metadata and static mapping remain supported. A schema change requires
regenerating/recompiling C# only; no Java/Rust/C++ query engine compilation is part
of consumer development. Generation has its own build-time dependencies; these
cannot leak into the runtime pure DSL. Schema drift is a separate validation
concern and is not disproved by successful code generation.

## ORM-C06: validation, packaging and compatibility

Each implemented operation links upstream source/semantic basis, deliberate C#
differences, positive/negative cases, supported profiles and actual evidence state.
Pure checks validate types, scopes, SQL/layout and semantics without a server.
Independent database tests validate real behavior; native consumers validate AOT
and dependency closure. [Validation](validation.md) distinguishes these gates from
research probes and documentation checks.

Product modules register source/test paths, genuine dependencies and selected
checks in the existing Korda mechanism. Metadata-only package edits validate
shipped metadata; source/generator/API changes validate affected public APIs and
compiled examples. Every top-level package is independently restored and consumed
from the exact candidate nupkg in an isolated package cache. Driver-specific
native assets and license/NOTICE closure are inspected as shipped.

Public signatures, defaults, nullability, error/cancellation/resource semantics,
XML reference and source examples evolve together. A semantically breaking
lowering change requires compatibility review even without a signature change.
No documentation check accepts database behavior, AOT or performance. No benchmark,
profiling or temporary evidence upload belongs in normal document CI.
