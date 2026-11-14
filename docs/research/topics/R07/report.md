# R07: Ownership, SafeHandle, GCHandle, and Parent–Child Resources

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Research date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; v1 design decision recorded; independent review pending**. This report provides reviewable implementation choices, not a claim that an actual product, all sources, or production platforms have been verified.

## 1. Input and Delivery Boundaries

The common baselines are Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997` and Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R07 in the pinned remote Plan graph has revision `0.1.1`; the actual local task packet SHA256 matches the graph: `e983236fed611d62a949927a5d1a14a4189e4338ae5da884df984e7a813015f8`. The corresponding D04 task packet is `0.1.1`, hash `75c6ccd848ed543a3eae0a2738ca1097a62959621c5b764565d3a5f10fe2ed02`.

This round completes only the design of resource identity, valid calls, parent-child ownership, and reclamation; D07 owns concrete Buffer layouts, while D05/D06 own callbacks and asynchronous cleanup, respectively. ArcForges is a formatting reference only. There is no product source implementation, execution of upstream tests, or C#/Rust/AOT compilation result.

## 2. Requirements, Non-Goals, and Decisions

Applications must receive natural C# resource objects: Dispose can reject new calls, and calls that have already started legitimately must not access freed native objects because of concurrent Dispose. After a parent wrapper closes, the parent state required by existing children must remain alive; shared ownership and borrowing cannot be conflated by copying pointers. GCHandle serves only as a strong root for a callback cookie; it cannot also act as a pin, handle-validity check, and ABA prevention scheme.

**v1 adopts private opaque pointers, a single SafeHandle owner, a separate managed admission gate, and explicit call/asynchronous leases.** Ordinary public APIs do not expose `nint`; synchronous hot paths allocate no GCHandle, use no global handle table, and start no unified native runtime. Generational tokens are introduced only for special reuse/cross-process identities, and do not permit omission of the quiescence protocol. See [D04](../../../contracts/lifetime-v0.1.md) for the complete specification.

Non-goals include isolating malicious native code, repairing arbitrary memory corruption, equating local quiescence with known remote database effects, and forcing every Engine to share the same threading model or runtime through one implementation.

## 3. Pinned Source and Actual Coverage

See [evidence.json](evidence.json) for detailed item-level locations and blob SHAs, and [coverage.json](coverage.json) for read/unread inventories. This round read the following pinned snapshots; floating branches do not support technical conclusions:

| Source | Pinned commit | Paths actually traced |
| --- | --- | --- |
| dotnet/runtime, v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | SafeHandle state word, AddRef, InternalRelease, and tests |
| Godot, 2026-11-11 master snapshot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | GodotObject.Dispose, runtime interop, managed callable, signal awaiter GCHandle |
| YetAnotherHttpHandler | `c386c1cc48d2e56711c15286cf2769353fdccf07` | SafeHandle parent references, RequestContext roots and release, TLS callback-reuse negative test source |

The Godot snapshot is used to investigate mechanisms; it neither selects Godot as a NativeWeave dependency nor declares that snapshot stable. Qt for Python was not read in depth in this round; its Python-object ownership and interpreter-shutdown mechanisms remain candidate supplementary sources. No entire project is marked as read.

## 4. The Actual SafeHandle Chain: Logical Closure Is Not Final Release

The constructor in [`SafeHandle.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs) establishes the initial owner reference; DangerousAddRef increments the count atomically, and Dispose enters InternalRelease. The reference count, Closed, and Disposed occupy one state word, and only final release calls ReleaseHandle. DangerousGetHandle merely retrieves the address without adding a reference.

A fact particularly relevant to NativeWeave is that DangerousAddRef rejects Closed, but **does not use Disposed itself as a rejection condition for every new AddRef**. If another lease remains, Dispose may have occurred while the object is not yet Closed. SafeHandle therefore protects physical lifetime but is insufficient to define the business API rule that new calls are forbidden after Dispose. [R07-S01]

We consequently add a short managed admission critical section: check Open and acquire DangerousAddRef under the same lock; Dispose changes the state to Closing under that lock, then stops business operations and releases the owner outside it. Neither FFI nor user callbacks run under the gate lock, and finally balances DangerousRelease. A future CAS implementation must still preserve a common linearization point for closing admission and acquiring a lease. [R07-D01]

The [SafeHandle tests](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Runtime.Handles.Tests/SafeHandle.cs) read cover valid/invalid handles, repeated Dispose, and SetHandleAsInvalid, and test Windows LastError behavior through AddRef→Dispose→DangerousRelease. They do not execute NativeWeave's concurrent gate, parent-child protocol, or actual FFI, and cannot serve as this project's race acceptance evidence. [R07-T01]

## 5. The Actual YAHA Chain: Parent References, Strong Context Roots, and Release Timing

