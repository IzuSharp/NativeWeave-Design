# C# Public API Design and Documentation Standard

Version: 1.0.0. Status: normative design standard, subject to the current exact acceptance record. Applies to every NativeWeave package, optional Engine, generator, adapter and future repository that explicitly adopts this standard. This document specifies engineering obligations; it does not announce a product release.

## 1. Authority and adoption

The application language is C#. Public APIs must be convenient, discoverable, strongly typed, explicit about resource ownership, and implementable with Native AOT. Rust Engines own their established domain algorithms, state and execution. An attractive C# API is not justification for rebuilding a managed SQL engine, network server or global native runtime.

Read the current requirements, accepted contract versions, [API specification index](../api/README.md), exact declarations, coverage rows and owning Delivery task before changing an API. The existing 34 Research, 32 Documentation, 21 contracts and 48 Delivery tasks remain the coordination system. This standard is an input to those tasks, not another scheduling graph.

AGENTS.md only governs agents that actually read that repository. A new repository must copy the [adoption template](../../templates/public-api/AGENTS.fragment.md), pin this standard's content hash and immutable Design commit in its adoption manifest, and install the checks described below. A link to a moving main branch does not establish adoption. A24 owns the Engine scaffold; A13 installs shared build rules; A22 owns compatibility policy; the module owner owns its API and documentation. NativeWeave's product repository will adopt these files only when product work is authorized.

## 2. Stable reference baseline and source research

For each API change, record the date, current official stable .NET SDK/runtime/C# release, applicable package versions, and actually inspected upstream source. This round uses .NET 11.0.0, SDK 11.0.100 and C# 15.0. `global.json` disallows preview roll-forward. Preview syntax, proposed language features, source on an unpinned main branch, and a documentation page's target selector are not evidence of stable availability.

Compare relevant feature families rather than counting unrelated BCL methods. Reference BCL/TAP, ADO.NET, EF Core, Dapper, LINQ, ASP.NET Core and Extensions according to the domain. Record a full source SHA, file, symbols, read ranges, retrieval date and coverage limits; distinguish a source file read from upstream tests run. Reuse earlier verified Rust source and experiment evidence when its exact version still applies. Do not redo a successful experiment merely to make its timestamp newer.

Each coverage row must identify reference APIs and versions, NativeWeave symbols, native Engine, managed/native operations, design support classification, AOT behavior, memory/call cost, restrictions and existing owning tasks. `full`, `equivalent`, `limited`, `planned` and `unsupported` describe design coverage. A separate implementation/evidence field determines whether a product can claim the feature. An upstream capability alone never implies NativeWeave exposes it.

## 3. Public surface and package boundaries

Use a `NativeWeave.<Domain>` namespace matching a developer concept. Keep ABI records, raw handles, `GCHandle`, function pointers, Rust discriminants and loader plumbing internal. Put maintainer-only extension contracts in a clearly separate namespace and package. Public SPI receives compatibility review even when most applications never use it.

Packages compose by capability. Installing a Database provider must not install Server, GPU or protocol Engines. Server must not require Database. Optional DI/Hosting/protocol packages may depend on the relevant application packages; Core must not depend on them. A package may depend on a small Extensions abstraction when its visible API actually uses that abstraction. Record transitive dependencies and their startup/allocation costs rather than calling every dependency free.

Prefer a small concrete factory or builder that returns a usable owner. Do not require global Initialize/Shutdown, duplicate module registration, manual native-library paths, handwritten entity handles, or a Rust toolchain for the ordinary path. Advanced configuration must extend the same underlying lifecycle, not create a parallel undocumented initialization path. Only an actual unsupported platform, missing asset or compatibility failure should make ordinary initialization fail.

Extension methods belong where IntelliSense can find them from the advertised namespace; examples state their package and `using` requirements. Avoid unrelated extension overloads that pollute every object. There must be a unique owner for each shared primitive; B01 owns Data primitives, B07 their fallible native codecs, and B09 consumes those definitions.

## 4. Types, signatures, nullability and overloads

Publish exact fully qualified declarations with accessibility, inheritance, generic constraints, nullability, parameter names and defaults. Parameter names and optional defaults affect source compatibility and documentation. An overload review must include lambdas, `null`, `default`, method groups and named arguments; compiling a single happy-path call is insufficient.

Use sealed reference types for native-resource owners with identity and disposal. Use small immutable value types for values whose default state is valid or explicitly rejected; never make a copyable struct own a native allocation. Use records for genuinely structural immutable data, not resources or a large mutable options graph. Interfaces represent an intentional consumption/extension seam, not one interface per class. Public abstract classes require a justified inheritance and versioning story.

