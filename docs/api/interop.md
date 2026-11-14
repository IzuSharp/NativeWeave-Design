# Interop and independent Engine public API specification

Version **1.0.0**; design specification, not a published implementation. Owners: D02–D11 / A01–A12, A17–A18, A22–A24. Baseline: .NET 11.0.0, SDK 11.0.100, C# 15.0; no Preview language requirement. The accepted D02/D04–D09 wire and lifecycle contracts remain authoritative. This specification fixes their C# application surface and maintainer seams; it does not create a universal SQL/HTTP/GPU runtime.

**Signature authority:** [Interop.cs](../../experiments/public-api/NativeWeave.Api.Design/Interop.cs) contains every declared public type, member, overload, generic parameter and nullable/default annotation for this domain. All native-behavior bodies are deliberately throwing design stubs. Compiler/XML/API inventory evidence is maintained by the integrated public-API verification project. [InteropExamples.cs](../../experiments/public-api/NativeWeave.Api.Consumers/InteropExamples.cs) is compile-only consumption, not product execution. [Coverage](interop-coverage.json), [primary sources](interop-sources.json), [packaging and consumption](nuget-and-consumption.md) and the [engineering standard](../standards/csharp-public-api-and-documentation.md) are normative companion inputs.

## 1. Boundaries and API inventory

| Layer | Public or private | Exact types / responsibility | Package / owner |
| --- | --- | --- | --- |
| Application metadata and preflight | Stable proposed public API | `NativeWeave.Interop.AbiVersion`, `EngineCapability`, `EngineThreadingModel`, `EngineInfo`, `EngineDescriptor`, `EngineLoadOptions`, `EngineCatalog` | `NativeWeave.Core`; A02/A24 |
| Safe immutable native results | Stable proposed public API | `NativeWeave.Interop.NativeBuffer`, `NativeBufferReader`, `NativeBufferReader<TResult>` | `NativeWeave.Core`; A03/A04 |
| Errors | Stable proposed public API | `NativeWeave.Interop.NativeEngineException`, `EngineLoadException`, `EngineLoadFailure` | `NativeWeave.Core`; A05 |
| Engine author extension seam | Explicit advanced public API, separately documented | `NativeWeave.Interop.Extensibility.NativeAssetDescriptor`, `EngineCapabilityDefinition`, `EnginePackageManifest`, `EnginePackage`, `NativeBufferFactory` | `NativeWeave.Core`; A02/A04/A24 |
| Generated imports and lifecycle adapters | Internal API; no application compatibility promise | Typed raw imports, per-owner SafeHandle, module admission, operation context/coordinator, UCO dispatcher and generated binding schema | A03/A06/A07/A09–A12; module-specific generation |
| C ABI | Versioned native interface | Exact records/status constants in [nativeweave_api_v1.h](../../experiments/public-api/abi/nativeweave_api_v1.h); domain exports owned by their domain specifications | D02/D05/D06/D08, A01/A09/A11 |
| Rust implementation | Private to the owning native module | `Box`/`Arc` ownership, fallible buffers, selected executor and actual mature Engine | D04–D11 and domain tasks |

Namespaces do not imply an assembly per namespace. The Core package is BCL-only, with no DI container, Tokio runtime, scheduler thread, network dependency or automatic Engine discovery. No public `Initialize`, `ShutdownAll`, raw-handle `Detach`, generic native `Execute`, universal `Deadline`, global executor or arbitrary callback registration is introduced. Ordinary domain factories supply their compiled descriptor and initialize only their own instance. The optional catalog is for explicit preflight and diagnostics.

## 2. Member semantics: identity, descriptors and preflight

The following rules apply to every member in the corresponding signature group. XML reference generation expands these rules into each public member's documentation; property access is synchronous and cancellation-free.

