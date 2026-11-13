# R06 — Incremental metadata generation and diagnosable Native AOT bindings

Research decision ready for independent review. This missing canonical task now has fixed Roslyn source inspection, a real compiler-driver probe and D03's concrete generation contract.

## Source-derived constraints

Roslyn v11 source at `3a38d0c1ca5f8d11dcbb01400ec26eff6d51f609`, GeneratorDriver.cs lines1–180, adds generated trees to the output compilation after running generators. The incremental generator cookbook at the same commit specifies additive, unordered generation with no access to peer generator output and emphasizes value-equatable models. The executed SDK11.0.100 compiler assembly reports version5.12.0.0; source and binary identities are distinguished rather than assumed equal by their names.

.NET11 LibraryImportGenerator source uses `ForAttributeWithMetadataName`, filters invalid method forms, combines environment/options, and tracks comparable generation stages. NativeWeave should reuse those stubs. It cannot emit LibraryImport declarations in an application SG and expect the framework generator to consume the newly generated declarations in that same pass. Emit engine imports at maintainer build time or a pre-compilation build step; ship them already compiled. App SG produces static entity descriptors and DTO mappings only.

## Real experiment

`experiments/interop-completion/GeneratorProbe.cs` instantiates actual CSharpGeneratorDriver from the installed SDK. Nine checks cover initial generated-source compilation, one descriptor per explicitly attributed model, unchanged-input cached steps, a changed field affecting the relevant descriptor, unchanged unrelated descriptor bytes, generated-source recompilation, an unsupported delegate-member diagnostic, and a second generator being unable to see a peer's newly generated type in the same pass. Raw result is `verification/interop-completion/linux/generator-run.stdout` with its command and exact source hashes.

The probe is design-time compiler execution, not a published source-generator NuGet package or an AOT compiler host. The native consumer it supports is separately AOT-tested. Its simple names and diagnostic locations are intentional probe limits; D03 requires fully qualified collision-safe names and precise product diagnostics.

## Selected pipeline

Explicit sealed marker → ForAttributeWithMetadataName → short semantic transform → value-equatable shape/codec model → deterministic descriptor/DTO output. Remove symbols, syntax nodes and Compilation references from persistent semantic model keys. Use element-wise equality for collections. Include target/configuration and ABI-description identity in the key; unchanged relevant input preserves bytes. Honor cancellation in transformations and never invoke Cargo, network or a database from the generator.

Manual typed metadata must be equally supported, so ordinary developers are not forced into SG or full expression capture. A descriptor identifies native fields/codecs/capabilities; it does not implement SQL parsing, relation algebra or dialect selection in C#. Strongly typed Fluent calls send supported native operations to SeaQuery/SQLx-based adapters.

## Error and boundary matrix

| Input/event | Required deterministic result |
|---|---|
| Unsupported member/codec or delegate | Diagnostic at offending member before native use; no silent fallback |
| Same short type names/nested generic shapes | Stable fully qualified identity or explicit rejection, never hint collision |
| ABI schema/version drift | Build diagnostic and package identity mismatch, not stale output reuse |
| Another SG emits a model/import | No same-pass dependency; explicit pre-compilation input or future compilation pass |
| Unrelated source edit | Model output unchanged; no Cargo or native rebuild |
| Cancelled IDE generation | No partial accepted output; next pass recomputes from current immutable input |
| Illegal UCO bool/char/string shape | NWABI diagnostic and controlled compiler/fatal test; callback catch is insufficient |

## Costs and alternatives

SG moves deterministic metadata construction to build time but introduces compiler/IDE work and package-version compatibility. Narrow attribute discovery reduces scanning; exact equality reduces unnecessary downstream work. Do not claim a numerical speedup from the upstream cookbook or the nine-check probe. Runtime reflection can aid tools but is not the ordinary AOT fallback. Complete LINQ capture/interception would add a large provider surface outside the declared goal.

D03 allocates A09/A10/A11/A12 responsibilities and diagnostic classes. B10 owns optional descriptors, B12 materialization. Future tests extend to multi-target builds, incremental invalidation/cancellation, supported compiler floors, generated NuGet consumption and actual Windows/Linux AOT public reachability. These are precise implementation obligations; the source/experiment resolves the generation-order and caching design questions now.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
