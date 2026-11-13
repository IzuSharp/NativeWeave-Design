# R11: Error, Rust panic and managed-callback exception boundaries

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; independent review pending**. The deliverable is the [D08 Error contract](../../../contracts/error-v0.1.md), the sole documentation authority for status numbers and the base ErrorRecord. Code examples are uncompiled; fatal behavior and actual AOT have not yet been executed.

## 1. Inputs, requirements and non-goals

Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R11 revision `0.1.1`, packet hash `4450ce8ebaea49e3040dcfec110453d2deca4958c633ef16269259d019e1fdd5`; D08 revision `0.1.1`, hash `64665225e71ff86c0dfa9eb006049333de7dc48bbf8c73624218e07ab68320c9`, matching the pinned remote graphs and local bytes.

Ordinary failures must not unwind across language boundaries, error reporting must not depend on another successful string allocation, asynchronous errors must not read TLS messages overwritten by the next call, and provider domain information must not be reduced to untyped text. Ordinary errors, contract defects, successfully caught panics and process-fatal faults must be distinguished.

Non-goals include recovery from access violations, abort, arbitrary heap corruption, double panic or every OOM; safe unwinding of arbitrary Rust/C++ exceptions across the C# runtime is not promised either. Ordinary Rust logic uses Result, and ordinary C# APIs use typed Exceptions or domain Results. Applications need not know native allocators or panic-payload layouts.

## 2. Source, official documentation and actual coverage

| Source | Pinned identity | Read scope |
| --- | --- | --- |
| rust-lang/rust 1.99.1 | `58cf8f9c35b355199727627d07ae34a4e2846d67` | std::panic::catch_unwind documentation, panicking implementation, panic-safety trait tests and 3 run-crash tests |
| Official .NET Native AOT documentation | Observed 2026-11-12; page updated 2026-11-04 | .NET 11 invalid UCO signatures and fail-fast limitations |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | Ordinary exception handling inside SignalAwaiter/GCHandleBridge UCO methods |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | Fail-closed TLS validation, asynchronous failure propagation, native error strings and statuses |

See [evidence.json](evidence.json) for source line ranges, blobs and limitations. [coverage.json](coverage.json) retains the unread UniFFI error bridge, runtime-internal UCO entry points and allocator OOM implementations; no source commit was fabricated from an official page. Upstream panic test source was read, but none of those tests were executed.

## 3. Actual boundaries of ordinary Rust failures and catch_unwind

