# C-LIFETIME-001: Ownership, resource leases and reclamation protocol

Version: 0.3.0. Task: D04; research: completion evidence for R07–R12 and R15/R16. Author: interop_design. Status: **research/design candidate completed; the registry records the exact reviewed version, content hash and acceptance state; product validation remains in the Delivery phase**. This document selects the v1 protocol; the research slices already have explicit evidence from actual concurrency tests and Windows/Linux Native AOT execution, while full product implementation, platform and production acceptance remain separately recorded. Only the integrator updates the registry after independent review; the author does not self-accept.

## 1. Goals and non-goals

The application layer receives natural C# resource objects, deterministic Dispose/DisposeAsync and cancellation behavior; internally, native ownership is managed according to each Engine's actual needs. The core lower layers of Database / ORM / Server must be Rust; an Engine that does not need asynchronous scheduling does not start a native runtime. Resource management must not depend on callers remembering raw-pointer validity periods, nor impose the full scheduling cost of an asynchronous server on a synchronous compression function.

This contract defines identity, ownership/borrowing, call admission, parent-child references, leases across asynchronous work, reclamation conditions and shutdown responsibilities. It does not define whether a database transaction has committed/rolled back, nor silently equate quiescence of native memory access with eligibility to return a connection to the pool. In-process native code shares the same trust domain; this protocol does not promise to isolate malicious native code or repair arbitrary memory corruption.

## 2. Design decision and candidate comparison

**v1 choice: private opaque pointer + a SafeHandle for each resource type + explicit call admission + asynchronous leases as needed.** Ordinary business APIs do not expose `nint`, GCHandle or a native allocator. Ownership information enters the single authoritative ABI description, and the generator emits matching release paths.

| Candidate | Benefits | Costs/limitations | Decision |
| --- | --- | --- | --- |
| Global generational handle table for every operation | Can reject some stale identities; suitable for explicit reuse or untrusted integer-handle boundaries | Table lookups, synchronization, extra indirection, generation overflow and table lifetime | Not the general v1 default; define a separate profile for pooled or cross-process identities |
| opaque pointer + SafeHandle | Existing .NET ownership/final-release mechanism; native layout remains entirely private | SafeHandle does not resolve logical closure, native asynchronous retention or callback quiescence | Adopt, supplemented by the separate responsibilities in this contract |
| Managed object references or GC.KeepAlive alone | Low surface complexity | Explicit Dispose can still race with use; cannot automatically protect native asynchronous tasks | Cannot serve as the sole safety mechanism |
| Native retain/release on every API call | Can support multiple native owners | Additional FFI and atomic operations; extra cost for calls that already borrow synchronously | Use only when shared ownership or ownership across asynchronous work requires it |

Initially, protect admission with a short, reviewable managed critical section; if actual performance evidence later requires it, a CAS protocol combining a count and a closing bit may replace it while preserving the same linearization semantics. Introducing a more complex reclamation mechanism solely to be lock-free is prohibited.

## 3. Actual source basis

The [R07 report](../research/topics/R07/report.md) records pinned SHAs and line ranges. .NET 11 `SafeHandle` stores the reference count, Closed and Disposed in the same state word. `DangerousAddRef` checks Closed but does not use the Disposed bit to prohibit all new references, so application-level logical closure needs its own admission gate while other leases still exist. `DangerousGetHandle` only reads the address; calling it alone does not acquire a reference for the duration of use.

Godot's managed objects, refcounted objects, signal awaiters and managed callables separately maintain ownership, associated GCHandles, object identity and release; these real mechanisms show that different resource relationships must be expressed explicitly. Its full engine object model, reflection and hot reload do not become NativeWeave's public runtime. YAHA's parent-reference, active-request and TLS callback lifetime tests provide actual counterexample scenarios; its Unity finalizer waiting behavior is not this project's default strategy.

## 4. Three forms of identity and ownership

| Object | Representation | Authority and validity period |
| --- | --- | --- |
| Native-owned resource | Private `nw_<engine>_<kind>*` | Released by the Engine that created the resource; SafeHandle owns one release right |
| managed callback context | `uintptr_t cookie` | Identified by a strong GCHandle created by managed code; native code only stores/returns it unchanged and never dereferences its bit value |
| borrowed data | D07 pointer+length or a domain-specific typed view | Only within the declared call/callback scope; asynchronous retention requires a separate owner lease |

Each successful create transfers exactly one ownership right; on failure, the out pointer is null. Shared ownership uses explicit clone/retain operations or a native-internal `Arc<State>`; copying a pointer must not fabricate a second owner. v1 provides no public Detach of a raw handle; if a specialized interop profile needs one, atomic transfer and recipient responsibilities must be defined separately.

Ownership preserves creator/releaser pairing: C# FreeHGlobal must not release a Rust Box/Vec, and another Engine's release function must not release the current Engine's resource. The module-load reference must live at least until the last function-pointer invocation, callback and resource release have completed.

