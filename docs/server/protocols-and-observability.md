# D19 — Native gRPC/MCP/TLS and cross-language diagnostics

Contract C-PROTOCOL-001. Design revision **0.4.0 public API refinement**. Inputs R28/R30/R34 with D18 and
Core ownership/async/error/buffer contracts. Exact-content acceptance belongs to the
registry and independent review; this specification does not assert product execution.

## 1. Required Rust host and independent protocol modules

All NativeWeave network/protocol transport runs on the required Rust Server Engine.
The selected initial composition is D18's Tokio/Hyper/Tower; mature native protocol
engines are Tonic0.14.9, rmcp3.10.0 and rustls0.23.46. C# exposes typed generated DTOs,
method/tool registration and business Handlers. Kestrel/grpc-dotnet/MCP C# SDK remain
comparators, not the production transport. A standalone Server app has a native
Server dependency even when it has no Database dependency.

The managed gRPC and MCP NuGet facades are independently selectable. The initial
`NativeWeave.Server.Native` asset contains one precompiled HTTP/TLS/Tonic/rmcp closure;
no protocol runtime, registry or services are initialized unless configured, but unused
protocol machine code may remain in the binary and B24 must measure that cost. Separate
native feature variants are not promised by v1. No protocol services belong in Core.
All packages negotiate native version/feature support; they cannot silently activate
a managed Host fallback. Ordinary new services, tool metadata and DTOs use the existing
native module. No .proto/tool-specific Rust compilation is required of consumers.

```json nativeweave-protocol-host-profiles-v1
{"host_task_ids":["B17"],"profiles":{"grpc":"native-tonic","mcp":"native-rmcp"}}
```

This block is part of the content-hashed specification. B15 is the complementary C#
application/Handler surface, B17 the native host, not mutually exclusive choices.

## 2. gRPC adapter: precise reuse and interfaces

Fixed Tonic source identity: `grpc/grpc-rust` tonic-v0.14.9,
`4c0f455c264fe2ec9f9ab5d0cc7fd2824d5daf70`. `Codec`, `Encoder`, `Decoder`,
`Grpc::unary/server_streaming/client_streaming/streaming`, and the four public service
traits are the reuse seam. [R28](../research/topics/R28/report.md) and
[executed codec](../../experiments/server-completion/protocol/src/lib.rs) show concrete
source and compilation evidence. No private Tonic type or unstable Hyper FFI becomes ABI.

An immutable runtime method descriptor carries method path, unary/client/server/bidi
kind, Handler ID, request/response type metadata identifiers, authorization policy,
message caps and deadline policy. C# generated protobuf code serializes the complete
message; the native byte codec copies/retains just those bytes. Tonic owns gRPC framing,
compression, headers/trailers, statuses, incremental decode and stream transport.
This is required language-boundary DTO mapping, not a managed gRPC stack.

The native HTTP route selects a validated `/package.Service/Method` descriptor and
constructs one of four adapters: `UnaryService<Bytes>`, `ServerStreamingService<Bytes>`,
`ClientStreamingService<Bytes>` or `StreamingService<Bytes>`. The concrete public
Tower service signatures use `tonic::Request<Bytes>` for a single request and
`tonic::Request<tonic::Streaming<Bytes>>` for inbound streams, with
`tonic::Response<Bytes>` or a bounded `Stream<Item=Result<Bytes,tonic::Status>>` response.
`tonic::server::Grpc::new(RawCodec::for_method(kind))` dispatches to the corresponding method and returns
`http::Response<tonic::body::Body>`. The executed fixture compiles the unary and
server-streaming forms; its review correction also executes client-streaming mode.
`for_method` is the Adapter's validated method-kind policy, not an upstream Tonic API.
B18 implements the complete bidirectional profile from these same public
traits; it must not import private Tonic transport helpers.

On the C# side, each generated method descriptor binds static encode/decode delegates
and a typed business delegate. Protobuf code generation and generated message/parser
code belong to the C# build; runtime schema compilation and arbitrary assembly lookup
are excluded. Deserialization failure releases the taken message buffer before
returning the selected protocol error. Method metadata and serializers may change
with an application build while the precompiled native module stays identical.

