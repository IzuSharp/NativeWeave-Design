# ADR-0002 — Source-driven integration and precompiled dynamic database profile

Date: 2026-11-12. **Status: proposed; independent review pending.** Supersedes the *candidate design assumptions* DB-D004/DB-D005, QUERY-D004/QUERY-D005 and mandatory per-model Rust generation in D14/D16/D17 at main `baa953772d2a771bb4da3aff0cf4b4be6fc811a1`. It does not invalidate inspected upstream facts, historical reviews of their original bytes or the retained lifecycle/transaction safety constraints.

## Context

The user's clarified requirement is a C# Native AOT application surface backed by mature Rust engines, with ordinary entities and Fluent queries using precompiled native modules. Full EF/IQueryable semantics are not required. The initial Plan still describes managed PostgreSQL and optional native DB tasks, whereas the merged database Design requires Rust and selects a schema-specific SeaORM build. These are two separate inconsistencies; neither can be fixed by adding only a general principle paragraph.

## Decisions recommended for review

1. Use source-driven Engine adapters with small shared interop contracts. Public API is preferred but internal source investigation, upstream extension and controlled forks are legitimate options when justified by a specific capability/cost gap.
2. Select **SeaQuery dynamic query construction plus SQLx execution as the default database implementation candidate**. The ordinary path has runtime identifiers/values and typed C# descriptors; it does not require compiling a SeaORM Entity for every C# business model. Rust remains responsible for query construction, SQL dialects, database execution, pool/transaction state and explicitly supported ORM policies.
3. Use a directly bound native builder as the correctness/reference path. Batched native commands and generated static fast paths remain performance candidates, not preselected universal IR. C# must not grow a second SQL semantic optimizer/dialect emitter.
4. Support handwritten static descriptors and optional incremental generation of model/DTO mappings. Natural typed Fluent composition is ordinary code building native expressions, not arbitrary C# lambda-to-SQL translation. Default query semantics are explicit SQL semantics, not hidden EF/C# null compensation.
5. Keep SeaORM's typed Entity/ActiveModel/Relation route as a separate specialized alternative when its generated Rust model benefits justify its native build coupling. Merely using raw statements through SeaORM is not evidence of obtaining its full ORM behavior. No full identity map, lazy-loading or graph-save engine is implied by SeaQuery+SQLx.
6. Make backend capability rejection and fallible value binding mandatory: SQLite silently ignores some SeaQuery constructs, and the inspected SQLx binder contains panic/discarded-error cases. The Adapter needs these checks even when upstream is mature.
7. Investigate a public Hyper/Tower/Axum foreign-service/body adapter, with Actix as a worker-affine alternative and Pingora for proxy-specific requirements. Retain Kestrel Native AOT as a baseline; no native Server production default is selected without comparative evidence.

## Evidence

[R25 source study](../research/topics/R25/source-driven-seaquery.md), [R27 Server study](../research/topics/R27/source-driven-server.md), the [recovered Linux Native AOT experiment](../research/source-driven-evidence/README.md) and the new finite response-body admission model. Native binary reuse for a second entity is actually demonstrated within the prototype's bounds; it is not just a language-level conjecture. No complete production ORM, server bridge, Windows build or performance superiority is established.

## Alternatives and consequences

The former schema-specific SeaORM route can provide compile-time Rust Entity behavior but imposes a native rebuild for application model variation in that route. Full LINQ capture/normalization duplicates substantial query compiler responsibilities without a requirement for full compatibility. A C# SQL builder with SQLx only at the bottom avoids neither duplicate dialect work nor the user's source-reuse objective. A command protocol can amortize FFI but costs another decoder and temporary storage; it needs measurements. Exporting private Rust AST layouts is rejected for ABI and ownership reasons, not because inspecting private source is forbidden.

The selected candidate still needs substantial integration: stable native handles/owned values, feature validation, typed result batches, fallible parameter codecs, asynchronous execution and cancellation, pool quarantine, explicit relation/CAS/migration scope, NuGet/RID assets, compatibility tests and independent review. This is smaller than recreating a full SQL provider, but no measured engineering or runtime saving is claimed yet.

## Implementation and remaining verification

Revise existing B01–B14 and A13–A16/A22/A24; B04 is required native database infrastructure, not an optional competing provider. B09 is binding metadata/operation definitions, B10 static descriptor generation, B11 Rust SeaQuery construction/binding, B13 runtime Fluent composition. Keep B17 optional. AOT per-OS, PostgreSQL failures, huge values, concurrency, unsupported backend operations, clean Rust-free consumers, RID-free local commands and source-generator parity remain explicit gates. Close the *design uncertainty* about mandatory per-entity Rust compilation for the dynamic profile; do not close production verification or independent acceptance.