| Member group | Inputs, outputs and errors | Lifetime, threading and cost |
| --- | --- | --- |
| `AbiVersion(uint Major, uint Minor)` and generated value members | Managed value; `Major=0` is an invalid loader requirement and is rejected by the manifest. Equality compares both fields; ordering is not promised. No conversion to `System.Version` is required. | Two 32-bit scalars; no owner or heap allocation. ABI compatibility still requires exact major, minimum minor, sizes and required capabilities. |
| `EngineCapability(string name)`, `Name`, `ToString`, generated equality members | Validate `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`, maximum 128 ASCII bytes, ordinal case sensitivity. Null throws `ArgumentNullException`; malformed throws `ArgumentException`. `default` has empty Name and is rejected by Require/Supports/manifest/options. | Immutable value with one managed string reference. Equality is ordinal. Does not load native code; `ToString` returns the existing identifier. |
| `EngineThreadingModel` | Values 0 Synchronous, 1 EngineLocalAsync, 2 SerializedWorker, 3 ExternalLoop. These are managed descriptive values, never wire enum layouts. Unknown values are rejected by manifest construction. | Describes native execution, not blanket Send/Sync or thread-safety permission. ExternalLoop is a future profile, not a certified desktop capability. |
| `EngineInfo` properties | Non-null immutable metadata: identity, NuGet ID/version, actual ABI, chosen RID, threading model and actual known capabilities. Package versions are NuGet strings, not lossy `System.Version`. | Borrow no domain owner; safe concurrently and after instance disposal. Snapshot retains its module association, but modules remain resident anyway. Access does not start native work. |
| `EngineInfo.Supports(capability)` / `Require(capability)` | Supports returns false for a valid unknown/missing name. Require throws `NotSupportedException` naming the feature. Invalid default capability throws `ArgumentException`. Neither reads upstream crate availability as a substitute for advertised adapter support. | Ordinal dictionary lookup after load; no FFI, no per-call allocation on success. Domain provider/profile validation may narrow support further. |
| `EngineDescriptor` properties | Identity/version/RID list describe the compiled package. RID list is exact and immutable. Descriptor construction belongs to generated EnginePackage code; no public application constructor. | Metadata access alone never loads a native binary. Concurrent reads are safe. |
| `EngineDescriptor.Inspect(options = null)` | Loads the declared asset, validates its hash, architecture/manifest/bootstrap/ABI and required capabilities, then returns `EngineInfo`. Synchronous because it is local loading/preflight, not network I/O. Argument errors are synchronous. Loader failures are `EngineLoadException`, with bounded actionable detail. | First call reads/hash-checks O(asset bytes), performs OS loading and one bootstrap call; later compatible calls reuse metadata. Does not construct a DB pool/listener/Tokio runtime. The process keeps any loaded module resident. |
| `EngineLoadOptions()` / `NativeAssetPath` / `RequiredCapabilities` | Defaults: package asset path; empty additional requirements. Override must be an absolute existing file matching the descriptor's exact RID/hash and full native dependency policy. Null collection or invalid capability is rejected. No `VerifyHash=false` or environment search-path override is offered. | An init-only options object is not deeply immutable if its collection is mutable: Inspect/Build snapshots and validates it before use. Caller must not mutate that collection during snapshot. Options are not an unlimited version-replacement mechanism. |
| `EngineCatalog(IEnumerable<EngineDescriptor>)` / `Engines` | Enumerate exactly once into a bounded snapshot; reject null collection/entry and duplicate `EngineId`, even when versions differ. Sort Engines ordinally by ID. Empty is valid. | O(n log n) setup, O(n) retained metadata. No assembly scan, module initializer discovery, background work or native load. Snapshot concurrent reads are safe. |
| `EngineCatalog.TryGet(id, out descriptor)` / `Get(id)` | Null/empty/malformed ID is an argument error. Absent valid ID returns false/null or throws `KeyNotFoundException` respectively. `NotNullWhen(true)` supports natural nullable flow. | O(1) expected lookup. Does not claim that installing a package automatically adds it to a custom catalog. |
| `EngineCatalog.Inspect(id, options = null)` | Equivalent to `Get(id).Inspect(options)`; no new overload semantics or extra initialization. | Same module cache as normal domain use, no second runtime. |

### Identity grammar and metadata snapshot limits

Every `EngineId` uses the same ordinal, case-sensitive ASCII grammar as
`EngineCapability`: `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`, with 1–128 bytes.
Manifest construction, catalog lookup and native-error identity construction apply
that rule consistently. There is no case folding, whitespace trimming or Unicode
normalization. A null ID throws `ArgumentNullException`; an empty, oversized or
malformed ID throws `ArgumentException` before native loading. The initial IDs are
`database.sqlite`, `database.postgresql` and `server`.

These v1 cold-metadata limits are fixed implementation limits, not measured resource
claims or optional defaults:

