# R29 — Byte Budgets, Backpressure, Cancellation, and Graceful Shutdown

Historical research began on 2026-11-12, with supplementary evidence through 2026-11-13. See [evidence.json](evidence.json) for the current task packet and pinned input hashes. The finite Python model, actual Bytes/Tokio/Body/permit Windows/Linux experiments, and added native protocol/network/TLS probes each have actual records; the complete product bridge and long workloads have not been implemented. Research design awaits independent review. The design is recorded in [D18](../../../server/hosting-and-streaming.md); Q16 is recommended for closure as design-resolved after independent review.

## 1. Guarantees to Establish

Load and maliciously slow peers must not cause unbounded bodies, producer waiting, native chunks, callbacks, or shutdown waits. Guarantee subjects are divided into application logical bytes, metadata counts, native-owned bytes, and actual platform RSS; neither one channel capacity nor total request-body length can replace all these metrics.

Non-goals: proving arbitrary real scheduling through a finite model; equating cancellation with physical stopping; prescribing the same RSS number for every deployment; implementing the entire streaming framework in this round.

## 2. Key Source Call Chains

| Pinned source | Observation | Design implication |
| --- | --- | --- |
| Tokio1.54.1 `bounded.rs` send765–825/reserve1070–1126 | send holds value while awaiting reserve; cancel can drop value; dropping an unused Permit returns capacity | Acquire credit before allocation and bound waiters; merely changing the channel to bounded is insufficient |
| Kestrel11 `Http1Connection.cs`110–155 | Input/output completion cancels RequestAborted; Abort also poisons the body | Body EOF must be separate from transport completion/abort |
| Kestrel11 `TransportManager.cs`119–193 | unbind/accept-loop exit→close→abort fallback→dispose | Listener, handler, native callback, and buffer have different endpoints |
| Hyper1.12 HTTP1 conn125–149 | Graceful shutdown requires continued polling | A total drain deadline and completion observation are required |

SHAs/URLs/blobs are all in evidence; only these ranges were read in this round. Kestrel HTTP2/3, kernel sockets, TLS, and actual allocators were not fully researched; see [coverage](coverage.json). Pinned licenses were identified as MIT; no upstream implementation was copied.

## 3. Selected Resource Algorithm

A unified budget coordinator simultaneously limits active connections, HTTP2 streams, application requests, metadata waiters, per-request payloads, global managed/native payloads, active uploads, and DB leases. Configured fixed limits are not performance guarantees; the referenced D18 profile is only a reproducible experiment starting point.

Acquiring credit is the linearization point permitting allocation/retention. Moving an item from a queue to a consumer does not return credit; final-owner release is required. Native→managed or managed→native copies are charged twice while both buffers remain alive. Canceling a pending waiter returns reservations; canceling an in-flight consumer only records intent and does not return credit for memory still being accessed. Bytes retained before native retirement still consume budget after request completion.

Global/per-request resource layers must not each acquire half and then wait indefinitely. Implementation chooses either atomic grant/cancellation through one coordinator or rollback when all-try-acquire fails; copying retains bounded slack and requests both sides' budgets together, prohibiting mutual waits for copy room at full credit. Metadata wait queues are bounded and tenant-fair; overflow returns 429/503 before reading the business body, without allocating an additional large buffer to retain input before rejection.

Pull provides backpressure: consumers request only the maximum bytes for which credit is already held; reads have at most one pending item, response writes have only one pending flush, and progress resumes only after owned-chunk release/advance. Async FFI results use Core take_result outside callbacks; callback contexts must not be released before all native/managed obligations are quiescent. The default safe adapter permits bounded copies and exposes no escapable native Memory across await.

## 4. Actual Finite-Model Results

[credit_model.py](credit_model.py) is an original, independently runnable logical model from this round. It has three producers of sizes 1/2/2, global credit 3, queue capacity 1, and one consumer, with waiting/reserved/materialized/queued/consuming/done states; canceling in-flight work only records intent, and only consumer release returns credit.

