# R27 — Required Rust Server Engine and its Adapter

Historical research began on 2026-11-12, with supplementary evidence through 2026-11-13; see [evidence.json](evidence.json) for the current task packet/baseline/hash. Status: an implementable independent Engine architecture has been selected; Rust is required by the project mission; product Rust/C#/AOT and performance tests have not been run. The specification is synchronized with [D18](../../../server/hosting-and-streaming.md).

## 1. The Problem to Solve

The Rust networking ecosystem can support particular protocols, executor integration, or scenarios with demonstrated complete-workload benefits, but C# developers should not rewrite business handlers or manage Rust resources. Research focuses on maintaining independent Engine boundaries, lifetimes, and resource budgets, rather than adding uncontrolled FFI overhead for every HTTP chunk.

Design decision: the required Rust Server accepts an explicit set of typed C# Handlers, reuses Core handle/async/buffer contracts, and owns its runtime and TLS; Kestrel is a comparison baseline only. The API does not promise portability of arbitrary ASP.NET middleware/HttpContext. Future GPU/media Engines will not thereby be forced to reference Server/Tokio.

## 2. Pinned Evidence and Comparison

| Project | Pinned version/commit | Mechanisms actually read |
| --- | --- | --- |
| Hyper | v1.12.0 / `7f67699ce32d717081deb7018b4da7d679277ac0` | HTTP1 connection graceful_shutdown125–149; Cargo features71–92 |
| Tokio | tokio-1.54.1 / `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` | mpsc bounded send765–825/reserve1070–1126 |
| Axum | axum-v0.8.9 / `c59208c86fded335cd85e388030ad59347b0e5ae` | serve run258–305/connection dispatch383–421 |

See [evidence](evidence.json) and [coverage](coverage.json) for URLs/blobs/licenses and coverage status. Pinned Tokio/Hyper/Axum licenses were identified as MIT; Axum's actual license path is `axum/LICENSE`, and the unsuccessful search for a nonexistent root `LICENSE` was not presented as successful. Regarding YetAnotherHttpHandler, this review uses only the limited evidence already registered by the interop topic to check FFI cost/owner pitfalls; this round does not renew a claim to have read the whole project.

| Candidate | Choice |
| --- | --- |
| Publish the Hyper C API directly as NativeWeave's public ABI | Rejected; Cargo explicitly states unstable/no semver, so a stable contract cannot depend on layout/function surfaces without stability guarantees |
| Expose the complete Axum routing/application framework directly to C# | Not the public layer; C# declares typed routes and business Handlers, while Rust performs route matching/dispatch and native middleware; no second application DI/serialization system is exposed |
| Tokio/Hyper Engine internals + a NativeWeave domain Adapter | Selected as the first required Rust Host design; internal replacements do not affect the Core ABI |
| Create a Tokio runtime per request and synchronously wait on Tasks in C# callbacks | Rejected; startup/thread costs, reentrant deadlocks, and shutdown complexity are unacceptable |
| Batch/streaming pull + bounded owned chunks | Selected; establish copying and lifetimes first, then add zero-copy capability based on evidence |

## 3. Actual Call Chain from Accept to Shutdown

Axum `WithGracefulShutdown.run` holds listener/make_service/signal. A separate task waits for the signal and then drops the watch receiver; the accept loop exits through `signal_tx.closed()`, and each connection clones a shutdown observer. Connection tasks use Hyper connection futures, calling `graceful_shutdown` in the signal branch; they keep polling until the connection ends, then drop their close receiver. After accepting stops, run waits for every close receiver to exit.

Hyper HTTP1 graceful shutdown only disables keep-alive; comments explicitly require continued future polling to complete flush/shutdown. A C# host that merely cancels a task or drops a Rust future cannot claim protocol-level graceful shutdown. Axum here imposes no mandatory total drain limit for NativeWeave; D18 needs an outer monotonic deadline, transitioning to abort on timeout and remaining separate from Core callback quiescence.

This reading does not cover every Hyper HTTP2 state machine, Tower readiness/limits, or RustTLS implementation; these are explicit coverage gaps, and Rust language memory safety cannot prove full-stack shutdown correctness.

## 4. C# Handlers and the Asynchronous FFI Protocol

Ordinary C# applications use NativeWeave's native Server typed Handler interface; the design signature is `WeaveRequestHandler(WeaveHttpContext,CancellationToken) -> ValueTask`, with context containing bounded copied headers, owned body reads/writes, and budget leases; PipeReader/PipeWriter may serve only as optional facades preserving equivalent ownership. This API is an uncompiled design draft. Route/JSON tools continue to use models known at compile time, without exposing internal Rust Request types to C#.

Rust implementation shape (pseudocode, not a compiled API):

```rust
// Lifetimes/states are illustrative only; concrete wire representations are generated from Core contracts.
async fn serve_request(request: EngineRequest, budget: BudgetLease) {
    let operation = create_operation(request, budget);
    start_managed_handler(operation.id()).await;
    // Pull body by credit; terminal notification does not mean the cookie may be released.
    await_terminal_and_transport_cleanup(operation).await;
    mark_native_quiescent();
}
```

The formal ABI reuses Core's two-phase create/start; terminal callbacks only copy status and a fixed ErrorRecord, and the completion coordinator outside callbacks takes the owned result through take_result once. Request reads return owned chunks/EOF, with a single pending read; borrowed response-write input is valid only during the synchronous FFI entry, and asynchronous retention requires copying into a Rust owner with acquired budget. All callback-requiring work retains an operation owner; GC/Drop does not imply absence of callbacks.