| Snapshot | Exact limits and rejection |
| --- | --- |
| `EngineCatalog` | At most 256 descriptors. Enumerate once, stop at the first excess entry, dispose the enumerator and throw `ArgumentException` for `descriptors`; never publish a partial catalog or load a module. |
| `EnginePackageManifest` | 1–64 assets and 0–64 capability definitions. Package ID/version and CPU baseline each use at most 256 UTF-8 bytes; RID at most 128 ASCII bytes; relative native path at most 4,096 UTF-8 bytes; bootstrap symbol at most 128 ASCII bytes matching `[A-Za-z_][A-Za-z0-9_]*`. Each asset hash remains exactly 64 lowercase hexadecimal characters. Total UTF-8 bytes of all manifest string fields, including repeated asset/capability records, must not exceed 65,536. |
| `EngineLoadOptions` snapshot | At most 64 additional required capabilities, with no duplicate names. An explicit native path uses at most 4,096 UTF-8 bytes and the absolute-path rule above. Invalid/default capability entries or excess count/bytes throw `ArgumentException` before file access or native load. |

Collection snapshots validate counts and cumulative checked byte sizes as entries
are observed; they do not fully materialize an unbounded enumeration and validate
afterward. Null collections/entries retain their declared argument errors. User
enumeration exceptions propagate without publishing a descriptor/catalog or
performing preflight. Manifest entries and strings are immutable; catalogs may
share validated descriptor objects instead of duplicating their contents.
`EngineInfo` and descriptor property snapshots inherit the same manifest limits;
actual known capabilities never exceed the 64-bit bootstrap map. These limits do
not attempt to bound all metadata objects explicitly created by application code.

### Preflight state and loading policy

A generated package stores one lazy descriptor and one typed module loader. Descriptor creation does not trigger native loading. Under a short module admission lock, the loader establishes a single content identity for `(engine_id, ABI major)`; it does not hold that lock during user callbacks, domain work or unloading. A single in-progress load has one completion/failure publication. All callers observe the same completed base validation. Additional caller capability requirements are checked against the validated module; a failed extra requirement does not poison an otherwise valid module.

The initial supported profile permits **one loaded content identity per engine ID in a process**. Identical descriptors reuse it; a different native asset hash, ABI major or incompatible owned-package closure fails `ConflictingModule` before domain creation. SQLite and PostgreSQL have distinct engine IDs and native basenames, so they coexist naturally; Server is a third independent module. A deployment upgrade selects a new package closure and starts a new process. There is no library unload or active-instance replacement API.

The package-owned resolver is registered once on the facade assembly. `NativeLibrary.Load` does not recursively invoke `SetDllImportResolver`; use the actual documented overload semantics rather than a recursive resolver. Package code restricts resolution to the selected manifest asset and required OS dependencies; it never searches the current working directory or accepts an arbitrary process environment path. Ordinary JIT development follows .NET's asset selection plus the descriptor's content validation; Native AOT uses the same lazy dynamic P/Invoke profile on the initial desktop targets. Direct P/Invoke/static linking is not silently enabled, because it changes resolution behavior and needs its own target profile.

Failed ABI/asset validation never publishes domain handles. A module already passed to the OS loader may remain mapped after a later bootstrap failure; record a latched failed selection and require process restart after correcting that binary. Repeating failed alternate loads cannot accumulate an unbounded collection of failed DLLs. A pre-load missing-file failure creates no module owner; retry after fixing the same installation is allowed, with no background retries. Hash checks establish consistency with the package, not authentication of a malicious native library or sandboxing.

## 3. Member semantics: buffers

`NativeBuffer` is immutable native-owned bytes whose allocation remains address-stable and whose destructor is safe and nonblocking on any release thread. Length is in `[0, int.MaxValue]`, additionally bounded by the Engine's negotiated per-result limit. Large data streams are chunked by the domain rather than creating a >2 GiB CLR span. Mutation, owner-thread destruction, GPU-mapped resources and borrowed request bodies use separate domain-specific owner types; they cannot be smuggled into this general immutable buffer profile.

