# D07 — Native buffers, allocation and transfer

**C-BUFFER-001@0.1.0-draft**. Status: proposed, partially evidenced; not accepted. Existing R10/R03/R29 and D07/A04/B06/B07/B16 remain owners. Read [D02](abi-v0.1.md), [D04](lifetime-v0.1.md), [D06](async-v0.1.md), [D08](error-v0.1.md) and [R01 Rust1.100](../research/topics/R01/rust-1.100.md). No SQL/HTTP domain state or mandatory global allocator is added to Core.

## 1. Three explicit transfer modes

**Synchronous borrowed span:** caller owns valid initialized bytes until return. Callee may not retain the address. Empty input accepts null+zero; nonempty requires nonnull, alignment appropriate to the element and a representable byte range. Before Rust slice construction, check finite limit, checked multiplication/addition and total size <=isize::MAX; even a zero-length Rust slice must be constructed without converting null into an invalid Rust reference. Rust uses `&[]` for the empty case. Shape checks do not validate an arbitrary inaccessible address.

**Native-owned buffer:** one opaque owner contains the actual collection, allocator identity and lifetime state. Only its creating module releases it. Borrowing a pointer/length view needs an active owner lease for the entire consumer read. The public managed API offers CopyTo/ToArray or a nonescaping synchronous callback/ref-struct view; it does not return an indefinitely valid Span after dropping the lease. A copied DTO owns its managed strings/bytes independently.

**Explicitly transferred/retained buffer:** a domain capability may transfer an owned native buffer or retain an already defined owner. Source and target record exactly one destruction responsibility and a clear transfer linearization point. No shared allocator assumption, silent ownership transfer through a borrowed pointer or arbitrary adoption of a CLR allocation is allowed.

## 2. Wire shape and bounds

Illustrative D02-compatible view, not yet a compiled public ABI:
```c
typedef struct nw_bytes_view_v1 {
    const uint8_t *data;
    uint64_t length;
} nw_bytes_view_v1;
```
Initial x64 expected size16/alignment8, offsets0/8. A writable view is a separate explicitly exclusive operation, not a cast of a shared read view. Capacity and allocator layout are never reconstructed from caller-supplied length to free an owned buffer. The opaque owner retains them. A future typed batch descriptor has explicit element encoding/endian/nullability and checked offsets; Rust private Value/Vec layouts are not serialized.

Every allocation-producing API has checked input, allocation and output limits. `length <= max` is evaluated before allocation/copy; `count * element_size`, header+payload and accumulated batch bytes are checked. A cap applied after `fetch_all`, JSON serialization or SQL rendering cannot establish a preallocation bound. Encoded SQL/value/output intermediates, retained source copies and metadata caches each need an accounting rule. D16/B09/B11 must prove conservative preflight bounds or use a reviewed fallible upstream seam for potentially expanding renderers.

## 3. Allocation and failure protocol

Default to the creating module's normal allocator and owned collections unless an actual budget/pool requirement justifies a custom allocator. Rust1.100 allows scoped Allocator/Vec<T,A>/Box<T,A>, but that allocator covers only allocations that actually use it, not nested String/Bytes/upstream caches or the entire process. The allocator instance/state must outlive every block and remain valid across movement of its owner. Grow/shrink failure preserves the old block; success transfers ownership and invalidates the old reference even at an unchanged address.

Use checked `try_reserve`/fallible construction where API error reporting promises allocation failure. Vec::from_fn and infallible Box allocation do not promise recoverable OOM. No blanket catch_unwind handles allocator abort. Allocator/deallocator/cleanup code must not unwind. Do not build a Core-wide memory pool merely because a stable allocator API is available.

Initialize a new owner under a local guard, publish only after success, then disarm the unpublished-owner cleanup path. DropGuard can remove duplicated early-return cleanup but is synchronous and its closure/captures themselves have destruction behavior. It cannot wait for a Future, confirm rollback or substitute for native/managed quiescence. Box::map/Arc::map may be useful before publication; a mapped object may move and must never invalidate an address already exposed to another language. Published shared Arc state is not magically uniquely mutable. Arc allocator APIs not actually stable remain excluded.

## 4. Managed pinning and async ownership

