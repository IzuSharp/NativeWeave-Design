# R07: Ownership, SafeHandle, GCHandle and parent/child resources

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Research date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; v1 design decision recorded; independent review pending**. This report presents implementation choices for review; it does not mean that the actual product, all sources or production platforms have been validated.

## 1. Inputs and delivery boundaries

The shared baselines are Design `1f7d89aa754647a6a530fa34a49acc4b0f5d9997` and Plan `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R07 has revision `0.1.1` in the pinned remote Plan graph, and the actual SHA256 of the local packet matches the graph: `e983236fed611d62a949927a5d1a14a4189e4338ae5da884df984e7a813015f8`. The corresponding D04 packet is `0.1.1`, hash `75c6ccd848ed543a3eae0a2738ca1097a62959621c5b764565d3a5f10fe2ed02`.

This increment completes only the design of resource identity, valid calls, parent/child ownership and reclamation; D07 owns the concrete Buffer layout, and D05/D06 own callbacks and asynchronous cleanup respectively. ArcForges is a format reference only. There is no product source implementation, upstream test execution or C#/Rust/AOT compilation result.

## 2. Requirements, non-goals and decisions

Applications must receive natural C# resource objects. Dispose can reject new calls, and a call that has already started legitimately must not access a freed native object because of concurrent Dispose. After a parent wrapper closes, the parent state required by existing children must remain alive; copying a pointer must not conflate shared ownership with borrowing. GCHandle may serve only as the strong root for a callback cookie, not simultaneously as pinning, handle-validity checking and an ABA prevention scheme.

**v1 uses a private opaque pointer, a single SafeHandle owner, a separate managed admission gate and explicit call/asynchronous leases.** Ordinary public APIs do not expose `nint`; the synchronous hot path allocates no GCHandle, traverses no global handle table and starts no unified native runtime. Generational tokens are introduced only for special reuse/cross-process identities and do not remove the need for the quiescence protocol. See [D04](../../../contracts/lifetime-v0.1.md) for the complete specification.

Non-goals include isolating malicious native code, repairing arbitrary memory corruption, equating local quiescence with knowledge of remote database effects, or forcing every Engine to use the same threads or runtime through one implementation.

## 3. Pinned sources and actual coverage

See [evidence.json](evidence.json) for itemized locations and blob SHAs, and [coverage.json](coverage.json) for the read/unread inventory. This increment reads the following pinned snapshots; floating branches do not support technical conclusions:

| Source | Pinned commit | Actual trace |
| --- | --- | --- |
| dotnet/runtime, v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | SafeHandle state word, AddRef, InternalRelease and tests |
| Godot, 2026-11-11 master snapshot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | GodotObject.Dispose, runtime interop, managed callable, signal awaiter GCHandle |
| YetAnotherHttpHandler | `c386c1cc48d2e56711c15286cf2769353fdccf07` | SafeHandle parent references, RequestContext rooting and release, TLS callback reuse negative-test source |

The Godot snapshot is used to investigate mechanisms; it neither selects Godot as a NativeWeave dependency nor declares that snapshot a stable release. Qt for Python was not read in depth in this increment; its Python object ownership and interpreter shutdown mechanisms remain candidate extension sources. No entire project is listed as read.

## 4. The actual SafeHandle path: logical closure is not final release

The constructor of [`SafeHandle.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs) establishes the initial owner reference; DangerousAddRef increments the reference count atomically; Dispose enters InternalRelease. The reference count, Closed and Disposed share one state word, and only final release invokes ReleaseHandle. DangerousGetHandle retrieves the address without adding a reference.

A fact with particular implications for NativeWeave is that DangerousAddRef rejects Closed, but **does not use Disposed itself as a rejection condition for every new AddRef**. If another lease remains, Dispose may already have occurred while the object is not yet Closed. SafeHandle therefore protects physical lifetime but does not suffice to define the application API rule that new calls are forbidden after Dispose. [R07-S01]

We therefore add a short managed admission critical section: check Open and acquire DangerousAddRef under the same lock; Dispose changes the state to Closing under that lock, then stops application work and releases the owner outside the lock. Neither FFI nor user callbacks execute under the gate lock; finally balances DangerousRelease. A future CAS implementation must still preserve a common linearization point for closing the gate and acquiring a lease. [R07-D01]

The [SafeHandle tests](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Runtime.Handles.Tests/SafeHandle.cs) that were read cover valid/invalid handles, repeated Dispose and SetHandleAsInvalid, and test Windows LastError behavior with AddRef→Dispose→DangerousRelease. They do not execute NativeWeave's concurrent gate, parent/child protocol or actual FFI and cannot serve as this project's race acceptance evidence. [R07-T01]

## 5. The actual YAHA path: parent references, strong context roots and release timing

