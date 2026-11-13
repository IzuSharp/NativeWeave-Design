# R04 — Static imports, reverse callbacks and boundary cost

Research decision ready for independent review. Existing real native-slice execution was incorrectly represented only by a continuation reference; this report gives R04 its own source/evidence/coverage record. All measurements below are scoped behavior/call-shape evidence, not product throughput claims.

## Decision

Prefer generated internal LibraryImport declarations over public raw pointers. Use static non-generic UnmanagedCallersOnly entries with explicit C calling convention and blittable wire fields for reverse callbacks. C# wrappers expose typed methods/Task while Rust engine state stays native. A synchronous path pays a logical gate, physical lease and one domain FFI call; a batch API can amortize boundary calls where the native engine supports it. No default SuppressGCTransition optimization is permitted on calls that may block, allocate, lock, reenter or callback.

## Source and experiments

The pinned .NET11 LibraryImportGenerator implementation is read through its attribute pipeline, invalid-method filter, tracked stub-generation stages and forwarded calling-convention attributes. It is reused, not replaced with a new marshaller. csbindgen1.9.8's exact parser/emitter are a raw declaration alternative; actual generated primitive DllImport bindings were compiled and executed against the same Rust extent export as LibraryImport, in normal and Linux AOT modes. DllImport was not rejected solely on its name.

Original run43363045559 already exercised native imports and synchronous callbacks in real Windows/Linux AOT consumers. New `interop-completion` adds native-thread reverse callbacks, normal GCHandle roots, explicit in-flight callback retirement and managed exception containment. Its final Linux normal/AOT runs contain 10,528/10,529 assertions, including 32 controlled callback/GC rounds and 10,004 extent checks; full command/source/binary identities are in the run manifest. Those counts describe checked assertions, not independent randomized schedules or all concurrency interleavings.

## Correctness details

LibraryImport SafeHandle marshalling can protect a physical native call, but does not close ordinary logical admission after Dispose while another lease remains. D04's Open-check and AddRef occur under the same short gate, FFI outside the gate, Release in finally. Mutable builder serialization is a third, separate obligation. Neither GC.KeepAlive nor a nonzero cookie substitutes for that protocol.

A reverse callback's cookie is a managed handle identifier, not an object address. A Normal GCHandle roots the target without pinning its data. The creating side keeps it until D05/D06 native quiet and all managed drain facts hold. It must not be pooled/reused merely because Task completed. The fixture forces GC while the native callback is active and observes the root remain valid, then frees only after retirement and all test control calls return.

Static callbacks catch ordinary managed mapping exceptions; the fixture injects one and native code resumes with a recorded fault. Invalid UCO signatures and runtime-fatal exceptions can fail before the callback body or outside ordinary exception recovery. Native and managed exceptions never unwind through the public C ABI.

## Cost model and alternatives

| Shape | Structural cost | Use |
|---|---|---|
| Direct sync call | One FFI transition plus lease/gate; bounded argument copy if needed | Small synchronous engine operations |
| Batched native request | Fewer transitions but encoding/retained-memory and latency costs | Measured high-frequency multi-item work |
| Async operation | create/start/take/retire/release, TCS/context/root, completion scheduling | I/O or long-lived native work |
| Delegate callback | Delegate/root management and possible marshalling | Only explicit compatibility profile with verified lifetime |
| Static UCO function pointer | No per-call delegate allocation; explicit stable cookie/retirement | Initial Native AOT callback interface |

No absolute nanosecond figure, zero-copy claim or end-to-end speedup follows from these probes. R17/D13 own same-workload direct-Rust, NativeWeave and managed-comparator measurement. Core optimization must preserve ABI/retirement invariants and show a meaningful full workload benefit.

## Closure

D02–D06/D08 specify the exact selected boundary. A10/A11/A12 implement generated imports/exports and diagnostics; A06/A07 implement full callback/async coordination. A14/A15 verify all published shapes and fatal cases on both OS. The source-driven selection and finite feasibility evidence resolve this research question; complete product distribution, performance and production race coverage remain explicitly future acceptance.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
