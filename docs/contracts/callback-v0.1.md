# C-CALLBACK-001: Registration, callback admission, revocation and quiescence

Version: 0.3.0; D05 / R08, R07, R09. Author: interop_design. Status: **research/design candidate completed; the registry records the exact reviewed version, content hash and acceptance state; product validation remains in the Delivery phase**. This protocol defines the recommended v1 design; code examples are uncompiled design skeletons. Implementation, AOT and cross-platform evidence undergo separate acceptance.

## 1. Problems to resolve

Callbacks may arrive from external threads, occur before registration/start returns, race with cancellation and Dispose, and trigger managed exceptions. Successful deregistration, absence of new business events, native code no longer accessing the cookie, and exit of callbacks that have already entered are different guarantees.

v1 separates **requesting stop** from **successful retirement**: requesting stop is nonblocking and reentrant; retirement succeeds only after all relevant access sources have permanently stopped. Deregistration is not implemented by synchronously waiting for a callback to exit from its own callback thread.

## 2. Sources and scope

The [R08 report](../research/topics/R08/report.md) provides complete sources. Godot's SignalAwaiter creates a strong GCHandle that a native one-shot callable holds and releases on destruction; the managed signal callback copies borrowed arguments, handles ordinary exceptions and may execute continuations inline. YAHA's TLS lifetime tests deliberately create GCHandle reuse after Dispose. These implementations provide concrete references for ownership and reentrancy, but their threading and engine assumptions do not directly become part of this protocol.

.NET 11 CancellationTokenRegistration Dispose/DisposeAsync has an exception in its own callback context to avoid self-waiting, so calling DisposeAsync from inside that context does not establish that the callback has exited. [D06](async-v0.1.md) requires cleanup through an independent managed coordination path.

## 3. ABI and cookie

D02 and [D08](error-v0.1.md) are authoritative for wire types, status values and ErrorRecord, respectively. The generator prefixes names here with the Engine name; D02's directly versioned exports are the default entry points. Only Engines choosing the optional function-table profile negotiate a function table through their `get_api`; the callback table below is a start-input record and does not require an Engine to export a function table.

```c
typedef struct nw_subscription nw_subscription;
typedef uint32_t (NW_CDECL *nw_on_event_fn)(
    uintptr_t cookie, uint32_t event_kind,
    const void *payload, uint64_t payload_bytes);

typedef struct nw_callbacks_v1 {
    uint32_t struct_size;
    uint32_t flags;                 /* v1 reserved: 0 */
    uintptr_t cookie;               /* opaque managed token */
    nw_on_event_fn on_event;
} nw_callbacks_v1;

uint32_t NW_CDECL nw_subscription_create(
    nw_engine *, nw_subscription **out_subscription, nw_error_info_v1 *);
uint32_t NW_CDECL nw_subscription_start(
    nw_subscription *, const nw_callbacks_v1 *, nw_error_info_v1 *);
uint32_t NW_CDECL nw_subscription_request_stop(nw_subscription *);
uint32_t NW_CDECL nw_subscription_try_retire(nw_subscription *);
void NW_CDECL nw_subscription_release(nw_subscription *);
```

`NW_CDECL` is the target C calling-convention macro. Pointer and table sizes follow the target ABI; do not hardcode the same table size for 32/64-bit targets. Native code copies the callback table before start commits; it must not retain the address of a table on the managed stack. The payload is borrowed for the current callback scope, with a fixed u64 byte count under D02; conversion to the target address range must be checked. The domain contract corresponding to event_kind defines its type and serialization schema. Asynchronous consumers must copy it before returning; if the domain needs an owned result, the callback only records a notification, and ownership is taken later through D06's one-time typed take, without retaining the borrowed pointer.

The cookie comes from a Normal strong GCHandle. Native code only returns it unchanged: it does not dereference it, increment it as an integer, use it as a security identity or log it as private object information. A nonzero cookie does not validate it; the normal protocol guarantees its validity throughout all possible callbacks. The general v1 notification payload is borrowed only; asynchronous operations requiring owned results use D06's explicit take_result rather than implicitly transferring ownership in callback success/failure returns.

## 4. Creation, start and failure atomicity

A successful create returns an owned handle but does not permit callbacks. Managed code then initializes the context, counters, managed delegates/static function pointers and any required cancellation registration before calling start. start performs one commit after all fallible preparation has completed:

- Failure before commit: no callback has occurred, been queued or been retained; failure is returned, and managed code may release through the never-started resource path.
- After commit: return OK even if the business operation fails immediately; failure is conveyed through the normal event/terminal-state channel. A synchronous callback may occur before start returns.
- The conflicting responsibilities of “a callback has already occurred, but start then returns failure and causes managed code to free through the path for ownership not taken over” are not allowed.

v1 does not support replacing the cookie or function table of an active subscription. Re-registration creates a new subscription/context, and the old object ends through its own retirement protocol; hot replacement and ABA do not become burdens of the base protocol.

## 5. Native callback admission and stop

Native code has `Created / Active / StopRequested / Retired` states and work/callback obligation counts. Before each callback, it must confirm under the native synchronization protocol that this callback class is permitted and account for a callback lease, then leave the critical section before invoking managed code. The lease is released after the callback returns. request_stop atomically closes production of new ordinary events and cancels/stops in-flight sources; it does not mean existing callbacks have returned.

`try_retire` returns only OK or PENDING, apart from contract errors such as invalid calls. At the OK linearization point it must simultaneously close all future callback sources, confirm that in-flight callbacks are 0, confirm that native work accessing cookie/payload is 0, and permanently lock in Retired. It does not call managed code under a lock, wait for external threads or trigger callbacks. PENDING does not write ErrorRecord. Repeated try_retire returns OK; after Retired, request_stop is idempotent OK.

release is legal only in Created with start never called, or in Retired with no control-call leases. It is a nonblocking ownership release that does not invoke callbacks. Violating these preconditions is an adapter defect and must not be concealed by forcing a free.

## 6. Managed callback entry points and ordinary user code

The native entry point of the default notification profile performs only bounded validation, necessary copying or registration of a take notification, state updates and bounded enqueueing. Public Tasks use asynchronous continuations; public events/streams are provided by a managed dispatcher/IAsyncEnumerable, without running arbitrary business continuations on foreign threads. Queues must bound both item counts and bytes, with an explicit overflow policy of backpressure, rejection or domain-permitted dropping; silent unbounded accumulation is prohibited.

Profiles that must return a decision synchronously, such as TLS validation, permit explicitly registered synchronous managed handlers. Such a profile requires a prompt return and prohibits await or blocking while waiting for the same Engine to close; exceptions return a fail-closed decision. It does not automatically inherit the threading or throughput guarantees of ordinary notifications.

A domain's public API may return a NativeSubscription implementing IDisposable/IAsyncDisposable, or wrap it in an IAsyncEnumerable enumerator. The following illustrates a call; the types and handler are uncompiled domain placeholders, not already published product APIs:

```csharp
await using var subscription = engine.Subscribe(HandleEvent, cancellationToken);
try
{
    await RunApplicationWorkAsync(cancellationToken);
}
finally
{
    subscription.Dispose(); // close admission and request stop; does not wait
    await subscription.DisposeAsync(); // outside the handler; wait for cleanup
}
```

Repeated Dispose/DisposeAsync returns the same cleanup result and must not free twice. Invalid synchronous Subscribe arguments may throw synchronously; native-start failure is represented by the corresponding NativeEngineException. Handler failures after a successful start are observable through the domain subscription completion/error channel and must not be silently lost after only being logged.

UCO entry points use static, nongeneric, exactly blittable signatures; bool/char do not enter the wire format. Ordinary exceptions are handled inside the entry point, converted to D08 statuses and recorded as managed failures; fatal errors such as invalid signatures and memory corruption are not advertised as recoverable. The generator must validate the entire function signature rather than merely add a catch in the method body.

```csharp
[UnmanagedCallersOnly(CallConvs = [typeof(CallConvCdecl)])]
private static unsafe uint OnEvent(
    nuint cookie, uint kind, void* payload, ulong bytes)
{
    // Design skeleton: all helpers must have tested non-throwing exit paths.
    CallbackState? state = null;
    bool entered = false;
    try
    {
        state = (CallbackState?)GCHandle.FromIntPtr((nint)cookie).Target;
        if (state is null) return NativeStatus.ContractViolation;
        state.EnterNativeCallback();
        entered = true;
        return state.CopyOrRecordAndEnqueue(kind, payload, bytes);
    }
    catch (Exception error)
    {
        return state is null
            ? NativeStatus.ContractViolation
            : state.RecordCallbackFailureWithoutThrowing(error);
    }
    finally
    {
        if (entered) state!.ExitNativeCallbackWithoutThrowing();
    }
}
```

This skeleton does not prove that helpers never throw; the formal implementation must inspect paths including finally, logging, OOM and queue-scheduling failures. An invalid GCHandle may point to another object or even cause a fatal failure; the catch above cannot serve as a safety strategy for late callbacks.

