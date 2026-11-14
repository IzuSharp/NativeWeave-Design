# C-ERROR-001: Status, domain errors, managed exceptions and Rust panic

Version: 0.4.0; D08 / R11. Author: interop_design. Status: **Research/design candidate complete; the registry records the exact reviewed version, content hash and acceptance status; product verification remains in Delivery**. This file is the sole documentary authority for v1 status values and the base ErrorRecord; generated code comes from the D03 ABI description, and D02 verifies layout. The illustrative snippets in this file have not been compiled separately; see the exact evidence at the end for executed research prototypes. Full product implementation/platform behavior still requires Delivery verification.

## 1. Goals

Ordinary failures are predictable and diagnosable, with no cross-language exception propagation; error reporting itself does not depend on successfully allocating large strings. Domain semantics are separate from basic interop failures, preserving original provider codes and traceable IDs. Process-fatal faults such as abort, invalid memory access and illegal UCO signatures are not wrapped in falsely recoverable Exceptions.

Rust ordinary fallible operations use Result; managed ordinary failures map to typed Exceptions or domain Results in natural APIs. FFI transfers only fixed-layout status and explicitly owned domain data.

## 2. Unified wire status values

`nw_status` is fixed as `uint32_t`; Rust uses u32 and C# uses uint. Do not infer the ABI from C enum size or Rust/C# bool.

| Value | Name | Semantics and constraints |
| --- | --- | --- |
| 0 | OK | This call succeeded; the sole success value for ordinary APIs |
| 1 | PENDING | Permitted only for APIs declared as non-blocking try_/poll; not a failure, and does not populate ErrorRecord |
| 2 | CANCELED | Only a confirmed terminal operation state; successful request_cancel does not return this value |
| 3 | INVALID_ARGUMENT | Input value/shape violates the contract; does not imply arbitrary invalid pointers can be probed safely |
| 4 | INVALID_STATE | A valid handle is in a disallowed state, such as repeated take |
| 5 | OUT_OF_MEMORY | Reportable allocation failure; does not promise to catch allocator abort or all managed OOM |
| 6 | NOT_SUPPORTED | Requested capability is not implemented; caller may select a declared alternative route |
| 7 | BUFFER_TOO_SMALL | Caller capacity is insufficient; output remains untransferred according to the specific API contract |
| 8 | CALLBACK_FAILED | Ordinary managed-callback failure; §6 distinguishes decision/ordinary notification/terminal notification, without rewriting an existing native terminal state or remote effect |
| 9 | NATIVE_PANIC | Successfully caught unwinding panic; the owning Engine is poisoned |
| 10 | ENGINE_POISONED | Reject new business operations; permit dedicated stop/retire/release control paths |
| 11 | CONTRACT_VIOLATION | Adapter/generated interface violates the protocol; not an ordinary user-input error |
| 12 | TIMEOUT | Timeout confirmed by that domain operation; does not mean remote effects were undone |
| 13 | DOMAIN_ERROR | Provider or domain error, using the corresponding domain/code and typed payload |

Unknown nonzero values are treated as unknown native failures, without implicit retry or interpretation as success. An unexpected PENDING on a non-try API is also a contract error. New statuses preserve the semantics of existing values without reusing numbers. Status is separate from API-specific result enums.

## 3. Fixed ErrorRecord

```c
typedef struct nw_error_info_v1 {
    uint32_t struct_size;
    uint32_t domain;
    int32_t  code;
    uint32_t flags;
    uint64_t correlation_id;
} nw_error_info_v1;
```

The initial expected natural layout on win-x64/linux-x64 is size=24, alignment=8, offsets=0/4/8/12/16; R03's actual layout probe and final C/Rust/C# verification confirm it, without extrapolation to untested targets. v1 flags are 0, and reserved bits must not be interpreted independently. `domain=0` is reserved for base interop; Engine domain IDs are registered by their contracts, and provider codes retain their original meaning rather than leaving only a human-readable message.