In [`YahaSafeHandles.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/YahaSafeHandles.cs), the context retains the runtime, and the request retains the context; releasing a request first invokes the corresponding native destroy and then returns the parent reference. The context SafeHandle owns the GCHandle for the TLS verification callback and returns it when the context is released. This is a verifiable parent/child lifetime chain, rather than merely a managed variable pointing to the parent. [R07-S02]

The constructor in [`RequestContext.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/RequestContext.cs) retains an additional request SafeHandle reference; Allocate creates a Normal GCHandle, and Release returns the GCHandle and signals completion, while a separate Dispose path releases the native handle. TryAbort checks under a lock that the context is still alive, holds both context/request AddRef references while invoking abort, and balances them in finally. The source explicitly distinguishes the managed callback context no longer being needed from the native handle being releasable. [R07-S03]

The finalizer in the same file waits for native completion. Its comments connect this to Unity Domain Reload and acknowledge that locking and scheduling may block the finalizer. NativeWeave does not copy this host-specific case: a bounded cleanup coordinator holds strong roots while operations are active; finalizers do not wait or run user code, and resources that cannot reach quiescence for an extended period are quarantined and retained. [R07-S03, R07-D02]

The TLS [lifetime test](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/test/YetAnotherHttpHandler.Test/CertificateVerificationCallbackLifetimeTest.cs) establishes a controlled handshake, disposes the handler during an active request, attempts to allocate a replacement callback handle and then asserts that the replacement validator was not called. It runs in a child process so that a callback exception cannot bring down the test runner. **This increment read the test source but did not execute it.** It provides a more concrete counterexample and acceptance shape than assuming that a non-null Target is safe. [R07-T02]

## 6. The actual Godot path: multiple ownership relationships cannot collapse into one bool

[`GodotObject.base.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/GodotObject.base.cs) distinguishes the memory owner, native pointer, associated GCHandle and refcounted/nonrefcounted release. Before releasing the associated handle, Dispose checks that the current target is still this, because another thread may have replaced the association; GetPtr checks disposed and a zero pointer. Its reflection and complete object system are not included in NativeWeave Core. [R07-S04]

The corresponding [`runtime_interop.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/runtime_interop.cpp) delegates different object relationships to CSharpInstance or a binding helper; the refcounted path may delete the object after unreference. We read this adaptation layer but did not finish reading the internals of CSharpInstance, so we do not claim to have proved every Godot threading and destruction combination. [R07-S05]

SignalAwaiter constructs a strong GCHandle; the native one-shot callable retains it and releases it in its destructor. ManagedCallable also has an explicit delegatehandle release path. This shows that a callback cookie may belong to a subscription lifetime held by native code rather than a single callback stack frame. [R07-S06] NativeWeave selects explicit stop/retire and contracts both that the source will make no further calls and that in-flight calls have returned, avoiding reliance on implicit guarantees from an entire engine object model.

## 7. Candidate comparison and resource matrix

| Approach | What it solves | What remains to solve | v1 disposition |
| --- | --- | --- | --- |
| opaque pointer + SafeHandle | Single owner, final release, managed final-release fallback | Closing application admission, asynchronous retention, callback quiescence | Default foundation |
| Global generation table | Detection of stale accesses to reused identities | Table thread safety, generation overflow, table lifetime, accesses still using the old object | Special profiles only |
| Native retain/release on every call | Independent native shared ownership | Two extra FFI calls and atomic-operation costs | As needed across asynchronous work or native sharing |
| Managed parent reference / KeepAlive | Preventing premature GC of managed objects | Cannot prevent explicit Dispose | Does not independently ensure native safety |
| Native child holding Arc<ParentState> | Keeping parent state alive while the child uses it | Logical closure, absence of reference cycles, destructor thread | Default parent/child mechanism candidate, implemented by each Engine |

Synchronous borrows last only until the call returns; callback payloads last only until the callback returns; asynchronous inputs must be copied or hold an explicit pin/owned lease; result ownership changes hands only when typed take succeeds. Each resource selects one explicit parent-lease authority; managed and native retention must not form a cycle. The allocator and release come from the same Engine, and module code must outlive the last function-pointer call. [R07-D01]

## 8. APIs, failure compensation and proof obligations

The usual public C# pattern is `using` for synchronous owners and `await using` for Engines/operations that require drain completion; ordinary users are not offered Detach of a raw pointer. D04 already has an uncompiled C# admission skeleton; D06 gives exact create/start, typed take, stop and retire interfaces. Rust may wrap an opaque owner in Box and retain shared state through Arc, but `Arc::from_raw`/`into_raw` must be paired by a generated or reviewed ownership protocol; a borrowed pointer cannot arbitrarily be turned into an owner.