## 5. Admission gate, call leases and linearization points

A resource has at least the logical states `Open / Closing / Released`. Open→Closing is the linearization point after which new business calls stop being accepted. Each call performs “check Open and acquire a SafeHandle reference” under the same synchronization protocol, then executes FFI outside the lock and releases the reference in finally. Dispose sets Closing under the same gate, then releases the owner reference outside the lock.

The following is an **uncompiled implementation skeleton**; the generator should emit equivalent try/finally logic without exposing a copyable value-type lease to applications:

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

`RequestStopIfApplicable` in the skeleton cannot acquire ordinary business admission that is already closed; it must use a previously held internal shutdown capability/owner reference, and the exception path must still release ownership. The formal implementation must expand and verify this method and its error paths, rather than directly copy this example with its omitted implementation. The closing-flag check and DangerousAddRef must not be split into two unsynchronized steps.

## 6. Parent-child resources and independent Engines

Default: a successfully created owned child holds a reference to the native parent state it needs. Dispose on the parent wrapper rejects new parent business calls and creation of new children, while existing children's valid access is maintained by their own owners/leases. If a domain defines cascading cancellation, its API should explicitly label it as cascade and provide asynchronous drain; safety cannot rely solely on a managed parent variable remaining reachable.

A Rust implementation may place the externally exposed opaque owner in a separate Box while children hold an internal `Arc<ParentState>`; each Engine may use its own equivalent reference mechanism. A long-lived DangerousAddRef on a C# parent SafeHandle can implement the same relationship, but all failure/release branches must be balanced. v1 selects only one authoritative parent-lease mechanism for each child type, avoiding unreclaimable cycles caused by mutual retention on the managed and native sides.

A parent state remaining alive in memory does not mean the parent is still Open to new business operations. Final release of a thread-affine resource must be delegated to its owning thread/executor; the SafeHandle finalizer thread cannot directly invoke arbitrary GUI/GPU destructors.

## 7. Asynchronous resources and GCHandle

An asynchronous operation holds the owner leases, input-memory leases, strong callback-context reference and module function-table reference it needs. They are released only when D06's retirement conditions hold. Managed Task success/failure/cancellation is the application-visible outcome; resource retirement is a separate state.

GCHandle uses a Normal strong reference; it preserves the target's reachability, not its object address. Native code holds only the cookie and must not treat it as a managed-object pointer. A stable native-data address requires D07's explicit pin/owned copy; the existence of a GCHandle does not imply pinning.

GCHandle values can be reused, so “nonzero handle value” or `Target != null` cannot distinguish whether a late callback points to a new object. v1 eliminates the reuse window on normal paths by prohibiting callbacks after retirement, ensuring all in-flight callbacks exit, and avoiding operation-context pooling. A generational token is only an additional check and cannot replace the quiescence protocol.

## 8. Reclamation invariants

For each resource r and operation o:

- `free_count(r) <= 1`。
- `native_access(r) => live(r) && valid_owner_or_lease(r)`。
- After `Closing(r)`, new ordinary business admission fails; previously acquired leases may still complete.
- Context reclamation requires: native code has permanently closed callback sources and confirmed quiescence; all managed callbacks have exited; setup has explicitly settled (start returned or the sentinel for never called); cancellation registration has been externally drained or is explicitly NoRegistration; in-flight control-call leases are 0. Notification subscriptions also drain/discard the managed pending queue and wait for active user handlers to finish.
- Every borrowed input, result and callback argument is released at its own ownership endpoint; publishing a Task must not cause an early return to ArrayPool or unpin.

Here, `native_obligations` describes only local work that will still access the current resource's memory or must execute on that resource. An Unknown remote database commit outcome may persist in a separate recovery record; it does not automatically prevent safe local reclamation. The database protocol separately determines whether a connection may return to the pool.

## 9. Dispose, DisposeAsync and finalizers

Dispose on a synchronous resource may directly complete a nonblocking release. Dispose on an asynchronous resource/subscription closes admission and requests stop; native cleanup may still be in progress when it returns, and public documentation must state this clearly. **Successfully completed DisposeAsync guarantees that all callback, cancellation-registration, control-call and native-resource cleanup specified for this object has completed.**

If `CloseAsync(CancellationToken)` provides a cancellable wait, cancellation only stops the caller's wait; background cleanup continues to hold all necessary resources and must not force a free. When progress stops, expose cleanup age, outstanding leases/bytes, pending retirement and the last phase; restrict new admission and poison the Engine if necessary. A timeout must not authorize a memory-unsafe release.

Finalizers do not wait for native work, execute user code or block executor shutdown. Asynchronous contexts are strongly referenced by ongoing operations/cleanup coordinators; a finalizer may only request a nonblocking stop and hand existing ownership to an already established cleanup path. If the execution environment can no longer make progress, conservatively retain/isolate resources and record diagnostics; do not claim that liveness is still guaranteed. Under D02, v1 native modules remain loaded until process exit, and closing an instance does not unload the library; any future hot-unload support must separately prove the absence of active resources, function pointers, threads and callbacks.

