# R26 — Kestrel Native AOT comparator, with an executed baseline

Current research revision: 2026-11-13. The initial report's choice of Kestrel as the
NativeWeave product host was an architectural deviation and is withdrawn. The user
requires the actual Server engine to be Rust. Kestrel remains a mandatory, fair
functional, memory, performance and developer-cost comparator. B15 is the C# application
and Handler surface; B17 is the required native host. There is no Kestrel product profile.

## Recovered work and fixed sources

This task was incorrectly still `planned` in Plan. Its existing report, evidence and
coverage already contained detailed source analysis, and that analysis is reused.
The source claims in [evidence.json](evidence.json) retain their original identities:
ASP.NET Core v11.0.0 at `1def4cdc07dc10fc267136060e3ef5c1a96d4a99`, including
`KestrelServerImpl.StopAsync` (240–291), `TransportManager.StopTransportsAsync`
(119–193), `KestrelServerLimits`, `HttpResponsePipeWriter` and its tests, and the
RequestDelegateGenerator's actual incremental source pipeline. Reading upstream tests
was never execution of those tests. The initially guessed RDG path was corrected in
the original evidence; no fictitious path is reinstated.

## New actual experiment

[KestrelComparator](../../../../experiments/server-completion/kestrel/Program.cs)
uses the .NET 11.0.100 SDK, `CreateSlimBuilder`, statically registered handlers,
bounded Kestrel connection/request-body limits, and a real loopback HTTP/1 connection.
It publishes with `PublishAot=true`, warnings as errors, and no root-all trimming
directive. The published native executable passes five behavioral cases: health,
binary echo including all byte values, 413 for a body above the configured limit,
client-disconnect cancellation of an active streaming Handler, and bounded shutdown.
The Linux execution is [recorded here](../../../../verification/server-completion/kestrel-local-2/run.json).
The source, command, exits and binary SHA-256 are recorded; the first compile failure
(ambiguous BadHttpRequestException) and its exact source inputs remain in `kestrel-local-1`.
It was fixed with a fully qualified type. Dynamic localhost port binding was also
changed to an explicit loopback IP before the successful run.

This closes the previously missing *minimal executable AOT comparator* research
obligation. It does not supply a performance ranking, HTTP/2/TLS Kestrel equivalence,
production endpoints or a soak test. The same frozen source subsequently passed
actual Windows2022 and Ubuntu24.04 Native AOT CI (run43388468172, source
`7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`); each platform has its own publish/run
logs and binary hash. See [CI verification](../../../../verification/server-completion/ci-verification.json).
The Windows source/log hashes were checked directly, including exact LF-to-CRLF
checkout conversion; no platform result is inferred from the other.

## Reusable lessons and resulting design

Kestrel shutdown first ends accepting work, closes connections, and escalates to abort.
NativeWeave uses this as a behavioral reference while delegating transport and parser
mechanics to Hyper/Tokio. Stop/abort/body completion/native retirement remain separate.
An HTTP client disconnect is an application cancellation signal, not evidence that
database COMMIT failed. A response whose headers are committed cannot be replaced by a
second JSON error. Body EOF is neither client-application acknowledgment nor proof that
all buffer owners retired.

Kestrel's mature Minimal API/source-generation experience informs the C# API shape:
static route/DTO registration, ordinary async/await, actionable AOT diagnostics,
normal `dotnet build` and `dotnet run`. NativeWeave will expose its own narrow application
surface over the Rust host. It does not promise arbitrary ASP.NET middleware or
HttpContext compatibility and will not copy Kestrel's network engine into managed code.

The source-level baseline has unbounded connection count unless explicitly configured;
connection limits, HTTP/2 stream limits, active Handler slots, waiting metadata and owned
payload bytes are different accounting domains. A channel-length bound is insufficient
for RSS or retained buffers. The comparator intentionally makes finite limits explicit.

## Fair comparison procedure and deferred product obligations

R17/D13 and future B23 compare three paths: direct native, native + C# Native AOT, and
Kestrel Native AOT. Freeze protocol version, TLS cipher/certificate policy, serialization,
payload distribution, DB workload, concurrency, warmup, hardware and error/timeout
policy. Record throughput, CPU, startup, idle/peak RSS, allocations, native allocation
retention, thread count, p95/p99 and long-lived stream behavior. Include the FFI bridge
and DTO work; do not compare a Rust empty Handler against a feature-rich managed service.
The present five tests report functional outcomes only and are not those benchmarks.

Future B16/B20/B22 must run slow upload/download, truncated bodies, reset/half-close,
header-committed failures, cancel/drain races, HTTP1 keep-alive synchronization and
resource retirement. Those are acceptance tests of a future implementation, not a
reason to leave this completed research design permanently `planned`.

Research closure proposal: source comparison and minimal AOT execution complete;
independent review and exact graph/evidence integration still required. D18 contains
the chosen Rust design. No product implementation or contract acceptance is asserted
by this report alone.
