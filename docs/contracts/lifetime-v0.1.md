# C-LIFETIME-001: Ownership, resource leases and reclamation protocol

Version: 0.4.0. Task: D04; research: completion evidence for R07–R12 and R15/R16. Author: interop_design. Status: **Research/design candidate complete; the registry records the exact reviewed version, content hash and acceptance status; product verification remains in Delivery**. This file selects the v1 protocol; the research slice has explicit evidence of actual concurrency and Windows/Linux Native AOT execution, while full product implementation/platform/production acceptance is recorded separately. Only the integrator updates the registry after independent review; the author does not self-accept it.

## 1. Goals and non-goals

The application layer receives natural C# resource objects, deterministic Dispose/DisposeAsync and cancellation behavior; internally, native ownership is managed according to each Engine's actual needs. The core lower layers of Database / ORM / Server must be Rust; an Engine that does not need asynchronous scheduling does not start a native runtime. Resource management must not rely on callers remembering raw-pointer validity periods, nor impose an asynchronous server's full scheduling cost on a synchronous compression function.

This contract defines identity, ownership/borrowing, call admission, parent/child references, leases across asynchronous work, reclamation conditions and shutdown responsibilities. It does not define whether a database transaction has committed/rolled back, nor equate native memory quiescence with a connection being fit to return to the pool. In-process native code shares the same trust domain; this protocol does not promise to isolate malicious native code or repair arbitrary memory corruption.

## 2. Design decisions and candidate comparison

**v1 choice: private opaque pointer + per-resource-type SafeHandle + explicit call admission + asynchronous leases as needed.** Ordinary business APIs do not expose `nint`, GCHandle or native allocators. Ownership information is included in the single authoritative ABI description, and generators emit matching release paths.

| Candidate | Benefits | Costs/defects | Decision |
| --- | --- | --- | --- |
| Global generational handle table for every operation | Can reject some stale identities; suitable for explicit reuse/untrusted integer-handle boundaries | Lookups, synchronization, additional indirection, generation overflow and table lifetime | Not the universal v1 default; separate profiles for pooling or cross-process identity |
| opaque pointer + SafeHandle | Existing .NET ownership/final-release mechanism; fully private native layout | SafeHandle does not solve logical closure, native asynchronous retention or callback quiescence | Adopted, supplemented by this contract's separate responsibilities |
| Managed-object references or GC.KeepAlive alone | Low apparent complexity | Explicit Dispose can still race with use; native asynchronous tasks are not automatically protected | Cannot serve as the sole safety mechanism |
| Native retain/release for every API call | Can support multiple native owners | Additional FFI and atomic operations; adds cost to calls that only borrow synchronously | Used only when shared ownership or ownership across asynchronous work requires it |

Initially use a reviewable short managed critical section to protect admission; if actual performance evidence later warrants it, a CAS protocol combining a counter and closing bit may replace it while preserving the same linearization semantics. Introducing more complex reclamation solely to be lock-free is prohibited.

## 3. Actual source basis

[The R07 report](../research/topics/R07/report.md) records pinned SHAs and line ranges. .NET11 `SafeHandle` stores its reference count, Closed and Disposed in one state word. `DangerousAddRef` checks Closed but does not use the Disposed bit to prohibit all new references; therefore, application-level logical closure requires its own admission gate while other leases remain. `DangerousGetHandle` only reads the address; calling it alone does not acquire a use-period reference.

Godot's managed objects, refcounted objects, signal awaiters and managed callables separately maintain ownership, associated GCHandles, object identities and release; these practical mechanisms show that different resource relationships must be represented explicitly. Its complete engine object model, reflection and hot reload are not adopted as NativeWeave's public runtime. YAHA's parent-reference, active-request and TLS-callback lifecycle tests provide concrete counterexample scenarios; its Unity finalizer waiting strategy is not this project's default.

## 4. Three forms of identity and ownership

