# R27 — Required Rust Server Engine and its Adapter

Historical research began on 2026-11-12, with supplemental evidence through 2026-11-13; see [evidence.json](evidence.json) for the current packet/baseline/hash. Status: an implementable independent Engine architecture has been selected; Rust is required by the project mission; product Rust/C#/AOT and performance tests have not run. The specification is synchronized to [D18](../../../server/hosting-and-streaming.md).

## 1. Questions to resolve

The Rust networking ecosystem can serve specific protocols, executor integration or scenarios with demonstrated benefits under complete workloads, but C# developers should not have to rewrite business handlers or manage Rust resources. The research focuses on preserving independent Engine boundaries, lifetimes and resource budgets without adding uncontrolled FFI overhead for every HTTP chunk.

Design decision: the required Rust Server accepts an explicit set of typed C# Handlers, reuses Core handle/async/buffer contracts and owns its runtime and TLS; Kestrel is only a comparison baseline. The API does not promise portability of arbitrary ASP.NET middleware/HttpContext. Future GPU/media Engines will not thereby be forced to reference Server/Tokio.

## 2. Pinned evidence and comparison

| Project | Pinned version/commit | Mechanisms actually read |
| --- | --- | --- |
| Hyper | v1.12.0 / `7f67699ce32d717081deb7018b4da7d679277ac0` | HTTP1 connection graceful_shutdown125–149；Cargo features71–92 |
| Tokio | tokio-1.54.1 / `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` | mpsc bounded send765–825/reserve1070–1126 |
| Axum | axum-v0.8.9 / `c59208c86fded335cd85e388030ad59347b0e5ae` | serve run258–305/connection dispatch383–421 |

See [evidence](evidence.json) and [coverage](coverage.json) for URL/blob/license and coverage status. Pinned Tokio/Hyper/Axum licenses were identified as MIT; the actual Axum license path is `axum/LICENSE`, and the unsuccessful lookup of the absent root `LICENSE` was not presented as success. YetAnotherHttpHandler uses only the scoped evidence already recorded by the interop topic to examine FFI cost/owner pitfalls; this round does not newly claim to have read the entire project.

| Candidate | Selection |
| --- | --- |
| Publish the Hyper C API directly as NativeWeave's public ABI | Rejected; Cargo explicitly states unstable/no semver, and stable contracts cannot depend on uncommitted layouts/function surfaces |
| Expose the complete Axum routing/application framework directly to C# | Not the public layer; C# declares typed routes and business Handlers, while Rust performs route matching/dispatch and native middleware; do not expose a second application DI/serialization system |
| Tokio/Hyper internal Engine implementation + NativeWeave domain Adapter | Selected as the initial required Rust Host design; internal replacement does not affect the Core ABI |
| Create a Tokio runtime per request, with C# callbacks synchronously waiting for Tasks | Rejected; startup/thread cost, reentrant deadlocks and shutdown complexity are unacceptable |
| Batched/streaming pull + bounded owned chunks | Selected; specify copies and lifetimes first, then add zero-copy capabilities based on evidence |

## 3. Actual call chain from accept to shutdown

Axum `WithGracefulShutdown.run` holds listener/make_service/signal. A separate task waits for the signal and then drops the watch receiver; the accept loop exits through `signal_tx.closed()`, and every connection clones the shutdown observer. The connection task uses a Hyper connection future and calls `graceful_shutdown` in the signal branch; it continues polling until the connection ends, then drops its close receiver. After it stops accepting, run waits for all close receivers to exit.

Hyper HTTP1 graceful shutdown only disables keep-alive; comments explicitly require continued polling of the future to complete flush/shutdown. A C# host that merely cancels a task or drops a Rust future cannot claim protocol-level graceful shutdown. Axum does not provide NativeWeave with a mandatory overall drain limit here; D18 requires an outer monotonic deadline, transition to abort on timeout and separation from Core callback quiescence.

This reading does not cover every Hyper HTTP2 state machine, tower readiness/limits or Rust TLS implementation; these are explicit coverage gaps. Rust language memory safety cannot be treated as proof of correct shutdown across the entire stack.

## 4. C# Handler and asynchronous FFI protocol

Ordinary C# applications use the typed Handler interface of NativeWeave's native Server; the designed signature is `WeaveRequestHandler(WeaveHttpContext,CancellationToken) -> ValueTask`. The context contains bounded copied headers, owned body reads/writes and budget leases; PipeReader/PipeWriter may serve only as optional facades preserving equivalent ownership. This API is an uncompiled design draft. Route/JSON tooling continues to use compile-time-known models without exposing internal Rust Request types to C#.

