# R07 / D04 — logical close versus physical SafeHandle lifetime

Research only. This extends the existing lifetime study after PR1 assets were moved into Design; it is not A03 product implementation. It does not change any migrated source or original evidence bytes.

## Question and inspected source

Does SafeHandle alone reject new business calls after Dispose when an earlier native call still owns a reference? The exact .NET11 source is dotnet/runtime commit `deae2e32bf0e018e09d64597b7c59b62b73bb3ce`, `src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs`, inspected lines130–281, Git blob `2d1f9313b485c57afab1f187e00a180df7fad3ba`. DangerousAddRef checks the Closed bit; InternalRelease records Disposed separately and closes on final reference release. Existing R07 already identifies this distinction. The new fixture makes that source-derived counterexample executable across C ABI and actual AOT.

## Experimental design

Reuse the exact migrated dependency-free native buffer library and SafeHandle facade. Negative control: hold a live native SumHeld call, Dispose the original facade, then call Sum while that earlier lease remains. Memory is still valid, so this does not intentionally invoke undefined behavior. The expected observation is safe physical access despite logical disposal. It is NOT a SafeHandle memory-safety defect; it is a mismatch with NativeWeave's stronger application admission contract.

Candidate: an internal, non-inheritable facade keeps its SafeHandle private. In one short lock, check Open and acquire DangerousAddRef; obtain the pointer, release the lock, execute FFI, and return the reference in finally. Dispose closes admission under the same lock, then disposes the owner outside it. A second Dispose returns without another owning release. No public raw pointer or copyable lease is exposed.

State/linearization table:

| Event | Precondition and atomic decision | After decision |
|---|---|---|
| Ordinary call | Open checked and reference acquired under the same gate | Call may execute outside the lock, even if a later Dispose closes admission |
| Dispose | First caller changes Open to Closing under the gate | Drop owning reference outside the gate; do not wait for admitted FFI |
| Post-close call | Closing observed under the gate | Throw before acquiring reference or calling native code |
| Call completion/failure | Its lease was successfully acquired | Release exactly that reference in finally |
| Final release | Owning reference and admitted references are all gone | SafeHandle invokes the original native destructor |

64 controlled rounds hold an admitted native call while Dispose must finish promptly. New ordinary/held calls must be rejected before the hold is released; the original result must remain correct; the final native live count must return to zero. A managed exception injected after acquisition verifies compensation. Three groups run in normal mode and Native AOT. The runner requires653 assertions per execution so silently missing the injected-exception assertion cannot pass.

## Run and evidence

With the existing pinned .NET11.0.100 and Rust1.100.0 toolchains plus target AOT prerequisites, run `python experiments/logical-admission/run.py` from the repository root. Native compilation reuses existing Cargo.lock with `--locked --offline`; old unit suites are not rerun. Only the new managed scenarios are run, then published and actually executed as AOT on each OS. The active workflow is `.github/workflows/logical-admission-research.yml`. Raw outputs/source hashes/binary hashes are kept under `verification/logical-admission/` after collection. Before such records exist, test outcomes are pending, not inferred from this design.

## Interpretation and cost

The gate adds one short managed critical section and a SafeHandle reference pair per call, with no per-call native retain/release, GCHandle, global handle table or runtime. This is a structural cost model, not a latency/allocation benchmark. There is no measured justification for a lock-free reclamation scheme here. The unchanged Rust1.100 DropGuard protects native unpublished-allocation cleanup; it cannot replace the managed logical gate or asynchronous retirement.

This facade protects lifetime and close admission for synchronous immutable access. It does NOT serialize simultaneous mutable query-builder operations: those need a separate engine-local mutation rule. It does not prove async callbacks, cancellation-registration drain, parent/child disposal, finalizer behavior, module unloading, weak-memory correctness on other architectures or production soak. Dispose does not imply remote database rollback or network shutdown. D04/D05/D06/D07 remain proposed contracts with separate future Codex acceptance; this study resolves only the finite local admission question.
