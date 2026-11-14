# Requirements charter and delivery boundaries

Status: requirements consolidation; version 0.3.0; date 2026-11-12. Basis: the NativeWeave main task uploaded by the user and the clarifications in this round. This charter is a research input, not the final architecture ADR.

## 1. Goal

NativeWeave is an independent, general-purpose framework. Modern C# is the application development language, providing business logic, strongly typed Fluent APIs, generics, and async/await. Production applications are published with Native AOT; Database, ORM, and Server must deeply reuse mature Rust engines for their actual foundations. Rust handles database drivers, query construction, dialects, execution, pools, transactions, native ORM capabilities, and network I/O, HTTP, connection management, scheduling, Streaming, and Backpressure; C# provides interfaces, static metadata, mapping, and business Handlers. Application developers should, in principle, not have to learn Rust, write FFI manually, or repeatedly handle cross-language lifetimes.

“Any application” expresses the direction for extensibility; it does not mean all workloads are supported, nor does it promise that C# + Rust outperforms both pure C# and pure Rust on every metric. Formal capabilities are stated for specific combinations of platform, version, feature, and evidence.

## 2. Non-negotiable constraints

| ID | Constraint | Verification method |
| --- | --- | --- |
| NW-P01 | C# First; C# is the complete application development language | Application developers do not handwrite Rust/FFI; independent managed components that do not consume an Engine do not acquire a native runtime dependency |
| NW-P02 | Native AOT Required | Actual publish, execution, and behavioral tests for every formal target; warning review |
| NW-P03 | Native Engines Required | Rust foundations for Database/ORM/Server are a product constraint; the specific combination of mature engines requires source and verification evidence |
| NW-P04 | Simplicity, elegance, and efficiency internally and externally | Every abstraction has a necessity, dependency, and cost ledger; remove layers that add no value |
| NW-P05 | Independent Engines | Each engine can be built, tested, versioned, and released independently; no implicit sharing of domain state |
| NW-P06 | Native-ready integration process | The integration specification covers ABI → glue → Adapter → AOT → package → compatibility → release |
| NW-P07 | Performance by Evidence | Comparable C# AOT / C# AOT+Rust / Rust workloads, with uncertainty reported |
| NW-P08 | Three independently modeled forms of parallel work | Research / Documentation / Delivery each have their own graph, file ownership, and status |
| NW-P09 | Plan both major phases in depth concurrently | Concrete research, specification tasks, and candidate implementation tasks for Database, ORM, and Server |
| NW-P10 | Independent content | ArcForges provides historical context and a formatting reference only; it is not a business or architecture dependency |
| NW-P11 | Modern stable mechanisms | Separate experimental/preview/nightly features from required production capabilities; verify versions as of a recorded date |
| NW-P12 | Honest evidence | Do not fabricate source coverage, compilation, execution, GitHub, review, or performance results |

## 3. Phase A: complete research and design required in this round

ABI types and versions, automatic bindings, strongly typed C# Adapters, Ownership/Lifetime, SafeHandle/GCHandle, callback unregistration and reentrancy, asynchronous completion/cancellation/shutdown state machines, buffers/Pinning/data transfer, errors/Panic, threading/backpressure, cross-platform build/AOT/NuGet/Cargo, and composable Engine integration.

Validate the design with at least two real candidate modules whose interactions differ substantially: one synchronous data-transformation module and one stateful asynchronous streaming module. Compression/codecs and HTTP or database streaming are preferred candidates, but current native .NET capabilities must be compared and selection decided independently. Research modules expose foundational defects; they cannot be used to bypass production acceptance for phase A.

## 4. Phase B: planning at equal depth in this round

- Database: PostgreSQL and SQLite candidate matrix; connection pools, type mapping, parameters, transactions/savepoints, query streams, batching, cancellation/timeouts, disconnections, retry idempotency, migrations, and recovery.
- ORM: entities/relationships/projections/Join/aggregation/pagination, SQL NULL/sorting/collation, parameterization, strongly typed Fluent Query, optional static metadata/DTO generation, no requirement for a complete LINQ Provider, controlled dynamic queries, and AOT metadata and diagnostics.
- Server: Kestrel/.NET only as a networking comparison, mandatory Rust networking engines, HTTP/TLS, gRPC/MCP adapters, request/response streaming, backpressure, resource reclamation, shutdown, and Metrics/Tracing.
- Combined verification: a reference application independent of ArcForges; real databases, transactions, migrations, request cancellation, fault injection, sustained workloads, and recovery.

Research and documentation proceed in parallel immediately. Formal product integration may consume only accepted local foundational contracts that have undergone the required verification. Managed providers are used only for independent source/benchmark comparisons, not as product database backends; actual integration acceptance must not be split into empty shells with no responsible owner.

## 5. Future boundaries

For GPU/GPUI/NSH, iOS/Android, thread-affine UI, SIMD, codecs, and other protocols, research only the integration boundaries and platform constraints; do not implement them comprehensively in this bootstrap batch. Mobile platform maturity, static linking/signing, and Java or platform interop restrictions must be verified separately.

## 6. Authorization and status for this round

Authorized: reading the specified repositories and public sources; research, documents, graphs, and minimal proof programs; safely creating research branches and Draft PRs; and preparing future Codex tasks.

This round does not write formal NativeWeave product code, refactor ArcForges Go Center, publish production NuGet/Cargo packages, or merge significant architecture decisions that have not been reviewed. Items requiring actual tests for which the environment is unavailable retain an explicit not-executed status.

## 7. Latest clarification

The user explicitly stated: **“The ArcForges reference specifications are for you to look at the format, not the content.”**

Accordingly, observe only document directories, entry points, links, tables, and record formats. NativeWeave technical choices, execution policies, and acceptance gates are established independently from the current goals and this project's evidence. Content read in the reference specifications is not used as a basis for this project, and its rules are not migrated.


## Source-Driven Deep Native Integration — clarified requirement

Study and reuse actual native structures, algorithms and lifecycle before designing the C# convenience layer. Prefer public APIs, but evaluate dedicated source-informed adapters, upstream extensions and controlled forks when justified. Never expose private Rust layout as ABI. Ordinary C# database entities/queries using enabled native capabilities consume maintainer-precompiled NuGet assets, without Cargo or a CI dependency for local execution. Typed Fluent is preferred over a full IQueryable/EF translator; no duplicate C# SQL engine. Optional generators supply static metadata/DTOs, not a mandatory runtime query compiler.

Preserve capability/error/ownership correctness, AOT and cross-platform acceptance. Compare native Server with Kestrel AOT honestly; Kestrel is never a product Host. The choice among Rust Server engines remains source/evidence-driven. Source pins, locked closure, behavior/ABI/performance regression and patch retirement belong to D10/D11 and existing tasks. Research decisions, implementation verification and production acceptance are distinct.