Rust implementation shape (pseudocode, not a compiled API):

```rust
// Lifetimes/states are illustrative only; concrete wire definitions come from Core contracts.
async fn serve_request(request: EngineRequest, budget: BudgetLease) {
    let operation = create_operation(request, budget);
    start_managed_handler(operation.id()).await;
    // Pull body data against credit; terminal does not mean the cookie may be released.
    await_terminal_and_transport_cleanup(operation).await;
    mark_native_quiescent();
}
```

The production ABI reuses Core's two-phase create/start; terminal callbacks copy only status and the fixed ErrorRecord, and the completion coordinator takes the owned result once through take_result outside the callback. Request reads return an owned chunk/EOF, with a single pending read; borrowed response-write input is valid only during the synchronous FFI entry call, and asynchronous retention must copy it to a Rust owner with an acquired budget. All work requiring callbacks retains an operation owner; GC/Drop does not imply that callbacks have ceased.

A terminal state may become observable before resource retirement; handles/cookies may be released only after native workers, callbacks and start/control/cancel registrations are all quiescent. Managed `Task` continuations must not run user code inline and synchronously block Tokio threads. Native locks must not span calls to arbitrary managed handlers; panic/errors must become stable failures while retaining cleanup, without unwinding across the ABI.

## 5. Byte-budget and zero-copy tradeoffs

Tokio `send(value)` already owns the value while awaiting `reserve`, so a bounded channel may still have arbitrarily many waiting producers with large payloads. The Permit from `reserve` can be dropped before sending to return capacity, making it suitable for acquiring a slot before construction; however, a slot is not byte credit. D18/R29 select a bounded metadata wait queue plus global/request byte credit before allocation, accounting for both copies while they coexist.

The initial Rust adapter permits one bounded copy in each direction: release the native owner immediately after copying a native chunk into a managed-owned slab; retain no managed pointer after output enters a Rust-owned chunk. This choice trades measurable cost for a provable lifetime and leaves room for future zero-copy extensions with explicit leases. Ordinary ReadOnlyMemory must not point to a released Rust allocation, and long-lived pinning must not conceal ownership defects.

Per-request costs include at least metadata encoding, dispatch, chunk notifications and cleanup control calls; FFI crossings grow with `payload/chunk`. Larger chunks reduce call counts but increase concurrently resident memory and cancellation latency. Measure TLS encryption, HTTP framing, database IO and FFI/copy time separately, rather than disguising DB waits as equal server performance or reporting only empty-handler peaks.

## 6. TLS, platforms and packaging

The Rust Engine internally owns the sole executor/transport; Rust terminates TLS without an outer second managed TLS stack. Certificate reload, cancellation during handshake, ALPN/HTTP versions, close-notify and native buffer reclamation all belong to B17/B22. Proxy termination is valid only with an explicit trusted-proxy configuration. D19 now uses Tonic/rmcp native integration points; new research fixtures execute protocol boundaries, while complete C# product interoperability remains for B18/B19 acceptance. HTTP2 availability alone does not establish complete protocol support.

Packages support independent installation, versioning and capability rejection; managed applications that do not reference the Server Engine need not install Rust Server, while applications using NativeWeave Server must consume the native module with no managed Host fallback. Independent package manifests pin the linker, dynamic-library resolution, CRT/libc, TLS dependencies and panic configuration for Windows/Linux RIDs. Reject incompatible versions/capabilities before listen; successful loading must not defer a layout error until the first request.

## 7. Research decisions and formal acceptance

The user goal determines Q15's Rust lower-layer requirement. The initial implementation design selects Tokio/Hyper/hyper-util/Tower, reusing optional Axum routing; ordinary C# applications do not recompile Rust per Handler. Equivalent-load tests objectively measure costs; the architectural Rust requirement does not establish a performance victory.

B17 delivers an independent engine, ABI adaptation and a minimal handler; B20 validates cancel/completion/retire interleavings, scheduler reentrancy and shutdown; B23 aligns protocol/TLS/hardware/data/error semantics to measure CPU, memory, tail latency, crossings and copies; B24 executes actual Windows/Linux AOT application loading and version rejection. Complete product execution has not occurred; see verification/server-completion for new research runs, while earlier native-slice/retained-byte evidence continues to be reused.

Independent review interfaces: R07/R08 examine owned results and quiescence; R26 checks that the managed comparator and product Host are not confused; R29 checks double accounting during copies, byte-credit deadlocks and slow readers; R17 checks that end-to-end comparison does not cherry-pick the best Rust microbenchmark. This author does not claim to have accepted their own new design.


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
