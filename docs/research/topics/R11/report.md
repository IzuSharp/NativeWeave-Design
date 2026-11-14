# R11: Errors, Rust Panics, and Managed Callback Exception Boundaries

**Current completion (2026-11-13):** source-driven research/design is ready for exact-content independent review. The original dated report below is preserved as a historical increment; its unexecuted statements describe that increment. Current evidence/coverage contain `completion_2026_11_13` and immutable later execution records.

Date: 2026-11-12. Author: interop_design. Status: **partially_evidenced; design decision recorded; independent review pending**. The delivery is the [D08 Error contract](../../../contracts/error-v0.1.md), which is the sole documentary authority for status numbers and the base ErrorRecord. Code examples are uncompiled; fatal behavior and actual AOT have not yet been executed.

## 1. Inputs, Requirements, and Non-Goals

Design baseline `1f7d89aa754647a6a530fa34a49acc4b0f5d9997`; Plan baseline `da9e4a6337a5af0ec3d5e40a4695a2760d6ac5f5`. R11 revision `0.1.1`, task packet hash `4450ce8ebaea49e3040dcfec110453d2deca4958c633ef16269259d019e1fdd5`; D08 revision `0.1.1`, hash `64665225e71ff86c0dfa9eb006049333de7dc48bbf8c73624218e07ab68320c9`, matching the pinned remote graph and local bytes.

Ordinary failures must not unwind across language boundaries; error reporting must not depend on another successful string allocation; asynchronous errors must not read a TLS message overwritten by the next call; provider-domain information must not collapse into untyped text. Ordinary errors, contract defects, successfully caught panics, and process-fatal failures must be distinguished.

Non-goals are recovery from access violations, abort, arbitrary heap corruption, double panic, or every OOM; no guarantee is made that arbitrary Rust/C++ exceptions can unwind safely across the C# runtime. Ordinary Rust logic uses Result; ordinary C# APIs use typed Exceptions or domain Results. Applications need not know native allocators or panic-payload layouts.

## 2. Source, Official Documentation, and Actual Coverage

| Source | Pinned identity | Scope read |
| --- | --- | --- |
| rust-lang/rust 1.99.1 | `58cf8f9c35b355199727627d07ae34a4e2846d67` | std::panic::catch_unwind documentation, panicking implementation, panic-safety trait tests, and 3 run-crash tests |
| Official .NET Native AOT documentation | Observed 2026-11-12; page updated 2026-11-04 | Invalid .NET11 UCO signatures and fail-fast limitations |
| Godot | `069458825a8e4a01938a176372c0709ab6fd9dc3` | Ordinary exception handling within UCO in SignalAwaiter/GCHandleBridge |
| YAHA | `c386c1cc48d2e56711c15286cf2769353fdccf07` | TLS verification fail-closed behavior, asynchronous failure propagation, native error strings and status |

See [evidence.json](evidence.json) for source line ranges, blobs, and limitations. [coverage.json](coverage.json) retains the UniFFI error bridge, runtime UCO entry internals, and allocator OOM implementation as unread; no source commit is invented from an official documentation page. Upstream panic-test source was read, but none of the tests were executed.

## 3. Ordinary Rust Failures and the Actual catch_unwind Boundary