Nullable reference types are enabled. `null` means a documented absence, not an undocumented sentinel for several policies. Empty collections, SQL NULL and a missing row are distinct. Specify default options independently from the compiler's parameter defaults. Builders are mutable, single-threaded configuration objects; Build snapshots and validates their values. Changing a builder afterwards must not silently mutate a running Engine.

Constraints must express the supported model rather than demand `new()` or reflection just for implementation convenience. Source-generated static metadata supports ordinary C# entities and DTOs. A missing mapping produces an actionable compile diagnostic or a deterministic configuration error, not arbitrary runtime reflection. Reflection that requires unbounded preservation is not an AOT fallback.

## 5. Async, streaming, cancellation and time

Use `Task`/`Task<T>` for ordinary asynchronous operations and append `Async` to their names. `ValueTask` requires a documented synchronous fast path or an inherited BCL contract, a single-consumer statement, and measured justification for pooling. Never expose a reusable operation source as an ordinary multiply-awaitable Task. Async methods do not silently block for native completion on the initiating thread.

Put `CancellationToken cancellationToken = default` last unless an established BCL override dictates otherwise. Argument validation occurs before admission; specify whether it throws directly or is observed through the returned awaitable. Cancellation before admission performs no work. Cancellation after admission requests cancellation; it does not prove no SQL, HTTP or external effect occurred, nor does it release retained native storage. Preserve C-ASYNC-001 terminal-result and native-quiescence separation.

Use `OperationCanceledException` for cancellation with the relevant token when known. Document timeout separately: configured operation timeouts produce a timeout classification, while caller cancellation produces cancellation. Convert a duration to a monotonic native deadline once at admission; remaining budgets pass downstream without resetting at every layer. Reject negative finite durations, handle zero deterministically, and state whether infinite is permitted. Do not expose a universal Deadline abstraction merely to rename `TimeSpan`.

An `IAsyncEnumerable<T>` contract must state when execution starts, whether enumeration can repeat, when a connection is held, whether elements are owned or borrowed, the maximum batch/byte budget, and what early `break`/enumerator disposal does. Reject concurrent `MoveNextAsync` on one enumerator. Apply enumeration cancellation as well as method cancellation. Streaming must not secretly materialize an unbounded result or buffer the entire HTTP body.

No sync-over-async convenience wrappers. A synchronous API exists only when the Engine offers a bounded synchronous operation with a clear reentrancy contract. Start/cancel/complete races, completion before start returns, callback revocation, and synchronous token registration are required implementation tests.

## 6. Ownership, buffers and concurrency

Every API must identify the owner of returned resources, the borrow boundary of supplied data, parent-child behavior, repeated-disposal behavior, and the result of use after logical close. `using` and `await using` are normal application syntax; custom dispose flags and release callbacks belong only in a justified maintainer SPI.

`Dispose` must not wait under a lock needed by completion. `DisposeAsync` may wait for native obligations; an explicit bounded Close operation reports incomplete cleanup without claiming reclaimed memory. A timeout cannot justify freeing a callback context or borrowed buffer still reachable by native code. Finalizers are a safety fallback, not a successful shutdown protocol. Physical module unloading is not inferred from disposing an Engine owner.

Accept `ReadOnlySpan<T>` only for synchronous borrowing that ends before return. For asynchronous retention, use `ReadOnlyMemory<T>` with a defined copy/pin/lease contract or an explicit owned memory type. Never retain a span or an unstable address across `await`. Buffer lengths state units, limits and overflow behavior. Copying is acceptable when it is the simplest safe route; calling it zero-copy requires measured evidence for the complete route, including serialization and native Engine copies.

Document thread safety per type and member family. An immutable descriptor can be shared; a session, transaction, enumerator, builder or borrowed request context generally cannot be concurrently mutated. Do not imply Rust `Send`/`Sync` or `Arc` automatically makes managed callbacks thread safe. Thread-affine Engines require an explicit dispatcher/affinity capability. User continuations run outside native locks and raw FFI callback frames.

## 7. Errors and observability

Use standard argument, disposal, cancellation and timeout exceptions where their semantics fit. Use narrowly scoped domain exceptions for provider failures and an Engine exception for native compatibility/panic/poison failures. Preserve stable category, native code/domain, operation and correlation identifiers without exposing a raw Rust error object or a secret-bearing connection string.

Use Try APIs for an expected nonexceptional absence or capability test. Use explicit result types when several independently meaningful facts must be returned, such as transaction outcome versus cleanup. Do not wrap every return value in a universal Result solely to imitate Rust. Expected SQL NULL is not an error; an unknown remote commit is not a retryable failure by default.

Classify unsupported capabilities before side effects where possible. Panic containment does not recover from abort, OOM abort or arbitrary memory corruption; a poisoned owner rejects further operations according to the accepted error contract. Managed exceptions must not escape reverse P/Invoke.