In [`YahaSafeHandles.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/YahaSafeHandles.cs), the context retains the runtime and the request retains the context; request release first calls the corresponding native destroy function, then returns the parent reference. The context SafeHandle owns the TLS verification callback's GCHandle and returns it when the context is released. This is a verifiable parent-child lifetime chain, beyond merely keeping a managed variable pointing to the parent. [R07-S02]

The constructor in [`RequestContext.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/RequestContext.cs) retains an additional request SafeHandle reference; Allocate creates a Normal GCHandle, Release returns the GCHandle and signals completion, while a separate Dispose path releases the native handle. TryAbort confirms under a lock that the context is still alive, holds both context/request AddRefs during abort, and balances them in finally. The source explicitly distinguishes the managed callback context no longer being needed from the native handle being releasable. [R07-S03]

The finalizer in the same file waits for native completion; comments connect this to Unity Domain Reload and acknowledge that locks and scheduling can block the finalizer. NativeWeave does not copy this host-specific exception: a bounded cleanup coordinator holds strong roots while operations are active; finalizers do not wait or run user code, and prolonged inability to reach quiescence leads to quarantine and resource retention. [R07-S03, R07-D02]

The TLS [lifetime test](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/test/YetAnotherHttpHandler.Test/CertificateVerificationCallbackLifetimeTest.cs) establishes a controlled handshake, disposes the handler during an active request, attempts to allocate a replacement callback handle, and then asserts that the replacement validator was not called. It runs in a subprocess so a callback exception does not bring down the test runner. **This round read the test source but did not execute it.** It supplies a more concrete counterexample and acceptance shape than assuming a non-null Target is safe. [R07-T02]

## 6. The Actual Godot Chain: Multiple Ownership Relationships Cannot Collapse into One bool

[`GodotObject.base.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/GodotObject.base.cs) distinguishes memory owner, native pointer, associated GCHandle, and refcounted/nonrefcounted release. Before releasing the associated handle, Dispose checks that its current target is still this, because another thread may have replaced the association; GetPtr checks disposed and zero pointers. Its reflection and complete object system do not enter NativeWeave Core. [R07-S04]

The corresponding [`runtime_interop.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/runtime_interop.cpp) delegates different object relationships to CSharpInstance or binding helpers; the refcounted path may delete an object after unreference. We read this adaptation layer but did not finish reading CSharpInstance internals, so no claim is made to prove every combination of Godot threading and destruction. [R07-S05]

SignalAwaiter creates a strong GCHandle, which a native one-shot callable holds and releases in its destructor; ManagedCallable also has an explicit delegatehandle release path. This shows that a callback cookie may belong to a native-held subscription lifetime rather than one callback stack frame. [R07-S06] NativeWeave chooses explicit stop/retire, making both no further calls from the source and return of all in-flight calls contractual, avoiding reliance on implicit guarantees of an entire engine object model.

## 7. Candidate Comparison and Resource Matrix

| Approach | What it solves | What remains to be solved | v1 disposition |
| --- | --- | --- | --- |
| opaque pointer + SafeHandle | Single owner, final release, managed finalization fallback | Business admission closure, asynchronous retention, callback quiescence | Default foundation |
| Global generation table | Detection of stale access to reused identities | Table thread safety, generation overflow, table lifetime, continued access to old objects | Special profiles only |
| Native retain/release on every call | Independent native shared ownership | Two additional FFI calls and atomic-operation costs | As needed across async boundaries or for native sharing |
| Managed parent reference / KeepAlive | Prevents premature GC of managed objects | Cannot prevent explicit Dispose | Does not independently provide native safety |
| Native child holds Arc<ParentState> | Parent state remains alive during child use | Logical closure, absence of reference cycles, destruction thread | Default parent-child mechanism candidate, implemented by each Engine |

Synchronous borrowing lasts only until the call returns; callback payloads only until the callback returns; asynchronous inputs must be copied or have an explicit pin/owned lease; result ownership changes hands only at successful typed take. Each resource chooses one explicit authority for the parent lease; managed and native retention must not create cycles. Allocation and release come from the same Engine, and module code must outlive the final function-pointer call. [R07-D01]

## 8. APIs, Failure Compensation, and Proof Obligations

Typical public C# usage manages synchronous owners with `using` and Engines/operations requiring completed drain with `await using`; ordinary users are not given a Detach operation for raw pointers. D04 already contains an uncompiled C# admission skeleton; D06 specifies exact create/start, typed take, stop, and retire interfaces. Rust may wrap opaque owners in Box and hold shared state in Arc, but `Arc::from_raw`/`into_raw` must be paired by generated or reviewed ownership protocols; owners cannot be manufactured arbitrarily from borrowed pointers.

