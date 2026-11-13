# R26–R31 follow-up — reusing native Server internals through a foreign handler

Date: 2026-11-12. Status: selected source paths inspected; new finite admission model executed; **no production Rust/C# Server bridge built or benchmarked**. Architectural choices remain proposed and independently unreviewed. Existing Kestrel, protocol, credit and reference-service research is retained.

## 1. Pins and coverage boundary

| Upstream | Version / fixed commit | Mechanisms actually inspected |
|---|---|---|
| Hyper | 1.12.0 / `7f67699ce32d717081deb7018b4da7d679277ac0` | Service trait, HTTP/1 connection builder/driver and shutdown, H2 Incoming data/flow release, experimental FFI |
| Tokio | 1.54.1 / `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` | Runtime shutdown/blocking-task constraints |
| Tower | 0.5.3 / `4b0a6b0e688bd177eb2c9c97f5268dd9703c66fc` | ConcurrencyLimit admission, ResponseFuture permit, response error/drop tests |
| Axum | 0.8.9 / `c59208c86fded335cd85e388030ad59347b0e5ae` | Accept/make-service/Tower-to-Hyper/connection spawn and graceful shutdown |
| Actix Web | 4.19.0 / `fdb6503d95228f44ba926f6347c11fd523e22193` | Worker count, per-worker limits and blocking pools |
| Actix Server | 2.10.0 / `f22be1d9731f764707dd3e286900d285c6f60b14` | Accept-to-worker connection counter and Rc-affine guard |
| rustls | 0.23.46 / `f04804fa13341a9b1dc02b5d1dd8a746f2c4b7fb` | Fatal TLS processing errors and write-side buffer limits |
| Pingora | 0.9.1 / `f86ffda5d3ae5c3baf5125682138b33b26c01b08` | ProxyHttp upstream-peer and request-filter hooks; limited alternative study |

See [source index](../../source-driven-evidence/source-inspection.json) for precise file ranges/hashes. These are not whole-repository audits. hyper-util's snapshot is available but not treated as comprehensively reviewed. The existing R26 Kestrel baseline remains the managed comparator; no fresh full Kestrel performance run or unchanged-feature equivalence is implied.

## 2. Public API → engine → adapter opportunity

Hyper `src/service/service.rs:32–56` accepts a Rust Service with an associated Future/response body. Compile **one ForeignService implementation**, not a Rust function for each C# route. Route registrations, handler IDs and configuration are runtime data. A native Future waits for a completion message from the C# handler bridge; native code owns the HTTP parser, socket driver, stream, protocol scheduling and TLS integration. C# owns application handlers and static request/response DTO serialization.

Hyper HTTP/1 `src/server/conn/http1.rs:470–521` constructs the protocol connection and Dispatcher around the provided service. Axum `axum/src/serve/mod.rs:353–415` makes a per-connection service, wraps it through TowerToHyperService, spawns the connection and continues polling during graceful shutdown. This supplies a mature connection/service seam; NativeWeave should not port the parser or rebuild a parallel C# networking core.

Hyper's `src/ffi/mod.rs:1–99` describes an **unstable, client-focused C API** requiring the unstable FFI configuration. It is not a stable full server binding. A dedicated native Adapter over public Service/Body APIs is the initial candidate. Source extensions remain permitted for proven missing capabilities; none has been demonstrated necessary for the handler seam.

## 3. Minimal handler/body bridge — proposed protocol

A native request operation owns its connection/request references and has a generation-tagged registration ID. Before dispatch, reserve request slots, waiting-handler capacity, header/body bytes and callback context. The native callback only enqueues a managed dispatcher item; it does not run arbitrary synchronous application work on the Tokio polling thread or block waiting for a Task. The managed dispatcher calls the C# handler and records success, HTTP failure or cancellation exactly once. Its completion wakes the native Future.

After returning headers, an independent body handle remains alive. Pull-based native body polling requests at most the permitted next chunk; managed producers provide owned/copy-or-leased bytes and an explicit release acknowledgment. Do not translate every byte into a callback or permit unbounded queued chunks. Treat trailers/end-of-body distinctly. Request body reads likewise retain byte credit until the last consumer/lease releases data, not simply until a protocol window is updated.

Draft C# API (not compiled):
```csharp
server.MapGet("/students", async (request, cancellation) =>
    await Responses.JsonAsync(await queries.ListStudentsAsync(cancellation), cancellation));
```
This only illustrates the application boundary. Route registration and JSON metadata must be static/AOT-compatible; arbitrary runtime reflection is not introduced. SQL/database work remains in the mandatory Rust database Engine. Shared runtimes between Server and Database are an optimization decision requiring shutdown and resource accounting evidence, not a Core mandate.

