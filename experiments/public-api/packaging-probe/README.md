# Design package-flow and Interop declaration probe

This is a bounded **design experiment**, not a NativeWeave product package or the B10 model generator. It closes two concrete gaps in the public-API design: the precise transitive generator inclusion route and whether an ordinary C# model/DTO/handler edit can reuse an already compiled native asset through that package route.

## Inputs and assertions

The probe uses SDK **11.0.100**, `net11.0`, C# **15.0**, the SDK's own Roslyn assemblies, and the existing research codec package at `verification/engine-completion/linux-reviewed/NativeWeave.Research.Codec.0.0.1.nupkg`. It reads that archive's managed facade and native library byte-for-byte; it never invokes Cargo/rustc or rebuilds the inherited codec. This is a new package-flow experiment using prior execution evidence, not a repeated claim to have newly implemented compression or a product ORM.

The scripted checks are:

1. Compile the actual `Interop.cs` declaration and `InteropExamples.cs` consumer with the exact reference pack and XML output. Reject a borrowed span returned through the generic reader with `CS9244`.
2. Compile and execute the shared C header layout probe on Linux x64.
3. Compile an intentionally small incremental generator and marker assembly. The generator inspects explicit Entity/DTO/Handler attributes into value-only shapes, sorts identities deterministically, and emits static registry metadata. Unsupported scalar shapes produce `NWPKGPROBE001`.
4. Assemble an isolated three-package local feed: a facade, a native leaf, and a build-assets leaf. The facade uses exact dependency ranges. The generator is included solely by a `buildTransitive` target, not by a direct analyzer reference in the consuming project. Package archives are assembled deterministically by the Python harness; this does not test the future production `dotnet pack` targets or signing.
5. Restore/build/run a new ordinary console application referencing **only the facade**. Assert its resolved graph contains exactly those three probe packages, its generator produces exactly one output, and the inherited native codec actually round-trips data.
6. Add an Entity and change a nullable DTO field, rebuild with `--no-restore`, and run again. Generated metadata must change, while the selected native asset hash remains identical. A separate unsupported model must fail at compilation.
7. Publish and execute the ordinary framework-dependent consumer. Optional `--aot` restores official SDK Native AOT packs and requires an actual published executable with `RuntimeFeature.IsDynamicCodeSupported == false` before recording AOT execution.

The consumer's effective PATH contains .NET and system tools, with Cargo/rustc/rustup absent. This demonstrates the normal consumption path does not invoke Rust; it is **not** evidence that the whole host image never contained a Rust installation. No user `rd.xml`, trimming roots, runtime expression compilation, runtime assembly scanning or source-generator network/native build is involved.

## Reproduction

Run from any directory with an installed exact SDK and Linux x64 GNU host. Both work and evidence paths must be chosen for this run; a nonempty work directory is rejected so previous outcomes cannot be accidentally overwritten.

```bash
python experiments/public-api/packaging-probe/run.py \
  --dotnet /absolute/path/to/dotnet \
  --work-directory /absolute/path/to/fresh/probe-work \
  --output /absolute/path/to/evidence \
  --aot
```

Without `--aot`, the entire dependency feed is local and the fixture makes no AOT claim. With `--aot`, `nuget.org` is used only to restore official SDK tooling/runtime packages; NativeWeave application-native payloads remain the exact inherited research bytes. AOT publishing needs the normal .NET platform compiler/linker prerequisites. All commands, exit statuses, normalized logs, input hashes, restored package identities and generated/native hashes are in `summary.json`.

`DOTNET_CLI_USE_MSBUILD_SERVER=0` and `--disable-build-servers` avoid the recovered environment's unavailable MSBuild server; this is an execution-environment setting, not an application AOT workaround. Direct compiler use for the generator retains `CS1701` as a warning because SDK11's Roslyn binaries reference System.Runtime10 while the probe deliberately targets the available net11 reference pack. Other warnings remain errors. Actual loading and execution by the SDK11 compiler checks this specific host combination; CLI success does not certify all Visual Studio/compiler hosts. The Interop declaration compile has no such relaxation.

## Evidence and limits

See [recorded attempts](../../../verification/public-api/interop-packaging/README.md). Failed attempts remain recorded, with their observed exits and corrections; only a successful row can be used as evidence for its stated scope. Normal compilation, native codec execution and Native AOT execution are separate checks.

This experiment does not implement production Entity mappings, SQL translation, Fluent query generation, full DTO codecs, server handler routing, the package closure validator, the output-location manifest loader, the production API's native behavior, or Windows/macOS/ARM support. The proposed exact package and loader design is [NuGet and consumption](../../../docs/api/nuget-and-consumption.md); actual complete release gates stay with A10/A12/A14–A16/B10/B12/B15/B24. Production examples and API reference must never present these probe package IDs as the installable NativeWeave SDK.
