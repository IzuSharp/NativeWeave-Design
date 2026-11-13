# R13 — Maintainer builds, native assets and ordinary C# consumption

Author: `/root`. Scope: researched build/link/package mechanisms and finite real integration; production A14–A16 remain separate. This completes the canonical triplet around earlier successful native-slice evidence.

## Source result

At dotnet/sdk `b8600c8854f5d1ac1442d717211d968f69a53acd`, `ResolvePackageAssets.cs` writes native libraries and RID runtime-target assets separately; `Microsoft.NET.RuntimeIdentifierInference.targets` derives self-contained publication from PublishAot and validates runtime/architecture combinations. A package's native asset selection belongs to NuGet/SDK resolution. Do not implement a current-working-directory DLL loader to compensate for malformed packaging.

At Cargo `3acc79c0c841844675bc53a605922dbfc441e750`, the compiler-artifact JSON message identifies package, target, profile and emitted filenames. The build-cache layout is explicitly internal. The real Engine runner selects its cdylib from these records, filters the exact target, and does not guess the `deps` directory. Existing Rust1.100 tests cover the new intermediate build-dir separation on Windows/Linux. Generator source is studied in R05/R06; compiler generators must stay deterministic and side-effect-free.

## Executed complete consumer path

The new [Engine fixture](../../../../experiments/engine-completion/run.py) builds a genuine miniz_oxide0.9.1 Rust cdylib, packages a static C# facade plus `runtimes/<rid>/native/` asset, copies only an independent consumer into a separate working directory, then performs RID-free `dotnet build` and `dotnet run`. Cargo/rustc/rustup are removed from the consumer's effective PATH and relevant tool-home environment; the runner asserts none is discoverable. The package has no .targets/.props/.rs files that could invoke a hidden native build.

The consumer restores the local NuGet, executes zlib interoperability in both directions with .NET ZLibStream, adds a new ordinary C# record, rebuilds with `--no-restore`, and verifies the native binary SHA is unchanged. Finally it explicitly publishes for the host RID with PublishAot=true and runs that executable outside the Rust build tree. Linux result: three Rust tests, sixteen ordinary consumer checks, seventeen AOT checks. This is a stronger consumer mechanism test than a direct project reference to a native build target.

It does **not** claim the operating system never had Rust installed: `clean_operating_system=false` is explicit in result.json. A16 retains a genuinely pristine image without Rust and a runtime-only target-machine execution after transferring the publish directory. The research proves the ordinary consumer command path does not discover or invoke Rust. Application changes stay C# changes.

## Linking and resource decisions

Initial dynamic x64 profiles use explicit C ABI exports and source-generated imports; module code remains loaded for process lifetime. SafeHandle disposal releases an instance, not the DLL. Windows MSVC and Linux GNU are separate asset identities. Static archive/DirectPInvoke/mobile linking is a separate profile with symbol-retention, platform linker and runtime dependency tests; desktop success does not justify it automatically.

Store toolchain/target/CPU/features/lock hashes and native-file hash alongside the package. Use per-worktree intermediates and an explicit cache key; host tools and target artifacts must not share an unqualified path. A cancelled build leaves staged outputs unpublished. Copy artifacts to the final package only after successful build, symbol inspection and hash verification; never reuse a previous successful binary after a new compiler failure.

## Failure and boundary analysis

| Failure | Required behavior and owning task |
|---|---|
| Wrong RID/architecture or missing asset | Deterministic load failure with requested Engine/RID/version; no managed engine fallback (A02/A14/A15/A16) |
| ABI/required capability mismatch | Reject before creating domain owners; no interpreting a shorter function table as complete (A02/A22) |
| Cross compile succeeds but target cannot execute | Record build-only, never AOT-run evidence; execute on matching runner (A14/A15) |
| Host-specific ISA or glibc accidentally leaks | Inspect binary/build flags against D01 profile; rebuild on declared baseline (A13/A14) |
| NuGet references unexpected native dependency | Inventory dynamic dependencies and licenses on each OS, fail release closure check (A16/A22) |
| Incremental stale binding | Bind generated header/import inventories and ABI manifest to exact source hash; negative changed signature fixture (A09/A13) |
| Ordinary Entity/DTO/Handler change | Rebuild C# only with unchanged native module; unsupported capability produces a clear diagnostic (B10/B12/B24) |

No arbitrary pointer-invalid invocation is used as a packaging negative: ABI misuse can terminate a process and belongs in an isolated test.

## Resolution and delivery

Choose maintainer prebuilt native assets, one initial coordinated managed+RID package family with independently identified Engine version/ABI. Do not add Rust MSBuild targets to application restore, and do not require explicit RID for normal development commands. D10 specifies upgrade/provenance and old/new compatibility. A13 owns build orchestration, A14/A15 OS execution, A16 independent consumption. Actual current CI evidence is indexed centrally rather than inferred from configured workflow YAML. No production package was published.