| Native adapter operation | C# semantic API | Ownership/ordering |
|---|---|---|
| `grpc_register_methods(descriptor_batch)` | `app.MapGrpc(generatedService)` | validate paths/kinds/caps, freeze descriptor generation before serving; no arbitrary runtime assemblies |
| `grpc_receive_message(op)` | `ReadAsync<TRequest>(cancel)` | pull, one pending read, owned bytes taken once after terminal success; decode failure releases lease |
| `grpc_send_message(op, bytes)` | `WriteAsync<TResponse>(value,cancel)` | serialize into bounded owner; one pending write; retain until native ack; bytes are not a gRPC frame |
| `grpc_set_status(code, detail, metadata)` | typed completion/result | native validates finite status/metadata; exactly one status commit; never append an HTTP JSON error |
| `grpc_cancel(reason)` | request cancellation | intent only; terminal/result and retirement remain distinct; no inference of remote side-effect rollback |

Unary and server-streaming require exactly one inbound message. This is an explicit
Adapter rule: pinned Tonic `map_request_unary` reads the first message, then calls
`Streaming::trailers`, which drains and discards additional messages unless the Decoder
rejects them. Each request therefore creates a fresh mode-aware Decoder with one remaining
message for these two method kinds. Its first complete message consumes that allowance;
a second complete message returns INVALID_ARGUMENT before the business Handler runs.
No message retains Tonic's INTERNAL missing-message error; one empty framed message is
valid. The counter must reset per request and must not be shared by connections or methods.
Client/bidirectional streaming uses its separate finite stream quotas and permits multiple
messages; applying the unary limit to those methods is an error. Tonic still owns framing,
incremental parsing and decompression. The Decoder sees already framed message payloads
and does not implement another gRPC parser. Independent review reproduced the default
permissive behavior and the strict correction; exact source and runs are linked in R28.

Native error/status is projected into a stable managed diagnostic category while preserving
the original gRPC code. In this Tonic version oversized framed length is OUT_OF_RANGE;
decompression-output cap is RESOURCE_EXHAUSTED. Do not pretend both paths are identical.
Default profile caps each encoded/decoded message to 1MiB, and imposes independent
stream byte/time/request quotas. Compression is disabled until explicitly selected
and validated. Client/server/bidi streams maintain independent inbound/outbound state,
bounded queues and half-close; no unbounded Task.WhenAll writes or read-ahead collection.

`tonic::server::Grpc` alone does not install Tonic transport's timeout layer. The
inspected `transport/service/grpc_timeout.rs` contains a private `GrpcTimeout` and
private parser; its timer covers the response future, not a returned streaming body.
The NativeWeave Rust Adapter therefore owns a small deadline policy component, not a
managed timer stack or an unsupported call to that private API. At header admission it
accepts at most one `grpc-timeout` value of 1–8 ASCII digits plus `H/M/S/m/u/n`, uses
checked duration arithmetic, and takes the minimum with the finite route deadline.
Invalid/duplicate values fail before the Handler (INVALID_ARGUMENT); zero is already
expired (DEADLINE_EXCEEDED); absence uses the route deadline. Cap the duration before
checked monotonic Instant addition. Unlike the inspected private helper's permissive
invalid-header fallback, this is an explicit strict NativeWeave policy.

The resulting deadline is stored once in the native request owner and drives
admission, inbound and outbound messages, response body, cancellation and retirement
coordination. Producing response headers cannot cancel the timer or restart its budget.
Expiry sets intent and competes for the terminal state; send DEADLINE_EXCEEDED trailers
if the protocol still permits them, otherwise reset/close with the real reason.
The timer itself retires with its operation. A disconnect, expired deadline and
explicit client cancel converge on cancellation intent, but cannot overwrite an earlier
success/error or prove a remote side effect did not occur. Headers/trailers already sent
cannot be rewound. All stream owners remain charged through body/callback retirement.

Research execution proves the byte-codec unary/empty/binary and server-streaming seam,
malformed length/truncation/compression rejection and HTTP2 transport separately. The
future B18 implementation must integrate all method kinds, static C# serializers and
Core callbacks; the current fixture does not claim a C# gRPC product or HTTP2+TLS
interoperability certification.

## 3. MCP adapter: explicit version, tool metadata and lifecycle

Fixed rmcp3.10.0 `53e64a93c8e32d8f7699af587b9e28566929940c` supplies
`StreamableHttpService<S,M>: tower_service::Service<Request<B>>`, `ServerHandler` and
existing JSON-RPC/MCP model/transport implementations. One native ForeignMcp type reads
runtime descriptor records for tools/resources/prompts and dispatches managed Handler
IDs. Its required methods include `get_info`, `supported_protocol_versions`,
`list_tools`, `get_tool`, `call_tool`; only declared capabilities are advertised.
`get_tool` returns the exact input schema, because returning None skips schema-dependent
SEP-2243 `Mcp-Param-*` standard-header consistency validation. The native SDK does not
thereby promise complete JSON Schema validation of all arguments. Generated typed
mapping and explicit argument/permission checks run before application dispatch; an
arbitrary-schema profile requires a separately selected mature native validator.

