# D09 — Engine-local execution, concurrency and shutdown

Contract **C-CONCURRENCY-001@0.4.0**. Complete research/design candidate; the registry records the exact reviewed version/hash and acceptance. Product verification remains in Delivery. R12/R09/R29 provide the research inputs. This specifies A08 and the executor boundaries used by A06/A07/B04/B16/B17/B20. Rust owns the required database/server engines; C# owns business handlers and natural async/await. Core has no mandatory Tokio runtime, scheduler thread, global dispatcher or service container.

## 1. Execution profiles

| Profile | Native engine owner | Managed interface | Typical use |
|---|---|---|---|
| Synchronous | No runtime; current caller thread | Direct borrowed call with D04 lease | Scalar codec, bounded compression, query-builder mutation |
| Engine-local asynchronous | Instance runtime/session owns workers and queues | Task operation via D06; nonblocking callbacks | SQLx and Rust HTTP host |
| Serialized/worker-affine | One native worker or executor owns mutable state | Bounded command admission; result completion | SQLite worker, non-Send connection work |
| External event loop | Declared host thread/loop is authoritative | Explicit dispatch and pump capability | Future GUI/GPU/mobile integration |

An engine chooses only the profile its native implementation needs. Runtime sharing is opt-in composition with one explicit owning instance and compatible shutdown policy; it is not a Core singleton. A Tokio Handle alone does not keep a Runtime alive. Each adapter stores the correct owner reference for as long as its tasks need the runtime, and releases it only after its own task/operation shutdown protocol.

The selected initial Server study composes engine-local Tokio/Hyper/hyper-util/Tower; Axum routing is optional inside that Rust engine. This is not a C#/Rust host choice. A synchronous engine never starts Tokio merely because the package references Core. Thread-affine release goes to the declared owner executor, never directly to an arbitrary SafeHandle finalizer thread.

## 2. Five distinct completion facts

1. **Admission closed:** no new ordinary work may be accepted.
2. **Business terminal:** each accepted operation has one outcome; cancel request does not overwrite it.
3. **Native quiet:** no future callback/input access can start and admitted accesses have ended, according to that operation's native protocol.
4. **Managed drain:** start/setup, callbacks, control leases, registration disposal and dispatcher work have ended.
5. **Released:** all owners whose obligations are satisfied have been dropped. Required OS-worker joins are a separate owned-resource obligation.

HTTP response-head, Body EOS, retained backing allocation, SQL transaction effect and pool reuse each keep their domain rules. A timeout only ends the caller's wait. It does not prove any later item in this sequence.

Tokio 1.54.1 `runtime.rs` at `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` explicitly states that started blocking work continues until it returns; Drop can wait indefinitely; shutdown_timeout/background may return while work/threads continue. Source read ranges 30–96 and 420–525, verified blob `52c06e53a34c1acfb0b1de499d32acf012a684c3`. Therefore these APIs cannot be exposed as proof that all native owners or worker threads have been reclaimed.

## 3. Instance state machine

| State | Ordinary calls | Internal controls | Exit requirement |
|---|---|---|---|
| Created | Configuration only | Initialize bounded resources | All mandatory resources ready or constructor compensation |
| Running | Admit subject to instance budgets | cancel/take/retire/release | Close, poison or external stop |
| Closing | Reject new ordinary calls | Complete accepted work; close sources; drain | All declared obligations satisfied |
| Quarantined | Reject | Only known-safe cleanup and diagnostics | Explicit proof of safe cleanup, or process termination |
| Closed | Reject | Idempotent managed status/close | Final nonblocking owner release |

Running→Closing is linearized under the same admission gate as capacity reservation and ownership lease acquisition. Engine poison independently closes ordinary admission but keeps the trusted cleanup capability available. Constructor failure unwinds only resources actually acquired, in reverse dependency order; no wait on a start/registration that never happened.

## 4. Capacity and progress

Every asynchronous instance declares maximum accepted operations, queued requests, waiting admissions, active streams, payload bytes, retained bytes and cleanup records. Queue count alone does not bound bytes. A command waiting for channel capacity can still retain an input owner; charge it before joining the waiter set. If fairness or ordering is promised, specify which native semaphore/channel mechanism implements it; do not infer it from async syntax.

Reserve cleanup and notification capacity before accepting work. Per-operation completion is a coalescing mailbox, not unbounded event allocation: under one short lock set dirty and schedule the existing slot if not already scheduled; coordinator consumes dirty state and atomically checks for another notification before clearing scheduled. This prevents the wake-between-drain-and-unschedule race. One existing slot is sufficient for idempotent status resampling, not arbitrary loss of data-bearing notifications. Ordered stream chunks require their separate bounded ownership queue.

A failed attempt at try_retire may require bounded retry scheduling even when there will be no new business callback. Retry uses one timer entry per pending operation with bounded backoff; it does not allocate another Task per retry. Busy loops, finalizer blocking and calling Task.Result from native worker callbacks are prohibited. Diagnostics include oldest cleanup age and current stage so a stalled engine can close admission before exhausting the process.

