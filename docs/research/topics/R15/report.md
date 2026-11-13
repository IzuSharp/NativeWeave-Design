# R15 — Bounded proof, lifecycle counterexamples and implementation mapping

Research decision ready for independent review. Prior finite model evidence existed under async-quiescence and R09 despite R15 remaining planned and having no canonical triplet. This report accepts its actual scope, adds a targeted notification-loss model and chooses tools by property rather than treating tool count as progress.

## Existing model evidence

The original async-quiescence study shows that publishing cancellation before actual native quiet is not permission to reclaim context. R09's extended retirement model includes start-return, control-call and cancellation-registration guards: the candidate explored541 states/1552 transitions; dropping start-return or control-lease guards produced access-after-free counterexamples, while dropping registration drain produced a cleanup-contract counterexample. Its exact source/results and limitations remain in their original files. Re-reading those results does not count as a new execution.

The distinction matters: missing registration drain does not automatically imply native UAF if other leases still protect native calls. A finite model must say which invariant failed. Reaching some valid reclaimed states is a non-vacuity check, not a proof that every fair/unfair execution eventually cleans up.

## New mailbox model

`experiments/interop-completion/mailbox_model.py` models one worker and one extra wake with a single pre-reserved completion slot. The negative coordinator reads dirty, then clears scheduled in a later step; a notification between those steps leaves dirty work with no scheduled worker. The candidate rechecks dirty and clears scheduled atomically. Breadth-first exploration records state/transition counts, the exact negative trace and at least one completed two-notification state. Actual output is `verification/interop-completion/mailbox-model.json`.

Each transition is atomic and sequentially consistent; the model does not include the CLR, Rust atomics, OS scheduling, allocation failure or network I/O. It is a compact explanation and future implementation oracle, not a new global planning graph or product executor.

## Source-derived tool comparison

| Tool | Useful property | Boundary |
|---|---|---|
| Existing finite Python/TLA-style state relation | Admission/start/callback/retire ordering and readable counterexample | Declared abstract transitions and event bounds only |
| Loom `9d549cd5…` | Actual Rust synchronization algorithm under instrumented primitives | Builder exposes thread/branch/permutation/preemption/time limits; record all configured bounds |
| Miri `443c6231…` | Rust UB/aliasing/invalid-memory behavior in supported code | Limited FFI/OS/network support, incomplete weak-memory exploration, finite executions |
| Kani `0aac16ef…` | Bounded scalar/loop helpers with explicit assumptions | Unwinding assertion failure is not a proof; problem size and unwind limits must both be declared |
| Real native/managed probes | Actual UCO, GCHandle, SafeHandle and cancellation interactions | Finite test schedules; cannot prove the complete implementation |

Pinned source and documentation ranges are in the supplemental source inspection. No Loom, Miri or Kani execution is claimed in this increment. Installing all three is not a prerequisite for accepting the design: the selected future implementation algorithm determines which instrumented proof/test is required. A TLA+/Coyote expansion is useful only for a specific property/algorithm that these smaller existing models cannot adequately express.

## Required proof obligations

For each chosen implementation identify: state representation; lock/CAS linearization point; memory ordering; invariant; exact source range; model abstraction; environmental assumptions; normal/failure tests; and a counterexample produced by removing a required guard where safe. Cover at-most-once terminal/free/take, no access without a live owner, no new admission after close, no lost wake, and no falsely successful cleanup. Separate safety from progress/fairness.

Never model a native try_retire return as automatically correct unless its implementation proof is separately provided; record it as an assumed imported predicate. Do not use an unbounded queue in a model of a supposedly bounded runtime, or remove failed-state transitions just to make the model pass. Model updates must follow protocol changes and preserve historical failures.

## Design closure

D12 gives evidence kinds, acceptance scopes and future task ownership. A19 maps models to the actual algorithm and supplies supported weak-memory exploration where relevant; A20 supplies property/fuzz/fault tests; A07/A08 implement the protocol. Current research resolves which invariants/tools/bounds are appropriate and provides real counterexamples. Whole-system correctness, arbitrary schedule liveness and future product validation are explicitly not claimed.
