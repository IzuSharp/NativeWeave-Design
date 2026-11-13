> **Research asset location correction:** these historical execution identities remain unchanged. Current source is `experiments/native-slices/` and original evidence is `verification/native-slices/original-pr1/` in NativeWeave-Design. See `docs/traceability/research-asset-migration.md` and its per-file mapping. No formal product implementation is authorized in this phase.

# R27/R29 — actual native Service/Body tests, beyond the finite model

Status: partially evidenced, not an independent review or production Server. Exact source **5dd696725afe75f2b8b03b104c8275db50dcf2c7**, [run43363994414](https://github.com/IzuSharp/NativeWeave/actions/runs/43363994414). Both Windows2022 and Ubuntu24.04 passed **four actual Rust tests** against Hyper1.12.0, hyper-util0.1.21, Tower0.5.3 and Tokio1.54.1 with a persisted lockfile. These are distinct from the older abstract Python admission model; no model counts are reported as network execution.

## Native paths exercised

**Tower negative control:** a ConcurrencyLimit(1) wraps a real service whose response contains a Body. Once the response Future completes, a second request is admitted while the first body has not been consumed or dropped; the observed live-body count becomes2. This reproduces the source-derived gap between response-future concurrency and stream lifetime.

**Shared stream-slot owner:** an OwnedSemaphorePermit is held by an Arc shared between Body and a simulated foreign callback context. Dropping the body closes its producer but does not release the stream slot while the callback owner exists. Dropping that owner releases the final permit. This tests local ownership sequencing, not native-to-managed callback quiescence.

**Backpressure and EOF:** a capacity-one body channel rejects a second queued frame; polling the first frame permits progress. Sender close produces EOF and retires the body's counted owner exactly once. Dropping afterward does not decrement twice. A bounded item count is not an arbitrary-byte bound.

**Actual HTTP1 transport/handler future:** a Hyper client and server communicate through Tokio's in-process duplex transport. The native Service waits on a oneshot representing application completion; the response does not finish before that completion. Then two streamed frames yield exactly `hello world`, Body retirement occurs, the callback still retains the stream slot, and both connection drivers finish after sender close. This exercises real Hyper parsing/connection/body machinery without rewriting its core.

## Architecture consequences

A compiled native service can wait for external completion and return a native Body without a generated Rust function per C# handler. The next Adapter layer must attach the existing C ABI/managed completion/GCHandle retirement protocol to this seam. The test uses a Rust oneshot, **not a C# Task bridge**. Kestrel remains the comparison baseline; no latency/memory/engineering winner is established.

Retain separate request/body/callback/cleanup ownership. Do not confuse the stream-slot lease with a byte lease: Bytes may outlive a delivered frame and must retain their own accounting until their last relevant borrower is done. No TLS, external TCP, HTTP2 credit exercise, time-limited abort/recovery, client-disconnect storm, multicore weak-memory model, long soak or process RSS bound is proven here. Actix worker-affinity and Pingora proxy scope remain source-researched alternatives, not executed implementations in this fixture.

Persisted evidence lives under NativeWeave `verification/native-slices/server-linux` and `server-windows`, with exact commands, source/lock hashes and raw outputs. R27/R29 remain continuable; D18/B16/B17/B20 must add the foreign managed handler bridge and full resource/cancel/close tests before formal acceptance.
