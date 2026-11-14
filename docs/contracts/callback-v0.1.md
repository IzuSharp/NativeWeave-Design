# C-CALLBACK-001: Registration, callback admission, revocation and quiescence

Version: 0.4.0; D05 / R08, R07, R09. Author: interop_design. Status: **Research/design candidate complete; the registry records the exact reviewed version, content hash and acceptance status; product verification remains in Delivery**. This protocol defines the recommended v1 design; code examples are uncompiled design skeletons. Implementation, AOT and cross-platform evidence undergo separate acceptance.

## 1. Problems to solve

A callback may arrive from a foreign thread, occur before registration/start returns, race with cancellation and Dispose, or trigger a managed exception. Successful unregistration, absence of new business events, native code no longer accessing the cookie, and already-entered callbacks having exited are different promises.

v1 separates **requesting stop** from **successful retirement**: requesting stop is non-blocking and reentrant; retirement succeeds only after all relevant access sources have permanently stopped. Unregistration is not implemented by synchronously waiting on a callback thread for that same callback to exit.

## 2. Sources and applicability

[The R08 report](../research/topics/R08/report.md) provides the complete sources. Godot's SignalAwaiter creates a strong GCHandle, which the native one-shot callable holds and releases on destruction; the managed signal callback copies borrowed arguments, handles ordinary exceptions and may execute continuations inline. YAHA's TLS lifecycle tests specifically create a GCHandle-reuse scenario after Dispose. These implementations provide concrete ownership and reentrancy references, but their threading and engine assumptions are not directly adopted by this protocol.

.NET11 CancellationTokenRegistration Dispose/DisposeAsync has an exception to avoid self-waiting in its own callback context; therefore, calling DisposeAsync inside it does not establish that the callback has exited. [D06](async-v0.1.md) requires cleanup to complete through a separate managed coordination path.

## 3. ABI and cookie

D02 and [D08](error-v0.1.md) are authoritative for wire types, status values and ErrorRecord. The generator adds Engine prefixes to the names here; D02's directly versioned exports are the default entry points. Only Engines selecting the optional function-table profile negotiate a function table through their `get_api`; the callback table below is a start-input record and does not require an Engine to export a function table.

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

`NW_CDECL` is the target C calling-convention macro. Pointer and table sizes are computed according to the target ABI; this table must not be hard-coded to the same size on 32/64-bit targets. Native code copies the callback table before start commits and must not retain the address of a table on the managed stack. The payload is borrowed for the current callback scope; its length is D02's fixed u64 byte count, and conversion to the target address range must be checked. The domain contract corresponding to event_kind defines its type and serialization format. Asynchronous consumers must copy before returning; if a domain requires an owned result, the callback only records a notification and ownership is acquired later through D06's one-time typed take. Borrowed pointers must not be retained.

The cookie comes from a Normal strong GCHandle. Native code only returns it unchanged; it must not dereference it, increment it as an integer, or treat it as a security identity or private object information in logs. A nonzero cookie is not a validity check; the normal protocol guarantees that it remains valid throughout all possible callbacks. v1 generic notification payloads are borrowed only; asynchronous operations that need owned results use D06's explicit take_result, without implicit ownership transfer through callback success/failure returns.

## 4. Creation, start and failure atomicity

Successful create returns an owned handle but does not permit callbacks. Managed code then initializes the context, counters, managed delegates/static function pointers and any required cancellation registration before calling start. start commits once after all preparation that can fail has completed:

- Failure before commit: no callback has occurred, been queued or been retained; return failure, and managed code may release resources along the never-started path.
- After commit: return OK even if the business operation immediately fails; failure is expressed through the normal event/terminal channel. A synchronous callback may occur before start returns.
- A sequence where “a callback has occurred, then start returns failure and directs managed code to free through the ownership-not-transferred path” is prohibited because it creates conflicting responsibilities.

v1 does not support replacing an active subscription's cookie or function table. Re-registration creates a new subscription/context, while the old object completes its own retirement protocol, avoiding hot replacement and ABA as burdens on the baseline protocol.

## 5. Native callback admission and stop

