# R28 — Native protocol adapters: Tonic, rmcp and rustls

Date: 2026-11-12. Scope: research and detailed design; future product implementation
is not executed. The prior managed gRPC/MCP-on-Kestrel choice is withdrawn. Its source
evidence remains useful as a comparator, but cannot satisfy a required Rust host.

## Fixed identities and actual reads

Tonic's canonical repository is now `grpc/grpc-rust`; the former `hyperium/tonic`
endpoint redirects. The selected release is `tonic-v0.14.9`, commit
`4c0f455c264fe2ec9f9ab5d0cc7fd2824d5daf70`. Read `tonic/src/codec/mod.rs:128–184`,
`server/grpc.rs:49–83,186–240,260–338,360–430`, `server/service.rs:25–145`, and
`codec/decode.rs:190–274,365–410`. These are public protocol/service seams, not an inspection
of every Tonic feature or transport configuration.

MCP Rust SDK `rmcp-v3.10.0` resolves to
`53e64a93c8e32d8f7699af587b9e28566929940c`. Read
`crates/rmcp/src/handler/server.rs:81–96,213–255,382–414,550–618,664–686,737–746`,
`transport/streamable_http_server/tower.rs:219–350,357–425,1473–1574,1734–1778,1955–1985,2050–2105,2220–2255,2398–2412,2571–2612`
and the tool-schema dispatch checks. Exact source digests and the additional inspected
model declarations are in [source-inspection.json](../../../../verification/server-completion/source-inspection.json).

rustls stays at the previously pinned 0.23.46,
`f04804fa13341a9b1dc02b5d1dd8a746f2c4b7fb`. Existing source inspection covers fatal
processing errors and output queue limits. The new executable fixture uses that exact
crate version and its ring provider, with an ephemeral localhost test identity generated in memory.

## gRPC: reuse framing without compiling Rust for each C# service

Tonic `Codec` separates message bytes from protocol framing. `Decoder.decode` receives
the bytes of exactly one full gRPC message; the Adapter does not parse the five-byte
header itself. A single `Bytes` codec can copy/retain validated message bytes into the
Core owned-buffer protocol. C# generated protobuf DTO code deserializes the message and
invokes a statically registered typed Handler; the reverse direction serializes DTO
bytes. Tonic owns compression flags, frame length, incremental decoding, trailers and
gRPC status. The user therefore adds a service/DTO in C# without rebuilding Rust.

`Grpc<T>` exposes unary, server-streaming, client-streaming and bidirectional-streaming
methods accepting corresponding public service traits; those traits have blanket
implementations for compatible Tower services. A runtime route table holds service
path, method kind, message caps, Handler ID and cancellation registration. It dispatches
to one compiled foreign service type. The published fixture compiles the byte codec
and initially executed unary and server-streaming paths. The review correction adds a
client-streaming multiple-message case; bidirectional behavior and full C# product
integration remain implementation acceptance obligations. All streaming methods must
keep independent one-read/one-write state and whole-stream quotas.

The inspected decoder rejects an encoded length over its cap *before reserve*, using
OUT_OF_RANGE in this exact version; decompression overflow uses RESOURCE_EXHAUSTED.
Do not rewrite both into a fabricated single upstream status. NativeWeave documents
its normalized public diagnostic category while preserving the actual protocol code.
Both encoded and decoded limits are configured, compression is explicitly selected,
and aggregate stream bytes/time remain bounded independently of per-message caps.

## MCP: runtime tools over the native Tower service

`StreamableHttpService<S,M>` implements `tower_service::Service<Request<B>>`, returns
an infallible HTTP response future and reports readiness immediately. It therefore
needs the D18 request/byte admission layer outside it; `poll_ready` alone is not a
capacity guarantee. `ServerHandler` exposes `call_tool`, `list_tools`, `get_tool`,
`get_info` and supported-version declarations. One concrete ForeignMcp Handler can
read an immutable runtime descriptor table and dispatch a C# Handler ID, avoiding
per-tool Rust macros or compilation. C# DTO serializers remain static and known.

Mandatory configuration differs materially from defaults: rmcp defaults to legacy
sessions, does not require modern per-request protocol metadata, and leaves Origin
validation disabled for an empty allowlist. NativeWeave sets legacy sessions false,
advertises only `2026-07-28` for its initial profile, requires modern metadata, sets
explicit Host/Origin policies and a streaming body cap. `get_tool` must return the
registered schema because its default None skips the schema-dependent SEP-2243
`Mcp-Param-*` standard-header consistency check. This is not a general JSON Schema
argument validator. C# generated typed mapping and explicit argument/authorization
validation still run before the business Handler; arbitrary schemas require an
explicitly selected native validator, not an assumed rmcp guarantee.

The source also disproves a simplistic “stateless always means GET 405 and disconnect
always cancels” rule. Without an event store, only POST is enabled and an unfinished
response drop cancels that request. With a resumable event store, GET may resume and
persisted requests survive disconnect. Initial NativeWeave profile disables that
store, legacy sessions and replay; an explicit future resume profile must define
retention, authorization, cursor lifetime and quotas before enabling it.

