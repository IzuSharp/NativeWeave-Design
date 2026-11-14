# R09: Asynchronous Results, Cancellation, Callbacks, and Resource Retirement

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; finite model executed; independent review pending**. The research output is [D06](../../../contracts/async-v0.1.md), also constraining D04/D05. Ordinary Task completion, native quiescence, verification of an actual implementation, and production acceptance are distinct facts.

## 1. Inputs, Goals, and Non-Goals

Pinned Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`, Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R09 task packet revision `0.1.1`, SHA256 `b695871a811c8d556edf74d8f75a2f2997bbb808286ae2abea49bd2db45d6afd`; D06 revision `0.1.1`, hash `0d6f8c06dbccf3fbd2a7a391addc203f797a003ede9bbf4b38edd68483917102`. The pinned remote graph and actual task packet bytes have been checked.

The goal is a natural Task/async/await and CancellationToken experience, explicitly handling synchronous completion, synchronous execution during cancellation registration, duplicate terminal states, late cancellation, result-owner transfer, reentrant Dispose, and stalled cleanup. Ordinary application developers do not write Rust. Synchronous Engines are not forced into a general asynchronous runtime; database commit effects are not replaced by Task cancellation status.

This round does not implement the entire framework, depend on preview runtime async, or pool contexts or IValueTaskSource. Actual .NET/Rust concurrency, weak-memory behavior, and Native AOT have not yet been executed.

## 2. v1 Design Decisions

1. Separate create from start; context and registration state become available before native code can take over.
2. Native code uniquely commits the business terminal state of an accepted operation; cancel only records a request and cannot immediately change the Task to Canceled.
3. Ordinary APIs return Task<T>, with TCS using RunContinuationsAsynchronously; multiple awaits have natural semantics, and allocation costs are explicitly accounted for.
4. The terminal callback only copies fixed status/error information; outside the callback, the completion coordinator invokes typed take_result once, with explicit failure atomicity and owner transfer.
5. Native try_retire proves only that native work and callbacks no longer access state; final release additionally requires start to have returned, cancellation registration to have drained externally, and managed callback and control-call counts to reach zero.
6. Per-operation quota is reserved before native acceptance; the operation is cleaned up automatically even if its Task is never awaited; result owners and active operations are accounted for separately. [R09-D01]

These are directly implementable recommended choices awaiting independent review, rather than leaving every option proposed in place of making decisions. Subsequent performance evidence may trigger local evolution without weakening current safety invariants.

## 3. Pinned Source and Coverage

| Source | SHA | Mechanisms read |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenSource.Register, CancellationTokenRegistration, TaskCompletionSource<T>, Task completion and continuation scheduling, cancellation tests |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | managed begin/callback/Dispose, Rust spawn/select/oneshot/complete/abort |
| Finite model in this repository | File SHA256 `016760cddb78698827bccc472a2d653cba55e20ba15c61c3480a3faea559cd1f` | Added setup/start/control/registration retirement partial orders and three negative controls |

Itemized source evidence and blobs are in [evidence.json](evidence.json); [coverage.json](coverage.json) explicitly identifies the complete Task scheduler, ManualResetValueTaskSourceCore, Tokio internal wakers, and UniFFI async bridge as unread. Tokio and UniFFI remain future supplementary evidence for comparing alternative implementations; reading Tokio call sites in YAHA is not described as reading the complete Tokio implementation.

## 4. .NET Cancellation Chain: The Callback Can Precede Registration Assignment

[`CancellationTokenSource.Register`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenSource.cs#L586-L687) first attempts to register a callback node and then must still handle a race with cancellation state; if already canceled, it may invoke the callback synchronously before returning the registration. This is not confined to exceptional paths; NativeWeave cannot treat obtaining the returned registration as the earliest possible callback execution point. [R09-S01]

Therefore context, handle, fixed counters, and cancel_requested must be initialized before UnsafeRegister. A setup lease retains the context; the callback may record cancellation and use a control lease to call request_cancel, which is allowed in Created state. registration_ready is published only after Register returns. If start has not yet occurred and cancellation has been observed, start can then be skipped safely; otherwise, after start commits, the native terminal state determines the result.

[`CancellationTokenRegistration.DisposeAsync`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs#L32-L110) waits, when necessary, for a callback executing on another thread; Unregister itself only attempts removal. The [tests](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Threading.Tasks.Tests/CancellationTokenTests.cs#L1560-L1745) read use synchronization barriers to demonstrate the design intent: the DisposeAsync result remains incomplete until the callback exits, and UnsafeRegister ExecutionContext behavior is covered. The tests were not executed. [R09-S02, T01]

NativeWeave's internal cancellation handler does not need to capture the caller's ExecutionContext and uses static UnsafeRegister; normal Task mechanisms maintain the application continuation's ExecutionContext. A domain callback requiring a particular context must opt in explicitly, rather than accidentally propagating internal thread context to users.

## 5. Task Chain: Asynchronous Continuations Are Not a Reclamation Barrier

[`TaskCompletionSource_T.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/TaskCompletionSource_T.cs) passes creation options to Task, and TrySetResult/TrySetCanceled enter Task state transitions; competing completion may also wait for another completion process to finish. It manages application results without knowledge of native handle, cookie, or pin lifetimes. [R09-S03]