Native code has `Created / Active / StopRequested / Retired` states and work/callback obligation counts. Before each callback, the native synchronization protocol must confirm that the callback type is permitted and account for a callback lease; it then leaves the critical section before invoking managed code. The lease is released after the callback returns. request_stop atomically closes production of new ordinary events and cancels/stops sources in flight; it does not mean existing callbacks have returned.

`try_retire` returns only OK or PENDING, except for contract errors such as invalid calls. The OK linearization point must simultaneously close all future callback sources, confirm that callbacks in flight are 0, confirm that native work accessing cookie/payload is 0, and permanently lock the state to Retired. It does not invoke managed code under a lock, wait for external threads or trigger callbacks. PENDING does not write ErrorRecord. Repeated try_retire returns OK; request_stop is idempotently OK after Retired.

release is legal only in Created when start has never been called, or in Retired with no control-call leases. It is a non-blocking ownership release that does not call back. Violating its preconditions is an adapter defect; forced free must not conceal it.

## 6. Managed callback entry and ordinary user code

The native entry point of the default notification profile performs only bounded validation, necessary copying or take-notification recording, state updates and bounded enqueueing. Public Tasks use asynchronous continuations; public events/streams are exposed through a managed dispatcher/IAsyncEnumerable, without running arbitrary business continuations on foreign threads. Queues must bound both item count and bytes, with an explicit overflow policy of backpressure, rejection or domain-permitted dropping; silent unlimited accumulation is prohibited.

Profiles such as TLS verification that must synchronously return a decision permit explicitly registered synchronous managed handlers. Such a profile requires a prompt return, prohibits await/blocking waits for the same Engine to close, and returns a fail-closed decision on exceptions. It cannot automatically inherit the threading or throughput guarantees of ordinary notifications.

A domain public API may return a NativeSubscription implementing IDisposable/IAsyncDisposable or encapsulate it in an IAsyncEnumerable enumerator. The illustrative call below uses uncompiled domain placeholder types and handlers; it is not an already released product API:

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

Repeated Dispose/DisposeAsync returns the same cleanup result and must not free twice. Synchronous Subscribe argument errors may throw synchronously; native start failures are expressed by the corresponding NativeEngineException. Handler failures after successful start must be observable through the domain subscription completion/error channel, rather than silently lost after logging.

UCO entry points use static, non-generic, exactly blittable signatures; bool/char do not enter the wire. Ordinary exceptions are handled inside the entry point, translated to D08 status and recorded as managed failures; fatal errors such as illegal signatures or memory corruption are not advertised as recoverable. The generator must validate the whole function signature, rather than merely adding catch to the method body.

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

This skeleton does not prove that helpers never throw; formal implementation must inspect paths including finally, logging, OOM and queue-scheduling failures. An invalid GCHandle may point to another object or even cause a fatal fault; the catch above must not be treated as a safety solution for late callbacks.

## 7. Reentrancy, closure and cleanup scheduling

Calling Dispose/RequestStop within a callback is permitted: it only closes admission, sets the stop request and schedules cleanup, without waiting for any callback. A native function must not invoke managed code while holding a lock needed for the callback to return; managed admission locks are likewise not held across FFI.

Calling DisposeAsync from the same subscription's callback scope when it would wait for that callback to exit is a usage error. A synchronous callback profile detects and rejects the call using a generated thread-local CallbackScope; a notification dispatcher must also detect it for its own in-flight handlers. If a domain supports asynchronous handlers, the marker propagates with the handler's asynchronous execution context, such as a dedicated AsyncLocal scope; ThreadStatic alone must not be used to guess identity across await. A purely synchronous decision profile does not pay this extra cost. Detection does not promise to identify arbitrary cyclic waits deliberately constructed through SuppressFlow or across threads; documentation and failure tests still prohibit synchronous waits inside a callback for the same resource to drain.

