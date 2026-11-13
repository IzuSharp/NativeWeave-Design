# R27/R29 → D18: body termination, reservations and retained byte ownership

Status: proposed design plus selected-source inspection and six finite Linux
Rust executions; no production Server adapter or C# Handler/TLS/load claim.
Date: 2026-11-12 America/Los_Angeles. Continue the existing R27/R29 and D18;
this is not a new task graph or a selection of the default Server engine.

## 1. What is reused, and what the adapter must add

Use the mature native Service/Body, HTTP parser and connection driver. C# owns
the application handler and static serializer/model metadata. One compiled
foreign Service receives runtime route/handler registrations; adding a C#
handler does not require a generated Rust function. The existing
[source-driven Server study](../research/topics/R27/source-driven-server.md)
remains the architectural baseline.

The missing adapter responsibilities are precise: logical admission, an
operation result, byte-owner credit, callback/module retirement and a bounded
shutdown protocol. A Tokio queue or a Hyper Body cannot by itself provide all
five. Add these at the boundary instead of replacing the native network core.

### Exact selected source

| Upstream | Fixed commit | Inspected mechanism |
| --- | --- | --- |
| Bytes 1.12.1 | `76c0fbb54ed4336caf9d2311658a2f4a5627c21d` | [`src/bytes.rs`](https://github.com/tokio-rs/bytes/blob/76c0fbb54ed4336caf9d2311658a2f4a5627c21d/src/bytes.rs), 237–293, 373–388 and 1096–1164: `from_owner`, slice, shared owner vtable, clone and final drop |
| Tokio 1.54.1 | `b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8` | [`bounded.rs`](https://github.com/tokio-rs/tokio/blob/b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8/tokio/src/sync/mpsc/bounded.rs), 446–480, 806–825, 1190–1273 and 1804–1960: receiver close, send, owned reservation and permit release |
| Tokio 1.54.1 | same commit | [`semaphore.rs`](https://github.com/tokio-rs/tokio/blob/b53b2001ed2ccfd9b87e32a0c6da1a1eebdc80b8/tokio/src/sync/semaphore.rs), 902–967, 1008–1052 and 1401–1412: `acquire_many_owned`, `try_acquire_many_owned` and `OwnedSemaphorePermit::drop` |
| Hyper 1.12.0 | `7f67699ce32d717081deb7018b4da7d679277ac0` | [`incoming.rs`](https://github.com/hyperium/hyper/blob/7f67699ce32d717081deb7018b4da7d679277ac0/src/body/incoming.rs), 178–226: H2 data/trailers, protocol credit and `NO_ERROR` reset handling |

The [source identity file](../../experiments/server-retained-bytes/source-inspection.json)
records whole-file SHA256/Git blob hashes, read ranges and the independently
checked relationship to the Cargo registry packages. Reading four files is not
a complete audit of any upstream repository. No copied private Rust layout
becomes a C ABI.

## 2. Four independent observations

| Observation | What it establishes | What it does not establish |
| --- | --- | --- |
| Handler/response Future returned headers | Response head is ready | Body complete, final byte owner gone, callback quiescent |
| `Body::poll_frame` returned `None` | This Body reported no further frame | Every byte consumed by the peer, exact transport termination reason, all retained buffers released |
| Tokio receiver closed | New ordinary channel sends/reservations are rejected | Already-issued permits revoked or all producers retired |
| Final `Bytes` owner dropped | That tracked allocation's reservation can be returned | Other copies, socket/TLS buffers, foreign callbacks or the whole process are retired |

Hyper H2 releases protocol capacity before yielding the received data frame.
The consumer can retain that `Bytes` long afterward. Independently, the
inspected `NO_ERROR` reset branches return `None` for data or trailers. Thus
an adapter over public `Incoming` must report **EndObserved** if that is all it
knows. It must not manufacture **NormalTransportCompletion** from `None`.
If a product profile requires the precise reset cause, negotiate a separate
capability backed by an actually available signal or a justified upstream
extension. The current evidence does not justify a default fork.

This `NO_ERROR` finding is source-inspected, not a new HTTP/2 wire test. The six
new tests below exercise actual Bytes, Tokio and the Body interface without
opening sockets or running TLS.

## 3. Proposed ownership and state protocol

Keep request admission (`Open → Closing → Retired`), body progress
(`Producing → EndObserved/Failed/Aborted`) and byte-owner reference count
separate. Each owned frame contains a Core-owned buffer/lease; its final
deallocator also returns the charge for the allocation that remains alive.

1. Before accepting a body operation, atomically obtain logical admission and
   the request/operation lease under the D04 gate. Work admitted before close
   can finish or be cancelled according to its operation protocol; work after
   the close linearization point is rejected before allocating payload.
2. Validate length, frame kind and negotiated chunk limit with checked integer
   conversions. Reject impossible sizes before awaiting any resource. A
   request larger than an entire credit pool cannot be left waiting forever.
3. Reserve bounded request/waiter metadata, queue position and byte credit
   before materializing payload. The experiment uses message reservation then
   byte reservation; a production global/per-request coordinator must also
   prove rollback and freedom from cyclic resource acquisition.
4. The byte credit belongs to an owner, not to a queue slot. Queue dequeue,
   successful local enqueue, response-head completion and Body EOF do not
   release it. A non-empty slice that keeps a larger backing allocation alive
   retains that allocation's full charge, not merely the slice length. The
   fixed Bytes implementation gives an empty slice no clone of this owner.
5. Copying into a second owned buffer charges both live allocations. A native
   `Bytes` converted to `Vec`/`BytesMut` may copy; never treat the destination
   as budget-free because the original owner was released. This fixture's
   permit accounts only for its controlled bridge-owned allocation, not copies
   created elsewhere. Decoding and transport buffers need separate charges.
   The lowest-risk
   bridge may deliberately use a bounded copy with explicit ownership.
6. After close, drain or revoke outstanding operations and reservations through
   their own protocol. `Receiver::close` deliberately permits sends through
   previously issued `OwnedPermit`s. Account for these obligations until they
   send or release. A producer holding that permit while awaiting byte credit
   must be explicitly cancelled or completed; channel close does not cancel
   the semaphore wait. The tests cover these obligations separately, not a
   complete close coordinator. Dropping the receiver also drops queued frames but cannot
   reclaim frames already handed to another owner.
7. Foreign byte leases remain rooted until explicit release and callback
   retirement. A public Task timeout ends that wait only. The cleanup
   coordinator retains owners, metadata budget and module references while
   retirement is pending. Do not free a cookie or native module at a deadline.

The proposed C# result is a discriminated Data/Trailers/End observation with an
owned lease for Data and bounded owned metadata for Trailers. It is not a
borrowed `ReadOnlyMemory` that can survive an arbitrary `await`. Candidate
operations use D02/D06/D07's existing versioned header, status/error, two-phase
operation and take-once result; this note does not invent a second binary
layout or make the experiment's private helper a public ABI.

| Candidate operation | Result and release obligation |
| --- | --- |
| CreateRead(request, maximumBytes) | Reserve admission/operation ownership; no unbounded speculative read |
| StartRead(operation, completion) | Exactly one terminal publication; callback only signals bounded managed dispatch |
| TakeFrame(operation) | At most one ownership transfer of Data, Trailers or EndObserved; failure retains native result ownership |
| ReleaseFrame(owner) | Exactly once per transferred owner; final shared owner returns charged bytes |
| WriteFrame(request, frame, operation) | Borrow only during synchronous entry or explicitly copy/retain under credit; no peer-consumption promise |
| CloseBody(request) | Close logical admission, account for outstanding permits, request cancellation, then retire all owned obligations |

The precise function names remain candidate. Future generated signatures must
use accepted Core wire types; neither a Rust `Bytes` nor a trait object crosses
the boundary. C# cancellation registration and native callback quiescence are
separate D06 gates even when both eventually wake the same Task.

## 4. Actual new finite experiment

[The new crate](../../experiments/server-retained-bytes/README.md) locks the
three libraries above and keeps the four previous native-slices Server tests
unchanged. The root author ran all six tests on Linux with Rust 1.100.0; a
different agent independently reran them with the same source/lock bytes.
Raw commands, input snapshots and result manifests distinguish local execution
from any later GitHub Windows/Linux run. Final CI evidence is linked from the
source-lifecycle checkpoint; it is not implied by this local result.

| Test | Directly checked behavior |
| --- | --- |
| `byte_credit_survives_last_retained_slice` | One allocation charge remains after original/clone drop and returns only after the last retained slice |
| `receiver_drop_releases_queued_but_not_external_bytes` | Queue destruction frees queued owners, while the externally held frame still owns its credit |
| `cancelled_byte_wait_restores_message_capacity_before_allocating` | Cancellation while awaiting bytes returns its reserved message slot and has allocated no new payload |
| `channel_close_does_not_revoke_an_already_reserved_send` | A pre-close permit can deliver after receiver close; its actual owner remains charged |
| `oversized_chunk_is_rejected_before_reservations_or_allocation` | Zero/oversized requests are rejected without consuming channel slots or byte credit |
| `body_end_does_not_retire_an_externally_retained_frame` | Actual Body EOF/drop does not release a frame retained outside the Body |

These observations are more specific than a finite state model, but still do
not prove a production allocator, foreign runtime, fairness, HTTP/2 reset
behavior, weak-memory implementation, AOT Server or RSS upper bound. Retained
foreign ownership is simulated by a real Rust `Bytes`, not by a C# GCHandle.

## 5. Findings and future task obligations

- **SR-LIFE-001:** EndObserved has insufficient information to certify peer
  consumption or an exact H2 termination cause. D18/B17 retain that distinction;
  add wire-level NO_ERROR, error reset, trailers and truncated-body tests.
- **SR-LIFE-002:** Queue close leaves issued permit obligations. B16/B20 must
  stop logical admission and explicitly drain/cancel permit owners, with bounded
  cleanup metadata and a pending-retirement outcome at deadline.
- **SR-LIFE-003:** Frame/slice ownership outlives body polling and queue slots.
  B16/B17 must charge the retained allocation until final release, including
  managed-owned copies and slices, and test callback/abort/close races.
- **SR-LIFE-004:** Source-compatible public APIs are sufficient for this finite
  credit-owner seam. They do not establish a complete managed Handler bridge or performance advantage. The product Rust requirement is fixed; R26/R17 supply honest comparator evidence.

Kestrel Native AOT remains a research comparator only. The required product Host is Rust,
with the current source-backed Tokio/Hyper/Tower/Axum composition in D18. B15 is its C#
application/Handler surface and B17 the native host; they are complementary, not alternative
host profiles. The old finite experiments remain scoped evidence, not a completed managed
bridge, RSS bound or product performance result. No formal Delivery is authorized now.