Tokio channel close prevents new ordinary reservations but outstanding Permit/OwnedPermit can still publish. An adapter closes producer admission, accounts for all reservations, and drains or releases each owned permit. Closing the receiver is not equivalent to dropping all retained values or backing buffers. R29's executed source-lifecycle probes are the authority for those examples.

## 5. Locks, calls and reentrancy

No native/managed/user callback, blocking FFI, await or destructor with external effects occurs while holding a shared admission/state mutex. State changes and owner acquisition are short critical sections; use a retained lease or moved command outside the lock. The native adapter's mutable SeaQuery builder has its own single-writer rule, separate from physical lifetime. Reentrant mutation is rejected with a deterministic status; immutable copies may be rendered independently if the engine contract permits.

Never infer Rust Send/Sync from a C opaque pointer. The binding description carries the engine's thread profile. `!Send` resources stay on their owner worker. Cross-thread commands contain owned bounded data and a completion token, not a borrowed pointer to an arbitrary managed stack. Callbacks may arrive on any native worker unless the profile explicitly guarantees otherwise; C# application work is dispatched to the declared managed scheduler.

Cancellation registration can execute synchronously before its returned token is assigned. Setup installs context and control authority first, publishes registration_ready only after registration returns, and drains from outside the callback. The new interop completion fixture actually exercises this .NET path together with native-thread UCO/GC/retirement; it does not claim to implement a full executor.

## 6. Close APIs and resource order

Illustrative managed API:

```csharp
public void Dispose();                     // close admission and request stop; no synchronous drain
public ValueTask DisposeAsync();           // successful completion means declared cleanup completed
public Task<CloseOutcome> CloseAsync(CancellationToken waitCancellation);
```

`CloseOutcome` distinguishes Closed, Pending and Quarantined plus bounded diagnostics. Cancelling CloseAsync cancels that wait only; it never transfers cleanup ownership back to an unrooted local variable. The coordinator remains rooted by the instance until cleanup completes or the process terminates. Synchronous leaf engines can complete disposal immediately.

Close order: close ordinary admission → request per-operation cancellation/shutdown → stop native callback producers and listeners → process terminal/take/error disposition → finish native and managed drains → release buffers/child/session resources → stop and join owned workers according to native semantics → drop runtime instance owner. It is a dependency order, not a claim that every engine needs every step. Child resources which are allowed to outlive the parent wrapper retain an independent parent-state owner until their own closure.

Callback-initiated Dispose requests stop and returns; a self-waiting DisposeAsync is rejected or explicitly routed to a non-self-wait API. No implementation blocks waiting for its own callback/handler to leave. Already accepted result extraction and internal cleanup remain permitted after ordinary admission closes.

## 7. Failure and platform rules

Regular queue/capacity exhaustion is explicit Busy/ResourceLimit before ownership acceptance; no unmanaged allocation occurs first and is then hidden behind an admission error. Accepted work has a unique terminal even on executor shutdown or a declared quarantined failure record. Native panic is contained at the actual task polling/execution boundary where possible, not only at spawn; D08 poisoning and nonrecoverable limits apply.

Windows/Linux initially require real native worker, close/cancel, ordinary app and Native AOT runs; cancellation timing alone is not sufficient evidence. Avoid assuming Linux file-descriptor cancellation equals Windows I/O cancellation. Runtime I/O resources become unusable after runtime shutdown and must not remain exposed as usable managed objects. Future mobile/GUI event-loop profiles require separately measured owner-thread release and suspend/resume behavior under D21.

## 8. Future implementation acceptance

| Obligation | Test oracle | Task |
|---|---|---|
| Bounded admission | Full queue plus blocked producers never exceeds operation/waiter/byte budgets | A08/B04/B16 |
| Callback/control drain | Closed admission with in-flight callback/start/control call never frees context early | A06/A07/A20 |
| No lost wake | Wake before store, during drain and before unschedule leaves a runnable or completed slot | A07/A19 |
| Native executor stop | Blocking job survives short timeout, retained owners remain charged until actual completion | A08/B20 |
| Permit close | Outstanding OwnedPermit after close is drained or released exactly once | B16/B17 |
| Thread affinity | Wrong thread mutation/release rejected; owner worker performs actual destruction | A23/B03 |
| No progress/quarantine | Repeated deadlines do not free resources or leak unbounded coordinator work | A08/B22 |

The protocol and source-derived selection are eligible for acceptance as a research/design contract after independent review. Full production executor implementation, OS-wide thread counts, long soak and performance evidence remain future Delivery obligations; the present prototype does not erase them.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

Every public type declares its concurrency category. Builders are single-threaded snapshots; immutable descriptors/catalog observations may be shared; sessions/transactions/streams/request contexts follow their domain's single-operation and borrow rules. Source/host owners manage independent Engine-local runtimes, and metadata inspection starts none. Loading multiple Engine packages does not authorize a mandatory Core Tokio runtime. A08/A23/B04/B17/B20 must review explicit thread affinity, cancellation/reentrancy and bounded-close behavior along with each public method. No UI/GPU executor API is claimed implemented by the extension template.
