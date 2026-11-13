# D02 — Stable C boundary and layout contract

**C-ABI-001@0.3.0**. Complete research/design candidate; the registry records the exact reviewed version/hash and acceptance. Product verification remains in Delivery. Existing R03/R04, D02, A01/A02/A09–A12 remain the work IDs. Consumes [D01](../platforms/support-and-aot.md), [D04](lifetime-v0.1.md), [D08](error-v0.1.md) and [D07](buffer-v0.1.md). D08 is the sole authority for status values; this document does not invent a competing error enum.

## 1. Scope and evidence

The ABI is a same-process C boundary, not a universal domain protocol. Initial proposed targets are Linux x64 GNU and Windows x64 MSVC, little-endian, natural alignment. New targets need their own probes. The source-driven native AST/SQL/HTTP implementations remain inside their Engine, independent of Core.

Rust1.100 source and actual API tests are in R01. Lifetime/callback/async/error source research remains in R07–R11. New NativeWeave fixture source `4a4adc883b80719d2a9b2bfb03be5ec86b543f3c`, run43363045559, actually executes repr(C)/C# size-offset checks, static imports, synchronous reverse callbacks, owned buffers and SafeHandle leases on both target OS with Native AOT. **Its local status numbers and test exports are not the production D08 ABI.** The complete header/type matrix below still needs C/Rust/C# generated golden fixtures; do not promote sample-layout success to complete A01 acceptance.

## 2. Fixed representation

| Meaning | C | Rust | C# generated storage | Rule |
|---|---|---|---|---|
| Status, version, capability tag | uint32_t | u32 | uint | No language enum layout; use explicit constants |
| Signed provider code | int32_t | i32 | int | Preserve D08 domain/code semantics |
| Count/offset in portable payload | uint64_t | u64 | ulong | Checked conversion to usize/nuint, finite profile limits |
| Address / same-process cookie | void*, uintptr_t | pointer / usize | nint / nuint | Never persist or reinterpret as managed object address |
| Boolean wire scalar | uint8_t | u8 | byte | Accept only0/1; Rust bool/CLR bool marshalling excluded |
| UTF8 / bytes | pointer + explicit length | borrowed slice only under contract | byte pointer + length | No implicit NUL scan or string marshaller |
| Floating value where enabled | IEEE binary32/64 | f32/f64 | float/double | NaN/Infinity/domain rules belong to the codec profile |

No C long, wchar_t, usize-sized public enum, Rust String/Vec/Box/Arc/Future/trait object, CLR reference or generic runtime type is an ABI value. Opaque handles are pointers to private native owners. C# public application APIs hide those pointers. Non-exhaustive upstream enums are mapped through NativeWeave's versioned constants, never exported as raw discriminants.

Use `#[repr(C)]` for complete wire structs and `StructLayout(LayoutKind.Sequential)` for the exact generated managed counterpart. Do not set Pack=1 to mask an alignment disagreement. Pad fields explicitly where a layout requires it; padding is not semantic data, must not be hashed or transmitted as an initialized value, and must not leak uninitialized bytes. Struct size, alignment and every field offset are generated/tested for each supported target. Avoid by-value aggregate returns; use a fixed scalar status and caller-owned out pointers.

## 3. Bootstrap and size-prefixed evolution

The only mandatory module bootstrap export is proposed as `nw_<engine>_get_abi_v1`. Engine-specific symbols avoid collisions; an optional versioned function table may be returned under A02 but is not required for a simple synchronous Engine.

Illustrative signature and record, **not yet compiled as the production ABI**:
```c
typedef uint32_t nw_status;
typedef struct nw_abi_info_v1 {
    uint32_t struct_size;
    uint32_t abi_major;
    uint32_t abi_minor;
    uint32_t pointer_width_bits;
    uint64_t capabilities;
    uint64_t reserved;
} nw_abi_info_v1;
nw_status nw_engine_get_abi_v1(uint32_t requested_major,
                              uint32_t out_capacity,
                              nw_abi_info_v1 *out_info);
```

Initial x64 expected record size32, alignment8, offsets0/4/8/12/16/24. ABI major mismatch returns NOT_SUPPORTED without transferring owners. A null output or capacity below the complete v1 record returns INVALID_ARGUMENT/BUFFER_TOO_SMALL as appropriate and writes nothing. On success, write only complete supported fields within out_capacity, zero defined reserved fields and set struct_size to the provider record size. A larger capacity never licenses writing beyond provider-known fields. The caller initializes its entire buffer, reads only min(capacity,provider size), and never reads an absent field.

Size alone is not capability negotiation. Required capability bits/codec IDs must be explicitly checked before domain calls; missing capabilities fail, not silently fall back to another engine/provider or altered SQL semantics. Minor revisions may append optional fields and capabilities without changing previous field widths/order/meaning, ownership or status numbers. Incompatible semantics/representation require a major version. Old/new binaries and unknown-size/bit negatives are A02/A22 tests.

## 4. Call and return invariants

Every export declares nullability, aliasing, input-borrow end, output-owner transfer, allowed threads/reentrancy, maximum work and error postconditions in the binding description. The same description feeds Rust/C/C# generation and drift checks; hand-maintained parallel type systems are not the default.