| Object | Representation | Authority and validity period |
| --- | --- | --- |
| Native-owned resource | Private `nw_<engine>_<kind>*` | Released by the Engine that created it; SafeHandle owns one release right |
| managed callback context | `uintptr_t cookie` | Identifies a strong GCHandle created by managed code; native code only stores/returns it unchanged and never dereferences its bit value |
| borrowed data | D07 pointer+length or a domain typed view | Only within the declared call/callback scope; asynchronous retention requires a separate owner lease |

Each successful create delivers exactly one ownership right; on failure, the out pointer is null. Shared ownership uses an explicit clone/retain operation or native-internal `Arc<State>`; copying a pointer must not fabricate a second owner. v1 does not provide a public Detach of raw handles; if a specialized interop profile requires it, atomic transfer and recipient responsibilities must be defined separately.

Ownership preserves creator/releaser pairing: C# FreeHGlobal must not release a Rust Box/Vec, and another Engine's release function must not release the current Engine's resources. A module load reference must survive at least until the final function-pointer call, callback and resource release have completed.

## 5. Admission gate, call lease and linearization points

A resource has at least the logical states `Open / Closing / Released`. Open→Closing is the linearization point after which new business calls are no longer accepted. Each call “checks Open and acquires a SafeHandle reference” under the same synchronization protocol, then executes FFI outside the lock and releases the reference in finally. Dispose sets Closing under the same gate, then releases the owner reference outside the lock.

The following is an **uncompiled implementation skeleton**; the generator should emit equivalent try/finally code without exposing a copyable value-type lease to applications:

```csharp
internal unsafe int InvokeGenerated(int argument)
{
    bool lease = false;
    try
    {
        nint pointer;
        lock (_admission)
        {
            ObjectDisposedException.ThrowIf(_closing, this);
            _handle.DangerousAddRef(ref lease);
            pointer = _handle.DangerousGetHandle();
        }
        return _api.Invoke(pointer, argument); // generated exact C ABI
    }
    finally
    {
        if (lease) _handle.DangerousRelease();
    }
}

public void Dispose()
{
    lock (_admission)
    {
        if (_closing) return;
        _closing = true;
    }
    try { RequestStopIfApplicable(); } // no wait or user callback under gate
    finally { _handle.Dispose(); }     // active leases delay physical release
}
```

`RequestStopIfApplicable` in the skeleton cannot acquire ordinary business admission that has already closed; it must use a previously held internal shutdown capability/owner reference, and the exceptional path must still release ownership. Formal implementation must expand and verify this method and its error paths, rather than directly copying this example with an omitted implementation. The closing-flag check and DangerousAddRef must not be split into two unsynchronized steps.

## 6. Parent/child resources and independent Engines

Default: a successfully created owned child holds the native parent-state reference it needs. Disposing the parent wrapper rejects new parent business calls and new child creation, but an existing child's legitimate access is maintained by its own owner/lease. If a domain defines cascading cancellation, its API must explicitly mark it cascade and provide asynchronous drain; a managed parent variable remaining reachable is not sufficient for safety.

A Rust implementation may place the externally exposed opaque owner in an independent Box and let the child hold an internal `Arc<ParentState>`; each Engine may use its own equivalent reference mechanism. A long-lived DangerousAddRef on a parent SafeHandle in C# can implement the same relationship, but every failure/release branch must balance it. In v1, each child type selects exactly one authoritative parent-lease mechanism to avoid unreclaimable cycles caused by managed and native sides retaining each other.

The parent state's memory remaining alive does not mean the parent is still Open to new business operations. Final release of thread-affine resources must be dispatched to their owning thread/executor; a SafeHandle finalizer thread cannot directly invoke an arbitrary GUI/GPU destructor.

## 7. Asynchronous resources and GCHandle

An asynchronous operation holds the owner leases, input-memory leases, strong callback-context reference and module-function-table reference it needs. They are released only when D06's retirement conditions hold. Managed Task success/failure/cancellation is the application-visible result; resource retirement is a separate state.

GCHandle uses a Normal strong reference; it fixes the target's reachability, not the object's address. Native code holds only the cookie and must not treat it as a managed-object pointer. When a stable native data address is required, use D07's explicit pin/owned copy; the presence of a GCHandle does not imply pinning.