Cleanup executes outside callbacks: send the required stop request and close ordinary managed control-call admission, retaining the coordinator's exclusive lifetime capability; wait until setup is explicitly Settled and the registration outcome is published; in the Registered branch, call CancellationTokenRegistration.DisposeAsync and wait externally for it actually to finish, while the NoRegistration branch does not wait for a registration that was never created; wait for previously acquired control-call leases to reach zero; complete required typed-result ownership acquisition; in the accepted branch, call native try_retire, while the never-started Created branch follows the release rule with no callback obligations; wait for managed callback counts and the dispatcher obligations below to reach zero; release the cookie/borrowed resources/handle. Owner closure does not revoke the coordinator's ability to process existing operations; its native calls must also have returned before final release. No phase holds a business lock across await.

### 7.1 The managed dispatcher is an independent drain dimension

Completion of a native callback does not mean that copied and queued user handlers have finished. A notification subscription additionally has `DispatchOpen / DispatchClosing / DispatchDrained`, pending-item/byte counts and an active-handler count. When the dispatcher starts a handler, it must check DispatchOpen and increment active-handler under the same atomic gate used for closure; no new handler for this subscription may start after the gate closes.

v1 explicit Dispose uses **discard-pending, join-active**: when closing the gate, take all ordinary event items that have not yet executed and return their owned copies/leases and budgets; running handlers are allowed to exit, and an asynchronous handler's count is returned only when its ValueTask actually completes. Native notifications arriving after closure only complete the required copy/ack or discard protocol, without calling the application; terminal/error/credit cleanup messages that must reach the internal coordinator must not be lost. If a domain requires all events to drain before normal stream EOF, it may define a separate drain mode but cannot silently change v1's explicit Dispose semantics.

Successful DisposeAsync simultaneously guarantees native-source quiescence, completion of managed cancellation/control/start cleanup, pending=0 and active-handler=0; no user handler for this subscription starts or continues executing afterward. Wait for active-handler completion outside that handler's own call scope; self-wait detection rules remain unchanged. If a handler hangs permanently, closure must not falsely succeed; retain the context/budget and expose the handler phase and age. Cancellation of the waiter must not force destruction of payloads still in use.

The native decision profile has no independently queued handlers; its user invocation is covered by the native callback count. An ordinary Task's terminal notification does not run a user handler and uses D06's preallocated terminal latch; the subscription dispatcher and Task continuations must not be combined into one count. Background work that users start and detach from a handler is outside the handler scope the framework can join and must not retain an expired borrow.

Each Engine using asynchronous callbacks needs a bounded cleanup-coordination queue; a synchronous Engine does not. Each context has at most one queued cleanup item, and backoff retries are coalesced into one Engine timing source; a new unbounded Task must not be created for each PENDING result. Call-completion and start-return paths may both notify the coordinator, but a notification is not evidence of quiescence; the final decision still queries try_retire. If progress stops, retain ownership, continue charging the existing budget, expose the phase and age, and stop new admission to that Engine; timeouts must not trigger unsafe free.

## 8. Safety properties and liveness assumptions

Required properties: `Retired => future_native_callbacks=0`; `callback_access(cookie) => cookie_live`; `free(cookie) => setup_settled && managed_cancel_drained && control_leases=0 && managed_callbacks=0 && native_retired`; each cookie is freed at most once. Notification subscriptions additionally require `DisposeAsyncSuccess => DispatchDrained && pending=0 && active_handlers=0`; specific NoRegistration/StartSkipped initialization sentinels follow D06, without waiting for steps that were not initiated.

Liveness additionally depends on continued native-executor progress, actual processing of stop requests, a runnable cleanup coordinator and no permanent loss of notifications/retries. Proving the safety condition that counts are 0 does not prove that they eventually reach 0. A malicious late callback is not a recoverable usage error; production adapters must demonstrate through actual tests that they do not produce one.

## 9. Normal operation, failure and version compatibility

Normal path: create→initialize→start→events→request_stop→last callback returns→try_retire OK→managed drain→release. start failure follows the ownership-not-transferred cleanup path; handler exceptions map to failure and stop; Engine poison stops new events but permits terminal/cleanup channels to complete under D08.

Callback tables allow only appended fields and capability negotiation; new callback types must not be invoked unless an old caller has declared support. v1 flags are 0, and nonzero reserved bits are rejected; fields beyond struct_size are not read. Compatibility upgrades must not change the meaning of the cookie or an old event payload layout.

