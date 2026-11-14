# D01 — Platform and Native AOT support profile

Contract **C-PLATFORM-001@0.4.0**. Status: complete design candidate; the registry records exact version, hash and independent acceptance. Production support is a separate Delivery result. Existing R01/R02/D01/A01/A14/A15/A16/B24 scopes apply. Research baseline is merged Design `7759248e8c3bb37a99481f09c690d2c9f9b49248`; no old evidence is overwritten.

## 1. Maintainer and consumer profiles

Pin maintainers to Rust/Cargo **1.100.0**, edition2024, and managed fixtures to .NET SDK **11.0.100**; require the recorded exact rustc commit, target triple, compiler/linker, Cargo.lock/features and native asset hashes. These are current researched pins, not permanently hardcoded claims about the latest stable. R01 records release/source inspection and stable/unstable negatives. A new release triggers an investigated update, not an automatic production upgrade.

Ordinary consumers use precompiled native NuGet assets and .NET tooling. Adding supported C# entities, DTOs, predicates or handlers must not default to Cargo or CI-built application native code. Native AOT publication has its own platform compiler/linker prerequisites; this is distinct from requiring the Rust toolchain. The real codec consumer removes Cargo/rustc/rustup from its effective environment, uses only a local NuGet and executes RID-free development plus AOT on both CI OS. A pristine image that never installed Rust remains an A16 release obligation; do not confuse these two claims.

## 2. Explicit matrix

| Profile | Actual current evidence | Formal acceptance still required |
|---|---|---|
| linux-x64 / x86_64-unknown-linux-gnu | Rust1.100 API probes; earlier SQLite query AOT; new owned-buffer/static PInvoke/UCO/SafeHandle/local-NuGet consumer AOT | Minimum distro/glibc policy, all formal ABI types, full async retirement, selected production Engine closure, packaging/security/fault/soak |
| win-x64 / x86_64-pc-windows-msvc | Rust1.100 API probes; new owned-buffer/static PInvoke/UCO/SafeHandle/local-NuGet consumer AOT on Windows2022 | Minimum client/server OS and CRT policy, full Engine/async/ABI/packaging/security/fault/soak |
| ARM64, 32-bit, macOS, iOS/Android, WASM | Not certified by these x64 tests | Independent R02/R33 target/link/runtime/lifecycle/ABI investigation; no extrapolation |

New Interop execution: NativeWeave source `4a4adc883b80719d2a9b2bfb03be5ec86b543f3c`, Actions **43363045559**. Both OS passed four native tests, RID-free `dotnet build/run`, and actual explicit-RID `PublishAot=true` executable execution. Each managed execution reports six groups,185 assertions and32 controlled in-flight-call/Dispose rounds. This is a finite fixture, not all product tests. Existing R01's two-platform13-test/13-command Rust evidence is reused, not counted as new C# AOT evidence.

## 3. Architecture and deployment constraints

Initial wire profiles are same-process little-endian x64, pointer and size_t width64. The first release build/verification baselines are Ubuntu24.04 GNU and Windows Server2022 MSVC; this is a chosen narrow initial profile, not certification of every Linux distribution or Windows version. Broader desktop/minimum-version support requires explicit A14/A15 rows. Match .NET11's x64-v2 minimum CPU profile and compile Rust to an explicitly compatible documented baseline; never assume a host-native instruction set is portable. C ABI natural alignment must be verified per target; same integer widths do not imply all target ABIs are interchangeable. Never distribute an artifact compiled with unrecorded host-specific CPU features. Do not imply Rust's internal ABI is stable across compilers or dynamic modules.

Use `extern "C"`/Cdecl-compatible imports; naked `extern "custom"` is not a managed-call ABI. Rust collections, Futures, trait objects and allocator state are native implementation details. A native dependency's MSRV does not prove that its selected feature/target/transitive closure compiles with the chosen toolchain; run the closure.

NuGet resolves `runtimes/<rid>/native/` with matching architecture and version. Application-local assets are tested without adding an ad-hoc working-directory loader. Module initialization fails on missing/incompatible assets. Modules stay loaded for process lifetime in the initial profile; instance Dispose is not library unload. Static linking, bundling/trimming and Direct P/Invoke variants require separate loader/link tests before adoption. Do not change search-path security assumptions by enabling direct imports without evaluation.

## 4. Native AOT evidence contract

A passing row records source commit, lockfile/features, OS/arch, exact SDK/rustc/linker, build and publish commands/exits, diagnostics, native/package/executable SHA256 and actual executable stdout/stderr. An AOT fixture asserts dynamic code is unavailable and checks native behavior; a JIT run alone is insufficient. Keep failed attempts and original byte hashes, including Windows line endings.