Tool execution failures use MCP tool error results; unroutable/protocol errors use
JSON-RPC errors. The SDK's error/status handling is reused. No managed reimplementation
of JSON-RPC session/transport machinery is added. Server-side C# JSON mapping of an
already decoded argument/result is language-boundary glue, not a second transport.

## TLS and lifecycle

Rust owns TLS termination exactly once. The design uses immutable rustls ServerConfig
snapshots, one pinned provider, explicit ALPN and bounded handshake concurrency/time.
Certificate reload validates a new complete config before atomically publishing it;
existing connections retain the prior config until they retire. Read-side fatal TLS
errors end processing. `close_notify`, abrupt EOF, HTTP stream completion and callback
retirement remain distinct. Platform trust and certificate reload need real Windows/
Linux deployment acceptance; the local test trust anchor is never a production default.

## Actual new experiment and limits

[protocol fixture](../../../../experiments/server-completion/protocol/src/lib.rs) and
[runner](../../../../experiments/server-completion/run.py) compile pinned Rust engines.
The retained run manifests identify the exact tests: byte-preserving unary/empty
messages; oversized/truncated/invalid-compression rejection before Handler invocation;
server-streaming frames/trailers; MCP method, Host/Origin and body caps; real loopback
HTTP1 and HTTP2; rustls handshake/ALPN/close-notify and certificate rejection. The final
run additionally exercises two runtime MCP tool names with the same compiled Handler.
See `verification/server-completion/protocol-local-*`; earlier input snapshots and
failures remain distinct, never counted as added coverage.

This is not a C# gRPC/MCP product bridge, TLS-over-HTTP end-to-end suite, mobile test,
performance result or production security certification. Core callback/AOT feasibility
is independently addressed by R08/R09. B18/B19 must integrate these established seams
with that bridge, generated serializers, deadlines and bounded streaming, then execute
Windows/Linux AOT interoperability and negative cases. That remaining implementation
work does not reopen the resolved native-engine architecture.

Detailed interface, capability and acceptance rules are in [D19](../../../server/protocols-and-observability.md).
Independent review and registry integration are required before formal design acceptance.

## Deadline seam found during final source review

The selected public `tonic::server::Grpc` path does not include all behavior of
`tonic::transport::Server`. At the same fixed commit, reading
`tonic/src/transport/service/grpc_timeout.rs:1–179,181–261` shows `GrpcTimeout` and
its parser are private, invalid headers are treated as absent by that helper, and
the timeout owns a response future. The parser covers the bounded gRPC timeout unit
grammar; selected upstream parser tests were read, not executed. The public
`transport/server/mod.rs:1075–1124` incoming-service API was also read; it does not
turn the private layer into a public reusable function.

D19 therefore specifies a small strict Rust Adapter deadline component with exact
header grammar, checked/capped monotonic budget, and timer ownership extending through
streaming Body/operation termination. This is necessary domain policy glue and does
not require a second runtime or a Tonic fork. Claiming that raw Grpc automatically
enforces streaming deadlines would be wrong. Full timeout/body races remain B18/B22
implementation tests, while the architecture and public/private boundary are resolved.

## Independent-review correction: single-request message cardinality

Review found a concrete counterexample to the initial D19 assertion: Tonic's
`map_request_unary` takes the first message and then awaits `Streaming::trailers`;
the latter drains and discards all remaining messages. An unrestricted byte Decoder
therefore permits two messages on a unary request and invokes the Handler with only
the first. This is source-confirmed at the ranges above and reproduced by an independent
five-case fixture under `experiments/database-completion/server-review/`, with actual
logs in `verification/database-completion/server-review-cardinality/`.

The corrected Adapter uses a fresh Decoder for each request, allowing one inbound
message for unary and server-streaming method kinds. A second complete message fails
with INVALID_ARGUMENT3 before the Handler. Zero messages retain Tonic's INTERNAL13;
one empty framed message remains valid. Client/bidirectional methods have a different
mode and finite stream quotas; their multiple messages must not be rejected by a reused
single-request counter. This is a small public Codec policy, not another parser or fork.

The author's corrected locked fixture executed **19 tests** on Linux in
`verification/server-completion/protocol-reviewed-local/`: the original 13 cases plus
default-permissive counterexample, strict unary, strict server-streaming, zero-versus-empty,
per-request counter reset and client-streaming multiple-message cases. The earlier
13-case Windows/Linux CI remains unchanged historical evidence; new source identities
and any subsequent two-OS run are recorded separately. Full streaming deadlines,
aggregate quotas and C# callback integration remain B18/B22 product obligations.


### Verified Windows/Linux research CI

CI run [43388468172](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43388468172)
tested source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. Protocol13/13 and
Kestrel Native AOT5/5 passed on both Windows2022 and Ubuntu24.04. Their actual
run manifests, stdout/stderr and source snapshots are retained under
`verification/completion-ci/43388468172/`; author checks of each raw log/input hash and
exact Windows LF-to-CRLF conversion are recorded in
`verification/server-completion/ci-verification.json`. This extends platform coverage
for these same distinct cases, not their product/FFI/soak scope or independent review.