## 10. Cost, modern C# and platforms

The synchronous hot-path cost is one admission critical section, SafeHandle AddRef/Release and one FFI call; there is no per-call GCHandle, global table or mandatory native scheduler. An asynchronous operation uses one stable context and one GCHandle; D06 accounts for actual allocations and TCS counts. Span/ReadOnlySpan can express synchronous borrowing but cannot cross an asynchronous-retention boundary.

The initial actual acceptance targets are win-x64 and linux-x64; pointer width and natural alignment are verified against D02's target matrix. Future Arm64/mobile/thread-affine profiles cannot inherit desktop finalizer assumptions. Static function-table signatures and generated metadata support AOT; this document contains no actual C#/Rust compilation results.

## 11. Implementation and acceptance mapping

| Verification ID | Scenario and criterion | Delivery |
| --- | --- | --- |
| LT-01 | Call lease acquisition races with Dispose: old calls complete, new calls are rejected, free occurs exactly once | A03, A20 |
| LT-02 | Children remain active when the parent closes; creation failure, double Dispose, release of the last child | A03, A17, A18 |
| LT-03 | GC pressure, finalizers, module unloading; no invocation through an unloaded function table or blocking of finalizers | A14, A15, A18 |
| LT-04 | Task has completed but callback/control call/start has not yet exited; buffer/context must not be released first | A07, A19, A20 |
| LT-05 | Late callbacks, GCHandle reuse, incorrect release function; negative cases in isolated processes | A06, A20 |
| LT-06 | Long-running cancellation/failure/shutdown loops; resource counts return within expected bounds after the baseline stabilizes | A21, B22 |

Tests require actual Windows/Linux AOT consumers, pinned source and binary hashes, raw logs, race seeds and timeouts. R09's finite model supports only the abstract protocol; these tasks still need to demonstrate actual SafeHandle, memory-model, FFI and thread-affinity behavior.

## 12. Decision status

The resource-safety design portion of Q04 may be recorded as design-resolved after independent review of this document, D05 and D06; the distinction between quiescence of local memory access and remote effects is now explicit. Corresponding implementation and production validation remain pending. Q02 now has an explicit recommendation for the v1 choice between private pointers and a generational table; D02 and independent review own acceptance of its complete ABI.


## Supplemental execution evidence — logical admission only

This non-normative update does not change the v0.1.0 admission protocol or accept the contract. The earlier uncompiled skeleton is now complemented by an equivalent synchronous research facade in `experiments/logical-admission/Program.cs`, tested at Design28f6cf7e6e4e80b9f32a92ad587a528d82911bd0/run43373306474. Both Windows/Linux passed normal and actual AOT runs with653 assertions and64 controlled gate/Dispose rounds each. The original SafeHandle-only facade admitted a new call while an old lease remained; the explicit Open/Closing gate rejected it while allowing the old call to complete. An injected managed failure returned its acquired reference.

See [R07 detailed study](../research/topics/R07/logical-admission.md) for exact source, traces, operation ordering, mutation-lock separation and future Codex test cases. The compiled fixture has no RequestStopIfApplicable, async callback, parent/child, finalizer or module-unload implementation, so those parts of this contract remain unverified by it. Keep native query mutation guards separate, avoid callbacks/await under them, and do not rely on Mutex poisoning for unsafe memory soundness. Research experiment success is not formal A03/A07/B11/B17 implementation or independent acceptance.

## 15. Completion recheck and separation of implementation obligations (2026-11-13)

Retain the existing [logical-admission evidence](../../verification/logical-admission/primary-results.json): it actually covers the synchronous-admission counterexample in Windows/Linux normal and Native AOT execution. The added [interop-completion](../../verification/interop-completion/linux/result.json) controls native-worker callbacks to remain in flight in Linux normal and Native AOT execution, verifying GCHandle strong rooting, no reclamation before native quiet, one-time take, continued readability of an independent result owner after operation release, and result release when managed conversion throws. The research fixture's private status codes and partly handwritten coordination code cannot serve as the product D08 ABI or a fully generated wrapper.

Physical leases, logical admission, a single writer for mutable objects, result ownership and Engine/module ownership remain separate requirements. A SafeHandle that delays free cannot replace the Open→Closing admission lock, nor can Arc reference counts alone establish that a worker OS thread has joined. Ordinary modules remain resident for the process lifetime; specialized thread-affine owners use [D09](concurrency-v0.1.md)'s dedicated release scheduling, and finalizers do not wait synchronously.

R07 provides complete research decisions and scope; unselected Qt/Python ownership mechanisms do not constitute indefinite prerequisites for the current C#/Rust design. This design may be accepted after independent review; the full parent-child, mismatched-owner, sustained-race, weak-memory, resource-zeroing and product-package tests in A03/A04/A20/B01 remain separate obligations.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