For a create function, a valid out-owner slot is set to null before fallible work; success publishes exactly one owner only after full initialization. Failures destroy unpublished known-safe state, never expose partially initialized objects. D08 error-output prefix rules apply separately. Do not memset an untrusted pointer or claim arbitrary pointer validation: the caller must supply valid readable/writable memory, correct alignment and nonoverlap; shape/capacity checks do not make bad addresses safe.

Borrowed input is valid only through the synchronous call unless an explicit retained-owner protocol is declared. An async create/start must copy or acquire the required native/buffer/managed roots before returning. A returned scalar status is not evidence that callbacks have retired, a transaction rolled back or a connection is reusable. Those facts retain D04/D05/D06/domain state machines.

## 5. Handles and concurrency

Adopt the existing D04 private opaque-owner pointer + SafeHandle profile, not a mandatory global handle table. Exactly one module owns the release function. Raw pointer copying is not a second owner; clone/retain operations must be explicit. No arbitrary stale/wrong-module pointer can be safely dereferenced; generated managed APIs prevent ordinary misuse, while separate generational-token profiles may add detection where justified.

A call must atomically check the managed logical Open gate and acquire its SafeHandle reference before extracting the pointer. Release the gate before FFI and release the reference in finally. Dispose closes admission under the same gate and drops its owning reference outside the gate. **Generated SafeHandle import leasing protects physical lifetime, not logical admission after Dispose while another lease is live, nor exclusive mutation.** A mutable native builder requires its own single-writer rule. The current simple fixture proves only the physical-lifetime slice; it must not be copied as the full D04 wrapper.

The module remains loaded until process exit in this initial profile. Resource/operation/callback ownership keeps all necessary function/module references alive. No hot-unload implication follows from disposing a datasource or Server instance.

## 6. Callbacks, errors and modern Rust

Use exact C ABI unmanaged signatures and static non-generic `[UnmanagedCallersOnly]` entry points with blittable parameters. A callback context is an opaque uintptr cookie, not a pinned managed object. No managed exception or Rust unwind crosses the C boundary. Ordinary failures return D08 statuses; contained native panic poisons appropriate state under D08, with explicit nonrecoverable abort/OOM/invalid-memory limits. Deallocation must not unwind or synchronously block on network/worker shutdown.

Rust1.100 `!`, Allocator, DropGuard, Box/Arc map and Vec::from_fn are internal implementation opportunities, not new wire types. Naked `extern "custom"` is excluded from PInvoke. DropGuard can protect an unpublished owner, not retire an async operation. Cross-module freeing cannot be delegated to another heap because custom allocation is now stable.

## 7. Verification and task boundary

A01 must deliver target-specific generated C/Rust/C# size/align/offset tests for every published struct, fixed status/Boolean/tag negatives, size-prefix no-write/sentinel tests, unknown ABI/capability tests and symbol/signature inventory. A03/A04/A05 verify owner transfer, buffers and errors; A06/A07 callbacks and async retirement. A10/A11/A12 generation/analyzers forbid unsupported types and layout drift. A14/A15 perform actual two-platform AOT import/export executions, not only native unit tests. A22 verifies old/new binaries and feature profiles.

Malformed-but-valid-memory tests belong in ordinary fuzzing; deliberately invalid memory/UCO ABI cases require isolated fatal tests. Race/model/sanitizer evidence remains scoped to the properties checked. Current test exports (`nw_probe_*` etc.) are research fixtures and must not be published as a stable Core API. Formal contract acceptance remains separate from this authored draft and finite execution evidence.

## 9. Completion evidence and research acceptance boundary (2026-11-13)

R03 now has a canonical [report](../research/topics/R03/report.md), evidence and coverage. Existing two-OS layout/AOT samples are retained. The new [interop completion manifest](../../verification/interop-completion/linux/result.json) actually runs the static C boundary and 10,000 independently checked extent cases; the [binding comparison](../../verification/interop-completion/binding-linux/result.json) executes csbindgen DllImport and framework LibraryImport against one native export in normal and Native AOT modes. `uint64_t` lengths still require `isize::MAX`/budget checks before constructing a Rust slice; arithmetic checks never validate an arbitrary address.

The isolated [invalid UCO experiment](../../verification/interop-completion/uco-invalid-linux/result.json) publishes a char/bool callback but terminates both normal and AOT children with unhandled `InvalidProgramException` before the callback body executes. This scoped observation supports rejecting such public signatures; it does not establish how an outer managed catch behaves or every ABI failure mode. No `catch` inside the callback can repair a body that was never entered.

[D03](../generators/binding-pipeline.md) fixes generation authority and completeness diagnostics; [D09](concurrency-v0.1.md) fixes Engine scheduling and shutdown; [D12](../verification/models-and-matrix.md) records product test obligations separately. The declaration/ownership/version decisions are eligible for independent design acceptance now. A01/A02/A12 must still implement and execute the complete generated golden matrix before product release; that future matrix is not a prerequisite for accepting its design.


### Committed target evidence

The [CI readback](../../verification/interop-completion/ci-evidence-read.json) verifies source `7ea84e11ee19e6dad4503a5872eb27c6c7f44e80`, run `43388468172`: actual Windows/Linux normal and Native AOT main interop execution (10,528/10,529 assertions respectively), Roslyn generation checks and static metadata restrictions. This supports the stated research slice; product conformance remains separately assigned. Supplemental panic/invalid-UCO/generator comparison runs are Linux-only.