Terminal state may be observable before resource retirement; handles/cookies can be released only after native workers, callbacks, and start/control/cancellation-registration obligations are all quiescent. Managed `Task` continuations must not run user code inline and synchronously block Tokio threads. Native locks must not span arbitrary managed-handler calls; panic/errors must become stable failures while preserving cleanup, rather than unwinding across the ABI.

## 5. Tradeoffs Between Byte Budgets and Zero Copy

Tokio `send(value)` already owns value while waiting for `reserve`, so a bounded channel can still have arbitrarily many waiting producers with large payloads. An unused `reserve` Permit returns capacity on drop, making it suitable for acquiring a slot before construction; a slot is still not byte credit. D18/R29 choose bounded metadata wait queues plus global/per-request byte credit before allocation, accounting for both sides remaining live during copies.

The first Rust adapter permits one bounded copy per direction: a native chunk is copied into a managed-owned slab, followed by immediate native-owner release; output enters a Rust-owned chunk without retaining a managed pointer. This choice balances provable lifetimes against measurable cost and preserves future explicit-lease zero-copy extensions. Ordinary ReadOnlyMemory must not point to freed Rust allocations, and long-lived pinning must not conceal ownership defects.

Per-request costs include at least metadata encoding, dispatch, chunk notifications, and cleanup control calls; FFI crossings grow with `payload/chunk`. Larger chunks reduce call counts but increase concurrent resident memory and cancellation latency. Measure TLS encryption, HTTP framing, database IO, and FFI/copy time separately, avoiding database waits that mask differences as equal server performance or reporting only empty-handler peaks.

## 6. TLS, Platforms, and Packaging

The Rust Engine internally owns the single executor/transport; Rust terminates TLS without an additional managed TLS layer. Certificate reload, cancellation during handshakes, ALPN/HTTP versions, close-notify, and native-buffer reclamation all enter B17/B22. Proxy termination applies only under explicit trusted-proxy configuration. D19 now uses native Tonic/rmcp integration points; new research fixtures execute protocol boundaries, while B18/B19 still accept complete C# product interoperability. HTTP2 support alone cannot establish support for every protocol.

The package can be installed and versioned separately and reject unsupported capabilities; managed applications that do not reference the Server Engine need not install Rust Server, while applications using NativeWeave Server must consume that native module, without a managed Host fallback. Separate package manifests pin Windows/Linux RID linkers, dynamic-library resolution, CRT/libc, TLS dependencies, and panic configuration. Version/capability incompatibility is rejected before listen, not discovered as a layout error on the first request after successful loading.

## 7. Research Decisions and Formal Acceptance

Q15's Rust foundation requirement is determined by the user's goals. The initial implementation design chooses Tokio/Hyper/hyper-util/Tower, with optional Axum routing reuse; ordinary C# applications need no Rust recompilation per Handler. Equivalent-load tests measure costs objectively; the Rust architecture requirement does not justify claiming a performance victory already exists.

B17 produces the independent engine, ABI adaptation, and minimal handler; B20 validates cancel/completion/retire interleavings, scheduler reentrancy, and shutdown; B23 aligns protocols/TLS/hardware/data/error semantics and measures CPU, memory, tail latency, crossings, and copies; B24 executes actual Windows/Linux AOT app loading and version rejection. Complete product execution has not occurred; new research runs are in verification/server-completion, and existing native-slice/retained-byte evidence remains reused.

Independent Review interfaces: R07/R08 check owned results and quiescence; R26 checks that the managed comparator and product Host are not conflated; R29 checks double accounting during copies, byte-credit deadlocks, and slow readers; R17 checks that end-to-end comparisons do not cherry-pick the best Rust microbenchmarks. This author does not claim to have accepted their own new design.


## Current completion and architecture correction (2026-11-12)

The latest user mission requires a Rust Server engine. Kestrel is solely the comparator.
The selected initial design is Tokio + Hyper/hyper-util + Tower, with Axum available
for native routing and composition where needed. Actix remains a worker-affine
alternative and Pingora a proxy-specific engine; neither is copied into C#. Public
Service/Body APIs suffice for the current Adapter; no fork is justified by this study.
Prior passages describing optional Rust or a Kestrel product host are superseded as
architecture decisions, while their scoped source/evidence identities remain historical.

D18 now defines the native Handler/Body bridge and retirement protocol; D19 binds
Tonic/rmcp/rustls to that same host. New actual protocol/network/TLS evidence is in
`verification/server-completion/`, with exact commands/source hashes and retained prior
attempts. Native HTTP1/HTTP2 loopback and bounded TLS tests are real executions, but
not a C# Server product, equivalent-load benchmark or production soak. The existing
Body/Bytes/permit and finite credit models are reused without inflating their coverage.

Research-design closure is proposed for this bounded source/lifecycle study; future
B16/B17/B20/B22/B23 implementation, complete cross-language transport and long-load
acceptance remain explicit obligations. Independent review and graph integration
must bind this exact revised content before acceptance.


### Verified Windows/Linux research CI

CI run [43388468172](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43388468172)
tested source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. Protocol13/13 and
Kestrel Native AOT5/5 passed on both Windows2022 and Ubuntu24.04. Their actual
run manifests, stdout/stderr and source snapshots are retained under
`verification/completion-ci/43388468172/`; author checks of each raw log/input hash and
exact Windows LF-to-CRLF conversion are recorded in
`verification/server-completion/ci-verification.json`. This extends platform coverage
for these same distinct cases, not their product/FFI/soak scope or independent review.