| Member | Exact behavior | Errors / cost |
| --- | --- | --- |
| `Length`, `IsDisposed` | Immutable length is available after closure. IsDisposed means no new read admission, not physical free. | O(1), no FFI/allocations. |
| `CopyTo(Span<byte>)` | Acquire logical admission + SafeHandle reference atomically, copy Length bytes, leave remaining destination tail unchanged, release in finally. | Short destination: `ArgumentException`, no write. Closed: `ObjectDisposedException`. O(n) copy, no managed allocation. |
| `CopyTo(int sourceOffset, Span<byte>)` | Checked `offset >= 0`, `offset + destination.Length <= Length`; destination length is the requested count. Empty range at Length is valid. | Invalid offset/range: `ArgumentOutOfRangeException`, no write. O(destination length) copy. |
| `TryCopyTo(Span<byte>)` | Checks logical admission even for a short destination. Returns false with destination untouched only when short; true copies all bytes. | Disposal still throws; Try does not swallow contract/native faults. No allocation. |
| `ToArray()` | Acquire lease before allocation; create a managed array and copy. Empty may return `Array.Empty<byte>()`; array lifetime is independent of NativeBuffer. | O(n), one managed array (except shared empty), possible OOM. Dispose in parallel does not invalidate the admitted copy. |
| `Read(NativeBufferReader)` / `Read<TResult>(NativeBufferReader<TResult>)` | Reader cannot be null. Invoke synchronously on the calling managed thread, outside all admission locks, with a span under an active lease. Reader exceptions propagate after lease release. Return scalar/copied result. | No native callback/UCO occurs. A cached static delegate avoids per-call delegate/closure allocation; captured lambdas may allocate. O(reader work). No cancellation is promised during arbitrary synchronous reader code. |
| `CopyToAsync(Stream, CancellationToken = default)` | Validate non-null writable destination, acquire one source lease for entire operation, allocate one staging array of exactly min(Length, 64 KiB) bytes, synchronously copy each chunk then await destination.WriteAsync. Keep that array live until the awaited write completes. Leave destination open. Hold source lease until copy completes/faults/cancels. Empty input needs no staging allocation. | Task-based because completion may span arbitrary I/O. One bounded staging array allocation and copy; no zero-copy claim. Pre-cancellation avoids copying. Cancellation/stream errors may occur after partial output and never undo bytes. No native pointer or call-scoped span survives await. A future pooled optimization must account for actual rented capacity and retained pool bytes; ArrayPool.Rent promises a minimum size, not this exact bound. |
| `Dispose()` | Atomically closes new read admission then drops the owner reference outside lock; idempotent. Already admitted reads/copy keep native memory alive. A reader may call Dispose on the same buffer and continue reading its current span. | Nonblocking, no user callbacks or network shutdown. May return before active reads finish. Finalizer fallback belongs only to the private SafeHandle and is not deterministic cleanup. |

`CopyToAsync` has a synchronous validation/admission wrapper. It checks destination
nullability and `CanWrite`, then acquires the source's logical read lease; null,
non-writable and already-closed usage errors throw synchronously in that order.
Only after valid admission does it observe pre-cancellation: a canceled token
returns a canceled Task associated with that token and releases the lease. It
performs no staging/native allocation, byte copy or stream write; the returned
canceled Task may allocate. This cancellation rule also wins for an empty buffer.
An admitted, uncanceled empty buffer releases its lease and returns a successfully
completed Task without calling the destination. Once asynchronous copying starts,
copy/write failures fault the returned Task and cancellation cancels it; `finally`
releases the staging array reference and source lease only after any admitted write
has completed. Cancellation never retroactively changes synchronous usage errors
or undoes already written bytes.

No naked `Memory<byte>`, `ReadOnlyMemory<byte>`, `Span<byte>` property, public pointer or `IMemoryOwner<byte>` implementation is provided: cached Memory/Span can outlive disposal and bypass the intended lease. This is an intentional limited equivalent to BCL memory ownership, with safer synchronous borrowing and explicit copies. Advanced domain APIs may define their own retained lease when they can prove its lifetime. Reading is concurrently safe because bytes are immutable; two concurrent writes to the same caller destination are the caller's responsibility.

Minimal consumer (design-compilation only):

```csharp
using NativeWeave.Interop;

using NativeBuffer result = ObtainResultFromAnEngine(); // domain-owned factory
int byteCount = result.Read(static bytes => bytes.Length);
byte[] retainedCopy = result.ToArray();
```

