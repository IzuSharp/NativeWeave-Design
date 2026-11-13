# R08: Callback registration, reentrancy, stopping and quiescence

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; independent review pending**. This increment deepens actual source analysis within the existing task and produces the [D05 callback contract](../../../contracts/callback-v0.1.md); it is neither new coordination planning nor product implementation validation.

## 1. Pinned inputs and questions

Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R08 revision `0.1.1`, packet SHA256 `690b702013f788e3c99144467a6c8157f313b1f5a5bdd398b87fad44c927d36a`; D05 revision `0.1.1`, hash `e493b0ba781d216860587eb6f8e46bc809bba78549733b92e9439c79d349cdbb`. All match the pinned remote graph and actual packet bytes.

The following must hold simultaneously: foreign native threads can notify managed code; an immediate synchronous callback after registration is safe; Dispose can be called inside a callback; stopping does not lose callbacks already in flight; a late callback cannot interpret a cookie as another object; and all ordinary exceptions remain within the language boundary. Non-goals are recovering arbitrary forged pointers through managed checks or forcing GUI, TLS decisions and ordinary notifications into the same threading model.

**v1 selects separate create/start, nonblocking request_stop, independent try_retire, explicit call leases and cleanup outside callbacks.** A stop request does not promise quiescence. Ordinary notifications first copy borrowed data/record the fixed terminal state, then hand off to a bounded managed coordinator; synchronous decision callbacks are reserved for profiles that explicitly require an immediate return, and synchronously waiting for their own shutdown is forbidden. See D05 for exact interfaces and [D06](../../../contracts/async-v0.1.md) for the result protocol.

## 2. Source coverage and classification

| Source | SHA | Directly read in this increment |
| --- | --- | --- |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | SignalAwaiter、signal_awaiter_utils、ManagedCallable、GCHandleBridge |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | C# callbacks, RequestContext, SafeHandle, Rust begin/body/complete/abort, TLS lifetime tests |
| .NET runtime v11 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenRegistration unregister/drain and its tests |

Paths, symbols, read line ranges and blob SHAs are in [evidence.json](evidence.json); unread Godot signal-dispatch internals and Qt for Python are listed in [coverage.json](coverage.json). The additional .NET source verifies managed cancellation-callback quiescence and is directly relevant to this question. All upstream tests were read but not executed.

## 3. The Godot call chain: strong roots, one-shot and copying before return

The constructor in [`SignalAwaiter.cs`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs) creates a strong GCHandle and passes it to native connect. The UCO SignalCallback retrieves the awaiter from the handle, copies borrowed Variant arguments into a managed array, marks completion and invokes the continuation; a local catch/log handles ordinary exceptions. [R08-S01]

[`signal_awaiter_utils.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/signal_awaiter_utils.cpp) places the handle in SignalAwaiterCallable and connects a ONE_SHOT signal; call invokes the managed SignalCallback, and the callable destructor releases the awaiter handle. [`managed_callable.cpp`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/managed_callable.cpp) likewise checks delegatehandle explicitly and releases it in destruction, returning through [GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs) to managed free. [R08-S02, S03]

The reusable mechanisms are registration-object ownership of the strong root and conversion of borrowed arguments into owned data inside the callback. Inline continuation is not copied: ordinary NativeWeave asynchronous notifications must not synchronously run user code after await on an arbitrary native thread. ONE_SHOT describes only the logical subscription count; its name alone proves neither concurrent destruction, the return of the final call nor draining of managed cancellation callbacks. This increment did not finish reading Godot's Object signal dispatcher and does not claim to have proved its global quiescence.

## 4. The YAHA call chain: the native stack may still access state after completion notification

[`NativeHttpHandlerCore.cs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs) initializes RequestContext, allocates the cookie through Allocate and invokes native begin. OnReceive receives borrowed body data, registers a continuation when WriteAsync backpressure has not completed, and returns a native task notification through CompleteTask on completion. OnComplete reads response/error information and completes the managed response; finally releases the RequestContext cookie, then queues Dispose to the managed thread pool. The comments explicitly prohibit releasing these handles directly on the native thread. [R08-S04]

The corresponding [`binding.rs`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs) creates a oneshot for a body frame, invokes managed on_receive and then awaits acknowledgement; failure becomes on_complete Error. At the normal end, after invoking on_complete, it still locks the request and sets `completed=true`. This is a concrete source example of logical terminal notification not meaning that the native call stack has exited. [R08-S05]

