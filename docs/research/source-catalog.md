# External Source Research Catalog and Priorities

Status: catalog of research entry points; 2026-11-12; not a dependency list. **P0/P1/P2 are reading priorities and do not create artificial start dependencies on one another.** Each topic may proactively expand its sources, but must explain the specific problem that each added project addresses.

The pinned SHAs and limited line ranges actually read in this round are recorded in [Interop evidence](interop/evidence.json), [domain sources](domains/sources.json), and [v11 supplementary checks](domains/v11-evidence.json). Official toolchain facts are in [toolchain](toolchain/evidence.json). The other paths/symbols in the tables below are entry points still to be located or investigated in depth, not completed coverage.

## P0: Sources That Determine Fundamental Safety and Feasibility

| Project | Specific research questions / priority entry points | Coverage in this round | Topics |
| --- | --- | --- | --- |
| [dotnet/runtime](https://github.com/dotnet/runtime) | NativeAOT, SafeHandle, LibraryImport generation, Span/Memory, async, and GC; implementations and tests must be read together | Official documentation verified; complete reading of pinned runtime source remains pending | R01–R04, R07, R09–R13 |
| [dotnet/roslyn](https://github.com/dotnet/roslyn), [csharplang](https://github.com/dotnet/csharplang) | IncrementalGenerator, syntax/semantic analysis, new union lowering, diagnostics, generation stability | Official feature documentation verified; compiler implementation research pending | R01, R05, R06, R23 |
| [rust-lang/rust](https://github.com/rust-lang/rust) | Rust2024, layout, FFI, panic, Pin/Future, safety boundaries, and tests | Official releases and reference verified; compiler source research pending | R01, R03, R09, R11 |
| [Cysharp/YetAnotherHttpHandler](https://github.com/Cysharp/YetAnotherHttpHandler) | RequestContext, SafeHandles, native binding/context, completion/cancellation/backpressure, and related tests | Partial call chain at a pinned SHA read; no execution results | R07–R12, R18 |
| [Cysharp/csbindgen](https://github.com/Cysharp/csbindgen) | emitter/type mapping/parser and AOT generation boundaries | Emitter excerpts at a pinned SHA read; other material only retrieved / pending research | R03–R06 |
| [Npgsql](https://github.com/npgsql/npgsql) | connector/pool/command/reader, type resolution, cancellation, AOT samples, and feature limits | Selected implementation and test/CI definitions at a pinned SHA read | R19, R21, R22 |
| [DapperAOT](https://github.com/DapperLib/DapperAOT), [Dapper](https://github.com/DapperLib/Dapper) | Incremental generation, call coverage, parameter and result mapping, dynamic fallback | Pinned DapperAOT generation entry points/snapshots read; normal Dapper implementation pending reading | R06, R23, R25 |
| [EF Core](https://github.com/dotnet/efcore) | QueryCompiler, precompilation, SQL translation/nullability, entities/relationships, provider tests | v10/v11 entry-point excerpts read; full translation chain research pending | R20, R23–R25 |
| [SQLx](https://github.com/transact-rs/sqlx) | pool, query/row, transaction/drop, SQLite worker, protocol cancellation/synchronization | v0.8.6 transaction chain and test excerpts read | R19–R22 |
| [ASP.NET Core](https://github.com/dotnet/aspnetcore) | Kestrel, RequestDelegateGenerator, response/request/connection lifecycle | Limited scope of v10/v11 response writer and tests read | R26, R29 |
| [Tokio](https://github.com/tokio-rs/tokio), [hyper](https://github.com/hyperium/hyper) | executor, bounded channel, HTTP streaming/shutdown, FFI boundaries | Channel/connection/feature excerpts at pinned SHAs read | R09, R12, R27, R29 |
| [PostgreSQL](https://github.com/postgres/postgres), [SQLite](https://www.sqlite.org/src/) | Server protocol, transactions/savepoints, actual SQL semantics, crash recovery | Official and driver research entry points; pinned engine implementation reading pending | R19–R24, R31 |

The old launchbadge URL for SQLx resolved to transact-rs/sqlx in this round; references should use the repository actually returned and a pinned SHA. Observations from an older release's source must not be treated as automatically covering the latest version.

## P1: Sources That Reduce Custom Development and Reveal Counterexamples

| Project | Why it is needed | Entry points for deeper study / cautions | Topics |
| --- | --- | --- | --- |
| [Godot](https://github.com/godotengine/godot) | A complex real-world case of native/managed object identity, signals, and lifetimes | modules/mono, GCHandle, destruction, threads, signals, tests; do not inherit the game engine runtime | R07, R08, R12 |
| [Qt for Python](https://github.com/qt/qtforpython) | ownership, parent-child relationships, event reentrancy, and thread affinity | Shiboken binding/object management, signal and destruction tests; Python runtime mechanisms cannot be applied directly to C# | R07, R08, R32 |
| [UniFFI](https://github.com/mozilla/uniffi-rs) | Existing designs for types/IDL, ownership, async bridges, and multilingual generation | Repository verified; generator, callback/future scaffolding, and tests pending reading; do not assume an official C# backend can be adopted directly | R05, R08, R09 |
| [Interoptopus](https://github.com/ralfbiedert/interoptopus) | Rust→C# inventory, patterns, and generation boundaries | Repository verified; current API, lifetime, async, and AOT tests need confirmation | R05, R18 |
| [Diplomat](https://github.com/rust-diplomat/diplomat) | Borrowing/lifetime descriptions and cross-language API generation | Repository verified; actual supported languages, C# paths, and limitations need verification | R05, R07 |
| [cbindgen](https://github.com/mozilla/cbindgen), [bindgen](https://github.com/rust-lang/rust-bindgen) | Different directions in the toolchain: Rust→C header and C→Rust | Repositories verified; layout/types/conditional compilation/tests; the two are not equivalent and do not automatically generate high-level C# APIs | R03, R05, R13 |
| [CsWin32](https://github.com/microsoft/CsWin32), [ClangSharp](https://github.com/dotnet/ClangSharp) | Comparison of mature C# static interop and metadata/clang approaches | Repositories verified; generators, diagnostics, tests; coverage of advanced Rust semantics cannot be assumed directly | R04–R06 |
| [linq2db](https://github.com/linq2db/linq2db) | Mature LINQ translation and multi-dialect implementation | builders, SQL conversion, mappers, AOT limits; a single success cannot establish support for the entire library | R23–R25 |
| [SeaQuery](https://github.com/SeaQL/sea-query), [SeaORM](https://github.com/SeaQL/sea-orm) | Rust query AST, type/transaction/relationship boundaries | Some directories located; code contents pending reading; Rust macros must not be treated directly as C# compile-time SQL validation | R22–R25 |
| [SQLitePCL.raw](https://github.com/ericsink/SQLitePCL.raw), [rusqlite](https://github.com/rusqlite/rusqlite) | Minimal C# SQLite bindings and a synchronous Rust approach | statement/connection lifetime, interrupt/WAL/threading, native loading | R20–R22 |
| [ET](https://github.com/egametang/ET) | Reference for Actor/Fiber scheduling and state management | First verify current mature paths and usage conditions; not a default general-purpose Server framework | R12, R26 |
| [Tower](https://github.com/tower-rs/tower), [Axum](https://github.com/tokio-rs/axum), [hyper-util](https://github.com/hyperium/hyper-util) | Division of middleware/backpressure/connection responsibilities | service, buffer, load-shed, shutdown tests; additional executor costs | R27, R29 |
| [grpc-dotnet](https://github.com/grpc/grpc-dotnet), [MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk) | Static registration and serialization approaches for protocol modules | AOT, stream cancellation, transport/version boundaries | R28 |
| [OpenTelemetry .NET](https://github.com/open-telemetry/opentelemetry-dotnet), [tracing](https://github.com/tokio-rs/tracing) | Cross-language diagnostic correlation and cost | Context propagation, sampling, asynchronous thread transitions; do not require every engine to introduce the complete stack | R30 |
| [TLA+](https://github.com/tlaplus/tlaplus), [Loom](https://github.com/tokio-rs/loom), [Miri](https://github.com/rust-lang/miri), [Kani](https://github.com/model-checking/kani) | Distinct capabilities for races, Rust validity, and bounded proofs | Specify the properties that can be checked and the FFI/OS scope not covered; tool count is not quality | R15, R16 |
| [Coyote](https://github.com/microsoft/coyote) | Candidate for managed concurrency scheduling tests | Repository verified; examine rewriting/scheduling in relation to AOT; test tools need not become product dependencies | R15, R16 |
| [BenchmarkDotNet](https://github.com/dotnet/BenchmarkDotNet), [Criterion](https://github.com/bheisler/criterion.rs) | Reproducible local performance experiments | AOT toolchain, cold-start and long-run limitations; cannot replace end-to-end workloads | R17 |
| [Testcontainers .NET](https://github.com/testcontainers/testcontainers-dotnet), [Toxiproxy](https://github.com/Shopify/toxiproxy) | Real-database and network failure reproduction | Host capabilities and boundaries between container/physical-machine evidence; validation tools only | R16, R21, R31 |

## P2: Examine Future Compatibility Boundaries and Avoid Premature Core Expansion

| Project | Research objective | Outside this round's product implementation scope |
| --- | --- | --- |
| [GPUI/Zed](https://github.com/zed-industries/zed), [gpui-kit](https://github.com/longbridge/gpui-kit), [nsh](https://github.com/longbridge/nsh) | Main-thread, event-loop, window/rendering resource, and mobile-shell constraints; the latter two repositories have been verified | Complete GUI products or commitments to adopt a particular engine |
| [wgpu](https://github.com/gfx-rs/wgpu), [wgpu-native](https://github.com/gfx-rs/wgpu-native) | GPU handles, callbacks, asynchronous mapping, threads, and stable C interface boundaries | Custom rendering frameworks or claims of support for all platforms |
| [Zstd](https://github.com/facebook/zstd), [zstd-rs](https://github.com/gyscos/zstd-rs) | Candidates for synchronous/streaming buffer engines, compared with .NET11's built-in Zstandard | Assuming a Rust wrapper necessarily outperforms .NET |
| [Apache Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) | Whether bulk data exchange, release callbacks, and columnar layouts are worth reusing | Requiring every DB return value to use a columnar layout |
| [.NET platform documentation](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/), [Rust platform support](https://doc.rust-lang.org/rustc/platform-support.html) | iOS/Android, static linking, CPU ISA, packaging, language/runtime bridges | "Official support" for platforms not actually built and executed |

## Source Evidence Admission

Pin the full SHA; record specific files, symbols, and line ranges; cover the studied mechanism completely through public API→implementation→error→release→tests. Label the evidence as README/documentation only, directory located, retrieved but unread, limited source reading, or confirmed by execution. This catalog marks only work actually performed as read.

Each new candidate requires its license, maintenance status, target support, and replacement cost to be added; popularity or modernity alone must not lead directly to adoption. Formal reuse requires reviewing the LICENSE and provenance at the exact version; GitHub's automatic license label is not a complete legal conclusion.


## Source-driven amendment / 2026-11-12

Existing IDs remain authoritative. R19–R25/D14–D17/B01–B14 cover native SeaQuery/SQLx, no managed fallback or per-entity Cargo, typed Fluent instead of full LINQ SQL translation. R26–R31/D18–D20/B15–B24 cover native Service/Body reuse and retirement budgets, retaining Kestrel AOT. R13/R14/R18/D10/D11/A13–A16/A22/A24 cover precompiled consumers, upstream mapping and controlled upgrades. See [impact/recovery record](../traceability/source-driven-impact.md). Partial source evidence does not complete all tasks.
