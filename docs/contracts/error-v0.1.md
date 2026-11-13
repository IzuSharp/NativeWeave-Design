# C-ERROR-001: Status, domain errors, managed exceptions and Rust panic

Version: 0.3.0; D08 / R11. Author: interop_design. Status: **research/design candidate completed; the registry records the exact reviewed version, content hash and acceptance state; product validation remains in the Delivery phase**. This document is the sole documentation authority for v1 status values and the base ErrorRecord; code is generated from the D03 ABI description, and D02 verifies layout. Illustrative snippets in this document have not been compiled independently; exact evidence for executed research prototypes appears at the end, while full product implementation/platform behavior still requires Delivery validation.

## 1. Goals

Ordinary failures are predictable and diagnosable, with no cross-language exception propagation; error reporting itself does not depend on successfully allocating large strings. Domain semantics are separate from basic interop failures, retaining original provider codes and traceable IDs. Process-fatal failures such as abort, invalid memory access and invalid UCO signatures are not wrapped as falsely recoverable Exceptions.

Ordinary fallible Rust operations use Result; ordinary managed failures map to typed Exceptions or domain Results in natural APIs. FFI carries only fixed-layout statuses and explicitly owned domain data.

## 2. Unified wire status values

`nw_status` is fixed as `uint32_t`; Rust uses u32 and C# uses uint. Do not infer the ABI from C enum size or Rust/C# bool.

| Value | Name | Semantics and constraints |
| --- | --- | --- |
| 0 | OK | This call succeeded; the only success value for ordinary APIs |
| 1 | PENDING | Allowed only by APIs declared as nonblocking try_/poll; not a failure and does not fill ErrorRecord |
| 2 | CANCELED | Only a confirmed terminal operation state; successful request_cancel does not return this value |
| 3 | INVALID_ARGUMENT | Input value/shape violates the contract; does not imply that arbitrary invalid pointers can be safely probed |
| 4 | INVALID_STATE | A valid handle is in a disallowed state, such as a repeated take |
| 5 | OUT_OF_MEMORY | Reportable allocation failure; does not promise to catch allocator abort or every managed OOM |
| 6 | NOT_SUPPORTED | Requested capability is unimplemented; caller may choose a declared alternative path |
| 7 | BUFFER_TOO_SMALL | Caller capacity is insufficient; outputs remain untransferred as specified by the particular API |
| 8 | CALLBACK_FAILED | Ordinary managed-callback failure; distinguish decision/ordinary notification/terminal notification under §6, without rewriting an existing native terminal state or remote effect |
| 9 | NATIVE_PANIC | Successfully caught unwinding panic; the owning Engine is poisoned |
| 10 | ENGINE_POISONED | Reject new business operations; dedicated stop/retire/release control paths remain permitted |
| 11 | CONTRACT_VIOLATION | Adapter/generated interface violates the protocol; not an ordinary user-input error |
| 12 | TIMEOUT | Timeout confirmed by this domain operation; does not mean remote effects were undone |
| 13 | DOMAIN_ERROR | Provider or domain error using the corresponding domain/code and typed payload |

Unknown nonzero values are treated as unknown native failures, without implicit retry or success classification. Unexpected PENDING in a non-try API is also treated as a contract error. New statuses preserve existing value semantics and do not reuse numbers. Status is separate from API-specific result enumerations.

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

The expected initial win-x64/linux-x64 natural layout is size=24, alignment=8, offsets=0/4/8/12/16; R03's actual layout probes and final three-way C/Rust/C# validation confirm it, without extrapolation to untested targets. v1 flags are 0, and reserved bits must not be interpreted independently. `domain=0` is reserved for basic interop; Engine domain IDs are registered by their contracts, and provider codes retain their original meaning rather than being reduced to human-readable messages.

`out_error` is optional diagnostic output, not a second operation deciding the business status. v1 writes a complete 24-byte record, not an ambiguous short prefix populated field by field. The ABI major version selects the layout; this record has no additional embedded version field. D02's `get_abi(out_capacity)` is a different output interface, and its capacity-failure status must not be applied to an already determined business error.

The caller zero-initializes the entire valid buffer **before each call**, then sets the leading `struct_size` to its actual writable capacity (u32). A nonnull pointer must be naturally aligned and point to at least 4 initialized, readable bytes; the capacity value must not exceed the caller's actual writable range, and the buffer must not overlap inputs or other outputs. Validity of the pointer itself remains a caller precondition; the provider does not probe arbitrary bad addresses.

