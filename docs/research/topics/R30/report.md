# R30 — Cross-language diagnostics, low-overhead paths and bounded exporters

Historical research began on 2026-11-12, with supplemental evidence through 2026-11-13; see [evidence.json](evidence.json) for current packet and input baseline/hash. This round additionally read the async span/subscriber boundaries of tracing 0.1.44 and actually executed an independent diagnostics Native AOT probe; research/design acceptance still awaits independent review. Not all metric/exporter implementations were read, and future product performance acceptance was not executed. The design is synchronized to [D19](../../../server/protocols-and-observability.md).

## 1. Selected boundaries

C# applications use ActivitySource, Meter and structured logging by default; exporters are independent optional packages. Avoid constructing Activities and costly tags when there is no listener; only small optional trace contexts and operation correlations cross FFI. Activity objects, ExecutionContext and Rust span guards must not become cross-language public handles. Sampling, dropped logs and exporter network failures must not change business terminal states or resource reclamation.

Non-goals: full payload/SQL logging enabled by default, arbitrarily high-cardinality metrics, uniformly replacing every Engine's diagnostics library, using correlation IDs as security identities, or claiming zero-cost telemetry.

## 2. Pinned sources and reading

| Source | Pinned commit | Path/range |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | ActivitySource.cs121–141、234–256 |
| opentelemetry-dotnet core-1.21.0 | `51c6db11dadde6ed5019af4f42332860f1a5d8da` | BatchExportProcessor.cs99–203；BatchExportActivityProcessorTests.cs28–53、117–260、300–322 |
| W3C TraceContext1 | Fixed URL for the 2021-11-23 Recommendation | §3.2.2 fields, §3.2.4 version rules |

Exact URLs/blobs are in evidence; [coverage](coverage.json) does not count test source as execution results. The pinned runtime license is MIT and the pinned OpenTelemetry license is Apache2. The W3C specification supports trace-field semantics; D19's 32-byte binary adapter layout is NativeWeave's own choice, not a W3C-prescribed ABI.

## 3. Activity from public entry point to allocation path

The `HasListeners` source read checks that the listener collection is nonempty and not disposed; the internal creation path returns null immediately without listeners. If callers construct large tag dictionaries/strings first, avoiding Activity creation in the library cannot offset those costs. The hot path therefore checks whether diagnostics are needed before constructing tags according to actual sampling; lightweight operation counts and failure terminal states remain reliably maintained.

`HasListeners` is not a sampling decision, nor does absence of listeners prohibit forwarding inbound trace context. Valid incoming context may be passed downstream according to configuration without creating an Activity object. Cross-language entry points capture values; when callbacks return on arbitrary threads, the completion coordinator restores the managed scope rather than relying on the same thread-local state. Rust span enter/exit scopes remain within Rust execution paths; guards must not outlive FFI calls with the expectation that managed await will handle them correctly.

Candidate C# path, not compiled:

```csharp
using var activity = TraceSource.StartActivity("nativeweave.db.execute");
if (activity?.IsAllDataRequested == true)
    activity.SetTag("db.system.name", providerName);
// correlationId correlates events; do not log SQL parameters or put it in metric tags.
var result = await operation.ConfigureAwait(false);
return result;
```

Failure/Unknown paths record separate outcome classifications and bounded error categories and release scopes in finally; cleanup must not be skipped for lack of a telemetry listener. Combining successful Task completion and business durability into one span status is also incorrect.

## 4. Export queue and shutdown call chains

`TryEnterOnEnd` first checks shutdown, registers activeOnEnd and then rechecks shutdown; a losing race undoes the registration. This double check prevents the gap in which shutdown completes after checking that it has not started but before registering. `TryExport` tries to add to the circular buffer; only the enqueue that reaches the batch threshold wakes the worker, avoiding a kernel transition for every entry. Full queues or exhausted spin budgets cause drops with counters.

`OnShutdown` uses Interlocked to enter shutdown, waits for accepted OnEnd calls using the remaining time budget, shuts down the worker and finally passes the remaining timeout to the exporter. The source supports bounded shutdown coordination, which does not imply arbitrary third-party exporters can be forcibly stopped; NativeWeave must isolate faulty exporters and make the business exit policy explicit.

Test definitions capture actual counterexamples: queue size 1 triggers export; registered OnEnd calls that have not exited prevent shutdown completion; finite timeouts end waiting; repeated multithreaded races ensure OnEnd is either rejected or awaited, leaving no registration that never exits. This round read the tests without executing them; upstream test names cannot count as passing evidence.

## 5. What NativeWeave adopts and what it does not copy

Adopt optional bounded batch export and failure drop counters; do not require all Engines to depend on OpenTelemetrySDK or format data under locks or perform synchronous network export in FFI callbacks. D19 defines fixed-value TraceContextV1 metadata and optional bounded tracestate; CoreErrorRecord.correlation_id remains a diagnostic identifier and does not replace trace IDs or authorization.

Metric labels are limited to route templates, protocol profiles, providers and normalized error categories; requestID/operationID, SQL and arbitrary user labels must not become unbounded default dimensions. Bound attribute counts/value bytes per span, event counts, queue entries and payload per entry; an entry-count limit does not prove byte/RSS bounds. Secrets, full bodies, raw SQL parameters and private keys are not logged by default; debug sampling also requires an explicit bounded policy.

Diagnostics themselves consume CPU and allocations; TryAdd's spin budget can also cost significant time under contention. B23 should separately measure disabled/sampled/full trace/exporter failure modes and record callback duration, CPU/op, allocations, queues/drops and business p99 changes, rather than only the ideal empty-listener path.

## 6. API/ABI, platforms and validation