The symbolic factory above illustrates ownership; the actual compile fixture accepts a typed result parameter and does not pretend to implement an Engine. Advanced export uses `await result.CopyToAsync(stream, cancellationToken)` while the caller retains/disposes result. `Read` is suitable for bounded parsing/decoding; it is not a way to return a span through a generic result or execute async code with a borrowed address.

## 4. Member semantics: failures

`NativeEngineException` follows the three conventional parameterless/message/message+inner constructors plus a precise native-record constructor. Standard constructors have **null native metadata**, not fake status 0. The rich constructor requires nonempty engine/operation, a non-success ordinary failure status (not OK or PENDING), and records the exact uint status, uint domain, signed int native code and ulong correlation (zero permitted). Unknown failure codes remain unknown failures. Native-record properties are all populated together or all null. `EngineLoadException` sets EngineId/Operation=`load` while its native-record fields remain null for pre-native failures; it carries the distinct `EngineLoadFailure` enum and requested RID.

| Condition | Public mapping | Consequence |
| --- | --- | --- |
| Invalid managed arguments / closed resource / invalid sequencing | `ArgumentException` family / `ObjectDisposedException` / `InvalidOperationException` | Fail before native acceptance where statically knowable. |
| Missing capability known at preflight | `EngineLoadException(MissingCapability)`; a later explicit `EngineInfo.Require` uses `NotSupportedException` | No silent provider or behavior substitution. |
| Native terminal CANCELED | Canceled Task / `OperationCanceledException` with associated caller token where applicable | Never infer native retirement or transaction rollback. |
| Confirmed native operation timeout | `TimeoutException` or domain timeout subtype preserving required outcome metadata | Remote effects may be unknown. A canceled close wait is a separate matter. |
| DOMAIN_ERROR | Database/Server-specific exception or explicitly designed domain outcome | Preserve provider code, bounded details and recovery identity. |
| NATIVE_PANIC / ENGINE_POISONED / CONTRACT_VIOLATION | Rich `NativeEngineException` | Close ordinary instance admission; retain dedicated cleanup control. |
| Missing RID/asset/export, bad architecture/hash/ABI, duplicate loaded content | `EngineLoadException` with enum values fixed in Interop.cs | Message includes engine/package/RID, expected and observed version where known, and supported remedy. Never includes credentials or raw addresses. |
| abort/OOM abort/bad address/UCO ABI violation | Process-fatal or host isolation policy | No false recoverability guarantee. |

Error messages use bounded, redacted data. Exception creation is a cold path; no exception/string formatting is required on success. Engine/version/correlation diagnostics are not security credentials. Repeated panics retain quarantined unknown payloads according to D08; their possible memory cost and damaged-engine restart requirement remain explicit.

## 5. Exact maintainer extension members

These APIs are opt-in engine author facilities. They are not required by applications adding Entity/DTO/Handler classes. They use static compiled inputs and do not introduce managed plugin assembly loading.

| Type/member | Required semantics and errors | Cost, AOT and ownership |
| --- | --- | --- |
| `NativeAssetDescriptor(runtimeIdentifier, relativePath, sha256, cpuBaseline)` and properties | Validate supported portable RID string, canonical slash-separated package path under `runtimes/<rid>/native/`, no root/traversal, 64 lower-case hex digest, nonempty CPU baseline. Validate shape only; do not read files. | Immutable strings, one descriptor object per asset. No dynamic code. |
| `EngineCapabilityDefinition(Capability, BitIndex)` and value members | One immutable pair. Manifest rejects invalid/default name and indices outside 0–63. Capability maps are engine-local and ABI-major scoped; two engines may use the same bit for different names. | One struct. No hashing of uninitialized padding or Rust enum discriminants. |
| `EnginePackageManifest(...)` and all properties | Validate nonempty identity/package/version/bootstrap; exact ABI major; enum/profile; at least one asset; unique RIDs, paths, capability names and bit indices. Snapshot collections deeply enough that entries and contents are immutable. Null/shape errors throw argument exceptions. | O(assets+capabilities) bounded cold setup. Loader subset of complete signed release metadata; no package self-hash cycle. |
| `EnginePackage.CreateDescriptor(manifest, assembly)` | Neither argument null. `assembly` is explicitly statically rooted, normally `typeof(KnownPackageType).Assembly`; no scanning or Assembly.Load. Compile manifest/bootstrap agreement checked by generator and build target. Return immutable descriptor. | Does not load native code or register with an application service locator. Generator emits a lazy descriptor property per facade. |
| `NativeBufferFactory.Adopt(engine, owner, address, length)` | Maintainer guarantees owner belongs to this loaded engine, is unique, contains the exact creator destructor, and keeps the immutable address stable. Reject null/closed/invalid handle, negative/oversized length, and zero address with nonzero length. Invalid addresses cannot be probed safe. On success transfer ownership of that SafeHandle to NativeBuffer; caller must never dispose/adopt it again. On failure **caller retains** the SafeHandle and must dispose it. | No byte copy; one wrapper/gate. No native memory allocation. SafeHandle destructor must be nonblocking, nonthrowing and free-threaded. A domain with affinity/asynchronous release cannot use this seam. |

