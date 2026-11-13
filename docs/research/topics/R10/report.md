# R10 — Bounded buffers, pinning, transfer and retained allocation

Research decision ready for independent review. The original two-OS native-slice study and later Body/Bytes retirement experiments already supply substantial R10 evidence; only the canonical triplet was absent. This report links those facts and adds the new cross-language checked-extent/result-transfer experiment without claiming all memory paths are now implemented.

## Chosen ownership modes

Three modes suffice: a call-scoped borrowed span; an opaque native-owned buffer released by its creating module; and an explicitly retained/transferred owner with a named linearization point. No raw Rust Vec/String layout or allocator metadata crosses ABI. C# exposes copy APIs or a scoped nonescaping view under an active lease. Returning Span after dropping its native owner lease is not a valid zero-copy API.

Default async submission copies bounded input before native acceptance. An optional pinned-memory capability keeps the actual pin/root/lease until all native accesses retire, not merely until Task completes. Normal GCHandle roots an object without pinning its data. ArrayPool return follows the same access-end rule. Callback-borrowed bytes must be consumed/copied before callback return unless a separate owned transfer is explicit.

## Source and real evidence

R01's fixed Rust1.100 allocator/DropGuard/Vec source inspection explains why allocator scope and cleanup behavior remain local. D07 records failure-safe reserve/grow rules and distinguishes an outer Vec allocator from nested upstream String/Bytes/caches. R29/source-lifecycle traces show Body/channel completion does not release an independently retained Bytes allocation or outstanding channel permit. Those original results and their exact source/artifact hashes are reused.

The new completion probe transfers a native ResultOwner to managed code, releases the operation, then reads the independent result and releases it after an injected DTO conversion exception. Live-result count returns zero. Second take is rejected with an empty output; late cancel does not revoke the first successful result. This is a real native/managed/AOT ownership slice, not the complete production result decoder.

The arithmetic predicate checks count×element-width with Rust checked u64 arithmetic plus isize/budget limits. C# BigInteger independently computes the expected predicate for 10,000 deterministic seeded inputs and explicit empty, overflow, isize and zero-width cases. Both normal and actual Linux AOT execute it. No deliberately invalid memory is dereferenced; integer validation cannot prove pointer provenance.

## Boundary and failure rules

| Boundary | Rule |
|---|---|
| Empty input | Null+zero permitted only where specified; construct empty Rust slice without null reference |
| Nonempty borrowed range | Valid initialized address is caller precondition; checked bytes/offset/capacity before slice construction |
| Failed allocation/grow | Return explicit failure and preserve prior owner; infallible abort is not catchable OOM |
| Transfer failure | Output remains empty and original side remains owner |
| Operation cleanup after take | Cannot free the already transferred result |
| Decoder/DTO exception | Release current batch/result in finally, initiate cursor cleanup, preserve transaction effect |
| Cancel/timeout | Stop waiting/request cancellation; keep and charge every still-accessible owner |
| Pool return | Only after all native/managed borrowers and queued I/O release their leases |

Limits precede expanding allocation. A byte cap after fetch_all, SQL rendering or full JSON serialization is not a preallocation guarantee. Server retained capacity, producer waiters, outstanding channel reservations, parser/TLS/socket buffers, task metadata and thread stacks are different accounting categories. A payload budget is not a hard process-RSS claim.

## Alternatives and design closure

Per-operation copies are simple and safe but cost bandwidth/allocation; retained native owners reduce copies but add lifetime/accounting complexity; persistent managed pins may affect GC and cannot be a default performance guarantee. Custom allocators/pools are introduced only for a demonstrated engine requirement and preserve creator/releaser identity. Arrow-style columnar interchange is a future batch capability when workloads justify it, not a compulsory Core format.

D07 gives exact wire view, ownership/size/pinning rules. A04/A20 implement complete scalar/record/buffer fuzz and owner pairing; B06/B07/B12 implement typed database batch mapping; B16/B17 handle native HTTP chunks. A21/B23 measure full copy/retained-memory costs. These future product validations do not prevent accepting the source-backed ownership and accounting design now.


## Committed Windows/Linux completion execution

[CI evidence readback](../../../../verification/interop-completion/ci-evidence-read.json) verifies actual GitHub run `43388468172` at source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`: Windows x64 MSVC and Linux x64 GNU each executed normal 10,528 assertions and Native AOT 10,529, 32 controlled callback rounds per mode, nine Roslyn checks and static metadata/AOT restriction checks. All command exits and source hashes were verified; Windows checkout CRLF accounts for its distinct input hashes. This extends the main fixture only. Linux-only generator-comparison/panic/invalid-UCO supplemental studies are not mislabeled as Windows results. Deliberate reflection fallback negative cases retain their IL2026/IL3050 diagnostics. Product package/full-protocol/long-load obligations remain separate.
