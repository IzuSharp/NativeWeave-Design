# R29 — Byte budgets, backpressure, cancellation and graceful shutdown

Historical research began on 2026-11-12, with supplemental evidence through 2026-11-13. See [evidence.json](evidence.json) for the current packet and pinned input hashes. The finite Python model, actual Bytes/Tokio/Body/permit Windows/Linux experiments and new native protocol/network/TLS probes have separate actual records; the complete product bridge and sustained-load work have not been implemented. Research/design awaits independent review. The design is written in [D18](../../../server/hosting-and-streaming.md); Q16 is recommended for closure as resolved at the design level after independent review.

## 1. Guarantees to establish

Load and malicious slow peers must not cause unbounded bodies, producer waits, native chunks, callbacks or shutdown waits. The guarantees distinguish application logical bytes, metadata counts, native-owned bytes and actual platform RSS; a channel capacity or total request-body length cannot substitute for all metrics.

Non-goals: proving arbitrary real scheduling with a finite model; equating cancellation with physical stopping; specifying one RSS figure for every deployment; implementing the entire streaming framework in this round.

## 2. Key source call chains

| Pinned source | Observation | Design implication |
| --- | --- | --- |
| Tokio1.54.1 `bounded.rs` send765–825/reserve1070–1126 | send holds the value while waiting for reserve; cancellation may drop the value; dropping an unused Permit returns capacity | Acquire credit before allocation and bound waiters; merely making the channel bounded is insufficient |
| Kestrel11 `Http1Connection.cs`110–155 | Input/output completion cancels RequestAborted; Abort also poisons the body | Body EOF must be separate from transport completion/abort |
| Kestrel11 `TransportManager.cs`119–193 | unbind/accept-loop completion→close→abort fallback→dispose | Listener, handler, native callbacks and buffers do not share one endpoint |
| Hyper1.12 HTTP1 conn125–149 | Graceful shutdown requires continued polling | An overall drain deadline and completion observation are required |

SHAs/URLs/blobs are in evidence; this round read only these ranges. Kestrel HTTP2/3, kernel sockets, TLS and actual allocators were not comprehensively studied; see [coverage](coverage.json). Pinned licenses were identified as MIT; no upstream implementation was copied.

## 3. Selected resource algorithm

A unified budget coordinator simultaneously limits active connections, HTTP2 streams, application requests, metadata waiters, per-request payloads, global managed/native payloads, active uploads and DB leases. Configured fixed limits are not performance guarantees; the referenced D18 profile is only a reproducible experimental starting point.

Acquiring credit is the linearization point permitting allocation/retention. Moving an item from a queue to a consumer cannot return credit; the last owner must release it first. Native→managed or managed→native copies are charged twice while both buffers are live. Cancelling pending waiters returns reservations; cancelling in-flight consumers conveys intent only and does not return credit for memory still being accessed. Bytes belonging to a completed request whose native resources have not retired still consume budget.

The global/per-request resource layers must not each acquire half and wait indefinitely. Implement either atomic grant/cancellation by one coordinator or rollback when an all-resources try-acquire fails; copies retain bounded slack and request both sides' budgets together, prohibiting mutual waits for copy room at full credit. Metadata wait queues are bounded and fair across tenants; overflow returns 429/503 before reading the business body, without allocating additional large buffers to retain pre-rejection input.

Pull provides backpressure: consumers request at most the bytes for which credit is already available; reads have at most one pending operation, response writes have only one pending flush, and progress continues only after releasing owned chunks/advancing. Async FFI results follow Core's take_result outside callbacks; callback contexts must not be released before all native/managed obligations are quiescent. The default safe adapter permits bounded copies and does not expose escaping native Memory across await.

## 4. Actual finite-model results

[credit_model.py](credit_model.py) is an original, independently runnable logical model from this round. Three producers have sizes 1/2/2, global credit is 3, queue capacity is 1, and there is one consumer; states include waiting/reserved/materialized/queued/consuming/done. In-flight cancellation records intent only; credit returns on consumer release.