The fields/offsets of 32-byte TraceContextV1 are in D19: size/version/flags/reserved/16-byte trace ID/8-byte parent span ID. C# Native AOT and Rust layouts have been compiled and executed separately: size=32, trace_id offset=8 and parent_span_id offset=24. Invalid size/version/zero IDs, unknown flags, oversized tracestate and actual cross-thread context restoration across FFI still require B20 integration validation; one-sided layout success does not mean cross-language transport has executed. Unsupported optional FFI metadata is ignored without changing business semantics; malformed external traceparent starts a new root, while illegal ABI memory access remains a contract error.

| Task | Executable acceptance criteria |
| --- | --- |
| B20 | Static layout assertions/serialization goldens; concurrent callbacks and parent correlation; admission/shutdown races; exporter full/failure/blocking/timeout; drop counts and no secret leaks |
| B22 | No sustained growth in registrations/Activities/buffers under 24h/72h churn/cancellation/fault loads; exporters must not retain business resources |
| B23 | Cost breakdown of diagnostic switches and sampling, consistent native/managed traces and aligned performance-test conditions |
| B24 | Independent exporter packages, clean-machine AOT, Windows/Linux timer/thread differences, SBOM and upgrade compatibility |

Q17's diagnostics boundaries have reviewable design decisions; actual low overhead, freedom from leaks and cross-platform AOT belong to these implementation obligations. Independent review interfaces: R08 examines callback hot paths and lifetimes; R29 checks budgets beyond counts alone; R34 checks that incoming traces cannot become identities or leak secrets; R28 examines protocol error/Unknown-to-trace mappings.


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


## 7. Completed tracing source and actual Native AOT diagnostics probe

New source identity: tracing0.1.44, crate VCS commit
`2d55f6faf9be83e7e4634129fb96813241aac2b8` in `tokio-rs/tracing`.
Read `tracing/src/span.rs:596–641,780–790`, `instrument.rs:176–231,277–324,378–389`
and `subscriber.rs:1–63`; source hashes and crate provenance are in
[source-inspection.json](../../../../verification/server-completion/source-inspection.json).
`Instrumented<Future>::poll` enters/exits the span per poll; `WithDispatch::poll`
sets the captured dispatcher per poll. A Span::enter guard held across await leaves
unrelated work inside the wrong span. A thread-local subscriber is not automatically
propagated to another worker; library code must not seize the process-global subscriber.
The Server adapter uses an explicitly owned dispatcher plus instrumented futures,
with value context carried in operations; callback scheduling restores managed context.

[DiagnosticsProbe](../../../../experiments/server-completion/diagnostics/Program.cs)
was published and executed as Linux x64 .NET11 Native AOT with warnings as errors.
The exact run is `verification/server-completion/diagnostics-local-2/run.json`.
Eleven assertions cover the 32-byte C# layout, disabled listener state, null Activity
creation, no steady-loop current-thread allocation, avoiding tag construction,
explicit remote parent, managed await/Task parent propagation and listener disposal.
The 200000-call observation was 13.589 ns/call and 0 allocated bytes on this run;
this single-process observation is not a transferable throughput claim or native-memory
measurement. It is the required disabled-observer cost witness. The initial failed
compile attempt is retained separately; no failed run is presented as success.

A separate Rust1.100 layout witness also executed successfully in
`verification/server-completion/diagnostics-rust-layout/run.json`. These probes do not
include native callback-to-managed trace propagation, exporter saturation or arbitrary
OS targets. They close the bounded design questions and leave concrete integration/
load obligations with B20/B22/B23, not a blanket requirement to redo the architecture.

## Windows observation failure and corrected measurement boundary

The first Windows diagnostics CI at run43390177287 passed the layout/listener/null
checks but failed its zero-allocation assertion. Its raw stdout/stderr and run manifest
remain under `verification/completion-ci/43390177287/diagnostics-windows-2022/`.
That version included the first clock calls inside the allocation measurement and
printed the numerical observation only after the assertion, so the failed run does
not preserve an allocation count and cannot attribute the extra allocation to
ActivitySource alone. It is not reported as a successful Windows observation.

The corrected source warms clock/counter setup outside the measurement and places
only the `StartActivity` loop inside the allocation counter window; its numerical
observation is printed before either assertion. The Linux NativeAOT rerun at
`verification/server-completion/diagnostics-reviewed-local/run.json` passed all eleven
checks and observed 200000 null returns, zero current-thread allocated bytes and
12.437 ns/call. This is another scoped observation, not a promise of a universal
zero-allocation or timing result. At that checkpoint Windows still required its corrected run; the threshold was not raised to mask its failure. The later retrieved run below closes this finite platform-evidence gap.

## Final corrected Windows/Linux evidence and diagnostic defaults

Existing Actions run43401371233 at source `5bb128424259f3d9cf594b4e50d7688ad5b6541e`
has now been retrieved, not rerun. The exact source/CRLF transformation, archives,
logs and binary hashes are recorded in `verification/server-completion/diagnostics-final-ci.json`.
Both Release Native AOT executions passed all11 assertions and observed200000 null
returns and0 current-thread allocated bytes in the StartActivity-only warm loop.
Windows observed16.634 ns/call; Linux20.468 ns/call. These single-run timings do not
compare operating systems or prove universal zero overhead. Debug, Meter/log sinks,
enabled sampling/export, native callback propagation and native memory were not measured.

D19 now makes configuration explicit: Release and Debug install no listener/provider,
process-global Rust subscriber or exporter by default. The optional convenience log preset
uses Warning/Error through application-configured sinks, with IsEnabled before formatting;
Debug does not automatically switch on high-volume tracing. Resource safety and retirement
checks stay active independently. B20/B23 implement and measure the explicit disabled,
Debug-local, sampled/full and exporter-fault modes; these product rows are not claimed here.