Reproduction command: `python docs/research/topics/R29/credit_model.py > docs/research/topics/R29/experiment-result.json`, exit 0, empty stderr. Environment: Python3.12.14, Linux6.18.57 x64/glibc2.41. To fully record D12 requirements, the final result was rerun through an instrumented wrapper; actual argv, UTC start/end times, and raw-stream hashes are in [run-manifest.json](run-manifest.json), without fabricating the first run's timing. Script and stdout SHA256 values are in evidence's run_manifest; the [raw results](experiment-result.json) retain complete versions and limitations.

Actual enumeration found 282 reachable states, 895 transitions, and 8 terminal states. Every state satisfies `allocated <= reserved <= 3`, queue<=1, and consumer<=1; canceling an item being consumed does not lose its credit. Every state has some path to completion. The counterexample also shows that with capacity1 and chunk4, one queued item plus 3 waiting producers with materialized payloads retain 16 units, although capacity×chunk is only 4.

This establishes only finite-state safety and existence of completion paths; it does not prove arbitrary scheduler fairness, absence of lost real wake-ups, absence of permanent OS traffic stalls, native-copy budgets, or RSS limits. The model permits abstract atomic resource transfers; formal implementations must realize them through actual synchronization primitives and race tests. A passing model must not become a claim of passing Tokio/.NET/AOT validation.

## 5. Cancellation, Half-Close, Deadlines, and Drain

Normal body EOF ends only the input direction, allowing a response to be generated; transport determines TCP half-close/HTTP2 reset, so read0 alone cannot universally mean request success or abort. Before headers commit, a standard error may be written; afterward only the stream is terminated, which does not prove the client read every byte. An early response before the body is fully read permits only bounded drain, closing/resetting after the deadline to avoid consuming attacker data indefinitely.

The total request deadline uses a monotonic clock; queueing, DB waits, body handling, and responses share it, and progress/chunks do not extend total time. Child deadlines take the smaller remaining allowance. After DB COMMIT is admitted, a separate commit deadline records confirmation or Unknown; an HTTP token cannot rewrite effects.

Shutdown first sets readiness=false/stops admission, then stops the listener and waits for accepted work until the drain deadline, aborting on timeout. Native callback quiescence, cancellation-registration disposal, and control-call counts must still complete; otherwise record fault quarantine and retain owners rather than freeing live memory to guarantee punctual exit. Repeated stop calls share the shutdown result; exporters receive a final separate small budget.

## 6. Cost, Platforms, and Formal Validation

Every credit lease/canceled waiter has metadata costs that should be reserved or bounded according to activity limits; do not create a Task or timer for every retry. Larger chunks save crossings but increase residency and cancellation latency. RSS also includes GC, pools, native-allocator fragmentation, thread stacks, TLS/H2/kernel buffers; observe trends and steady plateaus rather than one snapshot.

| Existing task | Counterexamples/proof obligations to realize |
| --- | --- |
| B16 | Credit before allocation, byte/count bounds, overflow, bounded waiters; cancellation in every reserve/queue/consume window; partial consumption, slow clients, unread bodies, half-close |
| B17 | Double accounting during copies, Rust-owned chunk and managed-slab transfers, panic/timeout, callback retirement; native-allocator counts |
| B20 | Admission-close/completion races, drain/abort/retire, COMMIT Unknown, exporter failure; monotonic deadlines do not reset |
| B22/B23 | Actual traffic under Windows/Linux AOT; 24h/72h connection churn, cancellation storms, resource trends; separate logical bytes/RSS/CPU/tail latency |

Cross-Review: R12 checks pins/owners and byte credit; R07/R08 check retirement; R26/R27 verify transport-completion semantics; database R21 checks Unknown. Product implementation status remains not-run; executed research probes retain their actual scope. Design choices need not await every product test to be established.


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