`out_error` is optional diagnostic output, not a second operation that determines business status. v1 writes a complete 24-byte record rather than an ambiguous field-by-field short prefix. The ABI major version selects the layout; this record has no additional embedded version field. D02's `get_abi(out_capacity)` is a different output interface, and its capacity-failure status must not be applied to an already-determined business error.

**Before every call**, the caller zero-initializes the entire valid buffer, then sets the leading `struct_size` to its actual writable capacity (u32). A non-null pointer must be naturally aligned and point to at least 4 initialized, readable bytes; the capacity value must not exceed the caller's actual writable range, and the buffer must not overlap inputs or other outputs. Pointer validity remains a caller precondition; providers do not probe arbitrary bad addresses.

| out_error / original status / input capacity | Provider behavior | Returned status |
| --- | --- | --- |
| null / any | Do not access diagnostic memory | Original business status unchanged |
| Non-null / OK or PENDING / any valid declaration | Write nothing; caller-zeroed fields remain unchanged | OK or PENDING unchanged |
| Non-null / failure / struct_size from 0–23 | Read at most the 4-byte capacity header; write no bytes and return no partial ErrorRecord | Original failure status unchanged, not replaced by BUFFER_TOO_SMALL |
| Non-null / failure / struct_size at least 24 | Construct a complete v1 record locally, then write exactly the first 24 bytes; output struct_size=24, flags=0; caller bytes beyond 24 remain unchanged | Original failure status unchanged |

Capacity values 0–3 do not revoke the precondition of an at-least-4-byte readable header; they only express insufficient space for v1 output. Before validating capacity, the provider must not use a complete `nw_error_info_v1` reference to read 24 bytes. A large-capacity buffer does not permit writing an unknown tail; future appended fields require expansion defined by an explicit ABI capability/version, and a v1 consumer reads only complete known fields actually returned. Status remains usable when diagnostic information is insufficient; generated wrappers prepare a complete 24-byte record on the stack by default. This write neither allocates nor transfers an owner.

correlation_id connects logs/traces and may be 0; it does not represent identity, authorization, an unguessable random value or a persistent query handle. It must not be used to read expired memory from a shared error table. The base record contains no TLS last-error string, cross-thread borrowed pointer, native exception object or panic payload requiring release.

## 4. Rich domain errors

Database SQLSTATE, constraint names, server diagnostics, HTTP error details and similar information are preserved through typed domain errors or explicitly owned payloads. Variable text uses D07 UTF-8 and explicit allocator/release protocols, with length limits, truncation markers and privacy rules. These allocations must not be prerequisites for returning the most basic failure status.

An asynchronous terminal callback passes only a borrowed fixed ErrorRecord, which managed code copies immediately; rich results acquire ownership through D06's one-time take_error/typed take_result. Failure to acquire a diagnostic payload still permits returning the base status and releasing untransferred resources. An API success return inconsistent with err fields is a contract defect; silently choosing one side must not conceal the error.

## 5. Managed mapping

Generated adapters map INVALID_ARGUMENT/INVALID_STATE to argument or state exceptions appropriate to the API; CANCELED maps to Task cancellation only from a terminal operation state; TIMEOUT maps to TimeoutException; domain errors map to provider/domain exceptions; PANIC/POISONED/CONTRACT map to NativeEngineException preserving Engine, operation, status, domain, code and correlation.

Exception messages contain no raw addresses, GCHandles, credentials or entire user data. Original Exceptions remain inside the managed process; do not attempt to serialize System.Exception across the C ABI. C#15 union may represent expected domain branches but is not a mandatory wrapper for all exceptions; default-union value-type boxing and AOT size require measurement.

Cancellation requests, Task status, native quiescence, database-connection reusability and remote effects are recorded separately. An Unknown commit result must enter a domain recovery record even when local resources can already be safely reclaimed; non-idempotent operations are not automatically retried.

Public failures use normal C# exception flow; raw status fields support diagnostics without requiring business code to manipulate wire pointers. The following is an uncompiled API illustration, with actual fields and construction determined by generated adapters/domain types:

```csharp
try
{
    using var result = await engine.ExecuteAsync(input, cancellationToken);
    await result.CopyToAsync(output, cancellationToken);
}
catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
{
    // The operation reported cancellation; this is not a transaction rollback proof.
}
catch (NativeEngineException error)
{
    logger.LogError(error, "Engine {Engine}; status {Status}; trace {Correlation}",
        error.EngineId, error.StatusCode, error.CorrelationId);
    throw; // no implicit retry of possibly effectful work
}
```

## 6. Managed→native callback boundary

A UCO entry point is a static, non-generic function with only exactly blittable parameters and return values. Ordinary handleable Exceptions are caught within the callback adapter; logging, error recording and finally exit paths must also prevent ordinary exceptions from crossing the ABI. Failure disposition is defined by callback role:

- Synchronous decision callback: return CALLBACK_FAILED or the rejection value explicitly defined by that profile; native code fails closed without accepting an unconfirmed security/business decision.
- Ordinary fallible notification callback: latch a binding fault and request stop or fail a domain operation that has not yet terminated; independently occurring remote effects are not thereby undone.
- **D06 terminal notification callback: the sole native terminal state already exists; callback failure must not cause a second Failure publication, rewrite Success/Canceled/Failure, or change a database Unknown/committed effect to not having occurred.** Managed code records the bridging error in a preallocated binding-failure latch and wakes the existing cleanup slot in finally; the coordinator publishes one managed Faulted result under D06 while retaining the original native status and domain effect. If the managed task has already completed, only add bridge/cleanup diagnostics, without changing its terminal state. A one-time take or abandonment of the result and full retire/drain/release are still required; CALLBACK_FAILED returned by a callback does not imply rollback of result ownership.

A void terminal-notification profile with no returned status follows the same latch/wakeup/cleanup rules. This rule directly follows [D06 terminal reception and cleanup](async-v0.1.md); “triggering domain failure” must not bypass its single-terminal-state constraint.

Official .NET11 documentation states that, when runtime marshalling is enabled, an invalid non-blittable UCO signature can fail fast on native invocation; catch inside the callback method body cannot fix the signature. bool/char use explicit wire types, and the generator rejects illegal signatures; only isolated-process tests verify the fatal path. See [official AOT interop](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop).

If error mapping itself fails to allocate, retain fixed status and the existing context without recursive formatting/logging; genuinely unrecoverable OOM, StackOverflow, access violations or fatal runtime states follow process policy. This contract does not promise that catch can recover from these faults.

## 7. Rust panic policy and candidate comparison

| Approach | Applicability and drawbacks | v1 decision |
| --- | --- | --- |
| Panic for every failure | Hard to distinguish error paths; unclear cost and recovery semantics | Rejected; ordinary failures use Result |
| panic=abort | Simple and explicit; every panic terminates the process and cannot be recovered | Permitted as an explicitly declared fatal profile; must not claim catchable NATIVE_PANIC |
| panic=unwind + boundary catch | Can isolate a caught panic to an Engine, but must handle partial mutations and payload destruction | Default research/release candidate profile, subject to the strict constraints below |
| C-unwind crossing into C# | Cannot make two language runtimes jointly handle arbitrary exception unwinding | Not used for the public ABI |

The original Rust1.99.1 research and this round's pinned Rust1.100 source both show that catch_unwind catches only unwinding panics; the panic hook executes first, abort is not recovered, and the returned panic payload may panic again during Drop. Its existence does not prove that modified state remains usable. Relevant official run-crash test source was read only; this round actually executed the separate research subprocesses listed in §13. [R11 report](../research/topics/R11/report.md)

## 8. Catching, poison and cleanup

Every exported entry point executes inside a guard that prevents unwinding across the ABI; asynchronous work must additionally be caught at its actual execution/poll boundary or have a supervisor consume its panic result. Wrapping only the spawn/start entry point cannot catch a later worker panic.