GCHandles can be reused, so “handle value is nonzero” or `Target != null` cannot determine whether a late callback points to a new object. v1 eliminates reuse windows on normal paths by prohibiting callbacks after retirement, ensuring all callbacks in flight exit, and avoiding operation-context pooling. Generational tokens provide only additional detection and cannot replace the quiescence protocol.

## 8. Reclamation invariants

For each resource r and operation o:

- `free_count(r) <= 1`.
- `native_access(r) => live(r) && valid_owner_or_lease(r)`.
- New ordinary business admission fails after `Closing(r)`; previously acquired leases may still complete.
- Context reclamation requires: native code has permanently closed callback sources and confirmed quiescence; all managed callbacks have exited; setup has explicitly completed (start returned or the never-called sentinel); cancellation registration has been externally drained or explicitly marked NoRegistration; and control-call leases in flight are 0. Notification subscriptions additionally drain/discard the managed pending queue and wait for active user handlers to end.
- All borrowed inputs, results and callback parameters are released at their own ownership endpoints; Task publication must not cause premature ArrayPool return or unpinning.

Here, `native_obligations` describes only local work that still accesses the current resource's memory or must execute on that resource. An Unknown remote database commit effect may persist in an independent recovery record; it does not automatically prevent safe local reclamation. The database protocol separately confirms whether a connection may return to the pool.

## 9. Dispose, DisposeAsync and finalizers

Dispose on a synchronous resource may directly perform a non-blocking release. Dispose on an asynchronous resource/subscription closes admission and requests stop; native cleanup may still be in progress when it returns, and public documentation must state this clearly. **Successful completion of DisposeAsync guarantees that the callback, cancellation-registration, control-call and native-resource cleanup specified for this object has completed.**

If `CloseAsync(CancellationToken)` provides a cancellable wait, cancellation only stops the caller's wait; background cleanup continues to hold all necessary resources and must not force free. Lack of progress should expose cleanup age, outstanding leases/bytes, pending retire and the last phase, restrict new admission and poison the Engine if necessary. A timeout must not become permission for a memory-unsafe release.

Finalizers do not wait for native work, run user code or block executor shutdown. An asynchronous context is strongly referenced by the ongoing operation/cleanup coordinator; a finalizer may only request non-blocking stop and transfer existing ownership to a pre-existing cleanup path. If the execution environment can no longer progress, conservatively retain/isolate resources and record diagnostics; continued liveness must not be claimed. Under D02, v1 native modules remain loaded until process exit, and instance closure does not unload the library; any future hot-unload feature requires a separate proof that no resources, function pointers, threads or callbacks remain active.

## 10. Costs, modern C# and platforms

The synchronous hot path costs one admission critical section, SafeHandle AddRef/Release and one FFI call; it has no per-call GCHandle, global table or mandatory native scheduler. An asynchronous operation uses one stable context and one GCHandle, with actual allocation and TCS counts accounted for by D06. Span/ReadOnlySpan can express synchronous borrowing but cannot cross an asynchronous-retention boundary.

The initial actual acceptance targets are win-x64 and linux-x64; pointer width and natural alignment are verified against D02's target matrix. Future Arm64/mobile/thread-affine profiles cannot assume desktop finalizer behavior. Statically typed function tables and generated metadata support AOT; this file contains no actual C#/Rust compilation results.

## 11. Implementation and acceptance mapping

| Verification ID | Scenario and criterion | Delivery |
| --- | --- | --- |
| LT-01 | Call-lease acquisition races with Dispose: old calls complete, new calls are rejected, free occurs exactly once | A03, A20 |
| LT-02 | Child remains active during parent closure; creation failure, double Dispose, final child release | A03, A17, A18 |
| LT-03 | GC pressure, finalizers, module unloading; no calls through unloaded function tables or blocking finalizers | A14, A15, A18 |
| LT-04 | Task has completed while callback/control call/start has not exited; buffer/context must not be released first | A07, A19, A20 |
| LT-05 | Late callbacks, GCHandle reuse, wrong release function; negative cases in isolated processes | A06, A20 |
| LT-06 | Long-duration cancellation/failure/closure loops; resource counts return to expected bounds after a stable baseline | A21, B22 |

