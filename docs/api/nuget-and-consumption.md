# NuGet, initialization and complete consumption specification

Version **1.0.0**; design-only, not a claim that the named packages are published. Owners: D01/D03/D10/D11/D31 and A02/A09–A16/A22/A24/B10/B15/B17/B24. Exact public signatures are in [Interop](interop.md), [Database](database.md) and [Server](server.md); the [standard](../standards/csharp-public-api-and-documentation.md) governs API/reference/consumer evidence. This specification supersedes ambiguous package sketches in older prose without changing their historical experiment identities.

The initial product profile is .NET 11.0 / C# 15, Linux x64 GNU and Windows x64 MSVC, with actual minimum OS/CPU certification performed by A14/A15. AOT applications do not need an installed .NET runtime to execute. Publishing still needs the documented .NET Native AOT native linker/build prerequisites on the build machine; **no Rust toolchain** is required for ordinary consumers. Those are different claims. R13/R18's historical no-Rust codec consumers are research evidence, not product package acceptance.

## 1. Selected package and assembly graph

`W` below denotes the exact normalized version selected from a validated NativeWeave release catalog. It is a schema variable, not a published version. Owned-package edges must use a reviewed exact range such as `[1.2.3]`; a bare version is not an exact NuGet dependency constraint. Versions may differ across package IDs if the release manifest declares that exact closure. BCL/Extensions dependencies follow their own reviewed compatible stable package policy; do not impose an unreviewed exact pin on the entire ecosystem.

| Package | Public assembly / namespace | Required owned dependencies | Normal user role |
| --- | --- | --- | --- |
| `NativeWeave.Core` | `NativeWeave.Core.dll`; `NativeWeave.Interop`, `.Extensibility` | None | Transitively used by Engine facades; BCL only, no native binary/runtime by itself. |
| `NativeWeave.Data` | `NativeWeave.Data.dll`; `NativeWeave.Data` | Core | Shared typed data/codec/mapping contracts; no SQL renderer, provider or Server. |
| `NativeWeave.Database` | `NativeWeave.Database.dll`; `NativeWeave.Database` and `NativeWeave.Query` | Data, Core | Common database/session/query API. Query namespace lives in this assembly to avoid Database↔Query circular references. |
| `NativeWeave.Database.Sqlite` | Provider facade; `NativeWeave.Database.Sqlite` | Database, Sqlite.Native, Generators/Analyzers build assets | One default install for SQLite; includes what ordinary Entity/DTO use needs. |
| `NativeWeave.Database.Sqlite.Native` | No C# facade; `runtimes/<rid>/native/[lib]nw_database_sqlite.[so/dll]` | None | Maintainer-precompiled SQLite+SeaQuery+SQLx adapter closure. Native descriptor/provenance bundled. |
| `NativeWeave.Database.PostgreSql` | Provider facade; `NativeWeave.Database.PostgreSql` | Database, PostgreSql.Native, Generators/Analyzers build assets | One default install for PostgreSQL; no SQLite/Server native package. |
| `NativeWeave.Database.PostgreSql.Native` | Native asset `nw_database_postgresql` | None | Maintainer-precompiled PostgreSQL+SeaQuery+SQLx closure with the reviewed TLS profile. |
| `NativeWeave.Database.DependencyInjection` | Extension assembly, extension methods discoverable under `Microsoft.Extensions.DependencyInjection` | Database | Optional registration helpers; depends on the needed Extensions 11 DI/options abstractions, not a Server host. |
| `NativeWeave.Server` | `NativeWeave.Server.dll`; `NativeWeave.Server` | Core, Server.Native, Generators/Analyzers build assets | One default install for a Rust HTTP server; includes Extensions 11 DI/Configuration/Logging/Options required by its builder. |
| `NativeWeave.Server.Native` | Native asset `nw_server` | None | One precompiled Tokio/Hyper/hyper-util/Tower/TLS/Tonic/rmcp closure. Never introduces a DB engine or second native Server runtime. |
| `NativeWeave.Server.Hosting` | Generic Host adapter | Server | Optional `IHostedService`/Host integration; no Kestrel or Microsoft.AspNetCore.App requirement. |
| `NativeWeave.Server.Grpc` | Strongly typed gRPC facade / descriptors | Server; protocol-specific generator assets | Optional application API over the same Rust Server instance and native module. |
| `NativeWeave.Server.Mcp` | Typed MCP tool/resource facade | Server; protocol-specific generator assets | Optional application API over that same Rust Server. |
| `NativeWeave.Generators` | Analyzer/compiler assets under `analyzers/dotnet/cs/` | No native runtime | Build-time static Entity/DTO/Handler metadata. Compatible compiler-host target is tested separately from net11 application target. |
| `NativeWeave.Analyzers` | Analyzer assets under `analyzers/dotnet/cs/` | No native runtime | API/ownership/AOT/unsupported-feature diagnostics; no automatic native compilation. |

