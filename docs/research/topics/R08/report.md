# R08: Callback Registration, Reentrancy, Stop, and Quiescence

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; independent review pending**. This round deepens actual source research within the existing task and develops the [D05 callback contract](../../../contracts/callback-v0.1.md); it is neither a new coordination plan nor validation of a product implementation.

## 1. Pinned Inputs and Questions

Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R08 revision `0.1.1`, task packet SHA256 `690b702013f788e3c99144467a6c8157f313b1f5a5bdd398b87fad44c927d36a`; D05 revision `0.1.1`, hash `e493b0ba781d216860587eb6f8e46bc809bba78549733b92e9439c79d349cdbb`. All agree with the pinned remote graph and actual task packet bytes.

The following must hold simultaneously: foreign native threads can notify managed code; an immediate synchronous callback after registration is safe; Dispose can be called inside a callback; stopping does not lose callbacks already in flight; a late callback cannot interpret a cookie as a different object; and all ordinary exceptions stop within language boundaries. Non-goals are recovering arbitrary forged pointers through managed validation, or forcing GUI, TLS decisions, and ordinary notifications into the same threading model.

**v1 chooses separate create/start, nonblocking request_stop, separate try_retire, explicit call leases, and cleanup outside callbacks.** A stop request does not promise quiescence. Ordinary notifications first copy borrowed data/record a fixed terminal state, then pass it to a bounded managed coordinator; synchronous decision callbacks are used only for profiles explicitly requiring an immediate return, and may not synchronously wait for their own shutdown. See D05's concrete interfaces and the [D06](../../../contracts/async-v0.1.md) result protocol.

## 2. Source Coverage and Classification

| Source | SHA | Directly read in this round |
| --- | --- | --- |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | SignalAwaiter, signal_awaiter_utils, ManagedCallable, GCHandleBridge |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | C# callbacks, RequestContext, SafeHandle, Rust begin/body/complete/abort, TLS lifetime tests |
| .NET runtime v11 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenRegistration unregister/drain and its tests |

Paths, symbols, read line ranges, and blob SHAs are in [evidence.json](evidence.json); unread Godot signal-dispatch internals and Qt for Python are listed in [coverage.json](coverage.json). The added .NET source verifies managed cancellation-callback quiescence, directly relevant to this topic. All upstream tests were read but not executed.

## 3. Godot Call Chain: Strong Roots, One-Shot Behavior, and Copying Before Return

The constructor in [`SignalAwaiter.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs) creates a strong GCHandle and passes it to native connect. UCO SignalCallback retrieves the awaiter from the handle, copies borrowed Variant arguments into a managed array, marks completion, and calls the continuation; ordinary exceptions are handled by local catch/log. [R08-S01]

[`signal_awaiter_utils.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/signal_awaiter_utils.cpp) stores the handle in SignalAwaiterCallable and connects a ONE_SHOT signal; call invokes managed SignalCallback, and the callable destructor releases the awaiter handle. [`managed_callable.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/managed_callable.cpp) likewise has explicit delegatehandle checks and destructor release, returning through [GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs) to managed free. [R08-S02, S03]

The reusable mechanisms are ownership of the strong root by the registration object and conversion of borrowed arguments into owned data inside the callback. Inline continuation is not copied: ordinary NativeWeave async notifications must not synchronously run user code after await on arbitrary native threads. ONE_SHOT describes only the logical subscription count; its name alone cannot prove concurrent destruction safety, return of the last call, or draining of managed cancellation callbacks. This round did not finish reading the Godot Object signal dispatcher and does not claim to prove its global quiescence.

## 4. YAHA Call Chain: The Native Stack May Still Access State After Completion Notification

[`NativeHttpHandlerCore.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs) initializes RequestContext, allocates a cookie, and calls native begin. OnReceive receives borrowed body data, registers a continuation while WriteAsync backpressure is incomplete, and returns a native task notification through CompleteTask on completion. OnComplete reads response/error information and completes the managed response; finally releases the RequestContext cookie and then queues Dispose to the managed thread pool, with comments explicitly prohibiting direct release of these handles on the native thread. [R08-S04]