After catching: atomically poison the owning Engine and reject new business operations; a still-trusted supervisor publishes one NATIVE_PANIC or ENGINE_POISONED terminal state for accepted operations and requests stop. Dedicated cleanup paths such as cancel, try_retire and release remain permitted; poison must not permanently trap resources behind an API that cannot be called. However, they may report only quiescence that has actually been proven, without fabricating success.

The v1 error-return path neither formats nor Drops unknown panic payloads. The isolation path may deliberately retain/forget such a payload and record a quarantined-payload count to avoid a second panic crossing the boundary; this is a resource-retention cost after an exception. Each Engine closes new admission after its first panic, but multiple already-running tasks may still panic separately, so quarantine-object limits must account for the number of accepted tasks rather than assume only one payload will be retained. Bytes reachable from an unknown payload may not be exactly countable and must be marked unknown/conservatively estimated. The host bounds the number of isolated Engines and decides on restart; this policy must not be advertised as leak-free operation after unlimited panics.

Cleanup of known-safe fields still uses guards that do not unwind; a panic during destruction, a panic in a panic hook, allocator abort and similar faults may terminate the process. If a resource cannot be proven safe to destroy, retain/isolate it rather than attempt undefined repair. DisposeAsync reports success only after actual successful cleanup; incomplete isolation retains diagnostics and unreleased budgets. D02 v1 keeps native modules loaded until process exit and does not support hot unload; any future separate hot-unload profile must first prove no active code/callbacks and exit of all owners. That future condition must not be interpreted as existing v1 unload capability.

```rust
// Design skeleton only; engine state and entry preconditions must be verified.
fn guarded_entry<F>(engine: &EngineState, body: F) -> u32
where F: FnOnce() -> Result<(), EngineError> + std::panic::UnwindSafe
{
    if engine.is_poisoned() { return ENGINE_POISONED; }
    match std::panic::catch_unwind(body) {
        Ok(Ok(())) => OK,
        Ok(Err(error)) => map_regular_error_without_panicking(error),
        Err(payload) => {
            engine.poison_without_panicking();
            std::mem::forget(payload); // recorded quarantine; not normal leak-free recovery
            NATIVE_PANIC
        }
    }
}
```

Cleanup entry points need separate guards and must not reuse the business-rejection check after poison shown above. Wrapping the entire Engine in AssertUnwindSafe regardless of internal state is prohibited; each assertion must explain post-catch state constraints, which operations remain legal, and why a partially modified unsafe representation will not be accessed.

## 9. Failure atomicity

Failure before create/start commits does not deliver a partially owned object; the out owner remains null, and acquired temporary resources are rolled back within their own language. After successful ownership transfer, the new owner releases the resource; an API must not both return failure and require the caller to guess whether adoption has occurred.

Completion results, native retirement and remote transaction effects each have their own records. Error classification defines when an Engine may remain usable after ordinary failure; PANIC and CONTRACT_VIOLATION poison by default, while NOT_SUPPORTED and INVALID_ARGUMENT ordinarily do not. Converting a fault into an Exception does not establish state recovery.

## 10. Diagnostics, performance and compatibility

The successful hot path does not construct error strings or Exceptions; the fixed record serves the cold failure path, and out_error is optional. Record status distributions, callback faults, panic/poison counts, quarantine bytes/objects and cleanup age; measure sampling/logging overhead separately. Correlation propagates across C#/Rust without forcing a complete diagnostics stack to become a dependency of every Engine.

An old consumer encountering a new status remains on the failure path; domain payloads have their own versions and capability declarations. The fixed base record strictly follows section 3's complete-v1-record capacity and write algorithm; future added record fields require a new ABI version or explicitly negotiated capability definition, without permitting writes to a v1 caller's tail or reinstating field-by-field short-prefix rules. Every version combination must test error paths and owned-payload release.

## 11. Verification and Delivery

