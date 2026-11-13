# R01 — Stable toolchain and useful modern language mechanisms

Author: `/root`. Research/design completion candidate, independently reviewed through the current acceptance ledger. Observation: 2026-11-13 UTC. This completes the .NET/C# gap around the existing [Rust 1.100 source and two-platform experiments](rust-1.100.md), without rerunning or relabelling that earlier evidence.

## Decision and exact identities

Use maintainer Rust/Cargo **1.100.0**, edition 2024, and .NET SDK **11.0.100**, C# **15.0**, target net11.0 for the initial implementation profile. Runtime 11 is an STS release; the official support table observed on this date gives support through 2028-11-14. Recheck lifecycle before each release; the [official release](https://github.com/dotnet/core/blob/main/release-notes/11.0/11.0.0/11.0.0.md), [support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) and [C#15 release description](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-15) were checked against the installed SDK and actual compiler. Moving documentation is dated evidence, not an immutable source pin. Rust compiler commit is `0ef1bc386059596dada8fb65b50425aab2ea637a`; Cargo is `3acc79c0c841844675bc53a605922dbfc441e750`.

Roslyn v11.0.0 source pin `3a38d0c1ca5f8d11dcbb01400ec26eff6d51f609` supplies compiler tests. SDK repository v11.0.100 resolved to `b8600c8854f5d1ac1442d717211d968f69a53acd`. An installed SDK's build identity is recorded separately in raw `dotnet --info`; a repository tag is not asserted to equal an installed binary's build commit. Complete file hashes and actual inspected ranges are in coverage.json. Earlier release observations remain historical; no claim that these versions remain the newest forever.

## Mechanism decisions

| Mechanism | Evidence and boundary | NativeWeave use |
|---|---|---|
| C#15 union types | Stable syntax compiled and executed with explicit LangVersion15.0; exhaustive match checked in fixture; value-case assignment allocates in this compiler | Useful application result modelling where measured appropriate; never C ABI storage and not an automatic allocation-free replacement for explicit tagged values |
| Closed hierarchies | Stable `closed` hierarchy compiled; derivation in a separate assembly rejected | Use for deliberately finite public state/value families; preserve versioning policy when adding cases |
| Collection-expression arguments | `[with(capacity: 8), ...]` compiled and executed; capacity assertion passed | Concise managed metadata construction; neither native allocation control nor an ownership mechanism |
| C# memory-safety proposals/features | Official C#15 description labels the memory-safety work preview, unlike the preceding stable features | Do not enable preview for normal packages; Span/ref escape rules still require concrete compiler and unsafe-boundary checks |
| Runtime Async | Official .NET11 runtime description supports explicit `Features=runtime-async=on`; default and opt-in configurations must have isolated build inputs | Optional implementation experiment, not a default ABI change or proof of smaller/faster code; keep Task/cancellation semantics and D05 ownership unchanged |
| Rust stable allocator, DropGuard, never, map APIs | Existing fixed-source review and 13 unit /13 command checks on both OS | Use locally where their semantics fit; no global allocator/runtime, no `extern custom` P/Invoke, no assumption all allocator extensions stabilized |

The finite language fixture assigns 2,048 `Success` value cases into an escaping union array and explicit tagged structs into another array. Linux normal/AOT observed 49,152 allocated bytes for the union assignments and zero for the tagged assignments, excluding preallocated arrays. This establishes a counterexample to “union means no boxing” at this compiler/workload. It is not a product throughput measurement or a promise that every union representation allocates identically. The inspected Roslyn generic custom-union tests emit boxing for a different generic case; they are corroborating implementation context, not falsely presented as the exact generated-union experiment.

## Async and exception boundaries

`AsyncLocal` context survives a real yield; delayed success, pre-cancelled Task.Delay and an exception after yield are executed. These language/runtime semantics do not install an ExecutionContext on a native callback thread. D05 explicitly controls scheduling and continuation execution. Runtime Async cannot make a native Future into a CLR Task or retire a callback root.

Initial local runs reused output paths and produced identical AOT hashes. They are preserved under verification/platform-completion/linux as observations, not proof of distinct compiler lowering. The corrected runner copies each profile to an isolated project directory, records the actual compiler command and runs both resulting executables. Hash differences alone also do not prove a particular lowering; source/metadata inspection must support that claim. The final local metadata inspection identifies three IAsyncStateMachine implementation types in the default assembly and none in the enabled assembly; both independently built AOT executables pass ten checks. Roslyn MethodCompiler and SourceMethodSymbol fixed-source branches explain this exact distinction. The first metadata inspector incorrectly matched generated names by d__ and its failure is preserved; the corrected inspector checks the actual interface implementation. This proves the intended lowering path for this fixture, not a performance benefit.

## Negative and platform evidence

The fixture's external assembly attempts to inherit the closed type and must fail with a C# diagnostic. Its normal program has nine checks; each AOT execution has ten including `!RuntimeFeature.IsDynamicCodeSupported`. The source inventory, original command outputs, exit codes, timestamps and executable hashes are preserved under verification/platform-completion. A failed expected negative is not reported as a failed positive. Actual Windows evidence is admitted only after its CI logs/artifacts have been retrieved and checked; Linux cannot stand in for it.

The existing Rust negatives cover alias/coherence changes, unstable Arc::new_in / try_map and invalid extern-custom usage. They remain linked rather than copied into new counts. R02 owns Native AOT platform restrictions; R03/R04 own interop layout/calling conventions. A modern feature never weakens those contracts.

## Consequences and remaining product obligations

D01 pins a reproducible initial profile and explicit OS/CPU scope. D03 may use stable language features to reduce generated C#, but no generator runs Cargo or synthesizes an independent SQL language. A14/A15 repeat the final product's whole selected dependency closure on each OS. A22 owns future toolchain upgrade investigation, and A21 owns actual performance comparisons. Those product tests are implementable acceptance obligations, not prerequisites for accepting this toolchain research.
