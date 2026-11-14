> Historical checkpoint. Current product constraints and acceptance boundaries are in [ADR-0003](../../decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md). Any optional Rust Server/Kestrel product-host wording below describes the prior snapshot, not current authorization. Original evidence retains its recorded scope.

# Preliminary Interop Source Findings and Boundaries Requiring Proof

Status: limited-source-research; date: 2026-11-12. Author: root. This is neither a complete security audit of any candidate library nor a formal NativeWeave technology selection.

Pinned source evidence: [evidence.json](evidence.json). Line ranges actually read and paths not covered are recorded separately.

## 1. YetAnotherHttpHandler: Lifetime Is a Protocol, Beyond Wrapping a SafeHandle

Pinned commit: `c386c1cc48d2e56711c15286cf2769353fdccf07`.

Read excerpts of the call chain: NativeHttpHandlerCore prepares RequestContext/GCHandle → yaha_request_begin → Tokio spawn and cancellation select → status/data/completion callbacks → RequestContext.Release → Dispose on the thread pool → release of request/context/runtime SafeHandles.

### INT-E001: Parent–Child Native Lifetimes Must Be Maintained Explicitly

YahaContextSafeHandle holds a runtime reference, and YahaRequestContextSafeHandle holds a context reference; SetParent calls DangerousAddRef, and release calls native destruction followed by DangerousRelease. The context holds the certificate callback's GCHandle until ReleaseHandle.

This source observation of the pinned implementation shows that managed object references and the duration of native use are distinct concerns. It does not prove that every use is correctly paired, nor does it mean NativeWeave must copy the same SafeHandle hierarchy.

[Actual source code](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/YahaSafeHandles.cs)

### INT-E002: Business Operation Completion, GCHandle Release, and Native Destruction Occur at Different Times

RequestContext.Allocate/Release manages the managed GCHandle; in the completion entry point's finally block, Release is followed by scheduling Dispose on the managed thread pool. The code explicitly preserves the release ordering between native completion and the native thread's return. RequestContext's finalizer path also waits for a completion event, in the context of Unity domain reload; the existence of this upstream pattern should not make a blocking finalizer the general default.

The candidate design must additionally answer: who holds the context before a callback exits; whether Dispose invoked from a callback could wait for itself; and how normal completion, failure, cancellation, and shutdown each advance toward quiescence.

[RequestContext](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/RequestContext.cs); [completion entry point](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L526-L625)

### INT-E003: Backpressure Across FFI Requires Consumption Acknowledgment and Data Validity Periods

The Rust response loop passes a body frame to on_receive and waits for a oneshot acknowledgment; C# OnReceive calls CompleteTask after the asynchronous flush completes, or returns an error on failure. This makes consumption acknowledgment a condition for further data progress. The upload path also uses ArrayPool rentals and CopyTo; "Rust across languages" cannot be equated with end-to-end zero-copy operation.

ResponseContext's actual copying strategy, oneshot reclamation, liveness when cancellation occurs during rx.await, a consumer that never acknowledges, and runtime shutdown still require complete tracing. The current evidence proves only that this acknowledgment structure exists, not eventual reclamation under every failure condition.