| out_error / original status / input capacity | Provider behavior | Returned status |
| --- | --- | --- |
| null / any | Do not access diagnostic memory | Original business status unchanged |
| nonnull / OK or PENDING / any valid declaration | Write nothing; caller-zeroed fields retain their values | OK or PENDING unchanged |
| nonnull / failure / struct_size 0–23 | Read at most the 4-byte capacity header; write no bytes and return no partial ErrorRecord | Original failure status unchanged; do not replace with BUFFER_TOO_SMALL |
| nonnull / failure / struct_size at least 24 | Construct a complete v1 record locally, then write exactly the first 24 bytes; output struct_size=24, flags=0; caller bytes beyond 24 remain unchanged | Original failure status unchanged |

A capacity value of 0–3 does not revoke the precondition of an at least 4-byte readable header; it only expresses insufficient space for v1 output. Before validating capacity, the provider must not read 24 bytes through a full `nw_error_info_v1` reference. A larger buffer does not permit writes to an unknown tail; future appended fields require extension through an explicit ABI capability/version declaration, and a v1 consumer reads only complete known fields actually returned. Status remains usable if diagnostics are insufficient; generated wrappers prepare the complete 24 bytes on the stack by default. This write requires no allocation or ownership transfer.

correlation_id links logs/traces and may be 0; it is not an identity, permission, unguessable random number or persistent query handle. It must not be used to read expired memory from a shared error table. The base record contains no TLS last-error string, cross-thread borrowed pointer, native exception object or panic payload requiring release.

## 4. Rich domain errors

Database SQLSTATE, constraint names, server diagnostics, HTTP error details and similar data are retained through domain-typed errors or explicitly owned payloads. Variable-length text uses D07 UTF-8 and an explicit allocator/release protocol, with length limits, truncation markers and privacy rules. These must not become mandatory allocations for returning the most basic failure status.

An asynchronous terminal callback carries only a borrowed fixed ErrorRecord, which managed code copies immediately; rich results transfer ownership through D06's one-time take_error/typed take_result. Failure to take over a diagnostic payload still permits return of the base status and release of untransferred resources. Inconsistency between API success and the err field is a contract defect; do not silently select one side to conceal it.

## 5. Managed mapping

Generated adapters map INVALID_ARGUMENT/INVALID_STATE to argument or state exceptions appropriate for the API; CANCELED maps to Task cancellation only from an operation's terminal state; TIMEOUT maps to TimeoutException; domain errors map to provider/domain exceptions; PANIC/POISONED/CONTRACT map to NativeEngineException preserving Engine, operation, status, domain, code and correlation.

Exception messages do not contain raw addresses, GCHandles, credentials or entire user-data payloads. Original Exceptions are retained only inside the managed process; do not attempt to serialize System.Exception across the C ABI. C# 15 unions may represent expected domain branches but are not a mandatory wrapper for all exceptions; boxing of the default union value type and AOT size require measurement.

Cancellation requests, Task state, native quiescence, database-connection reusability and remote effects are recorded separately. Unknown commit outcomes enter domain recovery records even if local resources can already be safely reclaimed; non-idempotent operations are not retried automatically.

Public failures use normal C# exception flow, with raw status fields available for diagnostics; business code need not manipulate wire pointers. The following is an uncompiled API illustration; generated adapters/domain types determine actual fields and construction:

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

UCO entry points are static nongeneric functions with only exactly blittable parameters and return values. Ordinary handleable Exceptions are caught inside the callback adapter; logging, error recording and finally exit paths must likewise prevent ordinary exceptions from crossing the ABI. Failure handling is defined by callback role:

- Synchronous decision callback: return CALLBACK_FAILED or the explicit rejection value for that profile; native code fails closed rather than accepting an unconfirmed security/business decision.
- Ordinary fallible notification callback: latch a binding fault and request stop or fail a domain operation that has not yet terminated; independently occurring remote effects are not undone by this.
- **D06 terminal notification callback: the single native terminal state already exists; responding to callback failure must not publish a second Failure, rewrite Success/Canceled/Failure, or change a database Unknown/committed effect to one that never occurred.** Managed code records the bridge error in a preallocated binding-failure latch and wakes the existing cleanup slot in finally; under D06, the coordinator publishes one managed Faulted result while retaining the original native state and domain effect. If the managed task has already completed, only add bridge/cleanup diagnostics without changing its terminal state. One-time take or abandonment of the result and complete retire/drain/release are still required; CALLBACK_FAILED returned by the callback does not imply rollback of result ownership.