The complete release manifest additionally preserves upstream repository/commit, Cargo.lock/features, compiler/linker, minimum OS/CPU, dependency closures, license/provenance and per-RID artifact hashes under D10. The public managed loader subset does not replace that record. Arbitrary applications constructing an unsafe custom manifest/native owner remain within the same process trust domain; these interfaces cannot sandbox untrusted native code.

A new engine's author supplies a small typed Rust adapter and semantic sidecar, not a new C# interpreter. A09–A12 generate the internal exact imports, private owner wrappers and static UCO dispatch; A24 emits the manifest and package scaffold. Shared lifecycle algorithms remain owned by A03–A07 and code generation must call the tested common implementation or generate from the same reviewed semantic implementation, never evolve private divergent copies. Product implementation may choose internal type organization without changing the application surface; every state transition and operation binding below is fixed.

## 6. C# → managed adapter → C ABI → Rust mapping

### 6.1 Bootstrap and immutable buffers

The [header](../../experiments/public-api/abi/nativeweave_api_v1.h) is the canonical design-time declaration of existing shared v1 records. [layout_probe.c](../../experiments/public-api/abi/layout_probe.c) checks x64 sizes and every member offset; running it proves C layout only, not Rust/C#/native product execution.

| Public surface | Managed operation and C boundary | Rust adapter / state / ownership | Implementation |
| --- | --- | --- | --- |
| Descriptor/Catalog constructors, metadata lookup | `CreateDescriptor`, immutable manifest snapshots; **no ABI operation** | None; C# package data only | A02/A24 |
| `EngineDescriptor.Inspect` | Select/hash/load; resolve `nw_<engine>_get_abi_v1(uint32_t requested_major, uint32_t out_capacity, nw_abi_info_v1* out_info)` via generated static import or validated typed pointer | Stateless adapter returns ABI and actual compiled capability mask. No domain instance/runtime creation. Unknown major -> NOT_SUPPORTED; capacity<32 -> BUFFER_TOO_SMALL/no write; null output -> INVALID_ARGUMENT/no write. | A01/A02/A13–A16 |
| `EngineInfo.Supports/Require` | Known-name lookup against returned mask + manifest bit mapping; **no domain FFI** | No effect | A02 |
| `NativeBufferFactory.Adopt` | Wrap already transferred SafeHandle/view; no generic allocator adoption | Buffer owner retains native collection/allocator/module lineage; actual address and length are obtained by that engine's typed take/view operation. | A03/A04/domain take |
| `NativeBuffer.Read/CopyTo/ToArray` | D04 Open gate + AddRef; stable readonly span; no per-byte FFI. Native view must already be valid or acquired by an explicit domain `buffer_view_v1(owner, out view, out error)` under lease. | Native immutable allocation stays live until final owner reference. No reconstruction of Vec capacity or private layout. | A03/A04 |
| `NativeBuffer.CopyToAsync` | One admitted owner lease across staged Stream writes; managed stream I/O does not invoke generic Rust executor | Original native buffer remains live; no native access to managed staging buffer after synchronous copy. | A04 |
| `NativeBuffer.Dispose` | Close managed admission; private SafeHandle invokes creating engine's `buffer_release_v1(owner)` exactly once at final ref | Nonblocking drop of private native immutable owner; no callback, no unwind, no network wait. | A03/A04 |
| Rich `NativeEngineException` | Copy `nw_error_info_v1` synchronously; domain rich payload through domain-specific take | D08 guarded Result/status mapping; contain unwind at actual async poll boundary; preserve poison/quarantine | A05/A07 |