[Native loop](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/native/yaha_native/src/binding.rs#L483-L719); [managed receive path](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/src/YetAnotherHttpHandler/NativeHttpHandlerCore.cs#L466-L523)

### INT-E004: Existing Tests Offer Reusable Ideas for Failure Scenarios

CertificateVerificationCallbackLifetimeTest disposes the handler during a TLS handshake, attempts to allocate a replacement GCHandle, and checks that the original callback is retained and that the replacement validator is not called unexpectedly. The test runs in a subprocess to prevent a callback exception from terminating the entire test runner.

This proves that the test source covers a specific lifetime scenario; **it does not prove a successful test run in this round**. The test uses reflection and dotnet test and is not NativeWeave AOT acceptance. Corresponding observable, process-isolated fixtures must later be designed for AOT artifacts.

[First 170 lines of the test read](https://github.com/Cysharp/YetAnotherHttpHandler/blob/c386c1cc48d2e56711c15286cf2769353fdccf07/test/YetAnotherHttpHandler.Test/CertificateVerificationCallbackLifetimeTest.cs#L1-L170)

## 2. csbindgen: Syntactic Binding Generation Differs from Safety Contract Generation

Pinned commit: `b9eb1e84bb8185b78a4e8364fd948fee300329a7`.

INT-E005: The emitter code read generates DllImport, specifies the calling convention/EntryPoint, and adds U1 marshalling for bool. Enum repr handling has explicit mapping branches. **This is not a verified NativeWeave LibraryImport/ownership/async generation pipeline.**

DllImport is not inherently incompatible with AOT. Blittable DllImport, LibraryImport, and a handwritten thin layer must be compared against the target version and marshaller behavior. NativeWeave must also determine the single source of truth for ABI descriptions, permitted types, diagnostics, per-platform layout tests, and lifetime annotations; a generator cannot be assumed to solve every safety problem automatically.

[Emitter line range read](https://github.com/Cysharp/csbindgen/blob/b9eb1e84bb8185b78a4e8364fd948fee300329a7/csbindgen/src/emitter.rs#L145-L195)

In-depth work on parser, type_meta, negative tests, and AOT execution of generated output remains incomplete. The type_meta file was retrieved in this round, but no semantic conclusion was drawn from it; "downloaded" must not count as "research coverage."

## 3. Official FFI Boundary Constraints

Official .NET guidance recommends prioritizing evaluation of LibraryImport, function pointers/UnmanagedCallersOnly, and SafeHandle; the binding remains responsible for exact matching and lifetime management. [Interop best practices](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/best-practices)

The latest AOT documentation explicitly states that UCO methods do not perform marshalling. In .NET11 with runtime marshalling enabled, a native call to a non-blittable signature may fail-fast before entering the callback body; normal exception catching cannot repair an invalid signature. Dynamic loading for Direct P/Invoke is controlled by the OS and does not use DefaultDllImportSearchPaths. [AOT interop](https://learn.microsoft.com/en-us/dotnet/core/deploying/native-aot/interop)

Official Rust documentation describes ABI and unwinding separately: panic=abort is not protected by catch_unwind, and foreign exceptions must not arbitrarily cross a non-unwind ABI. Normal recoverable failures use Result/status. [Rustonomicon](https://doc.rust-lang.org/nomicon/ffi.html), [catch_unwind](https://doc.rust-lang.org/stable/std/panic/fn.catch_unwind.html)

## 4. A Limited Model Actually Executed

The [experiment description](../../../experiments/async-quiescence/README.md) and [results](../../../experiments/async-quiescence/result.json) record a finite-state model: incorrectly treating "cancellation result published" as "native context may be reclaimed" produces a concrete UAF trace; the candidate barrier eliminated that counterexample within the model's scope.

The model does not include real GCHandle behavior, FFI, weak memory, thread scheduling, or Windows/Linux AOT; it does not make C-ASYNC/C-LIFETIME accepted. Its purpose is to provide a starting point that can be challenged for R08/R09/R15.

## 5. Subsequent Complete Paths and Comparisons

- R03/R04: C/Rust/C# layout and call probes; bool/enum/union, empty buffers, 32/64bit, and callback calling conventions.
- R05/R06: csbindgen, Interoptopus, UniFFI, Diplomat, cbindgen, bindgen, and CsWin32/ClangSharp, compared by actual capabilities and generation boundaries, without introducing all of them.
- R07/R08: object identity, ownership, and signal lifetimes in Godot modules/mono and Qt for Python; seeds only, with no source conclusions yet.
- R09/R12: complete cancellation, synchronous completion, synchronous callbacks during registration, shutdown, executor stop, and reclamation chains.
- R10/R16: length/capacity units, UTF8, validity of zero-length pointers, overflow, aliasing, and allocator pairing; fuzzing and actual cross-language experiments.
- R11: panic/unwind/abort, managed callback exceptions, and prohibition of continued use after state corruption; process-isolated negative cases.
- R17/R18: end-to-end cost and integration generality across different engines; do not preselect Rust based on FFI microbenchmarks.

## 6. Current Limitations and Reuse Policy

This round did not run these upstream tests, compile C#/Rust, or certify AOT. Unity adaptations, default runtimes, i32-limited buffers, and other features of upstream implementations are research subjects and do not automatically become NativeWeave constraints. Before copying code or introducing a dependency, the LICENSE at the pinned version must be read again and the reuse method recorded; this batch stores only original analysis and permanent links.