On create failure, the out pointer must be null; failures in SafeHandle wrapping, GCHandle creation, and cancellation registration each require compensation; failed child creation must return the acquired parent lease. Dispose may repeat, but owner release occurs exactly once. Dispose on an asynchronous operation requests stop; only successful DisposeAsync means all specified cleanup has completed.

Proof obligations are `native_access => live && valid_lease`, `free_count <= 1`, rejection of new business operations after Closing, no outstanding callback/start/control/cancellation-registration obligations at final release, and no calls to unloaded code during parent-child release. The R09 model covers only the abstract retirement conditions among these; mapping to the memory model and concrete implementation remains pending for R15/A19/A20.

## 9. Cost, Platforms, and Validation

The synchronous baseline costs one short admission critical section, SafeHandle AddRef/Release, and the business FFI call; no actual nanosecond value is claimed. Async adds a context, TCS, GCHandle, and cleanup slot, whose costs must not be hidden in "zero-copy" claims. Retained parent-child references reduce copying but delay native-state reclamation, so bytes and cleanup age must be measured.

Initial platforms are win-x64/linux-x64. Windows handle LastError, native destruction threads, and future Arm64/mobile/GUI affinity are verified separately; cross-platform safety is not inferred from a Linux Python model. C#/Rust skeletons are all draft and uncompiled. Delivery mapping is D04 LT-01–06: A03 handles, A06 callbacks, A07 async, A14/A15 actual AOT, A18 shutdown, A19 models, A20 races/faults, A21/B22 long workloads.

Formal tests must include Dispose racing with admission, parent Dispose before child completion, GC pressure and repeated Dispose, OOM during creation, handle-reuse negative cases, thread-affine finalizer negative cases, module unloading with the final lease, and resource counts returning within bounds. Negative cases that cannot guarantee process survival run in subprocesses, retaining exit codes, seeds, logs, and binary hashes.

## 10. Research Conclusions, Open Items, and Review Interfaces

Q04 lifetime design now has a concrete approach, and the design question can close after independent D04/D05/D06 review; the choice between private pointers and generational tables for Q02 has provided input to D02. Implementation validation and production acceptance remain pending and cannot therefore be declared complete.

R08 checks Dispose inside callbacks, final cookie release, and late-callback counterexamples; R09 checks leases for an unreturned start, cancellation registration, and take_result; R32 checks independent Engine parent/module lifetimes and thread-affine profiles. Affected files are D04/D05/D06 and the corresponding Plan tasks. Qt for Python and the complete Godot signal dispatch/deep CSharpInstance implementation are unread; this does not prevent review of the current proposal, but the task overall remains partially_evidenced. Subsequent checks may target actual counterexamples; whole-project research must not be marked complete.

Licenses: the licenses at the pinned dotnet/runtime, Godot, and YAHA snapshots were all read and are MIT; the evidence files record their blobs. This report paraphrases mechanisms and presents new design without copying large passages of upstream implementation; future product source reuse must still retain applicable notices and be checked item by item.

## Post-migration executed logical-admission evidence

The original report above is a historical source-analysis snapshot. [The new R07/D04 study](logical-admission.md) adds actual Windows/Linux normal and Native AOT negative/positive admission evidence: run43373306474,653 assertions and64 guided gate/Dispose rounds per invocation. It distinguishes logical admission, physical lifetime, native mutation and async retirement, and includes checked SeaQuery/Tower/Rust source implications. The local SafeHandle-only admission question is resolved; full task/contract acceptance and independent review remain pending. Research code and raw outputs are Design-owned, not product implementation.

## Current completion review — ownership beyond synchronous admission

The original report, source identities and logical-admission execution remain valid historical evidence. New `verification/interop-completion/linux/result.json` adds actual native-thread UCO/GC-root retirement and an independent transferred-result owner. A ResultOwner remains valid after operation release, second take produces no owner, and an injected DTO conversion failure releases exactly the transferred result. Thirty-two controlled callback/GC rounds execute in normal and actual Native AOT modes; the native callback must exit before try_retire succeeds. These are finite research fixtures, not full A03/A07 code.

The chosen default remains private opaque pointer + SafeHandle + explicit logical gate, with native Arc/state retention only where the engine requires it. No default global handle table or per-call native retain/release is added. Core lifetime mechanisms are reusable by mandatory Rust Database/ORM/Server and future synchronous/affine engines; a synchronous engine does not need an async runtime. D04/D09 identify internal cleanup authority after ordinary admission closes.

This task's current design questions have concrete answers and executable counterexamples. New exact-content independent review is still required before acceptance. Full parent/child product wrappers, finalizer scheduling, affine release, supported-target weak memory and long-load conformance are future A03/A07/A20/A23 obligations, not proof that no ownership design can be accepted now. Historical 'not executed' lists describe their original increments; consult the current supplemental manifest for actual later execution.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