`fixed` pins a managed span only for its lexical scope. Normal GCHandle roots an object but does not pin its data address. ArrayPool/Rented Memory may be returned only after all native use ends. Default async submission copies bounded input metadata/data into native ownership before returning; an explicit pinned-memory owner profile is optional and must carry a managed root/pin lease through native retirement, not just Task completion.

On request cancellation, neither side frees or returns still-accessible memory. Operation result publication, callback drain, cancellation-registration drain and resource retirement remain distinct D06 facts. Borrowed callback bytes are read/copied before returning unless the ABI explicitly transfers an owner. A reverse callback never runs arbitrary asynchronous user work while relying on a call-scoped buffer.

## 5. Read, copy and release example

The new native fixture keeps Vec<u8,Global> and its cleanup guard private in an owned object. The C# wrapper uses SafeHandle import leasing for a synchronous sum. Both Windows/Linux AOT tests demonstrate that Dispose cannot physically free the object while an admitted call still uses it. Empty input, bounded allocation rejection and a contained prepublication panic leave the live count at zero after cleanup.

This example does **not** prove logical post-close admission, mutable aliasing, arbitrary stale pointers or async buffer retirement. Production D04 uses a managed logical gate atomically with its call reference; a mutable builder also needs exclusive access. Public copy APIs may perform an additional managed allocation; no zero-copy or zero-allocation promise is made.

## 6. Streaming and accounting

Before starting work or producing a chunk, reserve both an operation slot and bytes sufficient for its ownership/copy path. Account for waiting producers as well as queued, delivered and retiring chunks. Transfer a byte reservation with the owner; release only after the last relevant read/lease/copy obligation ends. Queue capacity limits object count, not arbitrary object size. Unknown allocator retention is reported separately from explicitly budgeted payload bytes; do not advertise a hard RSS bound without measuring/proving all categories.

Database batches bound rows and bytes and retain physical session/cursor leases until consumption or cleanup. Reject or chunk a single oversized field before buffering it in full where the backend supports that policy; explicitly document exceptions rather than hiding full allocation behind a later limit.

Server bodies require separate live-stream and retained-byte accounting. Tower's response Future permit can end before Body; Hyper H2 flow credit can be returned while C# retains Bytes. A stream slot shared between Body and callback can protect the lifetime count, but cannot alone charge Bytes retained after a frame is delivered. TLS/parser/socket buffers, tasks, thread stacks and telemetry are additional budgets. The new native Server fixture tests stream-slot semantics only, not all memory categories.

## 7. Pooling, upgrade and failure rules

Pooling is optional and measured. A buffer cannot return to a pool while a native/managed borrower, queued callback or pending I/O can still touch it. Clear sensitive data according to a declared policy; clearing logical length does not erase capacity. A generation check helps detect some reuse errors but does not replace an owner lease. Repeated managed Dispose is idempotent; calling a native destructor twice with the same raw pointer is outside the contract and must not be used as an ordinary negative test.

Schema/ABI/capability mismatches fail before transfer. Decoder exceptions release the current owned batch in finally and initiate cursor cleanup without corrupting transaction outcome. Poison/timeout may require retaining and charging an unreleasable owner; do not falsely return its budget merely to keep admission moving. Library unload remains prohibited while any buffer/function pointer can be used.

## 8. Verification and remaining acceptance

A04 tests zero/nonzero spans, no null-reference construction for empty input, all overflow/capacity/offset boundaries, injected failed reserve/publication, explicit allocator pairing and CopyTo exact/short capacity. A03/A20 add call/Dispose, mutable contention, parent/child and pool-reuse races. A07 verifies async input/result/callback/root retirement. B06/B07 test SQLx encoding/decoding failures, huge field/batch and early stream termination; B16/B17 test slow/aborted Body and retained bytes. A14/A15/A16 verify native assets and real AOT consumers independently per OS; A21/B23 measure costs without extrapolating microbenchmarks.

The actual Interop fixture is NativeWeave commit `4a4adc883b80719d2a9b2bfb03be5ec86b543f3c`, run43363045559. No already-successful original Rust API/SQLite query experiment was rerun for this document. The additional native database/Server source and results are tracked in the recovery checkpoint. These facts narrow design uncertainty without completing production or independent acceptance.
