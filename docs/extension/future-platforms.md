# D21 — Future native engines, affinity and mobile platform boundaries

Contract C-EXTENSION-001. Design revision **0.4.0 design candidate**. Acceptance is recorded by the registry
against exact content and independent review; this document does not authorize product
implementation. Inputs R18, R32, R33; cross-contract D01–D12. GPU, GPUI, NSH, media,
SIMD and mobile UI are future domain integrations, not dependencies of Database/Server.

## 1. Purpose and concrete reuse

An Engine reuses a mature native implementation's data structures, algorithms and
resource model. C# supplies typed application APIs and static AOT bindings. Start with
public APIs, then a source-informed dedicated Adapter; use upstream extension or a
controlled fork only for a documented capability gap with tests, license/maintenance
ownership and an upgrade plan. Do not build a universal GUI/GPU/media runtime in Core.

[R32](../research/topics/R32/report.md) fixes Winit0.30.13/wgpu30.0.2 source identities;
[R33](../research/topics/R33/report.md) fixes Rust1.100/.NET11 platform evidence.
Winit's EventLoop/Proxy and ApplicationHandler are reused instead of a second managed
OS event loop. wgpu's Surface, queue submission, map callback, polling and device-loss
mechanisms are reused instead of managed GPU scheduling. GPUI/NSH are compatibility
targets for the method, not falsely certified modules or mandatory selected dependencies.

## 2. Engine descriptor and interface responsibilities

The base Engine negotiation reuses D02's version/size/capability scheme. Optional domain
tables describe real capabilities and may be absent. Proposed signatures below are
design-level pseudocode, not compiled NativeWeave APIs:

| Native operation | C# view | Ownership and restrictions |
|---|---|---|
| `engine_get_affinity(resource, out descriptor)` | immutable AffinityDescriptor | reports owner-thread, transferable or caller-thread rules per resource; no raw OS pointer |
| `engine_submit(owner, command_bytes, operation)` | ValueTask / typed command builder | validates and copies/retains only after quota acquisition; Core create/start/take/retire semantics |
| `engine_poll(owner, bounded_budget)` | owner-thread progress pump integration | allowed only when host owns pumping; framework-owned loop uses its wakeup/proxy seam |
| `engine_invalidate_surface(surface, generation)` | notification/event + invalidated wrapper | native urgent lifecycle action before deferred managed user notification |
| `engine_release_on_owner(resource)` | DisposeAsync / bounded CloseAsync | disallows new calls immediately; native destructor executes on valid owner thread after leases/fences |

No C# delegate, Span, Rust trait object, Rc, wgpu type or platform reference crosses the
C ABI. Generated wrappers retain engine/module roots and parent owners. Native resource
handles stay private. A domain with recycled public IDs uses its own generation guard;
Core does not require a global handle table. Additional C# entities, tools or view-model
types reuse the maintainer's prebuilt module through descriptors and never run Cargo.

## 3. Affinity, progress and cleanup state machines

An affinity resource transitions Created → Active → Closing → Retired. Invalidation
closes admission even if physical retirement must wait. Requests accepted before
Closing own leases and either complete or fail with the domain's terminal reason.
Wrong-thread direct calls fail before touching native state. Posting to a closed loop
returns the original command and its owner; it cannot silently leak/discard payload.

The platform surface has Dormant → Available(generation) → Invalidated → Dormant.
Resume creates a new generation; duplicate events are idempotent. New work carries
the currently valid generation. Surface destruction is different from device loss and
from whole-engine shutdown. A zero-size minimized window stays Dormant without invoking
wgpu configure. Outstanding acquired textures retire before reconfiguration.

A GPU mapped buffer transitions Unmapped → Mapping → Mapped → Unmapping → Unmapped,
with Closing/Faulted orthogonal. The native map callback only queues completion;
managed code obtains a controlled map lease after successful completion. GPU submission
is forbidden while mapped; unmap waits for CPU views to retire. A completed C# Task is
not a GPU fence and cannot release in-flight backing memory. Parent device/window roots
outlive child resource and callback retirement. If the driver reports device loss,
reject new admission, terminalize pending operations and preserve resources until
the documented safe-release point. Do not invent recoverability after a native OOM.

The host remains responsible for progress: event-loop-owned engines use the native
loop's wakeup; externally polled GPU engines declare who polls and when shutdown drives
remaining callbacks. Calling synchronous Wait/Task.Result on the owner thread while
waiting for that same loop is forbidden. Callback reentry follows D05; arbitrary
application code runs outside native locks. A finalizer cannot destroy a thread-affine
resource directly. It requests release; bounded ClosePending retains roots if progress
is impossible, with explicit process teardown diagnostics instead of unsafe cleanup.