The initial profile is **Mcp2026_07_28 without legacy sessions or event-store replay**.
The configuration uses public rmcp builder methods:

```rust
// Executed method/configuration seam in the research fixture; full product wiring pending.
StreamableHttpServerConfig::default()
    .with_legacy_session_mode(false)
    .with_json_response(true)
    .with_stateless_protocol_metadata_required(true)
    .with_max_request_body_bytes(1_048_576)
    .with_allowed_hosts(["api.example.com:443"])
    .with_allowed_origins(["https://app.example.com:443"])
    .enforce_origin_validation();
```

The service's `supported_protocol_versions` advertises exactly the enabled version.
Default rmcp settings are not the product policy: legacy sessions default true, strict
modern metadata default false, and Origin checking is normally disabled by an empty
allowlist. Origin is a browser defense, not authentication; requests without Origin
still require explicit application authorization. Public deployments must supply their
actual Host/Origin allowlists; loopback defaults are only for local tools. Explicit
ports prevent deprecated broad origin-port matching.

HTTP method/content-type/accept, body cap and Host/Origin checks precede dispatch.
`MCP-Protocol-Version` and `_meta.io.modelcontextprotocol/protocolVersion` agree;
`Mcp-Method`, `Mcp-Name`, client capabilities and request metadata are interpreted by
the pinned SDK. The Adapter supplies finite schema/depth/string/list limits and typed
static JsonTypeInfo mapping to C#. Unknown tools/versions and metadata conflicts fail
explicitly; there is no reflection scan or permissive legacy fallback.

| Profile | Availability and lifecycle |
|---|---|
| Mcp2026_07_28, no event store | initial implementation target; no implicit protocol session; POST only; GET/DELETE405; unfinished response drop cancels this request |
| modern persisted/resumable events | not enabled by initial profile; SDK can allow GET and continue persisted work on disconnect; requires explicit cursor/auth/storage/quota contract |
| legacy2025_11_25 | not enabled implicitly; future compatibility package must separately specify initialize/session/timeout/cancel behavior and run conformance |

The distinction comes from actual rmcp source: `CancelOnDisconnect` is disarmed on
natural EOF, and persisted requests are handled differently. Do not apply the initial
profile's cancel-on-disconnect rule to every stateless transport. Application operations
that outlive HTTP are durable, authorized operation records; they cannot quietly hold
a DB transaction forever under an implicit session.

### JSON parsing admission and allocation peak

The pinned rmcp `crates/rmcp/src/transport/common/server_side_http.rs:207–267`
(`expect_json`, blob `ba248ba82a9ea001cf24eb5e26a438b0011506db`) first collects
wire bytes and then calls `serde_json::from_slice::<ClientJsonRpcMessage>`.
The helper is `pub(crate)`. Its wire cap does not bound the allocated JSON tree,
and `get_tool` or C# typed validation is too late to protect the parse allocation.
The reviewed source excerpt is `verification/server-completion/rmcp-expect-json-reviewed.txt`.

B19's native Tower admission wrapper therefore applies D07 before handing the body
to the public `StreamableHttpService`. It retains one budgeted bounded wire buffer
and uses mature `serde_json::Deserializer` with `DeserializeSeed`/`Visitor` to scan
structure without building a `Value` tree. Bound depth, nodes, object members, total
string bytes and parser work/deadline; charge escaped-string scratch and the scan's
own stack/allocation before use. This is parser reuse, not a handwritten JSON grammar
or a call to the private rmcp helper. A bounded replay Body supplies the inspected
wire bytes to the public SDK after admission.

Compute and atomically reserve a conservative peak for the exact enabled SDK/parser
profile: retained wire bytes, rmcp's additional collection capacity, its typed/JSON
tree and allocator/collection growth, UTF-8 bridge copies and managed DTO materialization
while owners overlap. Use fixed-source layout/growth analysis and bounded fixtures to
justify the formula; the whole 1MiB wire allowance is not automatically admissible
within D18's 4MiB/request/side. The native and managed budgets are separate, and reserves
remain charged until their actual owners retire. Unsupported/unproved profile bounds
prevent enabling that profile; an individual request exceeding the bound is rejected
before SDK parse and before its Handler, with a bounded resource-limit response.