Reproduction command: `python docs/research/topics/R29/credit_model.py > docs/research/topics/R29/experiment-result.json`, exit 0, empty stderr. Environment: Python3.12.14, Linux6.18.57 x64/glibc2.41. To record D12 requirements completely, the final result was rerun through an instrumented wrapper; actual argv, UTC start/end times and raw stream hashes are in [run-manifest.json](run-manifest.json). The first run's times were not fabricated retrospectively. Script and stdout SHA256 are in evidence's run_manifest; the [raw result](experiment-result.json) preserves complete versions and limitations.

The actual enumeration found 282 reachable states, 895 transitions and 8 terminal states. Every state satisfies `allocated <= reserved <= 3`, queue<=1 and consumer<=1; cancelling an item being consumed does not lose its credit. Every state has some path to completion. The counterexample also shows capacity 1, chunk 4, one queued item + 3 waiting producers with already-constructed payloads retaining 16 units, while capacity×chunk is only 4.

This establishes only finite-state safety and existence of a completion path; it does not prove fairness of arbitrary schedulers, absence of actual lost wakeups, freedom from permanent OS traffic stalls, native copy budgets or RSS bounds. The model permits abstract atomic resource transfers; production implementations must realize them with actual synchronization primitives and race tests. A model pass cannot be converted into a Tokio/.NET/AOT pass.

## 5. Cancellation, half-close, deadlines and draining

Normal body EOF ends only the input direction, and a response may still be generated; transport determines TCP half-close/HTTP2 reset. A read returning 0 alone must not always mean request success or abort. Before headers are committed, a standard error may be written; afterward, only the stream is terminated. Termination does not prove the client read all bytes. An early response before the entire body is read permits bounded draining only; close/reset when the limit expires to avoid consuming attacker-controlled data indefinitely.

The overall request deadline uses a monotonic clock and is consumed jointly by queueing, DB waits, body and response; progress/chunks do not extend the total time. Child deadlines take the smaller remaining allowance. After DB COMMIT enters the wire, an independent commit deadline records acknowledgement or Unknown; the HTTP token cannot rewrite the effect.

Shutdown first sets readiness=false/stops admission, then stops the listener and waits for accepted work until the drain deadline; timeout triggers abort. Native callback quiescence, cancellation-registration release and control-call accounting must still complete. If they cannot, record fault isolation and retain owners rather than freeing live memory to guarantee timely exit. Repeated stop calls share the shutdown result; exporters receive a final, separate small budget.

## 6. Cost, platforms and formal validation

Every credit lease/cancellation waiter has metadata cost and should use reserved/bounded allocation based on active limits; do not create a Task or timer for every retry. Larger chunks save crossings but increase residency and cancellation latency. RSS also includes GC, pools, native allocator fragmentation, thread stacks and TLS/H2/kernel buffers; observe slopes and steady plateaus rather than a single snapshot.

| Existing task | Counterexamples/proof obligations to satisfy |
| --- | --- |
| B16 | Credit before allocation, byte and count boundaries, overflow and bounded waiters; cancellation in every reserve/queue/consume window; partial consumption, slow clients, unread bodies and half-close |
| B17 | Double accounting for copies, Rust-owned chunk/managed slab transfer, panic/timeouts and callback retirement; native allocator counts |
| B20 | Admission-close/completion races, drain/abort/retire, COMMIT Unknown and exporter faults; monotonic deadlines do not reset |
| B22/B23 | Actual Windows/Linux AOT traffic; 24h/72h connection churn, cancellation storms and resource trends; separate logical bytes/RSS/CPU/tail latency |

Cross-review: R12 checks pin/owner and byte credit; R07/R08 examine retirement; R26/R27 validate transport-completion semantics; database R21 checks Unknown. Product implementation remains not-run; executed research probes retain their actual scope. Design choices need not await all product tests to be established.


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