Known initial bootstrap identities are `nw_database_sqlite_get_abi_v1`, `nw_database_postgresql_get_abi_v1` and `nw_server_get_abi_v1`; their basenames are respectively `nw_database_sqlite`, `nw_database_postgresql`, `nw_server` (with OS prefix/suffix). Domain capability tables are owned by [database.md](database.md) and [server.md](server.md), not a second Core registry. A future package must use its own prefix to avoid symbol collision.

Every create/take out-owner is null on failure; successful ownership publication occurs only after complete initialization. Inputs borrowed for a call must be copied/retained before async acceptance. The 32-byte ABI record, 24-byte ErrorRecord, 16-byte view and 24-byte callback records preserve D02/D05/D06/D08 offsets. ErrorRecord short-capacity behavior is **not** bootstrap capacity behavior: a failure with <24-byte diagnostic capacity keeps its original status and writes no bytes. Unknown status/capabilities never mean success.

### 6.2 Typed asynchronous operation binding

Core does not expose a public generic operation object. Each public async domain method binds one exact generated operation set with the following immutable contract. `TInput`/`TResult` below describe compile-time managed types only; no CLR generic or Rust generic crosses the ABI.

| Internal managed adapter operation | C ABI operation role | State, output and failure contract |
| --- | --- | --- |
| `Create(in TInput)` | `nw_<engine>_<op>_create_v1(engine*, const <op>_parameters_v1*, <op>** out, nw_error_info_v1*)` | Reserve domain operation/input/cleanup budget first. Copy/retain all inputs required after return. Create success publishes one **Created**, unstarted owner, no callbacks. Failure leaves out null and rolls back native allocations. |
| `Start(operation, callbacks)` | `<op>_start_v1(op*, const nw_operation_callbacks_v1*, nw_error_info_v1*)` | Managed context/TCS/Normal GCHandle and registration setup precede start. Native copies table; before acceptance failure guarantees no retained/queued callback. After acceptance return OK even if terminal callback is synchronous before return. |
| `RequestCancel(operation)` | `<op>_request_cancel_v1(op*)` | Nonblocking/idempotent; records request, returns OK. Never signals CANCELED merely because token fired. Allowed trusted cleanup after poison/ordinary closure. |
| Static `OnTerminal` UCO | `uint32_t (*)(uintptr_t, uint32_t, const nw_error_info_v1*)` | One terminal CAS in native; bounded managed fixed-field copy to reserved latch. No application callback/continuation runs here. Duplicate notice poisons without second result/owner. Callback failure preserves original native effect/outcome. |
| `TakeResult(operation)` | `<op>_take_result_v1(op*, <op>_result_v1* out, nw_error_info_v1*)` | One transfer Ready→Taken. Prepare wrapper first. Failure keeps native ownership and empty out; conversion failure after successful take disposes acquired owner. May take after Retired until Released. |
| `TakeError(operation)` where needed | Domain-specific typed rich-error take | Same one-take and failure atomicity; base status does not depend on error-string allocation. |
| `TryRetire(operation)` | `<op>_try_retire_v1(op*)` | Nonblocking OK only after no future callback/input access and all admitted native accesses ended; otherwise PENDING. It is not business completion or DB connection reusability. |
| `Release(operation)` | `void <op>_release_v1(op*)` | Legal in never-started Created or proven Retired, with no live managed calls. Frees untaken result, native input/owner exactly once; no callbacks/unwind/blocking executor join. |

The managed coordinator state is `Setup` → `Started/StartSkipped/StartRejected/Indeterminate` → `TerminalKnown` → `NativeRetired` → `ManagedDrained` → `Reclaimed`; native and managed drain may progress independently but all guards must hold before Reclaimed. Domain parent close does not revoke coordinator-only take/cancel/retire/release authority. A TCS uses `RunContinuationsAsynchronously`; it is not a retirement barrier. Keep one per-operation context and Normal GCHandle in v1; no pooled context ABA or short ValueTask token assumption.

Exact cleanup ordering, synchronous cancellation registration, no-registration sentinels, fault latching, bounded mailbox/retry, self-wait rejection, poison, retained budgets and native-versus-managed drain are D04–D09. Those are implementation requirements, not optional prose. Task return and exception mapping are public; private coordinator class names and field packing remain implementation detail. Domain specs must replace every `<op>` with a concrete symbol, parameter/result record and engine capability before Delivery acceptance. No new generic Core execution protocol or untyped bytecode interpreter is implied.