## 4. Android and Apple lifecycle requirements

Android Winit Suspended means SurfaceView destruction; native render surfaces must be
dropped before that callback returns. The Adapter performs immediate native invalidation
and owner-thread release of the surface, then queues a C# notification. It cannot await
arbitrary managed code to satisfy the OS callback. Device resources that remain valid
are accounted separately from the destroyed surface. iOS resignation/activation maps
to its own lifecycle rules; do not apply Android's exact surface rule universally.

Memory warnings release optional caches and prevent new expensive work; they never
cancel the ownership proof for live buffers/callbacks. Background suspension may prevent
timely execution, and the process may terminate without graceful shutdown. Persistent
work uses durable application state; library finalizers are not a data durability mechanism.
JNI thread attachment/global references and Objective-C ownership are contained within
platform-specific adapters. They are not exposed as generic borrowed addresses to C#.

## 5. Platform/package matrix

| Profile | Current research conclusion | Future package/build requirements |
|---|---|---|
| Windows/Linux desktop | shared ABI/AOT baseline; UI/GPU product unimplemented | actual backend/API/driver, compiler/CRT/libc baseline, independent NuGet native assets |
| iOS ARM64 device | .NET Native AOT target documented; Rust tier2; not NativeWeave certified | macOS/Xcode SDK, explicit static/framework linkage, signing/entitlements, physical device |
| iOS simulator ARM64/x64 | separate artifacts/ABI from device | matching simulator SDK and actual simulator run; no reuse of device artifact by CPU-name alone |
| Android | Rust tier2+NDK; .NET11 Native AOT experimental/no built-in Java interop | explicit experimental opt-in, exact API/NDK/ABI, JNI shim, device test, fail if unsupported |

The .NET11 CoreCLR/R2R mobile default is not Native AOT and cannot silently replace it.
Do not reinterpret Mono AOT properties as Native AOT configuration. Maintainers build
native modules; consumers perform normal .NET local builds and explicit platform
publish. Final app linkage verifies exported symbols survive dead stripping, no second
runtime/event loop is added, and all dependencies/licenses are packaged. Platform
support is declared only for the tested complete tuple, not every upstream target.

## 6. Implementation examples and acceptance

Illustrative C# application shape, uncompiled as a NativeWeave API:

```csharp
await using var engine = await GraphicsEngine.AttachAsync(nativeWindow, options);
await using var buffer = await engine.CreateBufferAsync(descriptor, cancellation);
await engine.SubmitAsync(commands, cancellation);
await using var mapping = await buffer.MapReadAsync(cancellation);
Consume(mapping.ReadOnlyBytes); // lease cannot escape or outlive unmap
await engine.CloseAsync(deadline); // ClosePending is observable and retains owners
```

The public API must make illegal asynchronous borrows impossible or diagnosed. An
ordinary ReadOnlyMemory over a native pointer is not a lifetime contract. Default
cross-boundary transfer may copy with bounded credit; zero-copy mapping is an explicit
lease capability justified by native ownership and measured benefit.

Future A23 owns platform affinity/lifecycle probes, A24 the extension conformance
entrypoint, A16/A22 packaging/upgrades, and each later Engine its own dedicated task
fragment. Their tests include wrong-thread calls, owner-loop closure with queued work,
duplicate suspend/resume, stale-generation commands, mapping cancel/completion races,
device loss, window loss, old textures during reconfigure, queue saturation, finalizer
requests, module unload prevention and real platform AOT/installation execution.
No current Windows/Linux task waits on an unimplemented mobile/GPU product. This
contract can be accepted as an extension design after R18/R32/R33 and independent
review, while future device/product evidence remains a release obligation.


## Public API refinement, revision 0.4.0

The [C# Public API and Documentation Standard](../standards/csharp-public-api-and-documentation.md), [exact API declarations and reference](../api/README.md), and the domain specification are normative consumers of this contract. This revision adds public surface and documentation obligations; it does not change the v1 C wire representation merely because the document version increments. Historical 0.3.0 acceptance remains bound to its original bytes and review. Current acceptance requires the new exact content and independent review.

Every future GPU/GPUI/NSH/media/SIMD/mobile module explicitly adopts the [versioned C# API/documentation standard](../standards/csharp-public-api-and-documentation.md) using [the adoption templates](../../templates/public-api/). It must inspect relevant stable .NET APIs, design a complete convenient C# surface, map actual native operations, state affinity/ownership/AOT/platform/cost and maintain XML/reference/examples/compatibility in its owning tasks. The templates create no generic execution runtime and promise no current GUI/GPU/mobile product API. The new repository must install or pin the rules in its own AGENTS/build/CI; it does not inherit this repository implicitly. A23/A24 and A22 own conformance/adoption/upgrade rules.