This observation **does not establish a UAF in YAHA's current implementation**: its references, scheduling and other context must be considered as a whole. It means NativeWeave cannot treat being queued to the managed thread pool or Task completion as a general proof of quiescence. Thread-pool work may execute before the native callback returns; this project selects explicit try_retire and start/control lease barriers to reduce implicit scheduling assumptions. [R08-D01]

TLS verification is another profile: returning bool requires a synchronous decision, and an ordinary handler exception becomes false. Its lifetime test uses a delayed handshake, Dispose and replacement GCHandle allocation to expose the risk of calling the wrong target; this increment read but did not execute the test. NativeWeave therefore requires decision-callback exceptions to fail closed and includes every potentially throwing conversion/logging/exit action in the boundary policy, rather than wrapping only the user delegate. [R08-T01]

## 5. Managed cancellation registration has its own quiescence conditions

Unregister in [`CancellationTokenRegistration.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs) only attempts to remove the registration; Dispose/DisposeAsync wait for an executing callback when required, with special handling for the current callback itself. The tests that were read use a barrier to block the callback and verify that DisposeAsync does not complete before the callback is allowed to proceed. [R08-S06, T02]

Successful native try_retire therefore cannot replace draining the managed cancellation registration. Cleanup must occur outside native and cancellation callbacks, call DisposeAsync after the registration handle has been published, then wait for the native/control conditions. If DisposeAsync inside a callback waits for that same callback to exit, it waits on itself; synchronous Dispose only marks Closing/requests stopping and returns. If the API exposes DisposeAsync that requires waiting, the same synchronous callback scope must produce an explicit InvalidOperationException or a domain-specified prohibited-usage rule, rather than silently reporting a completed drain. [R08-D02]

## 6. Counterexamples and linearization points that must be testable

Late-cookie counterexample: T1 registers handle H; T2 requests stopping and immediately calls Free(H); T3 allocates a new context that reuses H; an old callback already queued by native code arrives, and `GCHandle.FromIntPtr(H).Target` retrieves the new object. A nonzero/non-null check cannot distinguish identities and may even invoke a different certificate validator. The fix is not to compare objects after dereferencing, but to ensure that H continues to belong to the original context whenever a callback could arrive, and to release it only after new callbacks are permanently forbidden and all in-flight callbacks have exited. [R08-D01]

A second counterexample comes from the [actually executed R09 model](../R09/retirement-result.json): the synchronous terminal callback has returned and native try_retire has succeeded, but the start entry point has not returned. Omitting the start-return lease allows managed code to release the operation while native start still accesses it, producing access_after_free in the model. A third counterexample omits the ordinary control lease and also produces access after release. The model does not simulate malicious native code, incorrect retire, real GC or memory barriers. [R08-M01]

| Action | Linearization point and guarantee |
| --- | --- |
| start commitment | The callback table and cookie have been copied/bound; native code then assumes the terminal/event obligations |
| start rejection | Still Created; no retained work/callbacks; caller may compensate |
| stop request | Atomically marks that no new application work/event sources are accepted, while allowing in-flight work to exit |
| callback admission | Increments the in-flight obligation under the same synchronization protocol that closes the source; a check followed by an unprotected increment is forbidden |
| native try_retire OK | Work and callback obligations are 0, and no future callback can enter; external call frames may still prevent release |
| managed Reclaimed | start has returned, cancellation registration has been drained externally, call/callback counts are 0, result handling has finished, and ownership is returned exactly once |

## 7. Candidates and implementation boundaries

Synchronous drain is simple but readily causes self-wait in reentrant Dispose, thread affinity and executor shutdown, so it cannot define general Dispose semantics. A generation token can detect some reuse errors, but cannot prove that old callbacks no longer execute or borrowed data remains alive. An event queue can isolate user code but adds copying/scheduling and requires reserved capacity; alone, it cannot prove native quiescence. v1 uses asynchronous quiescence and explicit leases, routes ordinary notifications through a bounded coordinator, and retains a very short synchronous return for decision profiles. [R08-D01]

The D05 wire uses a `uintptr_t cookie`, a static Cdecl function pointer, u32 status and a payload borrowed for the call scope; structure sizes follow the D02 target ABI. General notifications do not implicitly transfer owned objects through callbacks; asynchronous results use D06 typed take. Each queued/active task inside Rust must retain a state reference; cleanup outside callbacks checks actual quiescence before releasing the cookie. A GCHandle cookie is not interpreted as a Rust pointer.

## 8. Validation, costs and AOT

Formal tasks A06/A07/A18/A19/A20 cover D05 CB-01–07: synchronous firing during registration, Dispose inside callbacks, exceptions on foreign threads, duplicate notifications, stop/admission races, a paused final callback, GCHandle-reuse negative cases, control calls and start not yet returned, undrained cancellation registration, and module unloading. Profiles requiring immediate decisions validate fail-closed behavior, no synchronous waiting and explicit thread affinity.

Independent cross-review found that native quiescence does not cover handlers already queued to a managed dispatcher. This increment therefore refines D05 with a separate DispatchClosing: explicit Dispose discards pending items and releases their owned data, prevents new handlers from starting, and waits for active asynchronous handlers to actually finish; successful DisposeAsync guarantees that this subscription's handlers are also drained. This addition is a design inference and review revision; the finite R09 model does not simulate the dispatcher, and actual cases remain CB-03/A06/A18 obligations.

Each accepted asynchronous operation reserves a completion/cleanup slot; notifications coalesce, and callbacks do not wait to enqueue. A bounded queue with unbounded payload-holding waiters is prohibited. Measure callback latency, copied bytes, queue length, FFI crossings, cleanup P99, maximum retained bytes and prolonged quiescence stalls. Ordinary synchronous APIs do not need to enable this coordinator.

AOT requires static, nongeneric, exactly blittable UCO signatures; C#/Rust bool does not enter the wire directly. Windows/Linux Native AOT, actual races, GC pressure and fatal subprocesses have not yet been executed. The Python model verifies only an abstract partial order and must not be described as passing UCO or ABI validation. Future GUI/mobile thread affinity is a separate profile and does not require rewriting general stop/retire semantics.

## 9. Conclusions and independent review

Q04's callback reclamation strategy is ready for design-resolved review; production validation remains outstanding. R07 reviews cookie/parent/module lifetimes; R09 reviews synchronous start and managed cancellation-registration barriers; R12 reviews coordinator progress, thread affinity and shutdown; R15 reviews atomic admission and mapping to the actual memory model. Independent reviewers should especially exercise Owner Closing before a terminal result requiring take, Dispose inside callbacks, a never-awaited Task, and draining after poison.

Qt for Python and deeper Godot dispatcher internals remain unread, so the report as a whole remains partially_evidenced. MIT source licenses were read at the pinned SHAs; no upstream tests were run and no long source passages were copied. Follow-up reading should target these concrete evidence gaps; one unread source must not halt other independent design work.

## Current completion review — real reverse callback and managed registration drain

The original callback/source report and finite model are preserved. The new interop-completion fixture now actually invokes static managed UCO from a Rust-created native thread, holds a controlled callback barrier, requests retirement/cancellation concurrently and forces GC. Retirement stays pending while the callback is active; after permanent native completion and all test calls return, the cookie is freed. An ordinary callback mapping exception is caught and recorded before returning across FFI. Thirty-two rounds execute in normal and actual Linux Native AOT modes; raw evidence and precise source/binary hashes are in `verification/interop-completion/linux`.

The same fixture observes an already-cancelled token's UnsafeRegister callback before registration publication and verifies DisposeAsync remains incomplete while another callback runs, then completes after that callback exits. This closes the previously source-only registration-order experiment. It does not claim arbitrary invalid-cookie probing is safe or that a test barrier is appropriate production callback behavior; production callbacks remain short/nonblocking.

New UniFFI scheduler source at `482095c1ba1b76a1393b582e0589e2fdc9c64b14` invokes foreign continuations outside its mutex and stores wake/cancel state when no continuation is installed. Its callback/free semantics are deliberately not substituted for NativeWeave's no-future-callback retirement requirement. The alternative is now source-inspected rather than falsely listed as universally unexamined; exact read limits remain recorded.

D05/D06/D09 provide stable cookie, source closure, native quiet, managed start/control/callback/registration drain and bounded dispatcher rules. Existing Godot/YAHA evidence already suffices to compare ownership hazards; Qt is not an adopted runtime dependency and its broader source audit is outside this selected C# ABI design. Product notification subscriptions, many concurrent operations, allocator failure and two-OS long-load tests remain A06/A07/A20/B17 implementation obligations. Research/design acceptance awaits independent review of this new scope, not completion of the product.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