### 6.3 Notifications and affinity

Domain streams/subscriptions select D05 create/start/request_stop/try_retire/release with `nw_callbacks_v1` only when needed. Event payload is borrowed for the callback and copied/retained under a documented bounded domain profile before returning. Ordinary events dispatch on managed scheduling, not a native worker. Explicit Dispose discards queued ordinary events and joins active handlers; successful DisposeAsync includes native quiet, control/registration drain and dispatcher drain. Cancellation of close waiting never destroys active state. A synchronous decision callback is a separate declared capability with fail-closed exceptions; it cannot await its own engine's shutdown.

Serialized-worker and future UI/GPU owner-thread resources dispatch release to that owner executor. A future Engine must describe progress and event-loop ownership before claiming that profile; `EngineThreadingModel.ExternalLoop` metadata alone is not an implementation. General NativeBuffer is restricted to free-threaded immutable destruction. No ThreadPool hop is forced onto a synchronous codec, and no thread-affine resource is freed directly by the SafeHandle finalizer thread.

## 7. Compatibility and deliberately excluded surfaces

Public C# API compatibility, C ABI compatibility, upstream Rust compatibility and owned NuGet closure compatibility are separate. Appending an optional capability does not justify changing a public member's ownership/timeout/nullability or a C field's meaning. Public method removal/type/nullability/default changes require API review and migration documentation. ABI major changes require distinct negotiated modules; Rust crate/compiler upgrades require source/differential/native-conformance tests even if C# signatures do not change.

Explicitly unsupported in this initial profile: runtime loading of new managed assemblies into an existing AOT image; reflection-discovered engine/provider/handler classes; in-process replacement/hot unload of a loaded engine; universal whole-process memory accounting; unsafe memory adoption by application code; unmanaged pointer/allocator/GCHandle application APIs; automatic conversion of every Rust trait/generic to a public C# object; interruption of arbitrary synchronous native algorithms; forcing a common Tokio runtime on every Engine. Optional future GPU/UI/media/native capability modules follow the same manifest/ownership/error rules, but their domain API and platform certification remain D21/A23–A24 work, not invented current support.

## 8. Implementation and verification inputs

| Tasks | Required implementation evidence |
| --- | --- |
| A01/A02 | Header/all target C-Rust-C# size/offset/export inventory, ABI/capability/no-write negatives, module identity and unsupported-RID diagnostics. |
| A03/A04 | Call-versus-Dispose races; scoped read reentrancy; no use-after-free after async staging; copy bounds and untouched short destinations; adoption failure leaves caller owner; exact creator destructor. |
| A05–A08 | Status/error mapping, panic/poison, Task/cancel/close distinctions, every D04–D09 controlled race, no user continuation on UCO, bounded input/cleanup/waiter bytes. |
| A09–A12 | Same signature/schema/XML inventory; deterministic generation; no peer-generator dependency; analyzers reject unsupported wire/callback/borrow shapes; ordinary model edit does not rebuild Rust. |
| A13–A16/A22 | Exact NuGet package closure/asset hashes, wrong/missing/duplicate version negatives, RID-free JIT and actual AOT on each certified OS, clean no-Rust/offline-after-restore consumer, upgrade/restart behavior. |
| A17/A18/A23/A24 | At least two distinct real Engine kinds; generated package scaffold, minimal/no-runtime synchronous case, async/affine capability declarations; no unproven universal abstraction. |

This round's declaration compilation, native header layout checks and source review establish interface feasibility only. All product execution, performance, leak/soak and deployment claims remain future Delivery obligations. Historical accepted evidence stays bound to its original bytes. Any superseding contract version must receive new independent review and exact content binding.

The resumed [Interop/package-flow evidence](../../verification/public-api/interop-packaging/README.md)
includes actual .NET11/C#15 compilation of Interop.cs and its consumers, a rejected ref-like result
escape, and the five-record Linux x64 C layout probe. Its separate package experiment executes
normal and Native AOT consumers over an unchanged inherited research codec, with automatic
transitive model/DTO/handler metadata generation. That successful AOT row establishes this bounded
design mechanism; none of the throwing public-API declarations are described as a functioning
product implementation. [Type semantic policies](interop-symbol-policies.json) bind every public
type/member family to this document's exact semantics, native operation family and owning tasks.