Pinned [`std/src/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panic.rs#L290-L360) and the [stable catch_unwind documentation](https://doc.rust-lang.org/stable/std/panic/fn.catch_unwind.html) explain that catch_unwind catches only unwinding panics; ordinary fallible operations should use Result; abort is not recovered; the panic hook runs before the catch; catching a foreign exception has no generally dependable outcome guarantee; and the returned panic payload may panic again when destroyed. [R11-S01, O01]

[`panicking.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panicking.rs#L495-L600) uses a runtime intrinsic and ManuallyDrop state at the catch boundary to transfer closure results/exception payloads. These internals show that error payloads are also owners with destruction responsibilities; returning Err is not equivalent to safe disposal of every exception resource. [R11-S02]

NativeWeave selects panic=unwind as the default recoverable candidate profile, catching at entry and asynchronous-work boundaries and poisoning the owning Engine after a catch; ordinary failures still use Result. panic=abort is only an explicitly declared fatal profile and cannot claim to return NATIVE_PANIC. C-unwind does not enter the public C ABI. AssertUnwindSafe is not a license to repair arbitrary damaged state; each use must explain which representations remain valid after failure and which cleanup can execute safely. [R11-D01]

## 4. Counterexamples from the tests read

[`panic-in-ffi.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-ffi.rs) is a run-crash test: panic inside non-unwind FFI cannot be imagined as an ordinary return value. It includes an object observing destruction and declares expected process failure. [R11-T01]

[`panic-in-cleanup.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-cleanup.rs) triggers another panic during destruction while unwinding; the test has a special MSVC ignore annotation, so a Unix error-output string cannot directly become the Windows acceptance criterion. [R11-T02]

[`panic-in-hook.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-hook.rs) panics again inside a panic hook, providing another fatal path for which a catch body cannot guarantee recovery. [`library/std/tests/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/tests/panic.rs) checks static safety-trait relationships, not execution proof of all FFI containment. [R11-T03, T04]

No Rust compiler was available and these tests were not run in this round; “read test source” and “test passed” are strictly distinct. Formal verification must separately cover unwind, abort, payload Drop, hooks and cleanup double panic in subprocesses, recording target toolchains, exit codes and portable behavioral classifications rather than requiring identical error text across platforms.

## 5. Managed callback exceptions and UCO signatures

Godot [`SignalAwaiter`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs) and [GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs) handle ordinary Exceptions inside UCO methods; YAHA's TLS-validation callback returns false on ordinary exceptions. They provide concrete shapes for boundary containment and fail-closed behavior, not proof that any catch can contain the entire runtime. [R11-S03, S04]

The [official Native AOT interop documentation](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop) explicitly describes .NET 11: with runtime marshalling enabled, a native call to an invalid UCO signature with nonblittable parameters may trigger InvalidProgramException and fail fast; catch in the method body cannot repair the signature. [R11-O02] NativeWeave therefore uses generated static nongeneric exactly blittable signatures, maps bool/char to explicit wire types, and requires errors to be caught by generation/compilation diagnostics and subprocess negative cases.

Boundary catches must also account for failures in decoding, logging and finally actions themselves. Callback exceptions are recorded through existing contexts and fixed statuses; error paths do not recursively create large numbers of strings, Exceptions or queued Tasks. StackOverflow, runtime-fatal faults, access violations and OOM preventing continuation remain subject to host-process policy rather than masquerade as ordinary recoverable failures.

## 6. Choice of base statuses and error layout

| Candidate | Problem | Choice |
| --- | --- | --- |
| TLS last-error string pointer | Wrong thread under multithreading/async, overwritten by the next call, unclear release responsibility | Not used for Core's public error contract |
| Allocate owned text for every error | Rich information, but may fail to report the original error under OOM | Optional domain details only |
| Fixed status + fixed record | Reports basic failure without string allocation; straightforward layout verification | v1 foundation |
| Arbitrary Exception/panic objects across the ABI | Layout/destruction/runtime semantics cannot be unified | Reject |

D08 uses u32 status: 0 is OK; 1=PENDING only for declared try/poll APIs; 2=CANCELED only for a confirmed terminal state; the remaining 3–13 are argument/state/OOM/capability/capacity/callback/panic/poison/contract/timeout/domain errors, respectively. D08 alone owns the full numbering to avoid drift between duplicate tables. Unknown nonzero values fail without implicit retry.

The base ErrorRecord is `u32 struct_size, u32 domain, i32 code, u32 flags, u64 correlation_id`, expected to occupy 24 bytes on x64. The record has no cross-thread borrowed string, TLS-error pointer or panic object; callbacks copy it immediately on receipt. Correlation is for diagnostics only, not permissions or a persistent-memory lookup key. R03 owns the C-layout probe; final Rust/C#/C agreement and AOT still require actual validation. [R11-D02]

Detailed provider errors use typed owned results/UTF-8 payloads, following D07 release and D06 one-time take protocols. Failed takeover still permits basic status reporting while native code retains the owner. The successful hot path constructs no error strings; failure to allocate rich diagnostics does not lose the basic error.

## 7. Existing operations and resources after poison

Wrapping only spawn/start with catch_unwind cannot catch a later worker panic. Every asynchronous task must catch at its actual execution/poll boundary, or a still-trustworthy supervisor must consume its failure. The first panic atomically poisons the Engine and rejects new business work; each existing operation publishes NATIVE_PANIC/ENGINE_POISONED once and requests stop. Completed results or results with known effects must not be blindly overwritten; the domain retains knowledge of actual effects.

stop/cancel/try_retire/release must remain accessible through dedicated cleanup paths rather than a business gate that “rejects everything when poisoned.” But publishing failure to managed code does not permit fabricated quiescence; remaining workers, callbacks and external control calls must still drain. If the supervisor is no longer trustworthy or resource representations are damaged, isolate and retain owners/budget rather than force a free to make DisposeAsync falsely succeed. [R11-D01]

Dropping a panic payload may panic again. The v1 error-return path does not format/destroy unknown payloads; the poison path may deliberately forget them and record quarantine counts, which is not ordinary leak-free recovery. The Engine closes new admission, and the host limits isolated Engine counts and decides on restarts; multiple existing concurrent tasks may still panic separately, so quarantine budget must account for the accepted-task limit rather than falsely claim only one payload is retained. Bytes reachable from an unknown payload may not be precisely counted; record object counts and a conservative unknown-byte state.

Cleanup of known-safe fields also needs a boundary policy that does not unwind; double panic during destruction, hook panic and allocator abort may still terminate the process. A future isolated subprocess Engine could strengthen the fault domain, but it is not a mandatory new runtime or product scope in this round.

## 8. Failure atomicity and scenarios

create failure leaves the out owner empty and rolls back temporary resources; start rejection leaves no callback obligations; business errors after committed start go through the terminal path. Ordinary callback failure returns CALLBACK_FAILED and requires a definite stop/failure disposition. Successful result take transfers ownership and zeroes native state; failed take leaves output empty and native code retains the owner. Error strings do not determine whether transfer occurred.

The normal example is C# await returning an owned result released through using; the cancellation example is a caller token requesting stop while the terminal state still determines eventual native success/cancellation; the exception example is NativeEngineException retaining Engine/status/domain/code/correlation so the application decides whether to retry. D08's uncompiled skeleton shows only the guard shape; copying it with its omitted state and cleanup logic does not establish completed product implementation.

## 9. Verification tasks and performance accounting

D08 ER-01–07 maps to A02/A04/A06/A07/A14/A15/A18/A20/A21/B22: no error allocations on success paths, mapping every error/unknown value, error-struct capacity and version, OOM and failed detail takeover, ordinary managed-callback exceptions, invalid UCO and Rust fatal subprocesses, one terminal state and actual drain for existing operations after poison, and quarantine/resource budgets under long-running workloads.

Separately record status counts, error-detail allocations, panic/poison counts, accepted task counts, unretired bytes, quarantined objects/unknown bytes, cleanup age and fatal-subprocess exit behavior. A “caught a panic” microbenchmark does not prove full Engine recovery, and error-logging overhead must not be hidden outside successful-path throughput statistics.

Windows/Linux unwind toolchains, panic strategy, C calling conventions and AOT binary hashes enter the formal manifest. R11 did not execute these validations; R03 C-layout results also cannot substitute for Rust/C#/AOT cross-language agreement.

## 10. Design closure and further review

Q08 has explicit, reviewable decisions: a fixed error foundation, typed owned details, containment of ordinary managed exceptions, poison after catching unwind, explicit fatal-profile declarations, and separation of actual cleanup from error outcomes. The design research question may close after independent review passes, while ER-series implementation and production validation remain pending.

R03 reviews ErrorRecord prefixes and status evolution; R08 reviews failure inside callbacks, exit and prevention of duplicate ownership; R34 reviews error privacy, budgets and untrusted parameters; R12 reviews worker supervisors and draining after poison. UniFFI and runtime-internal UCO entry points remain unread, so the task overall remains partially_evidenced; these gaps are neither hidden nor used to leave every decision to the user.

Licensing: the full pinned Rust LICENSE-MIT and LICENSE-APACHE texts were read; the core standard library is dual-licensed, and particular files reused in future still follow their own declarations. Godot and YAHA MIT licenses were read. This report paraphrases mechanisms and presents new NativeWeave design rather than copy large source passages.

## Current completion review — Rust1.100 and actual fatal subprocess evidence

Rust1.100 source `0ef1bc386059596dada8fb65b50425aab2ea637a`, `library/std/src/panic.rs`315–410, reaffirms unwind-only catch, hook-before-catch and panic-on-payload-Drop. This is the current fixed-source supplement to the historical1.99.1 review, not an invented rewrite of that old source identity. UniFFI's actual Future polling boundary catches poll panics and stops polling the failed future; a catch around spawn alone would not have that scope.

Seven actual Rust1.100 child-process cases are now preserved in `verification/interop-completion/panic-linux`: caught ordinary unwind and intentionally retained payload succeed; payload Drop panic, panic hook panic, cleanup double panic, non-unwind C-ABI panic and panic=abort through catch terminate unsuccessfully with recorded stderr/exit codes. The payload-retention positive case intentionally keeps that payload: it is evidence for quarantine behavior, not leak-free recovery. These cases do not prove all concurrent engine poison paths or OOM behavior.

The new C#/Rust completion probe also injects an ordinary managed callback exception inside actual UCO, catches it before crossing FFI, and verifies no result owner survives an injected DTO conversion failure. Normal and actual Linux Native AOT runs are separately recorded. Original two-OS prepublication native panic evidence remains at its original identity.

D08 remains the sole authority for status numbers/error records; the experiment's private constants must not be promoted into it. Fatal invalid-UCO signatures, arbitrary corrupt pointers and every target's fatal text/exit conventions remain isolated product tests; a callback catch cannot fix an invalid signature. Error/result/effect/cleanup are separate facts, and quarantine never creates fake DisposeAsync success. The current error-boundary design is ready for exact-content independent review; future A05/A06/A07/A14/A15/A20/B22 conformance is distinct from research acceptance.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