The corresponding [`binding.rs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs) creates a oneshot at each body frame, calls managed on_receive, and awaits acknowledgment; failure becomes on_complete Error. At the normal end, after calling on_complete, it still locks the request and sets `completed=true`. This is a concrete source example showing that a logical terminal notification does not mean the native call stack has exited. [R08-S05]

This observation **does not establish a UAF in YAHA's current implementation**: references, scheduling, and other context must be considered together. It means NativeWeave cannot treat queueing to the managed thread pool or Task completion as general proof of quiescence. Thread-pool work may execute before the native callback returns; this project chooses explicit try_retire and start/control lease barriers to reduce implicit scheduling assumptions. [R08-D01]

TLS verification is a different profile: returning bool requires a synchronous decision, and ordinary handler exceptions become false. Its lifetime test uses delayed handshakes, Dispose, and replacement GCHandle allocations to expose the risk of calling the wrong target; this round read the test without executing it. NativeWeave accordingly requires decision-callback exceptions to fail closed, with all potentially throwing conversion/logging/exit actions included in the boundary policy rather than wrapping only the user delegate. [R08-T01]

## 5. Managed Cancellation Registrations Have Their Own Quiescence Conditions

Unregister in [`CancellationTokenRegistration.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs) only attempts to remove a registration; Dispose/DisposeAsync waits for an executing callback when necessary, with special handling for the current callback itself. The tests read block a callback with a barrier and verify that DisposeAsync does not complete before the callback is released. [R08-S06, T02]

Successful native try_retire therefore cannot replace managed cancellation-registration drain. Cleanup must run outside native and cancellation callbacks, invoke DisposeAsync after the registration handle is published, and then await native/control conditions. If DisposeAsync inside a callback waits for that same callback to exit, it creates a self-wait; synchronous Dispose only marks Closing/requests stop and returns. If an API exposes a DisposeAsync that must be awaited, use within the same synchronous callback scope should produce an explicit InvalidOperationException or a domain-defined prohibition, rather than silently report that draining has completed. [R08-D02]

## 6. Counterexamples and Linearization Points That Must Be Testable

Late-cookie counterexample: T1 registers handle H; T2 requests stop and immediately calls Free(H); T3 allocates a new context reusing H; an old native callback already queued arrives, and `GCHandle.FromIntPtr(H).Target` obtains the new object. Nonzero or non-null checks cannot distinguish identity and may even invoke a different certificate validator. The fix is not comparing objects after dereference; it is ensuring H always belongs to the original context whenever a callback may arrive, and releasing it only after new callbacks are permanently prohibited and all in-flight callbacks have exited. [R08-D01]

The second counterexample comes from the [actually executed R09 model](../R09/retirement-result.json): synchronous terminal notification has returned and native try_retire succeeds, but the start entry point has not returned. If the start-return lease is omitted, native start still accesses the operation after managed code releases it, producing access_after_free in the model. A third counterexample omits the ordinary control lease and also produces access after release. The model does not simulate malicious native code, incorrect retirement, actual GC, or memory barriers. [R08-M01]

| Action | Linearization point and guarantee |
| --- | --- |
| start commits | Callback table and cookie are copied/bound; native code then assumes terminal/event obligations |
| start rejects | Remains Created; no work/callback retained; caller can compensate |
| stop request | Atomically marks that no new business/event sources are accepted, while allowing in-flight work to exit |
| callback admission | Adds an in-flight obligation under the same synchronization protocol as source closure; checking first and incrementing without protection is forbidden |
| native try_retire OK | Work and callback obligations are 0, and no callback can enter in the future; external call frames are not necessarily releasable yet |
| managed Reclaimed | start has returned, cancellation registration has drained externally, call/callback counts are 0, result handling is complete, and the owner is returned once |

## 7. Candidates and Implementation Boundaries

Synchronous drain is simple but readily self-waits with reentrant Dispose, thread affinity, and executor shutdown, so it cannot define general Dispose semantics. Generation tokens detect only some reuse errors and cannot prove that old callbacks no longer execute or borrowed data remains alive. Event queues isolate user code but add copying/scheduling and require reserved capacity; alone they do not prove native quiescence. v1 uses asynchronous quiescence and explicit leases, with ordinary notifications routed through a bounded coordinator and extremely short synchronous returns retained for decision profiles. [R08-D01]

D05 defines the wire representation as `uintptr_t cookie`, static Cdecl function pointers, u32 status, and call-scoped borrowed payloads; structure sizes follow the D02 target ABI. General notifications do not implicitly transfer owned objects from callbacks; asynchronous results use D06 typed take. Within Rust, every queued/active task must retain a state reference; cleanup outside callbacks checks actual quiescence before releasing the cookie. A GCHandle cookie is not interpreted as a Rust pointer.