## 10. Verification matrix and Plan inputs

| ID | Required interleaving/fault | Pass condition | Delivery |
| --- | --- | --- | --- |
| CB-01 | Synchronous callback within start; callback completes before start returns | Context remains valid; handle is not released before start returns | A06, A07, A20 |
| CB-02 | Stop races with callback admission; concurrent callbacks from multiple threads | Explicit linearization point, balanced in-flight counts, no callbacks after retirement | A06, A19, A20 |
| CB-03 | Dispose inside callback, nested callbacks, prohibited self-wait, existing managed-queue events/asynchronous handler still in flight | Non-blocking stop; self-wait rejected; no handler starts after gate closure; closure succeeds only after pending items are released and active reaches zero | A06, A18 |
| CB-04 | Synchronous invocation during cancellation registration/self-DisposeAsync exception inside callback | Closure reported complete only after external drain | A07, A19 |
| CB-05 | GCHandle-reuse pressure, late notifications and duplicate terminal states | Normal protocol never invokes the wrong target; invalid negative cases are diagnosable in isolated processes | A20 |
| CB-06 | Non-blittable UCO, throwing callback, diagnostics themselves failing | Analyzer rejects illegal signatures; ordinary exceptions do not cross the ABI; fatal negative cases exit as expected | A12, A14, A15 |
| CB-07 | Long-lived PENDING, full queue, executor stops | No UAF or unlimited enqueueing; budgets and pending age are observable | A08, A21, B22 |

Actual Windows/Linux AOT, CPU architecture, compiler/ABI, raw logs and artifact hashes undergo separate acceptance. Existing Python models and upstream test source cannot replace these records.

## 11. Disposition of design research questions

After independent review, Q04 may close the design question “which callback reclamation protocol to use”: v1 adopts separate stop/retire, explicit leases, external managed cancellation drain and non-blocking cleanup. Verification obligations CB-01–07 and the LT/AS series remain pending in A06/A07/A19/A20 and other assigned tasks. Future engines need implement only their applicable capability profiles; all Engines need not be placed in one global runtime.

## 14. Completion review and scheduling boundaries for this round (2026-11-13)

[The R08 completion report](../research/topics/R08/report.md) retains the existing YAHA/Godot/.NET source chain and adds exact UniFFI scheduler/future source: its external continuations are invoked outside the mutex, and free/cancel may also trigger a stored notification. Therefore, a framework's free operation cannot be directly adopted as NativeWeave's quiet guarantee.

[This round's actual probe](../../verification/interop-completion/linux/result.json) executes 32 controlled native-thread callback/GC/retirement interleavings each in Linux normal and AOT runs; retire remains pending while a callback is in flight, and reclamation is permitted only after it has returned and managed registration has drained. The probe temporarily blocks callbacks to create races; production callbacks must preserve this contract's non-blocking notification behavior and must not copy this test barrier. A synchronous callback inside Register when the cancellation token is already canceled, and DisposeAsync waiting for an in-flight cancellation callback, are also actually executed.

The notification mailbox's dirty and scheduled states must be modified in the same atomic state or under the same short lock. A worker must atomically recheck dirty before clearing scheduled; an old snapshot must not overwrite a new notification. The [negative model](../../verification/interop-completion/mailbox-model.json) found a stale-check lost wakeup; the candidate has no counterexample only within its finite sequentially consistent scope. [D09](concurrency-v0.1.md) is the single authority for complete capacity, retry and closure rules. Acceptance of the research design after independent review does not require A06/A20/B14 to have completed the product dispatcher and long-duration stress tests.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

Ordinary application handlers are managed delegates bound through statically generated domain adapters. Public APIs do not expose GCHandle tokens or require user-supplied unmanaged function pointers. The maintainer SPI cannot revoke a callback by disposing its managed owner while native ingress or accepted callback work remains. Domain operation catalogs bind stable request/operation identifiers, terminal and quiescence notifications, and exact copy/borrow boundaries. A06/A10/A12/B15/B17 must test synchronous completion/reentry and document callback exception conversion; user continuations run outside raw FFI frames.