Package boundaries are not a second task ownership graph. B09/B11 still own native query bindings/execution, B12 materialization, B13 Fluent surface, B14 relationships; they may contribute source folders to one managed Database assembly. A13 owns shared project graph integration. Core owns no domain options/configuration singleton. Multiple pools/servers have separately owned state, budgets, runtime policy and disposal; referencing two packages does not couple their instance shutdown.

### Native Server optional protocol cost decision

The first release carries one Server native module with HTTP/TLS and optional Tonic/rmcp code compiled into the same tested closure. Installing `.Grpc` or `.Mcp` adds the relevant managed API/generator surface; it does not swap a DLL, load a Rust dylib with unstable private layouts, introduce a second Tokio runtime or require a consumer Cargo build. Protocol router/state and per-stream budgets are created only when configured on a Server instance. The base HTTP builder does not register gRPC services or MCP tools automatically.

This choice has a visible native download/binary-size cost for unused protocol code. A21/B24 must report it along with cold startup and unconfigured memory/thread counts. It avoids four subtly conflicting HTTP/HTTP+gRPC/HTTP+MCP/combined native assets and restore-time PackageReference manipulation. A future release may offer separately validated native feature profiles if the complete closure resolver remains simple and deterministic; no profile swapping or post-publication hot replacement is promised here. Managed protocol package independence therefore does not imply native code absence.

### Generator inclusion without hidden runtime work

Default provider/Server packages carry analyzer/generator build assets transitively according to NuGet analyzer rules, so an ordinary attributed model or handler needs no second registration package. Generated outputs are statically compiled C# only. A documented manual descriptor path gives identical semantics when analyzers are excluded; it does not introduce reflection mapping. Package fixtures must actually prove transitive generator inclusion rather than assuming dependency references flow every asset category.

No generator creates projects, launches Cargo, reads live schema/databases, contacts a network, writes unrelated directories or relies on another generator's newly emitted syntax. Raw `LibraryImport` declarations are generated before the compiler pass or shipped compiled; application generators never depend on the framework generator seeing their output in the same pass. All descriptors/diagnostics are deterministic, cancellation-aware and identity-collision tested.

## 2. User journeys and default behavior

Every journey starts with a normal C# project. The minimal path uses natural domain factories; explicit catalogs, native paths and capability overrides are advanced preflight only.

| Journey | Install / import | Entry and ownership | Default cost |
| --- | --- | --- | --- |
| Console SQLite | `NativeWeave.Database.Sqlite`; `using NativeWeave.Database.Sqlite` and domain namespaces as needed | `await using var source = SqliteDataSource.Create("app.db");` Open session only when needed. | Lazy per-package module validation; independently owned pool/worker only when first required by the domain factory contract. No Server/DI host. |
| Console PostgreSQL | PostgreSql provider package/import | `PostgreSqlDataSource.Create(connectionString)`; ordinary query API shared with SQLite where semantics overlap | No managed driver fallback; connection credentials never in native-load error text. |
| Advanced database | Same provider plus common namespace | `new DataSourceBuilder().UseSqlite(...).ConfigureLimits(...).Build()` | Options validated/snapshotted once; no repeated entity-by-entity registration if generator can provide static metadata. |
| DI database | Provider + `.DependencyInjection`; `using Microsoft.Extensions.DependencyInjection` | One `AddNativeWeaveDatabase(...)` source registration; sessions/transactions explicitly owned by operations/scopes per DB specification | No second `BuildServiceProvider`; factory-owned singleton source disposed by the root provider; caller-owned instance overload, if any, explicitly retains caller disposal. |
| Minimal HTTP | `NativeWeave.Server`; `using NativeWeave.Server` | Builder → routes → `Build()` → `RunAsync` / `await using` according to Server spec | One root DI provider; request scope created only if requested by handler/service binding; Rust does protocol/network I/O. |
| Generic Host service | Server + `.Hosting` | `AddNativeWeaveServer` on existing Host builder; native server service uses that root provider | No hidden second root provider; Host stop initiates close, a deadline never force-frees still-running native work. |
| Database + Server | Both engine leaf packages | Database source registered once in Server Services or manually supplied to handlers | Independent native modules and explicitly owned instances; adding a Handler/Entity changes managed code/metadata only. |
| Custom engine | One custom facade package following D11/A24 | Natural typed factory; optional `.Engine` descriptor for preflight | Compiled facade/adapter and supported assets selected at restore; no dynamic loading of new managed types into published AOT. |