## 4. Three source-backed traps

**Response Future limits are not streaming lifetime limits.** Tower `tower/src/limit/concurrency/service.rs:64–92` obtains a semaphore permit at readiness and moves it into `ResponseFuture`; `future.rs:12–40` stores the permit on that future. The inspected tests `tower/tests/limit/concurrency.rs:152–191` verify release on response error/drop. A response can be produced while its body is still streaming. NativeWeave therefore needs a body/operation lease or a distinct live-stream budget, rather than claiming ConcurrencyLimit alone bounds every ongoing stream.

**Protocol flow credit is not retained-memory credit.** Hyper Incoming `src/body/incoming.rs:147–208` releases H2 capacity for received data before returning the Bytes frame in the inspected path. If a managed caller retains that frame, connection flow control does not account for that lifetime. Track retained native/managed bytes, active leases and queued/waiting work separately. A finite channel count cannot bound an arbitrary large chunk.

**A shutdown timeout is not quiescence.** Tokio Runtime `28–61,447–475` documents blocking operations that cannot be stopped and timeout behavior that leaves unfinished work/threads behind. Hyper http1 `129–141` requires the connection future to keep being polled after graceful shutdown; Axum serve `267–304,353–415` stops accepts and waits on connection closure. Bound public waiting, retain callbacks/owners/budgets on ClosePending and use an explicit retirement proof before releasing native module roots. Never free a GCHandle because a runtime shutdown deadline expired.

## 5. Actix, TLS and other candidate costs

Actix Web server `149–229` creates workers per bind address, uses per-worker connection/TLS settings and per-worker blocking pools. Actix Server worker `71–107,143–180` has an accept-side count increment before dispatch and a worker guard with Rc-affine state. An unbounded channel type alone is not proof of unbounded accepted connections; inspect the admission counter and failure rollback. The C# bridge cannot move arbitrary !Send/Rc-backed Actix request state to .NET threads. It can pass validated data/IDs and send commands back to the owner worker. This is a credible alternative with different thread-affinity cost, not an interchangeable Tokio multithread configuration.

rustls conn `443–458` treats protocol processing errors as fatal and warns against continuing reads that only fill buffers; `510–546` limits its two write-side queues. NativeWeave must stop/close correctly and account for other queues, plaintext, application chunks and handshake work. These limits do not establish a whole-server RSS ceiling. TLS integration, certificate reload, close_notify and abrupt peer closure still need actual adapter tests.

Pingora ProxyHttp `48–118` is valuable for proxy upstream selection and request filters; this limited reading does not make it the best default application server. Keep it for proxy-specific evaluation. The comparison is about retaining mature native mechanisms at suitable seams, not adopting all available frameworks.

## 6. New finite experiment

`body_lease_model.py` was executed in the recovery session. Two requests share one configured stream slot. The negative control releases its permit after response headers: **45 states, 96 transitions, 21 violating states**, first witness `admit(0) → response_head(0) → admit(1)` while the first stream is still alive. The candidate retains the slot until body and callback retirement: **24 states, 32 transitions, no checked violation**, with both requests' retirement reachable.

This is an abstract sequentially-consistent admission check with finite requests; it neither runs Tower/Hyper nor proves all liveness, weak memory, byte bounds, callback implementation, shutdown or Native AOT. The model deliberately demonstrates why a separate lifetime condition is needed. The complete output and source hash are retained; no independent replay is claimed.

## 7. Decision and verification obligations

Public Hyper/Tower/Axum adaptation is the leading **research candidate** for a generic native HTTP Engine because the service/body seam allows native protocol ownership without per-handler Rust compilation. Actix remains a worker-affine alternative, Pingora a domain-specific comparator. Kestrel remains the modern C# Native AOT baseline; no selection of Rust Server as production default is made without benefit evidence.

D18/B17 must specify callback registration/generation, exactly-once completion, body/stream/byte leases, TLS/connection drain and runtime ownership. B16/B20/B22 retain slow-consumer, disconnect, cancel/close races, oversized chunk/header/queue limits, aborted body/trailers, callback reentrancy, unknown database commit and observability-budget tests. R17/B23 compare same protocol/TLS/serialization/DB workload and hardware across pure native, native+C# AOT and Kestrel AOT; include idle/peak RSS, threads, CPU, throughput, P95/P99 and long soak. No numeric winner or production memory budget is invented.
