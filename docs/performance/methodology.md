# D13 — Performance, memory and developer-cost methodology

Contract: C-PERF-001@0.4.0, research/design specification. Author: `/root`.
Status: review-ready; registry carries the exact reviewed version and acceptance state.
Evidence: [R17](../research/topics/R17/report.md), [R10](../research/topics/R10/report.md),
[R18](../research/topics/R18/report.md); implementation tasks A21, B23 and acceptance B22/B24.

## 1. Questions and comparison boundary

Measure how much NativeWeave adaptation adds to the same mature Rust Engine, and what a
feature-equivalent C# Native AOT application costs. Database/ORM/Server remain Rust product
domains regardless of which measured stack wins. Report adverse results and fix their causes.
Kestrel/Npgsql/managed alternatives are comparison executables, never hidden product fallbacks.

Three routes share operation semantics, data, protocol/TLS/auth/serialization settings,
resource budgets, error policy, database durability and deployment hardware:

| Route | What it establishes | What must remain equal |
|---|---|---|
| Direct Rust Engine | Engine baseline and inherent allocation/runtime cost | Exact upstream/lock/features; same query/protocol/codec work |
| C# AOT + Rust | Actual integration cost, including callbacks and DTO mapping | Same Engine/configuration plus documented boundary transformations |
| C# AOT comparator | Capability and engineering-cost comparison | Equivalent functional contract; disclose unavoidable engine differences |

A mock, byte-sum call or empty Handler can isolate overhead but cannot stand in for whole-domain
results. Record unsupported/failed cells, never silently remove unfavourable workloads.

## 2. Harness and exact reproducibility

A21 provides an external controller and separately built target executables. Use monotonic clocks
within a process; compute distributed duration at one observer or record clock-sync uncertainty.
Pin SDK/rustc/linker, OS/kernel/CPU/ISA, affinity/power policy, package/native hashes, features,
allocator, data seed and dataset hash, warmup, offered-rate sequence, duration and run order.
Record background load, container/cgroup limits and unavailable counters.

BenchmarkDotNet's inspected NativeAOT builder emits PublishAot and can default to the local
`native` instruction set. Override ISA to the declared release profile for cross-machine comparisons;
record an additional native-ISA experiment separately. BDN's inspected integration tests skip some
hosts and permit its own reflection warnings; neither is permission to skip NativeWeave's Windows
tests or suppress product AOT warnings. Harness dependencies stay out of product packages.

Use BDN for controlled microbenchmarks in isolated executables built with its NativeAOT toolchain and for supported allocation measurements. Do not substitute a JIT InProcess toolchain for a Native AOT target. Use the
external rate-controlled harness for network, DB, queueing and multi-process workloads. A Rust
Criterion-style sample is a microbenchmark comparison, not a replacement for the end-to-end driver.

## 3. Load and latency rules

Primary overload experiments schedule arrivals independently of responses (open-loop). Record
scheduled time, actual dispatch, completion/timeout, status, bytes, attempts and admission result.
Report offered, admitted and completed throughput separately. End-to-end latency starts at the
scheduled arrival; separately report queue delay, service time and client-side generator delay.
If the generator falls behind or saturates, invalidate the intended offered-rate cell.

Closed-loop throughput is useful but labelled as such. It cannot establish tail latency at a fixed
offered load. The executable [finite omission counterexample](../../experiments/performance-completion/omission.py)
shows service-only p99 of 1 synthetic ms while scheduled-arrival p99 is 100 ms. These are model
values, not measured NativeWeave performance. HdrHistogram expected-interval correction fills
missing samples, but must not be applied twice or confused with actually observed arrival latency.

Record p50/p90/p95/p99/p99.9 only with adequate sample counts. Preserve raw histograms, overflow
and rejected observations; specify resolution and maximum range. Distinguish successful, rejected,
cancelled and timed-out requests. Do not hide timeouts by reporting only completed successes.

## 4. Required workload matrix