`Create` constructs configuration/owner state; a name ending `OpenAsync` or explicit `OpenSessionAsync` is used when externally observable connection I/O is part of completion. Domain specifications state their actual lazy/eager behavior, capacity and failure point. No global initialization is required. Constructors/builders perform synchronous argument validation; asynchronous external failures appear on their Task. Default timeout/limits are domain-owned, finite and documented; Core has no universal deadline whose meaning differs between engines.

### Empty-project commands and publication status

The product-facing Getting Started generator will substitute a real validated release version into these commands **only after packages exist**:

```bash
dotnet new console -f net11.0 -n Example
cd Example
dotnet add package NativeWeave.Database.Sqlite --version <validated-release-version>
dotnet build
dotnet run
dotnet publish -c Release -r linux-x64 -p:PublishAot=true
```

Windows uses `-r win-x64` and executes its actual `.exe` on Windows. Cross-OS AOT output is not claimed. A successful build is not a published/AOT-executed sample. The current Design validation entry point builds the isolated signature/consumer projects by ProjectReference and deliberately does not execute throwing API stubs as product behavior; the integrated experiment README records exact commands and states. Future A16/B24 replaces that dependency with packed NuGet artifacts from isolated staging and verifies the full code path in both environments.

### Model/DTO/Handler change acceptance

A clean-consumer fixture adds a second ordinary Entity, projection DTO, dynamic parameterized predicate and typed HTTP Handler. It compiles/runs through normal `dotnet` commands, then publishes and executes AOT. Its native asset SHA-256 must be byte-identical to the previous app. The resulting generated code may change, but no Rust compiler/network service/build hook may run. Ordinary schema metadata is runtime data for the precompiled native query profile; serialization/handler dispatch is statically compiled C#.

A genuinely new native operator/codec/protocol/platform may require an updated native package. Report it as a capability/package update, with an actionable diagnostic identifying the currently unsupported feature. Never silently add per-Entity Rust generation or use a managed SQL/network implementation to conceal an absent native capability.

## 3. Asset selection and publish layout

Maintain source packages for both `linux-x64` and `win-x64` only after their actual release rows pass. Native assets use NuGet's `runtimes/<rid>/native/` asset mechanism, not `contentFiles/`. The .NET SDK may flatten native assets during publish; preserve unique basenames across engines and native dependencies. The generated build manifest records each output-relative final path and selected digest. Package-relative descriptor paths are source identities, not assumptions that a published output keeps the full NuGet folder hierarchy.

The maintainer resolver must handle both normal development assets selected by `.deps.json` and published flattened output. A build-transitive manifest emits the verified target-specific relative location under `AppContext.BaseDirectory`; the loader resolves that exact location and rejects traversal/absolute injected entries. It validates native content and ABI before domain creation. It does not discover an arbitrary DLL by walking directories. For RID-free development the asset selection checks the actual host RID against the package's supported list; unsupported architectures fail clearly. Restore success is not platform support.

No implicit fallback from Linux musl to GNU, x64 to Arm64, Windows to Linux, or a native provider to a managed provider is allowed. Mac/mobile/WASM are future explicit profiles. Minimum OS, glibc/CRT, OpenSSL/TLS closure and x64 instruction baseline are release manifest facts verified by A14/A15, not inferred from the filename. `net11.0` compile compatibility is broader than this initial native platform support.

