# R09: Asynchronous results, cancellation, callbacks and resource retirement

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; finite model executed; independent review pending**. The research output is [D06](../../../contracts/async-v0.1.md), which also constrains D04/D05. Ordinary Task completion, native quiescence, actual implementation validation and production acceptance are distinct facts.

## 1. Inputs, goals and non-goals

Pinned Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`, Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R09 packet revision `0.1.1`, SHA256 `b695871a811c8d556edf74d8f75a2f2997bbb808286ae2abea49bd2db45d6afd`; D06 revision `0.1.1`, hash `0d6f8c06dbccf3fbd2a7a391addc203f797a003ede9bbf4b38edd68483917102`. The pinned remote graph and actual packet bytes have been checked.

The goal is a natural Task/async/await and CancellationToken experience with explicit handling of synchronous completion, synchronous cancellation-registration execution, duplicate terminal states, late cancellation, result ownership transfer, Dispose reentrancy and lack of cleanup progress. Ordinary application developers do not write Rust. Synchronous Engines are not forced into a general asynchronous runtime; a Task's cancellation state does not replace knowledge of database commit effects.

This increment does not implement the entire framework, depend on preview runtime async, or pool contexts or IValueTaskSource. Actual .NET/Rust concurrency, weak memory and Native AOT have not yet been executed.

## 2. v1 design decisions

1. Separate create and start; make the context and registration state available before allowing native code to take over.
2. Native code alone commits the application terminal state of an accepted operation; cancel only records a request and cannot immediately change the Task to Canceled.
3. Ordinary APIs return Task<T>, with TCS using RunContinuationsAsynchronously; multiple awaits have natural semantics, and allocation costs are explicitly accounted for.
4. The terminal callback only copies fixed status/error data; the completion coordinator outside the callback invokes typed take_result once, with explicit failure atomicity and ownership transfer.
5. Native try_retire proves only that native work and callbacks no longer access the resource; final release also requires start to have returned, cancellation registration to have been drained externally, and managed callback/control call counts to have reached zero.
6. Reserve each operation's quota before native acceptance; clean up the operation automatically even if its Task is never awaited, and account separately for result owners and active operations. [R09-D01]

These are directly implementable recommended choices awaiting independent review; keeping every option proposed does not substitute for a decision. Later performance evidence may trigger local evolution without weakening current safety invariants.

## 3. Pinned sources and coverage

| Source | SHA | Mechanisms read |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | CancellationTokenSource.Register, CancellationTokenRegistration, TaskCompletionSource<T>, Task completion and continuation scheduling, cancellation tests |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | managed begin/callback/Dispose、Rust spawn/select/oneshot/complete/abort |
| Finite model in this repository | File SHA256 `016760cddb78698827bccc472a2d653cba55e20ba15c61c3480a3faea559cd1f` | Added setup/start/control/registration retirement partial order and three negative controls |

See [evidence.json](evidence.json) for individual source evidence and blobs; [coverage.json](coverage.json) explicitly lists the complete Task scheduler, ManualResetValueTaskSourceCore, Tokio's internal waker and the UniFFI async bridge as unread. Tokio and UniFFI remain follow-up evidence for alternative implementations; having read Tokio call sites in YAHA does not mean the Tokio implementation has been fully read.

## 4. The .NET cancellation path: a callback can precede registration assignment

[`CancellationTokenSource.Register`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenSource.cs#L586-L687) first attempts to register a callback node, then must still handle races with cancellation state; if already canceled, it may invoke the callback synchronously before returning the registration. This is not limited to exceptional paths. NativeWeave cannot treat receipt of the returned registration as the earliest possible callback execution point. [R09-S01]

The context, handle, fixed counters and cancel_requested must therefore be initialized before UnsafeRegister. A setup lease retains the context; the callback may record cancellation and invoke request_cancel, which is allowed in Created, through a control lease. registration_ready is published only after Register returns. If start has not yet occurred and cancellation has been observed, start may then be safely skipped; otherwise, after start commits, the native terminal state determines the result.

[`CancellationTokenRegistration.DisposeAsync`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/CancellationTokenRegistration.cs#L32-L110) waits, when necessary, for a callback executing on another thread; Unregister itself only attempts deregistration. The [tests](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Runtime/tests/System.Threading.Tasks.Tests/CancellationTokenTests.cs#L1560-L1745) that were read use synchronization barriers to demonstrate the intended design: the DisposeAsync result does not complete before the callback exits, and the tests also cover UnsafeRegister's ExecutionContext behavior. The tests were not executed. [R09-S02, T01]

NativeWeave's internal cancellation handler does not need to capture the caller's ExecutionContext and uses static UnsafeRegister; normal Task mechanisms maintain the application continuation's ExecutionContext. A domain callback requiring a particular context must select it explicitly, rather than accidentally propagating the internal thread environment to users.

## 5. The Task path: asynchronous continuation is not a reclamation barrier

[`TaskCompletionSource_T.cs`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/TaskCompletionSource_T.cs) passes creation options to Task; TrySetResult/TrySetCanceled enter Task state transitions, and racing completions may also wait for another completion process to finish. It manages the application result, without knowing the lifetime of native handles, cookies or pins. [R09-S03]

[`Task.FinishContinuations`](https://github.com/dotnet/runtime/blob/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Threading/Tasks/Task.cs#L3570-L3715) exchanges the completion sentinel and decides whether to inline based on flags including RunContinuationsAsynchronously. This option prevents the current completion thread from inlining an application continuation, but cannot prevent another thread from starting before the native callback returns. It therefore does not imply that release is necessarily safe after queuing to the thread pool. [R09-S04, D01]

We do not couple Task.TrySetCanceled to Token.IsCancellationRequested to trigger immediate release: a database write may already have been accepted or a server response sent, and cancellation is only a racing request. When Success races cancellation, returning Success can be valid; TIMEOUT must not be overwritten as Canceled either. The error domain must separately record knowledge states such as Effect=Unknown.

## 6. The YAHA path and the end of borrowed-data lifetimes

Managed code initializes RequestContext and allocates the cookie through Allocate before invoking [`yaha_request_begin`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs#L483-L725). Rust retains Arc request state, spawns asynchronous work and selects between cancellation and the request; a body frame first invokes managed on_receive and then awaits a oneshot acknowledgement. Managed [`OnReceive/CompleteTask`](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L464-L625) reports backpressure completion/failure back to native code. [R09-S05, S06]

After the normal on_complete call, Rust still sets the completed state; application receipt of completion therefore does not imply that the caller's native frame no longer accesses the object. RequestContext has separate GCHandle release, native handle release and finalizer policies; NativeWeave reuses only the idea of separating these obligations, not a policy dependent on blocking a particular host's finalizer.

This increment did not fully audit YAHA ResponseContext, Tokio internals or all memory borrows, so it does not declare every buffer lifetime correct from isolated call sites. Our general v1 tightens the rules further: only copy borrowed data inside callbacks, and obtain owned results through a separate typed take; the Server credit/ack protocol further defines chunk streaming.

## 7. The exact partial order of startup, results and shutdown

D06 requires quota and owner-wrapper reservation first, then context/TCS/GCHandle initialization after create succeeds, followed by cancellation registration. start rejection must leave no work or callbacks; once start takes over, it returns OK whether the application operation succeeds or fails synchronously, and reports the application result through the unique terminal notification. The start call lease remains valid until native code returns.

Recording a terminal state does not execute user code. The completion coordinator prepares the managed result wrapper and budget in advance and invokes take through an internal lifetime capability; on OK, native code clears the corresponding owner, while on failure the out value is empty and native code still owns it. A second take returns INVALID_STATE. Operation release handles an untaken result. Owner Closing must not block internal take/retire for accepted operations; it closes only ordinary external admission, and the coordinator is the sole final reclaimer.

Cleanup completion requires all of the following: the registration has been published and its externally invoked DisposeAsync has finished; start has returned; ordinary control leases are 0; native try_retire returns OK; managed callbacks are 0; the result has been published or its failure handled; and every coordinator native call has returned. Only then may the GCHandle be freed and input leases and the operation owner released. Native Retired and result Taken are orthogonal states: take is still allowed after retirement and before release.

All terminal states, Owner closure and timeout waits coalesce into the existing cleanup slot. Discarding a Task does not prevent automatic operation cleanup; however, an application that retains or ignores a returned OwnedResult still bears its Dispose/final-release responsibility. Automatic revocation of the user's result ownership must not be claimed. [R09-D01]

Independent cross-review completed two failure paths. D06's phase-by-phase compensation table explicitly covers NoRegistration, StartSkipped/Rejected/AcceptedReturned and Indeterminate: roll back directly before a complete context exists; steps never initiated must not wait for events that will never occur; indeterminate takeover requires quarantine rather than an assumption of safety. An ordinary terminal-callback failure uses a preallocated binding-failure latch, and finally still wakes the existing slot; the managed result becomes Faulted while preserving native state/effect, without requiring native code to violate the unique-terminal rule by emitting another Failure. These are design revisions; the current model does not cover every initialization failure or latch fault, and AS-02/03 and formal fault injection remain pending.

## 8. The finite model actually executed in this increment

The command, run from the Design repository root, is:

```sh
python3 docs/research/topics/R09/retirement_model.py
```

The actual environment was Python 3.12.14 on Linux x86_64, with exit code 0. The code [retirement_model.py](retirement_model.py), raw [stdout](model-stdout.txt), [stderr](model-stderr.txt), [results](retirement-result.json) and [run record](model-run.json) containing time, command and hash are all preserved. The model ran before its first Git commit; the run explicitly records `source_commit=null`, the baseline commit and the exact model SHA256. It neither invents an old commit containing new code nor presents a research run as a product acceptance manifest.

| Model | Reachable states | Explored transitions | Checked counterexample | Reclaimed states without a checked violation |
| --- | ---: | ---: | --- | ---: |
| All guards | 541 | 1552 | None | 8 |
| Remove start-return guard | 549 | 1560 | access_after_free | 12 |
| Remove control-lease guard | 553 | 1568 | access_after_free | 16 |
| Remove registration-drain guard | 565 | 1576 | cleanup_success_without_managed_registration_drain | 8 |

Breadth-first traversal is used, and each branch stops at its first checked violation. The positive case checks access after release, duplicate Task publication, duplicate free and cleanup success without a registration drain. The results list all shortest counterexample traces. [R09-M01]

The start negative case is: registration completes → enter start → commit → native terminal callback enters/notifies/returns → managed code publishes Task → close the gate → drain cancellation registration → retire native state → reclaim → the start frame continues accessing the resource and returns. The control negative case is: a valid control call has acquired a lease → cleanup ignores the lease and frees early → that call accesses the operation. Both show that native quiescence does not cover call frames actively entered by managed code.

The registration negative case is: the cancellation callback has entered → the not-started cancellation path is taken → native state can retire → DisposeAsync is declared successful while managed drain is skipped. **This proves a cleanup-contract violation, not automatically a native UAF**: the cancellation delegate still retains managed state, and the atomic admission gate can prevent a late native call. The report preserves this distinction to avoid overstating the negative case.

### Exact model assumptions and limitations

There is only one operation, one native terminal callback, one cancellation registration/invocation and one optional ordinary control call; each step is atomic and sequentially consistent. The model trusts that start rejection leaves no obligations, terminal commitment is correct, native retire actually closes future callbacks and lease admission is atomic. It does not prove the implementation of those conditions themselves.

It proves neither liveness, fairness, shutdown deadlocks, weak memory, real GCHandle/FFI/AOT, multiple operations/callbacks, pooling/ABA, counter overflow, result ownership transfer, pinning, OOM nor panic. The candidate's 8 successful reclamation states rule out only a vacuous positive case in which reclamation is entirely impossible; they do not prove eventual reclamation under every schedule. Correct commitment of a single terminal state is abstracted as a protocol event; duplicate malicious notifications still require real fault injection.

## 9. Candidate comparison and costs

| Choice | Correctness and experience | Costs and decision |
| --- | --- | --- |
| TaskCompletionSource | Natural multiple-await behavior and clear terminal publication | Per-operation allocation; adopted for v1 |
| pooled IValueTaskSource | Can reduce some allocations | Complex token/version, reuse, incorrect await and late-callback handling; no current evidence of benefit, so not the default |
| callback push | Direct readiness notification | Requires cookie quiescence; this increment uses fixed notification plus independent retire |
| poll/wake ABI | Can consolidate execution authority on the caller side | Waker registration, lost wakes, fairness and extra polling still require a protocol; a future evidence-driven profile |
| One FFI call to start and return a handle | One fewer call | A synchronous callback before managed handle initialization requires a more complex protocol; v1 uses two phases |

Cost accounting must include create/start/take/retire/release FFI, GCHandle, context/TCS, input copying/pinning, scheduling queues, native references and unretired bytes. Statistics must not be limited to application Task duration. High-frequency short work should first use synchronous/batch APIs; introduce pooling only when complete workload evidence demonstrates a benefit.

## 10. Validation tasks, open issues and closure scope

D06 AS-01–08 cover synchronous cancellation during registration, start rejection/synchronous completion, terminal races, in-flight leases, take-once/result-conversion failure, coordinator saturation/no progress, multiple awaits/ExecutionContext, and Windows/Linux AOT and long-load testing; they map to A04/A07/A08/A14/A15/A18/A19/A20/A21/B22. Implementation must map each state-machine action to actual CAS/lock/acquire-release semantics, using scheduling/property/fuzzing tools suited to the target for validation rather than merely listing Loom/Coyote names.

Q05 has a concrete Task choice with no default pooling; Q04 has a resource-retirement partial order and a reproducible experiment, allowing design research questions to close after independent review. Further R12 executor, R10 Buffer and R15 weak-memory evidence stays within each task's scope; recording the design as resolved does not require implementing every platform in this increment. Tokio/UniFFI and ValueTaskSource internals remain unread, so the overall research task remains partially_evidenced; investigation of the entire async ecosystem must not be marked complete.

Independent review should especially check Owner closure before terminal/take, a never-awaited Task, a registration callback before assignment, lost wakes from coalesced PENDING notifications, quotas and diagnostics for permanent failure to reach quiescence, and database cancellation with unknown effects. The pinned dotnet/runtime and YAHA licenses were read and are MIT; this report does not copy long source passages.

## Current completion review — source alternatives, real take-once and notification progress

The existing retirement model and its541-state result remain historical evidence. This increment actually executes synchronous/native-worker terminals, precancel and late cancel, duplicate completion rejection, once-only result take, result survival after operation release and DTO-conversion cleanup. Thirty-two controlled callback/GC rounds plus managed registration barriers execute normally and as Linux Native AOT. It is a bounded research operation, not the full future A07 coordinator. Exact evidence is `verification/interop-completion/linux/result.json`.

Previously unread alternative mechanisms are now inspected. .NET11 ManualResetValueTaskSourceCore has a short version and requires the outer owner to prevent access across Reset; version checks and single-continuation enforcement do not make a native cookie safely reusable. UniFFI's actual WrappedFuture separates poll, complete and free; its scheduler handles wake-before-store and calls callbacks outside the internal mutex. Its Arc-backed RawWaker retains future state. These mechanisms support keeping ordinary Task/TCS as the simple initial C# contract and deferring pooling until workload evidence justifies the additional ABA/reset/await rules.

The new finite mailbox model supplies a concrete lost-notification counterexample: worker reads no dirty work, notification marks dirty while scheduled remains true, worker clears scheduled using the stale read. Atomic dirty recheck/unschedule removes that counterexample in the declared finite SC model; exact negative17/candidate11 states and source hash are preserved. D09 specifies the matching bounded mailbox and pending-retirement retry rule; it does not claim a weak-memory proof.

The old preview-only Runtime Async statement is historical and superseded by R01/D01's current .NET11 check. This bridge uses ordinary Task and does not require a runtime-async-specific ABI. Current source/design questions are resolved with the above evidence. Independent review remains required; full setup-allocation compensation, poisoned-worker recovery, multi-operation saturation, every target and production weak-memory/load behavior remain explicit A07/A08/A19/A20/B22 obligations.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