The pinned [`std/src/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panic.rs#L290-L360) and [stable catch_unwind documentation](https://doc.rust-lang.org/stable/std/panic/fn.catch_unwind.html) explain that catch_unwind catches only unwinding panics; ordinary fallible operations should use Result; abort is not recoverable; the panic hook runs before the catch; catching foreign exceptions has no generally dependable result; and destruction of the returned panic payload may itself panic again. [R11-S01, O01]

[`panicking.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/src/panicking.rs#L495-L600) uses runtime intrinsics and ManuallyDrop state at the catch boundary to transfer closure results/exception payloads. These internals show that an error payload is itself an owner with destruction responsibilities; returning Err must not be equated with safely disposing of all exceptional resources. [R11-S02]

NativeWeave chooses panic=unwind, catching at entry and asynchronous-work boundaries, and poisoning the owning Engine after a catch as the default recoverable candidate profile; ordinary failures still use Result. panic=abort is only an explicitly declared fatal profile and cannot claim to return NATIVE_PANIC. C-unwind does not enter the public C ABI. AssertUnwindSafe is not a license to treat arbitrarily corrupted state as repaired; each use must state which representations remain valid after failure and which cleanup is safe. [R11-D01]

## 4. Counterexamples from the Tests Read

[`panic-in-ffi.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-ffi.rs) is a run-crash test: a panic inside non-unwind FFI cannot be imagined as an ordinary return value. It includes an object observing destruction and declares expected process failure. [R11-T01]

[`panic-in-cleanup.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-cleanup.rs) causes another panic during destruction while unwinding; the test has a special MSVC ignore note, so a Unix error-output string cannot directly become a Windows acceptance criterion. [R11-T02]

[`panic-in-hook.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/tests/ui/panics/panic-in-hook.rs) panics again inside a panic hook, demonstrating another fatal path for which a catch body cannot guarantee recovery. [`library/std/tests/panic.rs`](https://github.com/rust-lang/rust/blob/58cf8f9c35b355199727627d07ae34a4e2846d67/library/std/tests/panic.rs) checks static relationships among safety traits; it is not execution proof of all FFI containment. [R11-T03, T04]

This round had no Rust compiler and did not run these tests; "read test source" and "test passed" are strictly distinguished. Formal validation must cover unwind, abort, payload Drop, hooks, and cleanup double panic in separate subprocesses, recording target toolchains, exit codes, and portable behavioral classifications rather than requiring identical cross-platform error text.

## 5. Managed Callback Exceptions and UCO Signatures

Godot's [`SignalAwaiter`](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/SignalAwaiter.cs) and [GCHandleBridge](https://github.com/godotengine/godot/blob/069458825a8e4a01938a176372c0709ab6fd9dc3/modules/mono/glue/GodotSharp/GodotSharp/Core/Bridge/GCHandleBridge.cs) handle ordinary Exception within UCO methods; YAHA's TLS verification callback returns false on ordinary exceptions. They provide concrete forms of boundary containment and fail-closed behavior, not proof that any catch can contain the entire runtime. [R11-S03, S04]

The [official Native AOT interop documentation](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop) explicitly describes .NET11: with runtime marshalling enabled, a native call to an invalid UCO signature containing non-blittable parameters may trigger InvalidProgramException and fail-fast; a catch in the method body cannot repair the signature. [R11-O02] NativeWeave therefore uses generated static, nongeneric, exact blittable signatures, mapping bool/char to explicit wire types; errors must be detected through generation/compilation diagnostics and subprocess negative cases.

Boundary catches must also consider failure of decoding, logging, and finally actions themselves. Callback exceptions are recorded through the existing context and fixed status; error paths do not recursively create large numbers of strings, Exceptions, or queued Tasks. StackOverflow, runtime fatal errors, access violations, and OOM conditions that prevent continuation remain subject to host-process policy, rather than being disguised as ordinary recoverable failures.

## 6. Selection of Base Status and Error Layout

| Candidate | Problem | Choice |
| --- | --- | --- |
| TLS last-error string pointer | Wrong-thread access in multithreaded/async code, overwrite by the next call, unclear release ownership | Not used for the Core public error contract |
| Owned text allocated for every error | Rich information, but may fail to report the original error under OOM | Optional domain details only |
| Fixed status + fixed record | Reports basic failures without string allocation; straightforward layout verification | v1 foundation |
| Arbitrary Exception/panic objects across the ABI | Layout/destruction/runtime semantics cannot be unified | Rejected |

D08 uses u32 status: 0 is OK, 1=PENDING applies only to declared try/poll operations, and 2=CANCELED applies only to a confirmed terminal state; 3–13 are argument/state/OOM/capability/capacity/callback/panic/poison/contract/timeout/domain errors, respectively. D08 alone is authoritative for the full numbering, avoiding drift among duplicate tables. Unknown nonzero values are failures, with no implicit retry.

The base ErrorRecord is `u32 struct_size, u32 domain, i32 code, u32 flags, u64 correlation_id`, expected to occupy 24 bytes on x64. The record contains no cross-thread borrowed string, TLS error pointer, or panic object; callbacks copy it immediately on receipt. correlation is diagnostic only, not authorization or a persistent-memory lookup key. R03 owns C layout probes; final Rust/C#/C agreement and AOT still require actual validation. [R11-D02]

Detailed provider errors use typed owned results/UTF-8 payloads, following D07 release and the D06 single-take protocol. Failed takeover can still report a base status while native code retains ownership. The successful hot path constructs no error strings; basic errors are not lost when rich diagnostic allocation fails.

## 7. Existing Operations and Resources After Poison

Wrapping only spawn/start in catch_unwind cannot catch a later worker panic. Every async task's actual execution/poll boundary must catch it, or a still-trustworthy supervisor must consume task failure. The first panic atomically poisons the Engine and rejects new business operations; each existing operation publishes NATIVE_PANIC/ENGINE_POISONED once and requests stop. Already completed results or results with known effects must not be blindly rewritten; the domain retains actual knowledge of effects.

stop/cancel/try_retire/release must remain able to enter dedicated cleanup paths, bypassing the business gate that would otherwise reject everything after poison. However, publishing failure to managed code must not fabricate quiescence; remaining workers, callbacks, and external control calls must still drain. If the supervisor is no longer trustworthy or resource representations are corrupted, quarantine and retain owners/budgets rather than forcing free to make DisposeAsync falsely succeed. [R11-D01]

Dropping a panic payload may panic again. The v1 error-return path does not format or destroy an unknown payload; the poison path may intentionally forget it and record a quarantine count, which is not ordinary leak-free recovery. The Engine closes new admission, and the host bounds quarantined Engine counts and decides whether to restart; multiple existing concurrent tasks may still panic individually, so the quarantine budget must be calculated from the accepted-task limit rather than falsely claiming retention of only one payload. Reachable bytes of unknown payloads may not be measurable exactly; record object counts and a conservative unknown-bytes status.

Cleanup of known-safe fields also needs a non-unwinding boundary policy; destructor double panic, hook panic, and allocator abort may still terminate the process. A future process-isolated Engine could strengthen fault boundaries, but that is not a mandatory new runtime or product scope in this round.

## 8. Failure Atomicity and Scenarios

create failure keeps the out owner empty and rolls back temporary resources; rejected start leaves no callback obligation; business errors after committed start use terminal notification. An ordinary callback failure returns CALLBACK_FAILED and requires deterministic stop/failure. Successful result take transfers ownership and zeros it on the native side; failed take leaves output empty and native ownership intact. Error strings do not determine whether transfer occurred.

The normal example is C# await returning an owned result, released with using; the cancellation example has the caller's token request stop while the native terminal state still determines eventual success/cancellation; the exception example has NativeEngineException retain Engine/status/domain/code/correlation, leaving the application to decide whether to retry. The D08 skeleton shows only the guard shape and is uncompiled; copying a skeleton that omits state and cleanup logic cannot justify claiming a completed product implementation.

## 9. Validation Tasks and Performance Accounting

D08 ER-01–07 map to A02/A04/A06/A07/A14/A15/A18/A20/A21/B22: no error allocation on successful paths, mapping of all error/unknown values, error-struct capacity and versioning, OOM and failed detail takeover, ordinary managed callback exceptions, invalid UCO and Rust fatal subprocess cases, one terminal state and actual drain for existing operations after poison, and quarantine/resource budgets under long workloads.

Separately record status counts, error-detail allocations, panic/poison counts, accepted-task counts, unretired bytes, quarantined objects/unknown bytes, cleanup age, and fatal-subprocess exit behavior. A microbenchmark showing a panic was caught cannot prove complete Engine recovery, and error-logging overhead must not be hidden outside successful-path throughput statistics.

Windows/Linux unwind toolchains, panic strategies, C calling conventions, and AOT binary hashes enter the formal manifest. R11 has not executed these validations; R03 C layout results cannot replace cross-language Rust/C#/AOT consistency either.

## 10. Design Closure and Subsequent Review

Q08 now has explicit, reviewable decisions: a fixed error foundation, typed owned details, containment of ordinary managed exceptions, poisoning after caught unwind, explicit declaration of fatal profiles, and separation of actual cleanup from error results. The design-research question can close after independent review passes, while ER implementation and production validation remain pending.

R03 reviews the ErrorRecord prefix and status evolution; R08 reviews failure inside callbacks, exit, and absence of duplicate ownership; R34 reviews error privacy, budgets, and untrusted arguments; R12 reviews worker supervisors and draining after poison. UniFFI and runtime internal UCO entry points are unread, so the overall task remains partially_evidenced; these gaps are neither concealed nor used to leave every decision to the user.

Licenses: the full pinned Rust LICENSE-MIT and LICENSE-APACHE were read; its core standard library is dual-licensed, while each specific file reused in the future remains subject to its own notices. Godot and YAHA MIT licenses were read. This report paraphrases mechanisms and presents new NativeWeave design without copying large source passages.

## Current completion review — Rust1.100 and actual fatal subprocess evidence

Rust1.100 source `0ef1bc386059596dada8fb65b50425aab2ea637a`, `library/std/src/panic.rs`315–410, reaffirms unwind-only catch, hook-before-catch and panic-on-payload-Drop. This is the current fixed-source supplement to the historical1.99.1 review, not an invented rewrite of that old source identity. UniFFI's actual Future polling boundary catches poll panics and stops polling the failed future; a catch around spawn alone would not have that scope.

Seven actual Rust1.100 child-process cases are now preserved in `verification/interop-completion/panic-linux`: caught ordinary unwind and intentionally retained payload succeed; payload Drop panic, panic hook panic, cleanup double panic, non-unwind C-ABI panic and panic=abort through catch terminate unsuccessfully with recorded stderr/exit codes. The payload-retention positive case intentionally keeps that payload: it is evidence for quarantine behavior, not leak-free recovery. These cases do not prove all concurrent engine poison paths or OOM behavior.

The new C#/Rust completion probe also injects an ordinary managed callback exception inside actual UCO, catches it before crossing FFI, and verifies no result owner survives an injected DTO conversion failure. Normal and actual Linux Native AOT runs are separately recorded. Original two-OS prepublication native panic evidence remains at its original identity.

D08 remains the sole authority for status numbers/error records; the experiment's private constants must not be promoted into it. Fatal invalid-UCO signatures, arbitrary corrupt pointers and every target's fatal text/exit conventions remain isolated product tests; a callback catch cannot fix an invalid signature. Error/result/effect/cleanup are separate facts, and quarantine never creates fake DisposeAsync success. The current error-boundary design is ready for exact-content independent review; future A05/A06/A07/A14/A15/A20/B22 conformance is distinct from research acceptance.


## Supplemental invalid-UCO execution (2026-11-13)

The [isolated manifest](../../../../verification/interop-completion/uco-invalid-linux/result.json) records actual .NET11 normal and Native AOT publication followed by native invocation of an intentionally invalid char/bool `UnmanagedCallersOnly` callback with runtime marshalling enabled. Both child processes exited -6 with unhandled `InvalidProgramException`; `INVALID_CALLBACK_BODY_ENTERED` never appeared. This demonstrates that callback-body catch cannot repair an invalid signature. It does not establish all fail-fast variants or behavior of an outer managed catch. The normal blittable callback succeeds in the main fixture. Invalid-pointer fuzzing was not performed.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