AOT publish tests native assets adjacent to the output, static import reachability, unreferenced Engine trimming, source-generated JSON/model registrations and diagnostics. Do not claim single-file, self-extracting packaging, static native linking or arbitrary `PublishSingleFile` combinations until a distinct documented gate proves that target. Supplying an absolute `EngineLoadOptions.NativeAssetPath` is an advanced same-content diagnostic/deployment option, not a normal installation step and not a bypass of ABI/hash checks.

## 4. Closure validation, diagnostics and updates

The owned package graph, descriptor metadata and native assets must match a release-tested closure. A build-transitive target runs after restore and before build/publish to reject invalid direct dependency overrides even when NU1605/NU1608 warnings are suppressed. It does not modify references or restore another profile. Runtime bootstrap independently checks module identity/ABI/capabilities. Compatibility checking is not a security boundary against an application intentionally rewriting its own binaries.

| Diagnostic | Trigger | User-facing correction |
| --- | --- | --- |
| `NWPKG001` | NativeWeave package graph differs from an approved closure | Align the named owned package versions to one catalog entry; identify actual and allowed versions. |
| `NWPKG002` | Missing/duplicate native output asset or manifest entry | Restore/rebuild the named provider package; report expected RID/path without raw handles or credentials. |
| `NWPKG003` | Unsupported RID, architecture or CPU profile | List actual supported profiles and the selected one; do not suggest a silent architecture substitute. |
| `NWPKG004` | Native hash/build identity disagrees with descriptor | Reinstall the exact release closure or use a complete reviewed custom-engine build. |
| `NWPKG005` | Incompatible ABI or missing bootstrap | Report required and observed major/minor/export; use matching package/native assets. |
| `NWPKG006` | Required Engine capability absent | Name the API and capability; use a package/profile that actually implements it. |
| `NWPKG007` | Second incompatible content identity requested in one process | Upgrade as a fresh process/deployment; existing modules are not hot-replaced. |

Build diagnostics use IDs above; runtime errors use `EngineLoadException` and its enum. The same condition must not require reading raw FFI codes to fix a package install. Domain diagnostics such as unsupported Entity member, unknown query translation or duplicate endpoint remain in their domain/generator diagnostics, with source locations and supported alternatives.

Updates preserve immutable NuGet versions, exact source/ABI/dependency records and old/new-consumer tests. First publish verified native/build dependencies, then facades, then read back/restore the full closure before advertising the catalog. Partial uploads do not make a complete release. Existing deployments roll back by selecting a prior complete closure and restarting; unlisting is not deletion and does not invalidate existing caches. Detailed release signing/provenance/registry semantics remain D10, not a new unaudited publishing mechanism.

## 5. Developer-experience review and required evidence

| Concrete review case | Pass criterion | Tasks |
| --- | --- | --- |
| First SQLite query from empty console | One provider package, ordinary using/factory/query, no raw handle/model registration repetition/Rust install | B01–B14/A16 |
| First HTTP JSON endpoint | One Server package, natural typed handler/static serializer, no Kestrel/Reflection.Emit/native callback code in app | B15/B17/A16 |
| Handwritten static metadata option | Same behavior and AOT output semantics as generated metadata; documented extension seam | B10/B12/A10 |
| Native AOT without local Rust | Clean supported image, native linker prerequisites only; actual publish and executable behavior | A14–A16/B24 |
| Advanced configuration | Single immutable snapshot, normal Options/Builder discoverability, explicit timeout/capacity/ownership | B04/B15/B17 |
| DI lifetime | One root provider; provider-owned source/server disposed once; request scopes not allocated for a static route | B15/B20/B24 |
| Independent installation | SQLite installs neither PostgreSQL nor Server; Server installs neither DB provider; Core starts no native runtime | A16/B24 |
| Both protocols | Optional managed packages attach to one validated native host; no duplicate listeners/runtime/FFI replacement | B18/B19/B24 |
| Error/upgrade journey | Wrong package, ABI/RID/hash/export/capability and direct override each fails with exact remedy before domain work | A02/A05/A16/A22 |
| Actual sample provenance | Each example labelled design-compiles, real-product-runs, or actual AOT-executed with exact inputs | Every affected Delivery task |

These fixtures become permanent CI consumers and published documentation samples. The product API reference comes from the compiled assemblies/XML comments, not copied design stubs. Root `AGENTS.md` and Plan task acceptance link the same standard. No code was written to the NativeWeave product repository by this design specification.