## 7. Reentrancy, shutdown and cleanup scheduling

Calling Dispose/RequestStop inside a callback is permitted: it only closes admission, sets the stop request and schedules cleanup, without waiting for any callback. A native function must not call managed code while holding a lock required for the callback to return; the managed admission lock is likewise not held across FFI.

Calling DisposeAsync within the same subscription's callback scope when it would wait for that scope itself to exit is a usage error. The synchronous callback profile detects and rejects this call through a generated thread-local CallbackScope; the notification dispatcher must likewise detect it for its own in-flight handlers. If a domain supports asynchronous handlers, the marker propagates with the handler's asynchronous execution context, for example through a dedicated AsyncLocal scope; ThreadStatic alone cannot infer identity across await. The purely synchronous decision profile does not pay this additional cost. Detection does not promise to find arbitrary circular waits constructed through deliberate user SuppressFlow or across threads; documentation and failure tests still prohibit synchronously waiting inside a callback for the same resource to drain.

Cleanup executes outside callbacks: send any necessary stop and close admission to ordinary managed control calls while retaining the coordinator's exclusive lifetime capability; wait until setup is explicitly Settled and the registration result is published; the Registered branch calls CancellationTokenRegistration.DisposeAsync and waits externally for its actual completion, while NoRegistration does not wait for a registration that was never created; wait for acquired control-call leases to reach zero; complete any necessary typed-result takeover; the accepted branch calls native try_retire, while the never-started Created branch follows release rules with no callback obligations; wait for the managed callback count and the dispatcher obligations below to reach zero; release the cookie, borrowed resources and handle. Owner closure does not revoke the coordinator's ability to process existing operations; all of its native calls must also return before final release. No phase holds a business lock across await.

### 7.1 The managed dispatcher is a separate drain dimension

A native callback ending does not mean a user handler already copied and queued has ended. A notification subscription additionally has `DispatchOpen / DispatchClosing / DispatchDrained`, pending item/byte counts and an active-handler count. When the dispatcher begins a handler, it must check DispatchOpen and increment active-handler under the same atomic gate used by shutdown; after the gate closes, it must not start another handler for this subscription.

Explicit Dispose in v1 uses **discard-pending, join-active**: closing the gate removes all ordinary event entries not yet executed, returning their owned copies/leases and budget; handlers already executing may exit, and an asynchronous handler's count is returned only when its ValueTask actually completes. Native notifications arriving after the gate has closed only complete the required copy/ack or discard protocol and do not call the application; terminal/error/credit cleanup messages that must reach the internal coordinator must not be lost. A domain requiring all events to drain before normal stream EOF may define a separate drain mode, but must not silently change the v1 semantics of explicit Dispose.

Successful DisposeAsync simultaneously guarantees native-source quiescence, completion of managed cancellation/control/start cleanup, pending=0 and active-handler=0; thereafter no user handler for this subscription starts or continues executing. Waiting for active-handler completion occurs outside its own invocation scope; the self-wait detection rules remain unchanged. If a handler hangs permanently, shutdown must not falsely succeed: retain the context/budget and expose the handler phase and age; cancellation of the waiter does not forcibly destroy a payload still in use.

The native decision profile has no separately queued handler; its user invocation is covered by the native callback count. Terminal notification of an ordinary Task does not run a user handler and uses D06's preallocated terminal latch; the subscription dispatcher and Task continuations must not be conflated into one count. Background work that users start themselves and detach from a handler lies outside the handler scope that the framework can join, and must not retain an expired borrow.

Each Engine using asynchronous callbacks needs a bounded cleanup-coordination queue; synchronous Engines do not. Each context has at most one queued cleanup item, and backoff retries are coalesced into one timer source per Engine; an unbounded Task must not be created for every PENDING. Both call-completion paths and start-return paths may notify the coordinator, but a notification is not evidence of quiescence; try_retire is still queried ultimately. If progress stops, retain ownership, continue charging the existing budget, expose phase and age, and stop new admission to that Engine; timeouts must not trigger unsafe free.

## 8. Safety properties and liveness assumptions

Required properties: `Retired => future_native_callbacks=0`; `callback_access(cookie) => cookie_live`; `free(cookie) => setup_settled && managed_cancel_drained && control_leases=0 && managed_callbacks=0 && native_retired`; each cookie is released at most once. Notification subscriptions additionally require `DisposeAsyncSuccess => DispatchDrained && pending=0 && active_handlers=0`; the specific NoRegistration/StartSkipped initialization sentinels follow D06, without waiting for steps never initiated.