| ID | Test | Required observation | Delivery |
| --- | --- | --- | --- |
| ER-01 | Every status, unknown values, ErrorRecord capacities 0/3/4/23/24/larger with tail canary, wrong domain/payload versions | Original failure status unchanged; short records unwritten; complete records write only 24 bytes; no out-of-bounds access/false success, accurate mapping, balanced release | A05, A12, A20 |
| ER-02 | Ordinary Rust Result, exported-entry panic, asynchronous-worker panic | Ordinary failure permits continued use; panic poisons and publishes terminal state once | A05, A07, A18 |
| ER-03 | panic=abort, panic hook, panic again during Drop, illegal unwind across FFI | Independent subprocesses exit as expected without killing the test runner | A05, A14, A15 |
| ER-04 | Managed callback throws, error mapping/logging fails | Ordinary exceptions do not cross the ABI, fail-closed behavior, complete cleanup | A06, A20 |
| ER-05 | Non-blittable UCO, wrong calling convention | Analyzer diagnostics; actual process outcomes for isolated AOT negative cases | A12, A14, A15 |
| ER-06 | Poison races with other concurrent operations and cancel/retire/release | New business operations rejected; accepted operations reach terminal state/explicit isolation; quiescence is not fabricated | A05, A08, B22 |
| ER-07 | Domain-error text truncation, unknown transaction effects, failed error-payload acquisition | Semantics preserved, no incorrect retry, memory/privacy boundaries | B05, B07, B22 |

The full product test matrix above has not yet been implemented; §13 explicitly lists the research subset executed this round. Formal product acceptance must pin panic policy, compiler, OS/architecture, AOT binary, exit codes, stdout/stderr and fault-injection seeds; globally disabling warnings or changing the oracle to obtain a pass is prohibited.

## 12. Research-question disposition

Q08 has an explicit design decision: Result/status for ordinary failures, a fixed error record, managed entry-point containment of ordinary exceptions, poison after Rust unwind capture, and separately declared fatal profiles. It may be marked design-resolved after independent review; ER-01–07 remain implementation and production-acceptance obligations. Closing a research question does not permit recording unexecuted experiments as verified.

## 13. Completion review and error evidence for this round (2026-11-13)

[The R11 completion report](../research/topics/R11/report.md) now includes pinned Rust1.100 source and [7 actual isolated subprocesses](../../verification/interop-completion/panic-linux/result.json): catching ordinary unwind and quarantining an unknown payload return normally; payload Drop, hooks, cleanup double panic, extern-C escape and the abort profile each produce the expected non-successful termination. Raw stdout/stderr/exit, source hashes and compiler arguments are retained; these local results are not extrapolated into proof of full Engine poison recovery.

[The main probe](../../verification/interop-completion/linux/result.json) actually verifies containment of an ordinary managed-callback exception within the method and finally release after a result-conversion exception; the [invalid UCO probe](../../verification/interop-completion/uco-invalid-linux/result.json) terminates subprocesses with an unhandled InvalidProgramException before entering the method body when native code invokes char/bool callbacks under both normal/AOT execution. The latter shows that catch inside the method cannot correct the signature, without claiming verification of every process-fatal mechanism or outer-catch semantics.

This file remains the sole authority for wire status. Private experimental enums must remain experimental data and must not be written back as new numbers in this contract. Error semantics, isolation costs and cleanup interfaces are sufficient to guide implementation; formal design acceptance awaits independent review, while full ER-01–07 product verification, new Windows fatal cases and long-duration isolation-budget verification remain in their Delivery phase.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

The exact public exception signatures are in [Interop](../api/interop.md) and the declaration inventory. NativeEngineException preserves wire error diagnostics for native failures; pre-native EngineLoadException failures have no fabricated native success/error record, so unavailable wire fields are nullable. Rich native failures populate the documented diagnostic tuple. Database/Server ordinary errors use domain exceptions; argument/disposal/cancellation/timeout follow BCL categories. Expected absence uses explicit cardinality/Try semantics. Neither a generic Result wrapper nor an IsTransient flag permits automatic replay after an unknown transaction effect. A05/A02/B07/B20 own XML exception semantics and secret-redacted diagnostics.