Treat AOT/trimming warnings as failures in the fixture unless a narrowly documented target-specific justification is reviewed. Do not use broad warning suppression or runtime reflection fallbacks. Error/crash/invalid-UCO signatures run in isolated subprocesses, not in a test host expected to survive arbitrary native UB.

## 5. Costs and remaining tasks

Record startup, package size, managed/native heaps, thread/runtime counts and whole-workload latency/throughput before comparative claims. The new byte-sum fixture is not a benchmark and does not demonstrate a native performance advantage. A14/A15/B24 retain independent Windows/Linux release gates; A16 retains clean-machine no-Rust consumers and offline-after-restore cases. R02 owns target viability; D02/D07 own exact ABI/buffer contracts; D10 owns build/upgrade provenance. Acceptance of this proposal requires completion of its actual review/evidence requirements, not just merging a document.

## 6. Modern language and runtime profile

Use C#15.0 explicitly in maintained projects and net11.0 reference assemblies. Stable union,
closed hierarchy and collection-expression arguments are available; the R01 fixture compiles
and executes them, including external closed-inheritance rejection. A union holding a value case
can box: do not put it in a hot allocation-sensitive result path without measurement. Fixed ABI
records remain explicit blittable storage. Preview memory-safety language work is not enabled by
default and does not excuse unsafe-boundary review.

Runtime Async is opt-in. The research publishes isolated default and
`-p:Features=runtime-async=on` projects, captures compiler arguments, inspects emitted metadata,
and runs both AOT executables. Adopting it for the product requires the actual A07/Engine bridge
semantics, diagnostics and relevant cost comparison; no FFI or cancellation contract changes.
C# Task/ValueTask remains the application interface independently of compiler lowering.

## 7. Build and runtime matrix owned by existing tasks

| Task | Concrete required row | Failure policy |
|---|---|---|
| A13 | Exact Rust/SDK/lock/features, C/Rust/C# layout and emitted symbol inventory | Failed build never publishes an older cached native file |
| A14 | Ubuntu24.04 x64 native build, ordinary consumer, actual AOT and runtime-only transfer | Wrong ELF/GLIBC/ISA/dependency fails with artifact evidence |
| A15 | Windows2022 x64 MSVC native build, ordinary consumer, actual AOT and runtime-only transfer | Wrong PE/CRT/architecture/exports fails; no implicit system DLL substitution |
| A16 | Independent NuGet, RID-free build/run, explicit-RID AOT, no-Rust clean image, offline-after-restore | Ordinary model/Handler edit retains native SHA; missing capability fails clearly |
| A22 | Old/new package and ABI/feature combinations on each OS | Reject incompatible major/layout/semantic combination before owner publication |
| B24 | Actual Rust DB/ORM/Server/protocol product closure and package matrix | Research fixtures do not satisfy product release rows |

Cancellation, callback retirement, buffer ownership and thread affinity are D04–D09, not OS-specific
exceptions. All native exports contain unwind-mode panics; no claim is made that OOM abort, access
violation or an invalid unmanaged signature is recoverable. Modules remain loaded until process
exit; instance shutdown drains actual resources without unloading executing code.

R33/D21 hold explicit future profiles for ARM64, mobile/UI/GPU/WASM. Do not include unsupported RID
assets or silently fall back to managed drivers/hosts. Unsupported targets fail at restore/build or
at explicit capability negotiation, with a precise supported-profile message.


## 8. Public surface validation and supported-profile claims (2026-11-14)

The public API declaration/consumer projects in `experiments/public-api/` fix net11.0 and C#15.0
without Preview. [Interop](../api/interop.md), [Database](../api/database.md) and
[Server](../api/server.md) distinguish compile-only declarations from actual product/AOT execution.
A declaration assembly building successfully does not certify a Rust Engine, package or target.
The common header/layout probe verifies only the compiler/architecture actually executed.

Desktop packaging retains default lazy dynamic PInvoke. Direct PInvoke, static linking, single-file
extraction and additional RIDs are separately negotiated/verified profiles, not implied by successful
net11 compilation. A static rooted `typeof(KnownType).Assembly` descriptor is permitted under AOT;
reflection-scanned plugins and new managed-assembly loading into the published image are not.
Use [the package/profile specification](../api/nuget-and-consumption.md) for native asset selection,
unsupported-RID messages and independent clean consumers. A14/A15 run real target builds;
A16/B24 verify normal development and publication without a local Rust toolchain.