Tests require actual Windows/Linux AOT consumers, pinned source and binary hashes, raw logs, race seeds and timeouts. The R09 finite model supports only the abstract protocol; these tasks must still establish actual SafeHandle, memory-model, FFI and thread-affinity behavior.

## 12. Decision status

The resource-safety design portion of Q04 may be recorded as design-resolved after independent review of this file, D05 and D06; the distinction between local memory quiescence and remote effects is now explicit. Corresponding implementation and production verification remain pending. Q02's v1 choice between private pointers and generational tables has an explicit recommendation; full ABI acceptance belongs to D02 and independent review.


## Supplemental execution evidence — logical admission only

This non-normative update does not change the v0.1.0 admission protocol or accept the contract. The earlier uncompiled skeleton is now complemented by an equivalent synchronous research facade in `experiments/logical-admission/Program.cs`, tested at Design28f6cf7e6e4e80b9f32a92ad587a528d82911bd0/run43373306474. Both Windows/Linux passed normal and actual AOT runs with653 assertions and64 controlled gate/Dispose rounds each. The original SafeHandle-only facade admitted a new call while an old lease remained; the explicit Open/Closing gate rejected it while allowing the old call to complete. An injected managed failure returned its acquired reference.

See [R07 detailed study](../research/topics/R07/logical-admission.md) for exact source, traces, operation ordering, mutation-lock separation and future Codex test cases. The compiled fixture has no RequestStopIfApplicable, async callback, parent/child, finalizer or module-unload implementation, so those parts of this contract remain unverified by it. Keep native query mutation guards separate, avoid callbacks/await under them, and do not rely on Mutex poisoning for unsafe memory soundness. Research experiment success is not formal A03/A07/B11/B17 implementation or independent acceptance.

## 15. Completion review and separation of implementation obligations for this round (2026-11-13)

Retain the existing [logical-admission evidence](../../verification/logical-admission/primary-results.json): it actually covers the synchronous-admission counterexample in Windows/Linux normal and Native AOT execution. The added [interop-completion](../../verification/interop-completion/linux/result.json) controls a native worker callback so that it remains in flight under Linux normal and Native AOT execution, verifying a strong GCHandle root, no reclamation before native quiet, one-time take, continued readability of an independent result owner after operation release, and result release when managed conversion throws. The research fixture's private status codes and partially handwritten coordination code cannot stand in for the product D08 ABI or a complete generated wrapper.

Physical leases, logical admission, a single writer for mutable objects, result ownership and Engine/module ownership remain separate requirements. A SafeHandle that delays free cannot replace the Open→Closing admission lock, nor does Arc reference counting alone prove that the worker OS thread has joined. Ordinary modules remain resident for the process lifetime; specialized thread-affine owners use [D09](concurrency-v0.1.md)'s dedicated release scheduling, and finalizers do not wait synchronously.

R07 now provides a complete research decision and scope; the unselected Qt/Python ownership mechanisms do not constitute an indefinite prerequisite for the current C#/Rust design. This design may be accepted after independent review; complete parent/child, mismatched-owner, long-duration race, weak-memory, resource-return-to-zero and product-package tests remain separate obligations of A03/A04/A20/B01.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

Public resource owners are sealed reference types; value structs never own disposable native allocations. NativeBuffer exposes a scoped synchronous read or explicit copy, not an escaping raw pointer. Domain CloseAsync returns an explicit cleanup observation; pending cleanup is not memory reclamation. DisposeAsync follows the existing quiescence protocol even when the caller stopped waiting. Domain descriptions must identify whether children pin a parent and which calls reject immediately after logical close. A03/A04 and each owner task implement the exact [Interop](../api/interop.md), [Database](../api/database.md) and [Server](../api/server.md) signatures, XML lifetime notes and early-disposal consumers.