Expose .NET `ILogger`, `ActivitySource`, `Meter` and stable diagnostic identifiers where appropriate. Disabled diagnostics avoid per-operation message formatting and unnecessary allocation. No SQL parameter values, authorization headers, TLS secrets or arbitrary payloads are logged by default. Trace/correlation context crosses the adapter as bounded data, not an implicit managed execution context captured indefinitely.

## 8. Exact implementation mapping

For every native-facing feature, specify the complete path:

`C# public member -> managed admission/adapter -> versioned C ABI operation -> Rust adapter -> pinned Engine operation`.

The mapping includes parameter representation, encoding, optional values, status/out values, capability bits, borrowed/owned storage, operation IDs, callback completion, state transitions, cancellation, cleanup, and release order. A method name alone is not an implementation contract. Rust private layout never becomes the ABI. Existing ABI bootstrap/status/handle/lease definitions remain authoritative; a new domain operation extends the declared operation inventory without silently changing the base wire contract.

A managed façade may validate arguments, encode values, generate descriptors, materialize DTOs and run business handlers. Native Engines own query AST/dialect decisions, connection/pool/transaction execution, routing/protocol/network I/O, flow-control and native state. Record the actual boundary cost: FFI calls, managed/native allocations, bytes copied/pinned/retained, callbacks, queueing, runtime instances, and asymptotic work. An allocation ledger is a design estimate until measured.

## 9. API documentation is part of implementation

Every public/protected symbol requires XML documentation and an API Reference entry. Include summary, parameters, generic parameters, return value, exceptions and remarks for lifetime, concurrency, cancellation, platform/capability and costs. Types document shared policy; members may explicitly inherit it and list exceptions. Inheritance must be mechanically resolvable; a vague 'see implementation' is not documentation.

Keep API Reference generated from the actual compiled public surface and XML documentation. Preserve exact signatures and stable documentation IDs. Narrative guides explain composition and choices; they must link back to the reference and runnable sample source. Do not hand-maintain a second conflicting signature set. The design declaration catalog is a design input; future product assemblies become the release reference authority.

Examples have explicit evidence states: `draft`, `static-reviewed`, `design-compiled`, `design-executed`, `design-native-aot-executed`, `product-compiled`, or `product-executed`. Each executed state pins source, toolchain, platform, command, exit status and artifact/log hashes. A stub-only AOT run validates compilation/linking, never database or server behavior. Released documentation must not offer unimplemented designs as installable packages. See [documentation system](../api/documentation-system.md).

## 10. Compatibility and review gates

Version source crates, native ABI, managed packages/API and domain semantics independently. Adding an optional parameter instead of retaining a binary overload, tightening nullability, adding interface members, changing defaults, switching Task to ValueTask, changing disposal/blocking, changing exception categories or altering query semantics all need compatibility assessment. A new overload can break source code through ambiguity even when binary API comparison passes.

Use a versioned public API baseline and .NET package/assembly compatibility validation against the last supported release. A baseline update requires review; it must not automatically accept removals. Obsolete APIs include a diagnostic ID, explanation, migration path and planned removal release. Experimental APIs live in explicitly marked packages/namespaces and do not quietly enter the stable surface.

Every relevant Delivery acceptance includes: declaration and consumer compilation; actual required-platform Native AOT execution; generated metadata/handler scenarios; XML/reference/symbol coverage; exact API compatibility; native capability/ABI mapping; resource/cancellation/error tests; package dependency inspection; minimal and advanced consumer paths; and independent review of usability as well as correctness. Tasks with no public API record a justified not-applicable decision and still check any native ABI/internal boundary they own. Evidence is scoped to the owning task; A16/B24 own pristine no-Rust consumption and final release composition.

Reviewers must not accept their own changed design. Record finding IDs, severity, affected inputs, actual fixes and a final exact-content recheck. Preserve prior acceptance snapshots, even when new versions supersede them. A passing linter cannot replace source/semantic review. Do not relax a failing gate to make a new API pass; first determine whether it is a historical gate that must run at its original immutable input or a current invariant that must be fixed.

## 11. Required change packet

An API change is ready for independent review only when it contains:

1. The developer scenario and smallest complete consumer example, including package and namespace.
2. Exact declarations and overload/negative-consumer checks.
3. Per-symbol semantics or a precise inherited semantic profile with explicit overrides.
4. Updated reference coverage and full managed/native mapping.
5. Cost ledger, Native AOT/generator behavior and unsupported boundaries.
6. XML/reference/guides/examples and compatibility impact.
7. Owning existing tasks, updated contract versions/hashes, actual validation and independent findings.

The template directory provides a reusable adoption checklist and change packet. These artifacts must be installed or pinned in a new project; other repositories do not inherit this standard automatically.
