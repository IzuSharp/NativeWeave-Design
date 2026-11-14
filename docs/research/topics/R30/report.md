# R30 — Cross-Language Diagnostics, Low-Overhead Paths, and Bounded Exporters

Historical research began on 2026-11-12, with supplementary evidence through 2026-11-13; see [evidence.json](evidence.json) for the current task packet and input baseline/hash. This round adds reading of tracing 0.1.44 async span/subscriber boundaries and actually executes an independent diagnostic Native AOT probe; research/design acceptance still awaits independent review. Not all metric/exporter implementations were read, and future product performance acceptance was not executed. The design is synchronized with [D19](../../../server/protocols-and-observability.md).

## 1. Selected Boundaries

C# applications use ActivitySource, Meter, and structured logging by default; exporters are separate optional packages. With no listeners, Activity creation and costly tag construction should be avoided; only small optional trace-context and operation-correlation values cross FFI, and Activity objects, ExecutionContext, or Rust span guards must not become public cross-language handles. Sampling, dropped logs, or exporter network failures must not change business terminal states/resource reclamation.

Non-goals: enabling full payload/SQL logging by default, arbitrary high-cardinality metrics, replacing every Engine's diagnostic library with one common library, using correlationID as a security identity, or claiming zero-cost telemetry.

## 2. Pinned Sources and Reading

| Source | Pinned commit | Path/scope |
| --- | --- | --- |
| dotnet/runtime v11.0.0 | `deae2e32bf0e018e09d64597b7c59b62b73bb3ce` | ActivitySource.cs121–141, 234–256 |
| opentelemetry-dotnet core-1.21.0 | `51c6db11dadde6ed5019af4f42332860f1a5d8da` | BatchExportProcessor.cs99–203; BatchExportActivityProcessorTests.cs28–53, 117–260, 300–322 |
| W3C TraceContext1 | Pinned URL of the 2021-11-23 Recommendation | §3.2.2 fields, §3.2.4 version rules |

Exact URLs/blobs are in evidence; [coverage](coverage.json) does not treat test source as execution results. The pinned runtime license is MIT, and the pinned OpenTelemetry license is Apache2. W3C specifications support trace-field semantics; D19's 32-byte binary adapter layout is NativeWeave's own choice, not a W3C-prescribed ABI.

## 3. Activity from Public Entry Point to Allocation Path

The `HasListeners` code read checks that the listener collection is nonempty and not disposed; the internal creation path returns null directly without listeners. If the caller first constructs large tag dictionaries/strings, avoiding Activity creation cannot offset those costs. Hot paths therefore check whether diagnostics are needed first, then create tags according to actual sampling; lightweight operation counts and failure terminal states remain reliably maintained.

`HasListeners` is not a sampling decision, nor does it mean that inbound trace context cannot be forwarded without listeners. Valid incoming context may be passed downstream according to configuration without creating an Activity. The cross-language entry captures values; after callbacks return on arbitrary threads, the completion coordinator restores managed scopes without relying on the same thread-local state. Rust span enter/exit scopes remain within Rust execution paths; a guard must not outlive an FFI call in expectation that managed await will handle it correctly.

Candidate C# path, uncompiled:

```csharp
using var activity = TraceSource.StartActivity("nativeweave.db.execute");
if (activity?.IsAllDataRequested == true)
    activity.SetTag("db.system.name", providerName);
// correlationId correlates events; do not log SQL parameters or place it in metric tags.
var result = await operation.ConfigureAwait(false);
return result;
```

Failure/Unknown paths record distinct result classifications and bounded error categories, releasing scopes in finally; absence of telemetry listeners must not skip cleanup. Combining successful Task return and business durability into one span status is equally incorrect.

## 4. Export Queue and Shutdown Call Chain

`TryEnterOnEnd` first checks shutdown, registers activeOnEnd, then checks shutdown again; losing the race undoes the registration. This double check avoids a gap where shutdown finishes after the open check but before registration. `TryExport` attempts a circular-buffer add; only the enqueue reaching the batch threshold wakes the worker, avoiding a kernel transition per item. A full queue or exhausted spin budget drops the item and increments a counter.

`OnShutdown` uses Interlocked to enter shutdown, waits for accepted OnEnd calls using the remaining time budget, then shuts down the worker and finally passes remainingtimeout to the exporter. The source supports bounded shutdown coordination, not forced termination of any third-party exporter; NativeWeave must isolate faulty exporters and make the business-process exit policy explicit.

Test definitions capture actual counterexamples: a queue of size1 triggers export; registered but unfinished OnEnd calls prevent shutdown completion; a finite timeout ends the wait; repeated multithreaded races ensure OnEnd is either rejected or awaited, without leaving registrations that never exit. This round read these tests but did not execute them; upstream test names are not passing evidence.

## 5. What NativeWeave Adopts and Does Not Copy

Adopt optional bounded batch export and failure-drop counters; do not require every Engine to depend on OpenTelemetrySDK, or format under locks or perform synchronous network export inside FFI callbacks. D19 defines TraceContextV1 fixed-value metadata and optional bounded tracestate; CoreErrorRecord.correlation_id remains a diagnostic identifier, not a substitute for traceid or authorization.

Metric labels are limited to route templates, protocol profiles, providers, and normalized error categories; requestID/operationID, SQL, and arbitrary user labels must not become unbounded default dimensions. Bound attribute counts and bytes per value per span, event counts, queue item counts, and each payload; an item-count limit does not prove byte/RSS limits. Secrets, full bodies, raw SQL parameters, and private keys are not logged by default; debug sampling also needs an explicit bounded policy.

Diagnostics consume CPU and allocations; TryAdd's spin budget can also cost significant time under contention. B23 should measure disabled/sampled/full-trace/exporter-failure modes separately, recording callback time, CPU/op, allocations, queue/drop counts, and changes in business p99, rather than testing only the ideal empty-listener path.

## 6. API/ABI, Platforms, and Validation

The fields/offsets of 32-byte TraceContextV1 are in D19: size/version/flags/reserved/16-byte traceid/8-byte parentspanid. C# Native AOT and Rust layouts were separately compiled and executed, with size=32, trace_id offset=8, and parent_span_id offset=24. Invalid size/version/zeroID, unknownflags, excessive tracestate length, and actual cross-thread context restoration across FFI remain B20 integration validations; successful one-sided layout checks do not mean cross-language transport was executed. Unsupported optional FFI metadata is ignored without changing business semantics; malformed external traceparent starts a new root, while invalid ABI memory access remains a contract error.

| Task | Executable acceptance |
| --- | --- |
| B20 | Static layout assertions/serialization goldens; concurrent callbacks and parent correlation; admission/shutdown races; exporter full/failure/blocking/timeout cases; drop counts and no secret leakage |
| B22 | No sustained registration/Activity/buffer growth under 24h/72h churn/cancellation/failure workloads with telemetry; exporters must not retain business resources |
| B23 | Breakdown of diagnostics-switch and sampling costs, consistent native/managed traces, and aligned performance-test conditions |
| B24 | Independent exporter package, clean-machine AOT, Windows/Linux timer/thread differences, SBOM, and upgrade compatibility |

Q17 diagnostic boundaries have reviewable design decisions; actual low overhead, absence of leaks, and cross-platform AOT are these implementation obligations. Independent Review interfaces: R08 checks callback hot paths and lifetimes; R29 checks budgets beyond counts alone; R34 checks that incoming traces cannot become identities or leak secrets; R28 checks protocol error/Unknown-to-trace mappings.


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