A terminal-notification void profile without a returned status follows the same latch/wakeup/cleanup rules. This rule directly follows [D06 terminal reception and cleanup](async-v0.1.md); “trigger domain failure” must not bypass its single-terminal-state constraint.

Official .NET 11 documentation states that, with runtime marshalling enabled, an invalid nonblittable UCO signature may fail fast when called from native code; catch inside the callback body cannot repair the signature. bool/char use explicit wire types, and the generator rejects invalid signatures; isolated-process tests verify fatal paths. See [official AOT interop documentation](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop).

If error mapping itself fails to allocate, retain the fixed status and existing context without recursive formatting/logging; genuinely unrecoverable OOM, StackOverflow, access violations or fatal runtime states follow process policy. This contract does not promise catch-based recovery from these faults.

## 7. Rust panic policy and candidate comparison

| Approach | Applicability and drawbacks | v1 decision |
| --- | --- | --- |
| Panic for all failures | Error paths are difficult to distinguish; unclear costs and recovery semantics | Reject; use Result for ordinary failures |
| panic=abort | Simple and explicit; any panic terminates the process and cannot be recovered | Permitted as an explicitly declared fatal profile; must not claim NATIVE_PANIC is catchable |
| panic=unwind + boundary catch | Can isolate a caught panic to an Engine, but must handle partial mutations and payload destruction | Default research/release candidate profile; must meet the strict constraints below |
| C-unwind across into C# | Two language runtimes cannot jointly take responsibility for arbitrary exception unwinding | Not used for the public ABI |

Both the original Rust 1.99.1 research and this round's pinned Rust 1.100 source show that catch_unwind catches only unwinding panics; the panic hook runs first, abort cannot be recovered by it, and the returned panic payload may panic again during Drop. Its existence does not prove that modified state remains usable. Relevant official run-crash test source was read only; the actual executions in this round are the independent research subprocesses listed in §13. [R11 report](../research/topics/R11/report.md)

## 8. Catch, poison and cleanup

Each exported entry point executes inside a guard that prevents unwinding across the ABI; asynchronous work must also catch at its actual execution/poll boundary or have a supervisor consume the panic result. Wrapping only the spawn/start entry point cannot catch a later panic inside a worker.

After catching: atomically poison the owning Engine and reject new business operations; a still-trustworthy supervisor publishes one NATIVE_PANIC or ENGINE_POISONED terminal state for accepted operations and requests stop. Dedicated cleanup paths such as cancel, try_retire and release remain permitted; poison must not permanently trap resources behind an uncallable API. However, they may report only quiescence that has actually been proven, never fabricated success.

The v1 error-return path does not format or Drop an unknown panic payload. The isolation path may deliberately retain/forget that payload and record a quarantined-payload count to prevent a second panic from escaping; this is a resource-retention cost after an exception. Each Engine closes new admission after its first panic, but multiple already concurrent tasks may still panic separately, so the quarantine-object bound must account for accepted task counts rather than assume only one payload will be retained. Bytes reachable from an unknown payload may not be precisely measurable and must be marked unknown or conservatively estimated. The host limits isolated Engine counts and decides on restarts; this policy must not be advertised as leak-free operation after unlimited panics.

Cleanup of known-safe fields still uses guards that do not unwind; panics in destruction, panic-hook panics, allocator abort and similar faults may terminate the process. If safe destruction of a resource can no longer be proven, retain/isolate it rather than perform undefined repairs. DisposeAsync reports success only after actual successful cleanup; incomplete isolation must retain diagnostics and unreleased budget. D02 v1 retains native modules until process exit and does not support hot unloading; a future separate hot-unload profile must first prove the absence of active code/callbacks and the exit of every owner, and this future condition must not be interpreted as existing v1 unloading capability.

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

Cleanup entry points need separate guards and do not reuse the check above that rejects business operations after poison. Wrapping the entire Engine in AssertUnwindSafe regardless of its internal state is prohibited; every assertion must explain post-catch state constraints, which operations remain legal, and why partially modified unsafe representations will not be accessed.

## 9. Failure atomicity

Failure before create/start commits does not deliver a partially owned object; the out owner remains null, and acquired temporary resources are rolled back within their own language. After a successful ownership transfer, the new owner releases the resource; a call must not both return failure and require the caller to guess whether adoption already occurred.

Completion results, native retirement and remote transaction effects each have their own records. Error classification defines when an Engine remains usable after an ordinary failure; PANIC and CONTRACT_VIOLATION poison by default, whereas NOT_SUPPORTED and INVALID_ARGUMENT generally do not. Turning a fault into an Exception does not establish that state has recovered.

