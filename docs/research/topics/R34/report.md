# R34 — Native boundary security and resource-abuse analysis

Date: 2026-11-12. This previously missing report closes the design threat-boundary
study and supplies concrete negative tests; it does not certify a future product.

## Trust domains and fixed evidence

The process contains trusted generated C# bindings and maintainer-produced Rust
modules. User-controlled HTTP bodies, headers, SQL values/identifiers, tool arguments
and native configuration remain untrusted *data*. Native code loaded in-process is
not sandboxed by C#, Rust, SafeHandle, capability bits or a C ABI. A malicious library
can corrupt the address space; incompatible/untrusted plugins require process isolation.
Do not promise that arbitrary invalid pointers passed by an external native caller
can always be turned into safe errors.

Rust 1.100.0 `library/core/src/slice/raw.rs:6–33,118–140,145–168` at
`0ef1bc386059596dada8fb65b50425aab2ea637a` makes the slice safety preconditions explicit:
non-null/aligned even for zero length, one allocation, initialized bytes, no forbidden
aliasing, `len*sizeof(T) <= isize::MAX` and no address wrap. Debug precondition checks
are not validation of provenance. The Adapter must special-case the agreed null+zero
FFI representation before constructing a Rust reference. It must reject length,
alignment and arithmetic errors before dereferencing, while relying on the binding's
owner/lease proof for validity and lifetime.

Tonic 0.14.9 decode length/decompression checks, rmcp 3.10.0 Host/Origin/body limits,
rustls 0.23.46 fatal error and certificate validation, and retained Bytes/permit work
are read or executed as linked by R28/R29 and
[source-inspection.json](../../../../verification/server-completion/source-inspection.json).
The new Rust fixture actually rejects overlong/truncated/invalid-compression gRPC,
forbidden MCP Host/Origin, a streaming body over cap without Content-Length, untrusted
TLS certificates and incorrect server names. It uses only public library APIs.

## Boundary-by-boundary decisions

| Boundary | Required validation/ownership | Failure behavior |
|---|---|---|
| ABI descriptor | size/version, reserved bits, supported capabilities, checked field offsets | fail before reading optional fields; no unchecked future-version fallback |
| slice/batch | checked multiplication/addition/conversion, alignment, maximum aggregate size, owner lease | reject without dereference/allocation; null+zero maps to empty by branch |
| object handle | generated wrapper admission gate + physical lease; engine-local request ID generation if used | reject calls after Dispose; keep old in-flight owners; never make a Core global handle registry mandatory |
| SQL value/identifier | values bind as parameters; identifiers come from validated metadata or explicit quoted engine API | reject unsupported codecs/dialects; no interpolation fallback or client evaluation |
| HTTP input | mature Hyper parser, independent connection/stream/header/body/deadline limits | per-stream refusal where valid; fatal protocol violation closes connection |
| gRPC | Tonic framed length and decompressed cap; finite message queue and total stream budget | preserve protocol status; reject before application Handler |
| MCP | fixed version and schema registry, exact metadata/header checks, Host/Origin + app authorization | protocol error distinct from tool error; no dynamic arbitrary assembly/tool loading |
| diagnostics | fixed tag sets, bounded UTF-8 attributes/queue bytes, no secrets or raw arguments | drop diagnostics with counters; do not block release/completion |
| module distribution | maintainer artifact/version/hash/SBOM and platform profile | mismatch fails load; no application-controlled library search paths |

Checked integers and memory validity are separate: a numerically valid address does
not prove a live allocation. Exception/panic catching is also not a memory sandbox;
panic=abort, OOM and process corruption cannot be reliably translated to recoverable
business errors. An ordinary native panic caught at an unwind-enabled FFI boundary
still retires owned resources before the module is reused; the Core fault policy
defines whether that engine can continue.

## Resource attacks and cancellation races

Admission happens before body allocation or DB acquisition. Active, waiting,
retirement-pending and callback-dispatch metadata each remain within explicit quotas.
Bytes are charged to the backing allocation's last owner, not to visible slice length
or network flow credit. Copy overlap reserves both sides. A queue permit outstanding
at close is not revoked automatically. Deadlines are monotonic total deadlines;
receiving another chunk does not restart the budget.

Cancelled/disconnected requests cannot overwrite an already terminal native result,
release a transferred result twice, or declare an uncertain database commit rolled
back. Authentication/tenant context is copied as validated metadata, never inferred
from trace IDs or untrusted forwarding headers. Unauthorized requests must not allocate
long-lived DB/stream state. TLS handshake limits exist independently of HTTP slots.

## Verification closure and future implementation obligations

The research suite provides concrete engine-level negative witnesses and D18/D19
state/limit specifications. D07/D08/D12 provide the shared ABI/allocator/error/proof
requirements. Future A20/B07/B16/B18/B19/B22 must fuzz the actual generated boundaries,
include deterministic overflow values, malformed UTF-8, stale/disposed wrappers,
split frames, duplicate conflicting headers, compression bombs, cancellation races,
retained slices, exhausted quotas and secret-leak assertions. Run sanitizer/Miri
where applicable, fault injection and Windows/Linux AOT tests. A source review plus
finite negative cases supports design acceptance; it does not assert production fuzz
coverage, proof against hostile in-process code, or a whole-process RSS bound.


## Dependency and distribution inventory

`verification/server-completion/package-identities.json` ties executed Cargo packages
to their VCS commits and compares the read Tonic/rmcp files to the published source.
`dependency-inventory.json` enumerates the 157 locked registry packages and records
available package license metadata/file hashes. Target-specific packages not downloaded
on Linux are explicitly identity-only, not silently claimed as read. This is a research
inventory, not a product SBOM, legal opinion or security-advisory clearance. B24 must
review the exact distributed RID/features/crypto/OS dependency graph and license/NOTICE
texts and current advisories before release. Test TLS keys are generated ephemerally;
historical stored-key input bytes are explicitly omitted with their original hashes
and run logs preserved, rather than copied into public evidence.


### Verified Windows/Linux research CI

CI run [43388468172](https://github.com/IzuSharp/NativeWeave-Design/actions/runs/43388468172)
tested source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`. Protocol13/13 and
Kestrel Native AOT5/5 passed on both Windows2022 and Ubuntu24.04. Their actual
run manifests, stdout/stderr and source snapshots are retained under
`verification/completion-ci/43388468172/`; author checks of each raw log/input hash and
exact Windows LF-to-CRLF conversion are recorded in
`verification/server-completion/ci-verification.json`. This extends platform coverage
for these same distinct cases, not their product/FFI/soak scope or independent review.

## Protocol cardinality correction from independent review

Tonic's default unary path can drain and discard a second request message before
calling the Handler with the first. Per-message byte caps do not enforce method
cardinality. R28/D19 now require a fresh one-message Decoder for unary/server-streaming,
with INVALID_ARGUMENT3 on the second complete message before dispatch. Multiple-message
client/bidirectional streams use a separate mode and bounded aggregate quotas. This
public Codec policy is independently reproduced in five reviewer cases and in the
author's corrected 19-case protocol fixture; original 13-case CI remains historical.
See `verification/database-completion/server-review-cardinality/result.json` and
`verification/server-completion/protocol-reviewed-local/run.json`. Neither finite
suite is represented as full protocol security certification.