| Domain | Normal cells | Adversarial/boundary cells |
|---|---|---|
| Interop | direct calls, batches, owned results, sync/async completion | tiny payload overhead, late cancel, callback contention, close |
| Query/ORM | cached/uncached descriptors, joins, relations, projection, aggregate, pagination | NULL/Unicode/large values, bind error, unsupported dialect, skew/N+1 |
| Database | SQLite/PG, short/long tx, streaming, bulk, concurrent reads/writes | pool exhaustion, slow reader, disconnect, commit Unknown, rollback drain |
| Server | HTTP1/HTTP2, TLS, unary/streaming, selected gRPC/MCP | slow headers/body/client, stream resets, retained buffers, shutdown |
| Packaging/DX | cold start, restore/build/run/publish, ordinary model/Handler edit | wrong RID/ABI, offline after restore, clean consumer without Rust |

Both cold and warm measurements are necessary; report cache and connection reuse explicitly.
Windows/Linux are independent cells. Large/small payloads and low/high concurrency must both be
present, so batching wins are not extrapolated to tiny requests or vice versa.

## 5. Memory and ownership accounting

Measure managed allocations/op, native allocations/op and bytes copied with their instrumentation
overhead. GC allocated bytes do not measure native allocation or peak live memory. Track live owner,
request, operation, callback root, connection, queue slot, permit, byte-credit and retirement counts.
For each counter define its acquire/release linearization point and expected quiescent value.

Report private working set/RSS, peak RSS, GC heap committed/live, native allocator retained/live,
thread stacks/count, code and mapped-library bytes. Kernel socket/TLS buffering and child-process
memory are separate observations. A bounded queue or application byte-credit proof is not an RSS
bound. Retained Bytes slices retain their full allocation owner; release credit at the last actual owner.

Memory soak uses repeated steady-state load/drain cycles and evaluates trend after warmup and full
retirement, with allocator retention disclosed. A rising counter that should return to zero is a defect;
flat RSS alone cannot prove absence of a leak. Process exit is not a resource-retirement test.

## 6. Statistical decisions and developer cost

Use multiple independent process launches, randomise route/run order and keep raw samples.
Predeclare a comparison's equivalence/regression band from a reviewed baseline, measurement noise
and workload requirements. Report effect sizes and confidence intervals, not just an isolated mean
or a favourable p-value. Do not invent a universal 'within 5%' target before baseline data exists.

Track generated/handwritten lines by role, dependencies, build time, binary/package size, platform
steps, custom patches, FFI calls per logical operation and application code required for a new entity
or Handler. Count complexity moved into generated/native code rather than hiding it. Performance
optimisations require an explicit owner/lifetime/error cost and a measured relevant benefit.

## 7. Failure, cancellation and result integrity

Use an external functional oracle alongside load. Transaction Unknown, rejected requests and
cancelled operations remain in the result dataset. Reconcile durable effects independently after
lost COMMIT replies. Report recovery latency and resources retained at timeout. Stop load generation
on an integrity violation and preserve the seed, trace and last ownership counters.

Benchmark cancellation requests stop new work; bounded cleanup preserves owners until safe
retirement. A harness deadline does not authorize freeing in-flight native memory. Fault injections
and throughput runs are separate labelled modes; failures never become performance successes.

## 8. Delivery and acceptance

A21 implements the reusable controller, metadata schema, histograms and observation adapters.
B23 consumes actual AOT reference applications and direct native/managed comparators; B22 owns
fault/soak oracles, B24 binds final release profiles. Store immutable input/run/artifact hashes and
independent analysis in the existing ledger. D13 can be design-accepted before these products exist.
No throughput, superiority, whole-memory bound or production long-load result is asserted here.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

Public API cost review now records each façade path's FFI crossings, managed/native allocations, copied/pinned/retained bytes, serialization, queueing, runtime instances and complexity. Measure minimal versus advanced/DI paths; disabled logging; first use versus steady state; typed parameters versus raw SQL; query construction versus execution/materialization; Stream versus explicit chunks; and optional protocol binary size versus configured runtime state. V1 Server native closure contains HTTP/TLS/Tonic/rmcp code, while managed protocol facades/configured state remain optional; report this cost instead of claiming absent native code. Count developer setup steps, repeated registrations, project rebuild scope, generated diagnostics and time from empty project to useful call. No performance improvement is accepted from signature compilation. A21/B23/B24 own product measurements.