Liveness additionally depends on the native executor continuing to make progress, stop requests actually being processed, the cleanup coordinator being runnable, and notifications/retries not being permanently lost. Proving only the safety condition that counts are 0 does not prove they will eventually reach 0. A malicious late callback is not a recoverable usage error; production adapters must demonstrate through actual tests that they do not produce one.

## 9. Normal operation, failure and version compatibility

Normal: create→initialize→start→events→request_stop→last callback returns→try_retire OK→managed drain→release. start failure follows cleanup for ownership not taken over; a handler exception maps to failure and stop; Engine poison stops new events but allows terminal/cleanup channels to complete under D08.

The callback table permits only appended fields and capability negotiation; new callback types must not be invoked unless an old caller has declared support. v1 flags are 0, and nonzero reserved bits are rejected; fields beyond struct_size are not read. A compatible upgrade must not change the meaning of the cookie or the layout of an old event payload.

## 10. Verification matrix and Plan inputs

| ID | Required interleaving/failure | Pass criterion | Delivery |
| --- | --- | --- | --- |
| CB-01 | Synchronous callback inside start; callback completes before start returns | Context remains valid; handle is not released before start returns | A06, A07, A20 |
| CB-02 | stop races with callback admission; concurrent callbacks on multiple threads | Explicit linearization point, all in-flight counts balanced, no callbacks after retirement | A06, A19, A20 |
| CB-03 | Dispose inside a callback, nested callbacks, prohibited self-wait, events already in the managed queue/asynchronous handlers still in flight | Nonblocking stop; reject self-wait; no new handler starts after gate closure; shutdown succeeds only after pending entries are released and active reaches zero | A06, A18 |
| CB-04 | Synchronous cancellation-registration invocation/self-DisposeAsync exception inside the callback | Report shutdown complete only after external drain | A07, A19 |
| CB-05 | GCHandle reuse pressure, late notifications and duplicate terminal states | No invocation of the wrong target under the normal protocol; violating negative cases are diagnosable in isolated processes | A20 |
| CB-06 | Nonblittable UCO, callback throws, diagnostics themselves fail | Analyzer rejects invalid signatures; ordinary exceptions do not cross the ABI; fatal negative cases exit as expected | A12, A14, A15 |
| CB-07 | PENDING persists indefinitely, queue full, executor stopped | No UAF or unbounded enqueueing; budgets and pending age are observable | A08, A21, B22 |

Actual Windows/Linux AOT, CPU architecture, compiler/ABI, raw logs and artifact hashes undergo separate acceptance. Neither existing Python models nor upstream test source can replace these records.

## 11. Disposition of design research questions

After independent review, Q04 may close the design question of “which callback reclamation protocol to use”: v1 uses separate stop/retire, explicit leases, external managed cancellation drain and nonblocking cleanup. Verification obligations CB-01–07 and the LT/AS series remain pending in tasks such as A06/A07/A19/A20. Future engines need only implement the corresponding capability profile; all Engines need not share one global runtime.

## 14. Completion recheck and scheduling boundaries (2026-11-13)

The [R08 completion report](../research/topics/R08/report.md) retains the existing YAHA/Godot/.NET source chain and adds exact UniFFI scheduler/future source: its external continuations are invoked outside the mutex, and free/cancel may also trigger a saved notification, so a framework's free cannot be directly adopted as NativeWeave's quiet guarantee.

The [actual probe in this completion round](../../verification/interop-completion/linux/result.json) executes 32 controlled native-thread callback/GC/retirement interleavings in each of Linux normal and AOT execution; retire remains pending while a callback is in flight, and reclamation is permitted only after it has returned and managed registrations have drained. The probe temporarily blocks the callback to construct the race; production callbacks must retain this contract's nonblocking notification behavior and must not copy this test barrier. Synchronous callbacks inside Register when the cancellation token is already cancelled, and DisposeAsync waiting for an in-flight cancellation callback, were also actually executed.

The notification mailbox's dirty and scheduled states must be modified in the same atomic state or under the same short lock. Before clearing scheduled, a worker must atomically recheck dirty; an old snapshot must not overwrite a new notification. The [negative model](../../verification/interop-completion/mailbox-model.json) found a stale-check lost wakeup; the candidate has no counterexample only within its finite sequentially consistent scope. [D09](concurrency-v0.1.md) is the single authority for the complete capacity, retry and shutdown rules. Independent review and acceptance of the research design do not require A06/A20/B14 to have completed the product dispatcher and long-running stress tests.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