## 10. Diagnostics, performance and compatibility

The successful hot path constructs no error strings or Exceptions; the fixed record belongs to the cold failure path, and out_error is optional. Record status distributions, callback faults, panic/poison counts, quarantine bytes/objects and cleanup age; measure sampling/logging overhead separately. Correlation propagates across C#/Rust without making a complete diagnostics stack mandatory for every Engine.

An old consumer continues to treat a new status as failure; domain payloads have their own version and capability declarations. The fixed base record strictly follows §3's capacity and write algorithm for a complete v1 record; future added fields require a new ABI version or explicitly negotiated capability and do not authorize writes into a v1 caller's tail or restoration of field-by-field short-prefix rules. Error paths and owned-payload release must be checked for every version combination.

## 11. Verification and Delivery

| ID | Test | Required observation | Delivery |
| --- | --- | --- | --- |
| ER-01 | Every status, unknown values, ErrorRecord capacities 0/3/4/23/24/larger with tail canaries, incorrect domain/payload versions | Original failure status unchanged; no write for a short record and exactly 24 bytes for a complete one; no out-of-bounds access/false success, accurate mapping, balanced releases | A05, A12, A20 |
| ER-02 | Ordinary Rust Result, panic at an exported entry point, asynchronous worker panic | Ordinary failure permits continued use; panic poisons and produces one terminal state | A05, A07, A18 |
| ER-03 | panic=abort, panic hook, another panic on Drop, illegal unwind across FFI | Independent subprocesses exit as expected without killing the test runner | A05, A14, A15 |
| ER-04 | Managed callback throws, error mapping/logging fails | Ordinary exceptions do not cross the ABI, fail closed, complete cleanup | A06, A20 |
| ER-05 | Nonblittable UCO, incorrect calling convention | Analyzer diagnostics; actual process results from isolated AOT negative cases | A12, A14, A15 |
| ER-06 | Poison races with other concurrent operations and cancel/retire/release | New business operations rejected; accepted operations have a terminal state/explicit isolation; quiescence cannot be fabricated | A05, A08, B22 |
| ER-07 | Domain-error text truncation, unknown transaction effect, failed error-payload takeover | No loss of semantics or incorrect retries; memory/privacy boundaries | B05, B07, B22 |

The complete product test matrix above has not yet been implemented; §13 explicitly lists the research subset executed in this round. Formal product acceptance must pin panic policy, compiler, OS/architecture, AOT binary, exit codes, stdout/stderr and fault-injection seeds; globally disabling warnings or changing the oracle to obtain a pass is prohibited.

## 12. Disposition of research questions

Q08 has explicit design decisions: Result/status for ordinary failures, a fixed error record, containment of ordinary managed exceptions at entry points, poison after catching Rust unwind, and separately declared fatal profiles. It may be marked design-resolved after independent review; ER-01–07 remain implementation and production-acceptance obligations. Closure of a research question does not permit unexecuted experiments to be recorded as verified.

## 13. Completion recheck and error evidence (2026-11-13)

The [R11 completion report](../research/topics/R11/report.md) now includes pinned Rust 1.100 source and [7 actual isolated subprocesses](../../verification/interop-completion/panic-linux/result.json): catching ordinary unwind and quarantining an unknown payload returned normally; payload Drop, hook, double panic during cleanup, extern-C escape and the abort profile each caused the expected unsuccessful termination. Raw stdout/stderr/exit results, source hashes and compilation parameters are retained; these local results are not extrapolated into proof of full Engine poison recovery.

The [main probe](../../verification/interop-completion/linux/result.json) actually verifies containment of ordinary managed callback exceptions within the method and finally release on result-conversion exceptions; the [invalid UCO probe](../../verification/interop-completion/uco-invalid-linux/result.json) terminates the subprocess with an unhandled InvalidProgramException before entering the method body when native code calls a char/bool callback in both normal and AOT execution. The latter shows that catch inside the method cannot correct the signature, without claiming verification of every process-fatal mechanism or external-catch semantics.

This document remains the sole authority for wire statuses. Private experiment enumerations must remain experimental data and must not be written back as new numbers in this contract. Error semantics, isolation costs and cleanup interfaces are sufficient to guide implementation; formal design acceptance awaits independent review, while complete ER-01–07 product validation, new Windows fatal cases and long-running isolation-budget validation remain in their Delivery phase.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