B19 negative acceptance includes many tiny JSON elements, deep nesting, long escaped
strings and overlap at both per-request/global limits. It must prove parse/Handler
admission stays zero when reservations cannot fit, release exactly once on preflight
failure/cancel, and preserve normal MCP semantics for admitted requests. Product
implementation of these cases remains future Delivery; the current source reading
exposes the allocation seam and defines its concrete required adapter behavior.

The exact C# API is `app.MapMcp("/mcp", registry, options)`; `McpRegistry.AddTool`
receives static input/output JsonTypeInfo and a typed delegate. Generated bindings
may call this same explicit API; no undeclared GeneratedTools or alternate registration
path is required. Native descriptors hold tool name/schema, Handler ID and limits;
C# owns typed argument/result mapping and business authorization. Native rmcp returns
tool execution failures as tool error results; malformed/unroutable protocol requests
produce JSON-RPC errors, and pre-parser failures use HTTP errors. These layers cannot
all be flattened into one Engine status. Tool annotations are advisory metadata, never
authorization. Expensive enumeration/schema generation is bounded and happens before
serving, not per request.

The initial data bridge serializes the already native-decoded argument object into a
bounded UTF-8 owned buffer for generated C# JsonTypeInfo mapping; the result returns
through the inverse bounded mapping. Charge temporary native JSON values, UTF-8 bytes
and managed DTO buffers to their actual simultaneous owners. This can incur a second
JSON encode/decode at the language boundary and must be measured, not described as
zero-copy. A future native field-oriented projection may reduce that cost only with
an explicit capability and equivalent protocol/schema semantics. It is not a second
managed MCP parser/session/transport implementation.

The real Rust fixture changes tool names at runtime and calls both through one compiled
Handler, proving the native registry seam without Rust per-tool code generation.
It also executes method, Host/Origin and streaming body cap rejection. C# FFI DTO,
request cancellation and production conformance remain future B19 acceptance work.

## 4. TLS, native lifetime and safety

rustls0.23.46 owns one TLS layer under Hyper. Pin the crypto provider and feature set,
certificate/trust policy, ALPN and supported protocol versions in the native package.
Bound handshake concurrency/time independently of active HTTP requests. Application
payload caps do not bound TLS buffers, socket buffers or allocator-retained pages.
Fatal TLS processing errors stop reads and close the connection; continuing to buffer
after a fatal error is forbidden. Graceful close_notify and abrupt transport EOF are
different outcomes and do not prove C# callback quiescence.

Certificate reload builds/validates an immutable config and atomically swaps the
new-listener reference. Active connections hold their old snapshot until retirement;
never mutate/free a certificate/key object still used in a handshake. Private keys
are never in diagnostics, descriptors exposed to C#, source control or test manifests.
Research TLS tests generate ephemeral localhost certificates at runtime, check trust
and hostname rejection, negotiate h2 ALPN and observe close_notify; test trust is not
a production trust default. Native TLS+actual network+protocol+cross-language behavior
must be exercised together by B18/B19/B22, separately from these scoped proofs.

Host/Origin policy cannot substitute for authentication. Only explicitly trusted
proxies supply forwarding/identity headers. SQL values remain parameterized in the
required Rust DB layer. Every buffer/length uses the D07 checked arithmetic and owner
contract; in-process native code is trusted, not sandboxed by a safe language.
R34 documents resource, malformed-input and diagnostic-data boundaries.

## 5. Diagnostics: C# defaults and small contexts across FFI

Use `ActivitySource`, `Meter` and structured-logging interfaces by default; OpenTelemetry exporters are optional packages. dotnet/runtime 11 `ActivitySource` creates no activity when there is no listener, so expensive tags, links and formatted strings should be constructed only after enabled/sampling checks. `HasListeners` is only a fast check and cannot replace sampling; existing trace context may still be forwarded according to configuration without listeners, without creating an Activity object.

### Build configuration and explicit diagnostic modes