[`Task.FinishContinuations`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/Task.cs#L3570-L3715) exchanges the completion sentinel and chooses whether to inline based on RunContinuationsAsynchronously and other flags. That option prevents the current completing thread from inlining application continuations, but cannot prevent another thread from starting before the native callback returns. It therefore does not establish that release after queueing to the thread pool is always safe. [R09-S04, D01]

We do not bind Task.TrySetCanceled and Token.IsCancellationRequested to immediate release: a database write may already have been accepted or a server response already sent, and cancellation is merely a racing request. Success may legitimately win a race with cancellation; TIMEOUT must not be overwritten as Canceled either. The error domain must separately record knowledge states such as Effect=Unknown.

## 6. YAHA Chain and the End of Borrowed-Data Lifetimes

Managed code initializes RequestContext and allocates a cookie before calling [`yaha_request_begin`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs#L483-L725). Rust retains Arc request state and spawns asynchronous work, selecting between cancellation and the request; each body frame first calls managed on_receive and then awaits a oneshot acknowledgment. Managed [`OnReceive/CompleteTask`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L464-L625) returns backpressure completion/failure to native code. [R09-S05, S06]

Rust still sets completed state after the normal on_complete call; receiving completion at the application layer therefore does not imply that the calling native frame no longer accesses the object. RequestContext also has separate GCHandle release, native-handle release, and finalizer policies; NativeWeave reuses only the idea of separating these obligations, not a strategy dependent on host-specific finalizer blocking.

This round did not fully audit YAHA ResponseContext, Tokio internals, or all memory borrowing, so it does not declare all buffer lifetimes correct based on local call sites. Our general v1 further tightens the rules: callbacks only copy borrowed data, and owned results use a separate typed take; Server chunk streams are further specified by their credit/ack protocol.

## 7. Exact Partial Order of Start, Results, and Shutdown

D06 requires quota and owner wrappers to be reserved first; after successful create, context/TCS/GCHandle are initialized, followed by cancellation registration. A rejected start must leave no work or callback; once start takes over, it returns OK whether business completion is synchronously successful or failed, and reports the business result through the unique terminal notification. The start-call lease remains valid until native return.

Recording a terminal state runs no user code. The completion coordinator prepares managed result wrappers and budgets in advance and calls take using an internal lifetime capability; on OK, native code zeros the corresponding owner, while failure leaves the output empty and native code still owning it. A second take returns INVALID_STATE. Operation release handles an untaken result. Owner Closing must not block internal take/retire for an accepted operation; it closes only ordinary external admission, and the coordinator is the sole final reclaimer.

Cleanup completion requires all of the following: registration has been published and external DisposeAsync has completed; start has returned; ordinary control leases are 0; native try_retire returns OK; managed callback count is 0; the result has been published or failure handled; and all coordinator native calls have returned. Only then may the GCHandle be freed and input leases and the operation owner released. Native Retired and result Taken are orthogonal states: take remains possible after retirement and before release.

All terminal states, Owner closure, and timeout waits coalesce into the existing cleanup slot. Discarding a Task does not prevent automatic operation cleanup; however, an application retaining or ignoring a returned OwnedResult still has its Dispose/final-release responsibility, and automatic revocation of the user's result ownership must not be claimed. [R09-D01]

Independent cross-review completed two failure paths. D06's stage-by-stage compensation table explicitly distinguishes NoRegistration, StartSkipped/Rejected/AcceptedReturned, and Indeterminate: roll back directly before a complete context exists; do not wait for events that can never occur for steps not initiated; quarantine uncertain takeover rather than assuming safety. An ordinary terminal-callback failure uses a preallocated binding-failure latch, and finally still wakes the existing slot; managed state becomes Faulted while native state/effect is retained, without requiring native code to violate unique completion by emitting another Failure. These are design revisions; the current model does not cover every initialization failure or latch fault, and AS-02/03 and formal fault injection remain pending.

## 8. Finite Model Actually Executed in This Round

The execution command from the Design repository root is:

```sh
python3 docs/research/topics/R09/retirement_model.py
```

The actual environment was Python 3.12.14 on Linux x86_64, with exit code 0. The code [retirement_model.py](retirement_model.py), original [stdout](model-stdout.txt), [stderr](model-stderr.txt), [results](retirement-result.json), and [run record](model-run.json) with times, command, and hashes are all retained. The model ran before its first Git commit; the run explicitly records `source_commit=null`, the baseline commit, and exact model SHA256. It does not invent an old commit containing new code or present a research run as a product acceptance manifest.

| Model | Reachable states | Explored transitions | Checked counterexamples | Reclaimed states without checked violations |
| --- | ---: | ---: | --- | ---: |
| All guards | 541 | 1552 | None | 8 |
| Remove start-return guard | 549 | 1560 | access_after_free | 12 |
| Remove control-lease guard | 553 | 1568 | access_after_free | 16 |
| Remove registration-drain guard | 565 | 1576 | cleanup_success_without_managed_registration_drain | 8 |

Breadth-first traversal is used, stopping each branch at its first checked violation. The positive case checks access after release, duplicate Task publication, duplicate free, and declared cleanup success without registration drain. The results list all shortest counterexample traces. [R09-M01]

The start negative trace is: registration completes→enter start→commit→native terminal callback enters/notifies/returns→managed code publishes Task→close admission→drain cancellation registration→native retirement→reclaim→start frame continues accessing state and returns. The control negative trace is: a valid control call acquires a lease→cleanup ignores the lease and frees early→that call accesses the operation. Both show that native quiescence does not cover stack frames of calls actively made by managed code.

The registration negative trace is: cancellation callback enters→cancellation path without starting→native code can retire→DisposeAsync is declared successful if managed drain is skipped. **This proves violation of the cleanup contract, not automatically a native UAF**: the cancellation delegate still holds managed state, and the atomic admission gate can prevent a late native call. The report retains this distinction to avoid overstating the negative case.

### Exact Model Assumptions and Limitations

Only one operation, one native terminal callback, one cancellation registration/invocation, and one optional ordinary control call are modeled; each step is atomic and sequentially consistent. The model trusts that rejected start leaves no obligations, terminal-state commitment is correct, native retirement truly closes future callbacks, and lease admission is atomic. It does not prove implementations of these conditions themselves.

It does not prove liveness, fairness, shutdown deadlock freedom, weak-memory behavior, actual GCHandle/FFI/AOT, multiple operations or callbacks, pooling/ABA, counter overflow, result-owner transfer, pinning, OOM, or panic behavior. The candidate's 8 successful reclamation states only rule out a vacuous positive case in which reclamation is wholly impossible; they do not prove eventual reclamation under all schedules. Correct commitment of a unique terminal state is abstracted as a protocol event; duplicate malicious notifications still require actual fault injection.

## 9. Candidate Comparison and Costs

| Choice | Correctness and experience | Cost and decision |
| --- | --- | --- |
| TaskCompletionSource | Natural multiple-await semantics, clear terminal-state publication | Per-operation allocation; adopted in v1 |
| pooled IValueTaskSource | May reduce some allocations | Complex token/version, reuse, invalid await, and late-callback handling; no current evidence of benefits, so not the default |
| callback push | Direct readiness notification | Requires cookie quiescence; this round uses a fixed notification plus separate retire |
| poll/wake ABI | May unify execution control on the caller side | Waker registration, lost wakes, fairness, and extra polling still need a protocol; retained as a future evidence-driven profile |
| Start and deliver a handle in one FFI call | Saves one call | Synchronous callback before managed-handle initialization requires a more complex protocol; v1 uses two phases |

Cost accounting must include create/start/take/retire/release FFI, GCHandle, context/TCS, input copies/pins, scheduling queues, native references, and unretired bytes; statistics cannot be limited to business Task duration. High-frequency short work should first use synchronous/bulk APIs; introduce pooling only when complete workloads demonstrate benefits.

## 10. Validation Tasks, Open Items, and Closure Scope

D06 AS-01–08 cover synchronous cancellation during registration, rejected start/synchronous completion, terminal-state races, in-flight leases, single take/result-conversion failure, coordinator saturation/lack of progress, multiple awaits/ExecutionContext, and Windows/Linux AOT with long workloads, respectively; they map to A04/A07/A08/A14/A15/A18/A19/A20/A21/B22. Implementation must map state-machine actions individually to actual CAS/lock/acquire-release semantics, using scheduling/property/fuzzing tools appropriate to the target rather than merely listing Loom/Coyote names.

Q05 now has an explicit Task choice and no default pooling; Q04 has a resource-retirement partial order and reproducible experiment, allowing closure of the design-research questions after independent review. Further evidence from R12 executors, R10 Buffer, and R15 weak memory stays within each topic's scope; this round need not implement every platform before recording that a design question is resolved. Tokio/UniFFI and ValueTaskSource internals are unread, so the research task overall remains partially_evidenced; a complete async-ecosystem survey must not be marked finished.

Independent review should especially check: Owner closing before terminal/take, Tasks never awaited, registration callbacks before assignment, lost wakes when PENDING notifications coalesce, quotas and diagnostics when quiescence never occurs, and database cancellation with unknown effects. The pinned dotnet/runtime and YAHA licenses were both read and are MIT; this report copies no large source passages.

## Current completion review — source alternatives, real take-once and notification progress

The existing retirement model and its541-state result remain historical evidence. This increment actually executes synchronous/native-worker terminals, precancel and late cancel, duplicate completion rejection, once-only result take, result survival after operation release and DTO-conversion cleanup. Thirty-two controlled callback/GC rounds plus managed registration barriers execute normally and as Linux Native AOT. It is a bounded research operation, not the full future A07 coordinator. Exact evidence is `verification/interop-completion/linux/result.json`.

Previously unread alternative mechanisms are now inspected. .NET11 ManualResetValueTaskSourceCore has a short version and requires the outer owner to prevent access across Reset; version checks and single-continuation enforcement do not make a native cookie safely reusable. UniFFI's actual WrappedFuture separates poll, complete and free; its scheduler handles wake-before-store and calls callbacks outside the internal mutex. Its Arc-backed RawWaker retains future state. These mechanisms support keeping ordinary Task/TCS as the simple initial C# contract and deferring pooling until workload evidence justifies the additional ABA/reset/await rules.

The new finite mailbox model supplies a concrete lost-notification counterexample: worker reads no dirty work, notification marks dirty while scheduled remains true, worker clears scheduled using the stale read. Atomic dirty recheck/unschedule removes that counterexample in the declared finite SC model; exact negative17/candidate11 states and source hash are preserved. D09 specifies the matching bounded mailbox and pending-retirement retry rule; it does not claim a weak-memory proof.

The old preview-only Runtime Async statement is historical and superseded by R01/D01's current .NET11 check. This bridge uses ordinary Task and does not require a runtime-async-specific ABI. Current source/design questions are resolved with the above evidence. Independent review remains required; full setup-allocation compensation, poisoned-worker recovery, multi-operation saturation, every target and production weak-memory/load behavior remain explicit A07/A08/A19/A20/B22 obligations.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