On create failure, the out pointer must be null; failures in SafeHandle wrapping, GCHandle allocation or cancellation registration require individual compensation; if a parent fails to create a child, any acquired parent lease must be returned. Dispose may repeat, but owner release occurs exactly once. Dispose for an asynchronous operation requests stopping; only successful DisposeAsync means that all specified cleanup is complete.

The proof obligations are `native_access => live && valid_lease`, `free_count <= 1`, no new application work accepted after Closing, no callback/start/control/cancellation-registration obligations at final release, and no parent/child release calling unloaded code. The R09 model covers only the abstract retirement conditions within these obligations; the memory model and mapping to a concrete implementation remain for R15/A19/A20.

## 9. Costs, platforms and validation

The synchronous baseline costs one short admission critical section, SafeHandle AddRef/Release and the application FFI call; no measured ns value is claimed. Asynchronous work adds a context, TCS, GCHandle and cleanup slot, whose costs must not disappear into zero-copy claims. Retained parent/child references reduce copying but delay reclamation of native state; bytes and cleanup age must be measured.

The initial platforms are win-x64/linux-x64. Windows handle LastError, native destructor threads and future Arm64/mobile/GUI affinity are validated separately; cross-platform safety is not inferred from a Linux Python model. Both C#/Rust skeletons are draft and uncompiled. Delivery mapping for D04 LT-01–06 is: A03 handles, A06 callbacks, A07 asynchronous work, A14/A15 actual AOT, A18 shutdown, A19 models, A20 races/faults, A21/B22 long-load testing.

Formal tests must include collisions between Dispose and admission, parent Dispose before child completion, GC pressure and repeated Dispose, OOM during creation, handle-reuse negative cases, thread-affine finalizer negative cases, module unloading and the last lease, and resource counts returning within bounds. Negative cases that cannot guarantee process survival run in child processes with exit codes, seeds, logs and binary hashes preserved.

## 10. Research conclusions, open issues and review interfaces

The Q04 lifetime design has a concrete approach, and its design question may close after independent D04/D05/D06 review; the Q02 choice between private pointers and a generational table supplies D02 with its basis. Implementation validation and production acceptance remain pending and must not be claimed complete on this basis.

R08 checks Dispose inside callbacks, final cookie release and late-callback counterexamples; R09 checks leases for start not yet returned, cancellation registration and take_result; R32 checks independent Engine parent/module lifetimes and thread-affinity profiles. Affected files are D04/D05/D06 and the corresponding Plan tasks. Qt for Python and the full Godot signal dispatch/deeper CSharpInstance implementation have not been read. This does not prevent review of the current recommendation, but the overall task remains partially_evidenced; subsequent reading may target real counterexamples, and research across the entire project must not be marked complete.

Licenses: the licenses at the pinned dotnet/runtime, Godot and YAHA snapshots were all read and are MIT; the evidence files record their blobs. This report paraphrases mechanisms and presents new design, without copying long upstream implementations; future product source reuse must retain applicable notices and be checked item by item.

## Post-migration executed logical-admission evidence

The original report above is a historical source-analysis snapshot. [The new R07/D04 study](logical-admission.md) adds actual Windows/Linux normal and Native AOT negative/positive admission evidence: run43373306474,653 assertions and64 guided gate/Dispose rounds per invocation. It distinguishes logical admission, physical lifetime, native mutation and async retirement, and includes checked SeaQuery/Tower/Rust source implications. The local SafeHandle-only admission question is resolved; full task/contract acceptance and independent review remain pending. Research code and raw outputs are Design-owned, not product implementation.

## Current completion review — ownership beyond synchronous admission

The original report, source identities and logical-admission execution remain valid historical evidence. New `verification/interop-completion/linux/result.json` adds actual native-thread UCO/GC-root retirement and an independent transferred-result owner. A ResultOwner remains valid after operation release, second take produces no owner, and an injected DTO conversion failure releases exactly the transferred result. Thirty-two controlled callback/GC rounds execute in normal and actual Native AOT modes; the native callback must exit before try_retire succeeds. These are finite research fixtures, not full A03/A07 code.

The chosen default remains private opaque pointer + SafeHandle + explicit logical gate, with native Arc/state retention only where the engine requires it. No default global handle table or per-call native retain/release is added. Core lifetime mechanisms are reusable by mandatory Rust Database/ORM/Server and future synchronous/affine engines; a synchronous engine does not need an async runtime. D04/D09 identify internal cleanup authority after ordinary admission closes.

This task's current design questions have concrete answers and executable counterexamples. New exact-content independent review is still required before acceptance. Full parent/child product wrappers, finalizer scheduling, affine release, supported-target weak memory and long-load conformance are future A03/A07/A20/A23 obligations, not proof that no ownership design can be accepted now. Historical 'not executed' lists describe their original increments; consult the current supplemental manifest for actual later execution.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