| Mode | Default behavior and cost boundary |
| --- | --- |
| Release default | Expose ActivitySource/Meter and structured logging hooks; install no listener, meter provider, global Rust subscriber or network exporter. Format log messages only when the caller-configured sink IsEnabled; build trace tags only for enabled/sampled activities. Trace sampling does not suppress enabled Warning/Error logs. |
| Debug default | Keep the same diagnostic activation defaults. Debug build configuration alone does not enable request/body/SQL tracing, a global subscriber or an exporter. Explicit bounded local debugging and Debug assertions may add cost and must not define Release safety behavior. |
| Explicit diagnostics | An application selects sinks, levels, sampling and exporter budgets. NativeWeave's convenience logging preset is Warning/Error; callers may change it. With no configured sink no log is emitted. Check IsEnabled before formatting, and use structured fields with the existing redaction and cardinality limits. |
| Sampled/full tracing or exporter failure | Measure these separately from the disabled path on both OS profiles. Include allocations, CPU, callback latency, queue byte/entry bounds, dropped diagnostics and finite shutdown; no zero-overhead claim follows from the disabled witness. |

Correctness, admission, ownership and retirement counters/checks remain active independently of
logging level, sampling and build configuration. Diagnostics cannot disable or replace them.
The existing cost fixture is a finite **Release Native AOT no-listener** observation; it does not
measure Debug overhead, logging sinks, Meter listeners, enabled tracing, Rust dispatch or export.
B20 implements this matrix; B23 measures the full selected product workload in these modes.

Pass only optional `TraceContextV1` at Engine entry points; do not pass `Activity`, `ExecutionContext`, Rust span guards or GCHandles across the boundary as generic diagnostic data. The following is a candidate layout for domain-extension metadata, not mandatory Core fields; D08 `ErrorRecord.correlation_id` remains only a correlation number:

| offset | Field | Wire type/constraint |
| --- | --- | --- |
| 0 | size | u32, v1 uses 32, read as a bounded extension |
| 4 | version | u16, v1 uses 1 |
| 6 | trace_flags | u8, retain only flags understood by this profile |
| 7 | reserved | u8=0 |
| 8 | trace_id | 16 bytes, W3C byte order; all-zero is invalid |
| 24 | parent_span_id | 8 bytes; all-zero is invalid |

The layout contains only fixed bytes, without platform pointers; this round's independent C# Native AOT and Rust repr(C) probes both compiled and executed size/offset assertions, with raw results in `verification/server-completion/diagnostics-local-2` and `diagnostics-rust-layout`. They did not transfer this structure through actual FFI; B20 must still verify golden bytes, invalid fields and actual callback paths. An Engine without this capability ignores it without affecting business results. Optional tracestate is passed through separate bounded UTF-8 metadata and copied in the synchronous entry point; baggage is not forwarded by default. Full format validation follows the [W3C Trace Context 1 Recommendation](https://www.w3.org/TR/2021/REC-trace-context-1-20211123/) §3.2/§3.3; malformed external contexts start a new root and are counted, without serving as authentication/authorization evidence. This 32-byte layout is this project's domain Adapter choice, not a binary ABI defined by W3C. Out-of-bounds structure access across the ABI remains a contract error, and invalid pointers are not tolerated.

Rust-internal tracing spans and managed Activities share trace/parent correlation without assuming thread-local state migrates across callback/async boundaries; tracing `Instrumented` and explicit `WithDispatch` establish/exit scope on each Future poll, and Span::enter guards must not cross await. Domain libraries do not call set_global_default to seize the process subscriber; completion callbacks carry only operation/correlation IDs, with the request scope restored in the managed continuation. Retry child spans must retain attempt numbers; database Unknown is a separately observable event and must not record a false Rollback/Succeeded. Sampling affects diagnostics only, not resource release or business counters.

Metric tags may include route template, protocol profile, provider and normalized error category; request IDs, operation IDs, SQL literals and arbitrary tool arguments must not become unbounded dimensions. Trace event/attribute lengths, counts per span, total exporter queue and batch sizes are bounded; a reference profile might use 32 attributes per span, a maximum 256 UTF-8 bytes per string and a 2048-item queue, while also bounding each item's payload. Count limits are not byte/RSS limits.

OpenTelemetry `BatchExportProcessor.TryExport` drops and counts items when its queue is full or spinning fails, and shutdown passes the remaining timeout to the worker/exporter. NativeWeave adopts the same fault-isolation principle: network exporters do not block in FFI callbacks or under business locks; a full queue drops diagnostics and counts the drops without preventing business completion. Actually measure worst-case callback duration and CPU usage during exporter failure; “has a bounded queue” is not a zero-cost guarantee. Shutdown ends business work/resources first, then gives telemetry a finite flush deadline; unexportable diagnostics must not prevent exit forever.


