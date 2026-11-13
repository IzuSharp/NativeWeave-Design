# R12 — Native executor ownership, thread affinity and honest close semantics

Research decision ready for independent review. This canonical report closes the missing task record and supplies D09 with concrete ownership/progress rules rather than a mandatory Core runtime.

## Source findings

Tokio1.54.1 at `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8`, `tokio/src/runtime/runtime.rs` lines1–110 and420–525, distinguishes Runtime owner from cloned Handle. Arc<Runtime> keeps its owner alive; Handle alone does not prevent shutdown. Started spawn_blocking work continues until it returns. Runtime Drop may wait indefinitely; shutdown_timeout/background can return while work/threads continue. The locally cached crate file was byte-checked against the GitHub blob. Therefore a close acknowledgment from these methods is not general evidence of joined threads or reclaimed memory.

UniFFI's actual scheduler releases its state mutex before invoking a foreign callback, explicitly avoiding a cross-runtime lock cycle. Its Empty/Waked/Set/Cancelled states also show why wake-before-registration needs stored state. NativeWeave need not adopt the whole UniFFI runtime to apply these proven interface constraints.

Existing SQLx/SQLite worker and Tokio/Bytes/Hyper studies establish more specific session/Body/permit endpoints. The new Completion study executes native-thread callbacks and managed cancellation drain. The added finite mailbox model finds the wake-between-dirty-check-and-unschedule counterexample and eliminates it when dirty recheck and schedule clearing are one atomic decision; its finite SC scope is explicit.

## Design choice

Synchronous engines have no runtime. Database and Server engines own their own asynchronous runtime/executor or explicit shared owner where composition is justified. Worker-affine resources stay on their native owner thread; a typed bounded command carries owned data and completion identity. Future external GUI/GPU loops are declared capabilities, not hidden defaults. C# performs business Handler work through Task/async and a declared dispatcher, never by blocking a Tokio worker on Task.Result.

Open admission and capacity/owner acquisition are one linearization decision. Keep mutexes short and execute native calls, callbacks, user code, awaits and destruction outside them. Physical lifetime, logical close and mutable serialization are separate protocols. A C pointer does not imply Send/Sync; the binding description captures the native thread policy.

## Close and no-progress behavior

Running→Closing rejects new ordinary work. Internal cancel/take/retire/release still operates for admitted work. Quiescence requires permanent producer closure plus active callbacks ending; managed drain additionally covers start/setup, control leases, registration disposal and queued/active handler work. Released resource owners and required OS-thread joins are distinct evidence. Native runtime shutdown comes after its dependent work is safely retired, or the engine is honestly quarantined.

Dispose requests stop without waiting in a callback/finalizer. Successful DisposeAsync guarantees the declared cleanup; a cancelled CloseAsync cancels only its wait. Pending cleanup retains roots, byte reservations and instance owner. Diagnostics expose cleanup stage/age and outstanding owner counts. An uncooperative blocking job cannot be safely force-freed because a deadline expired.

## Capacity and scheduler details

Use bounded admission, waiting-producer, operation, payload, retained-byte and cleanup-slot budgets. Pre-reserve notification/cleanup capacity before accepting native work. A coalescing per-operation mailbox may merge notifications only when the coordinator resamples state; it must not discard data-bearing stream chunks. Under one lock mark dirty and ensure scheduling; coordinator atomically rechecks dirty before unscheduling. Pending retirement uses a bounded existing retry slot/timer so absence of another native callback cannot permanently strand cleanup.

Closing a Tokio receiver does not destroy pre-existing OwnedPermit reservations. Stop producer admission, then account for each outstanding reservation and drain/discard owned messages with correct cleanup. Protocol credit and memory backing owners remain independent. SQL transaction effect Unknown is not cured by executor shutdown or connection disposal.

## Closure and implementation mapping

D09 specifies profiles, instance states, exact close ordering, failure/poison behavior and test oracles. A08 implements engine-local progress/capacity, A07 mailbox and retirement, A23 thread affinity, B04/B20 domain close coordination. Required Windows/Linux worker stop, no-progress and long-load tests are product obligations. The research does not claim a full native scheduler audit or substitute an SC model for weak-memory correctness; it resolves the choice against a giant default runtime and defines safe semantics for the actual native engines.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