## 8. Validation, Cost, and AOT

Formal tasks A06/A07/A18/A19/A20 cover D05 CB-01–07: synchronous triggering during registration, Dispose within callbacks, exceptions on foreign threads, duplicate notification, stop/admission races, a paused final callback, GCHandle-reuse negative cases, control calls and start not yet returned, undrained cancellation registrations, and module unloading. Profiles requiring immediate decisions must validate fail-closed behavior, absence of synchronous waiting, and explicit thread affinity.

Independent cross-review noted that native quiescence does not cover handlers already queued to the managed dispatcher. This round accordingly refines D05 with a separate DispatchClosing: explicit Dispose discards pending work and returns its owned data, prevents new handlers from starting, and waits for active asynchronous handlers actually to finish; successful DisposeAsync also guarantees that this subscription's handlers have drained. This addition is a design inference and review revision; the finite R09 model did not simulate the dispatcher, and actual cases remain assigned to CB-03/A06/A18.

Every accepted asynchronous operation reserves a completion/cleanup slot; notifications are coalesced, and callbacks do not wait for enqueueing. A bounded queue combined with unbounded payload-holding waiters is forbidden. Measure callback latency, copied bytes, queue length, FFI crossing counts, cleanup P99, maximum retained bytes, and prolonged quiescence stalls. Ordinary synchronous APIs need not enable this coordinator.

AOT requires static, nongeneric, exact blittable UCO signatures; C#/Rust bool does not enter the wire directly. Windows/Linux Native AOT, actual races, GC stress, and fatal subprocess cases have not yet been run. The Python model checks only abstract partial orders and cannot be described as passed UCO or ABI validation. Future GUI/mobile thread affinity is a separate profile and need not rewrite general stop/retire semantics.

## 9. Conclusions and Independent Review

The Q04 callback-reclamation strategy is ready for design-resolved review; production validation remains outstanding. R07 reviews cookie/parent/module lifetimes, R09 reviews synchronous start and managed cancellation-registration barriers, R12 reviews coordinator progress, thread affinity, and shutdown, and R15 reviews atomic admission and mapping to real memory models. Independent reviewers should specifically challenge the ordering where Owner enters Closing before a terminal result requires take, Dispose within callbacks, Tasks with no await, and draining after poison.

Qt for Python and deep Godot dispatcher internals are unread, so the report overall remains partially_evidenced. MIT source licenses were read at pinned SHAs; no upstream tests were run and no large source passages copied. Subsequent checks should target these specific evidence gaps; an unread source must not stop other independent design work.

## Current completion review — real reverse callback and managed registration drain

The original callback/source report and finite model are preserved. The new interop-completion fixture now actually invokes static managed UCO from a Rust-created native thread, holds a controlled callback barrier, requests retirement/cancellation concurrently and forces GC. Retirement stays pending while the callback is active; after permanent native completion and all test calls return, the cookie is freed. An ordinary callback mapping exception is caught and recorded before returning across FFI. Thirty-two rounds execute in normal and actual Linux Native AOT modes; raw evidence and precise source/binary hashes are in `verification/interop-completion/linux`.

The same fixture observes an already-cancelled token's UnsafeRegister callback before registration publication and verifies DisposeAsync remains incomplete while another callback runs, then completes after that callback exits. This closes the previously source-only registration-order experiment. It does not claim arbitrary invalid-cookie probing is safe or that a test barrier is appropriate production callback behavior; production callbacks remain short/nonblocking.

New UniFFI scheduler source at `482095c1ba1b76a1393b582e0589e2fdc9c64b14` invokes foreign continuations outside its mutex and stores wake/cancel state when no continuation is installed. Its callback/free semantics are deliberately not substituted for NativeWeave's no-future-callback retirement requirement. The alternative is now source-inspected rather than falsely listed as universally unexamined; exact read limits remain recorded.

D05/D06/D09 provide stable cookie, source closure, native quiet, managed start/control/callback/registration drain and bounded dispatcher rules. Existing Godot/YAHA evidence already suffices to compare ownership hazards; Qt is not an adopted runtime dependency and its broader source audit is outside this selected C# ABI design. Product notification subscriptions, many concurrent operations, allocator failure and two-OS long-load tests remain A06/A07/A20/B17 implementation obligations. Research/design acceptance awaits independent review of this new scope, not completion of the product.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