## 6. Acceptance inputs and future Codex implementation

| Existing task | Concrete implementation and release obligations |
|---|---|
| B18 | runtime native method registry; compiled C# protobuf descriptors; Core operation bridge; unary/client/server/bidi streams; metadata/trailers/deadline; bounded encoded/decompressed lengths; real HTTP2/TLS interoperability on Windows/Linux AOT |
| B19 | native rmcp ForeignHandler and exact profile; static C# tool/DTO metadata; get_tool schema registration; modern metadata checks; authn/authz; finite JSON/body/schema limits; error/tool-error distinction; disconnect/EOF/cancel and no replay/session leak |
| B20 | compile TraceContextV1 size/offset, async parent propagation; no TLS/SQL/key leakage; bounded byte+entry telemetry queue and overflow counters; exporter failure and bounded shutdown |
| B22 | cancellation/retirement races, half-close/reset, client disconnect after side effect, DB Unknown recovery, old/new protocol package mismatch, long-lived streams and quota exhaustion |
| B24 | pinned crate/NuGet/native dependency manifests, license/NOTICE/SBOM, certificate policy/provider, cross-platform native assets, upgrade conformance and independent NuGet consumption |

The native dependency graph is locked and inspected in the protocol experiment. Its
Tokio/Hyper/http/Bytes families are unified; protocol adapters do not each instantiate
a runtime. Version changes require source/test review of these exact seams and updated
artifact contracts, not blind semver trust. Codec and serialized DTO ownership are
explicit; no managed HTTP or complex network runtime is introduced to hide incompatibility.

The report/source manifests and actual fixture logs support research/design acceptance
after independent review. Future product, long-load and production conformance tests
remain labeled obligations. A current finite success does not certify untested protocol
extensions or all mobile targets. This distinction closes the design without claiming
the future B18/B19 code already exists.

R30 additionally preserves actual Windows/Linux Release Native AOT disabled-observer/layout/managed-parent probes from run43401371233. Its 0 current-thread allocated bytes in the fixed warm loop is scoped evidence, not a zero-overhead or native-memory claim; see the exact diagnostics run manifests.


### Verified Windows/Linux research CI

CI run [43388468172](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43388468172)
tested source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. Protocol13/13 and
Kestrel Native AOT5/5 passed on both Windows2022 and Ubuntu24.04. Their actual
run manifests, stdout/stderr and source snapshots are retained under
`verification/completion-ci/43388468172/`; author checks of each raw log/input hash and
exact Windows LF-to-CRLF conversion are recorded in
`verification/server-completion/ci-verification.json`. This extends platform coverage
for these same distinct cases, not their product/FFI/soak scope or independent review.

### Corrected diagnostics CI evidence

The corrected measurement ran successfully on Windows2022 and Ubuntu24.04 in
[43401371233](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43401371233),
source `5bb128424259f3d9cf594b4e50d7688ad5b6541e`. Each actual AOT execution passed
11 assertions. The 200000-call warm no-listener loop observed 0 current-thread allocated
bytes on each OS; the recorded times were 16.634 ns/call on Windows and 20.468 on Linux.
These are single-run observations, not transferable latency or native-memory guarantees.
The retrieved archive digest, byte-exact logs, source checkout transformation and executable
digest are bound by `verification/server-completion/diagnostics-final-ci.json`.
The earlier Windows failure remains preserved and is not relabelled as successful.


## Public API refinement 0.4.0

[Server API sections7–10](../api/server.md) define exact closed generic gRPC method
registration, typed text MCP tools/resources/prompts, static codecs/schema limits,
capabilities and the v1 C payload/export inventory. The earlier semantic operation
table is explanatory; implementation uses the declared nw_server_* exports. Public
RequestAborted/GrpcCallContext cancellation is delivered by bounded control signals
plus a pre-take snapshot, outside raw native callback frames. Optional trace context
uses the exact32-byte record above and bounded tracestate; enabled metrics read a
fixed native snapshot, with no default exporter/global subscriber.

B18/B19/B20 own their public XML/reference/guides/examples and API compatibility in
the same implementation task. They must verify four gRPC cardinalities, typed schema
and serializer agreement, hostile input allocation peaks, no per-DTO/tool Rust rebuild,
and independent Windows/Linux AOT consumption. Finite historical research evidence
above is preserved and cannot be reclassified as execution of this new public surface.
