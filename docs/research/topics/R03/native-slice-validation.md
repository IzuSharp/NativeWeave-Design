> **Research asset location correction:** these historical execution identities remain unchanged. Current source is `experiments/native-slices/` and original evidence is `verification/native-slices/original-pr1/` in NativeWeave-Design. See `docs/traceability/research-asset-migration.md` and its per-file mapping. No formal product implementation is authorized in this phase.

# R03/R04/R07/R10 — executed native/managed boundary continuation

Status: **partially evidenced**, author self-review, independent review pending. This adds new executable evidence to the original source research; no existing successful Rust API or database AOT experiment was rerun. Recovery details: [checkpoint](../../../traceability/native-slices-recovery.md).

## Provenance and actual execution

NativeWeave original sources were already saved at `994fbd95da4ebbc51ee2772f04a43eb3956e5c58`. The missing build/consumer/CI infrastructure was added at **`4a4adc883b80719d2a9b2bfb03be5ec86b543f3c`**, then executed in [run43363045559](https://github.com/IzuSharp/NativeWeave/actions/runs/43363045559). Ubuntu24.04 x64 and Windows2022 x64 both passed. The native crate has no third-party dependencies; Rust/Cargo1.100.0 and SDK11.0.100 are fixed.

| Check | Result and exact scope |
|---|---|
| Native unit tests | Four tests per OS: repr(C) layout, owned/empty buffer, bad input/publication rollback, synchronous callback |
| NuGet consumption | Actual local package with native RID asset; consumer has PackageReference, not a source ProjectReference |
| Ordinary application | `dotnet build` and `dotnet run` with no RID argument succeeded on each OS |
| Native AOT | Explicit-RID PublishAot=true, actual executable run and RuntimeFeature dynamic-code-disabled assertion |
| Managed assertions |185 per execution, six groups; normal and AOT execution each performed32 controlled call/Dispose races |
| Failure handling | Oversized allocation request, invalid mode, prepublication contained panic, invalid ABI capacity, null callback and disposed-wrapper reuse rejected |
| Physical ownership | After an admitted native call entered, Dispose left native live-count1; completion released the last call lease and live-count returned0 |

Linux native/package/AOT SHA256: `196d80ed98e58c7afbc25470ffdfce4ac162eb644a45224cac0a25d5748a71a9` / `9259fe8adce55509b07833e590cc7addf65f1343cbbdc1c110b115354849ddc8` / `f7ac38599170f7b6662eacc770e488cd96bd7940b8a37c912624ca624fd394ec`.

Windows native/package/AOT SHA256: `7c7906046558da6264d8a732bbfa632f19c5d2f77585e9cc4f3a8548b265217a` / `fb1e2b876b8bfd109d6f6001872bee604286321f40728263842a69e304c229c4` / `b7d4d9affe57b8dd289b5b47b4cfaa97cc00ada8c69a7ce6776828bb08b54d62`.

Raw commands/stdout/stderr/results/source hashes and binary digests are preserved under NativeWeave `verification/native-slices/`, with an artifact-to-file manifest. Refer to the exact evidence commit in Plan's current checkpoint, not an assumed floating latest version. Evidence preservation is not another test run. Windows checkout CRLF and Git LF identities are recorded separately.

## What Rust1.100 actually contributes here

The native owner uses Vec<u8,Global> and a DropGuard-backed unpublished-owner rollback path. Rust1.100's stable APIs permit this small implementation without adding a third-party scope-guard crate. Recovered R01 tests already cover their finer allocation/map/never/custom-ABI semantics. This slice specifically tests cross-language lifetime and AOT composition rather than claiming those language features eliminate lifetime protocols.

Cargo output paths are obtained from `compiler-artifact.filenames` JSON. Separate target/build directories avoid relying on Cargo intermediate path layout. The managed consumer references only the packed native asset; application compilation does not invoke Cargo. Native and consumer jobs share a host, so absence of a Rust installation is not proven.

## Findings and limitations

**NS-01 — physical lease is not logical admission.** The simple SafeHandle import tests establish that an already-admitted call remains alive through Dispose. They do not test a new call arriving after logical close while another reference remains. D04's separate Open/Closing gate, atomic lease acquisition and mutable-owner serialization remain mandatory. A passing simple wrapper cannot replace those contracts.

**NS-02 — experiment status IDs are private.** Local probe errors are intentionally small test constants. They do not match all D08 production states and must not be promoted into Core imports unchanged. D02's complete header/size-prefix/golden tests remain A01 work.

**NS-03 — panic scope is finite.** The injected panic occurs before publication and is successfully contained under unwind. This does not establish recovery from allocator abort, arbitrary invalid pointers, unknown-payload destructor panic or concurrent poisoned engine state. Test counters are instrumentation, not a global Core allocator/runtime.

**NS-04 — platform evidence is narrower than support.** Both tested OS now have real C# AOT and native NuGet load evidence for this slice. That does not certify a minimum Windows/glibc matrix, ARM/mobile, production Database/Server integration, clean-machine no-Rust installation or performance. No source-generator for domain models is implemented.

## Changes to existing documentation and work

D01/D02/D07 are now authored concrete proposals with exact wire/owner/target and remaining-verification obligations. D04/D06/D08 stay authoritative for admission/retirement/error policy. A01/A03/A04/A14/A15/A16 should consume this finite fixture and add their missing cases instead of rerunning it unchanged or marking their full tasks done. R03/R04/R07/R10 remain continuable partial research; independent D32 review is still pending.
