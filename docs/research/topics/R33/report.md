# R33 — Mobile Native AOT, native linking and application lifecycle

Date: 2026-11-12. This previously missing topic supplies a versioned platform boundary,
not a claim that NativeWeave already supports mobile applications.

## Verified current identities

Rust 1.100.0 commit `0ef1bc386059596dada8fb65b50425aab2ea637a`:
`src/doc/rustc/src/platform-support/apple-ios.md:1–100` and `android.md:1–72`.
.NET runtime v11.0.0 `deae2e32bf0e018e09d64597b7c59b62b73bb3ce`:
NativeAOT `BuildIntegration/Microsoft.NETCore.Native.targets` library-output/linker
properties and `docs/compiling.md:34–66`.
Microsoft documentation snapshot `c3377f5f732f604c8f9bffc14d814dd35c99f3c0`:
`docs/core/deploying/native-aot/index.md:177–231` and
`docs/core/compatibility/maui/11/mobile-code-generation.md:9–91`.
Winit's fixed iOS/Android lifecycle reads are shared with R32. Digests and scopes are
in [source-inspection.json](../../../../verification/server-completion/source-inspection.json).

## Platform facts that must not be conflated

Rust's aarch64 iOS device/simulator and x64 simulator targets are tier 2 without host
tools. They require the corresponding Xcode SDK; device and simulator are distinct
artifacts even when both use ARM64. Rust Android targets are tier 2, std/ELF, built
with an appropriate Android NDK/API baseline. Having an available Rust target does not
prove that the complete C# Native AOT application, native engine, linker, signing and
OS lifecycle combination is supported.

The .NET 9+ Native AOT table includes iOS ARM64 and simulator x64/ARM64, while Android
remains experimental with no built-in Java interop. The .NET 11 mobile change to
CoreCLR/R2R is not Native AOT: Android R2R may JIT; Apple R2R may use the interpreter.
Neither Mono AOT nor `MauiEnableFullReadyToRun` satisfies NativeWeave's Native AOT
release requirement. D21 records Android as an experimental future profile and does
not promise product support before device evidence.

NativeAOT supports native library outputs and explicit platform linker integration.
Cross-OS Native AOT compilation is not supported by the ordinary toolchain path;
Windows/Linux AOT CI cannot certify Apple linking/signing. Static Rust libraries or
packaged native frameworks must be produced by maintainers per target/profile. The
ordinary C# application adds metadata and statically reachable bindings, not an
entity-specific Cargo build. Dead-stripping/export preservation is explicit and
validated from the final signed app; “the archive contains the symbol” is insufficient.

## Lifecycle and ownership findings

Winit's Android `Suspended` callback corresponds to SurfaceView destruction and
requires dropping render surfaces before the callback returns. Resume creates a new
surface generation; back-to-back duplicate events are allowed. iOS activation and
resignation are different lifecycle signals and must not be modeled as Android's exact
surface destruction rule. Memory-warning callbacks should release optional caches;
they do not permit freeing an in-flight mapped buffer or active callback cookie.

An engine-local platform shim is therefore unavoidable glue, not a reason to invent
a universal Core UI runtime. It holds the native platform object and affinity rules,
performs urgent invalidation synchronously, and reports normalized state transitions
to C# through a bounded channel. JNI/Objective-C references, thread attach/detach and
autorelease ownership never cross the public generic ABI as unowned pointers.
Background/suspend does not guarantee future scheduling or a graceful callback;
durable application work must tolerate process death and should not depend on a finalizer.

## Design result and remaining platform execution

D21 defines separate iOS-device, iOS-simulator and Android-experimental package entries,
each pinning SDK/NDK, minimum OS/API, CPU ABI, native static/shared form, runtime mode,
native dependencies, callback calling convention and license manifest. Framework-owned
event loops are adopted through a documented integration seam; NativeWeave never
starts a second UI loop. Unsupported profiles fail at build/configuration time with
specific diagnostics instead of silently switching to JIT, interpreter or managed engine.

Future A23/B24 tests must inspect the final binary's architecture/symbols, install and
run signed apps on actual devices/simulators, test suspend/resume/window loss/memory
pressure/relaunch, and confirm that default entity/Handler additions do not invoke
Cargo. These are future platform implementation/acceptance obligations because this
phase explicitly does not implement mobile UI. No unrun mobile build, code-signing,
GPU experiment or Native AOT device success is claimed by this research.
