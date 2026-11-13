# R32 — UI thread affinity and GPU lifetime extension research

Date: 2026-11-12. This previously missing topic is completed as a source-backed
extension-boundary study. It does not implement GUI/GPU products or claim device execution.

## Fixed source and scope

Winit 0.30.13, `e9809ef54b18499bb4f2cac945719ecc2a61061b`:
`src/event_loop.rs:28–46,80–122,238–271,549–570` and
`src/application.rs:19–83,125–187,193–219`.
wgpu 30.0.2, `2b38d994b38dd001157d31fd3321111103a8dd80`:
`wgpu/src/api/surface.rs:28–48,103–124,138–198,218–228`,
`buffer.rs:300–335,356–398,547–629`, `device.rs:86–96`.
Exact file hashes, URLs and read boundaries are in
[source-inspection.json](../../../../verification/server-completion/source-inspection.json).
No GPUI or NSH-specific implementation is claimed read by this study.

## What the source actually constrains

Winit EventLoop is neither Send nor Sync, normally must be created on the main thread,
and can be built only once. EventLoopProxy is its public cross-thread wakeup seam;
posting to a dead event loop returns the original undelivered event. `run_app` may
never return on iOS, so stack unwinding after that call is not a cleanup strategy.
These constraints rule out a Core that unconditionally moves every operation onto one
Tokio runtime or destroys all native objects directly from a .NET finalizer thread.

wgpu Surface retains its window handle source and drops it after other surface fields.
Reconfiguration with an old acquired SurfaceTexture alive is invalid/panicking; zero
width/height is invalid. CurrentSurfaceTexture distinguishes Success/Suboptimal from
Timeout/Occluded/Outdated/Lost/Validation. Treating every failure as retry is incorrect:
Lost/Outdated require owner-thread recovery with old acquisitions retired; zero-sized
minimized windows should pause presentation. A stale C# wrapper must not point into a
reconfigured native surface merely because the numeric handle was recycled.

Buffer mapping completion requires device/instance polling or queue submission.
Callbacks run on whichever thread drives progress and must be short, since native
polling does not return until they finish. CPU mapping excludes GPU use. The inspected
map path releases its mapping mutex before invoking the inner callback; a foreign
Adapter must preserve this no-user-code-under-native-lock discipline. Owned map leases
must end before unmap, resubmit or parent destruction. A C# Task completion is not proof
that a GPU submission fence has completed or the buffer can be freed.

## Chosen integration pattern

Keep native event loops, rendering, resource validation and device/queue algorithms in
the mature engine. Add an engine-local affinity descriptor and bounded command queue,
with completion through the existing Core callback/operation protocol. C# constructs
typed commands and handles application/UI state; it never translates a GPU or UI engine
into a managed runtime. No global scheduler or universal object model is introduced.

Three explicit capabilities cover the relevant differences: owner-thread command
submission, externally driven progress/polling, and revocable platform-resource leases.
They are optional to a particular Engine; a SIMD/synchronous codec engine pays none of
this cost. Direct calls are allowed where the upstream type genuinely permits them;
affinity is per resource/operation, not a blanket claim that every GPU call is main-thread-only.

Native lifecycle callbacks that invalidate an OS surface must first close render
admission and invalidate/drop the native surface synchronously on its owning thread.
Managed notification is then queued. Waiting for an arbitrary async C# Handler before
returning the platform callback is unsafe on Android and can deadlock the event loop.
An owning .NET wrapper's Dispose requests retirement; finalization only requests safe
release on the owner thread. If that thread is gone, report unrecoverable ClosePending
or process-teardown retention; do not silently call a thread-affine destructor elsewhere.

## Failures, platform limits and Codex obligations

Validate dimensions/format/support before invoking a panicking configuration API.
Queue overflow rejects before copying payload; rejected commands return/release their
owners exactly once. Device loss atomically rejects new work, completes pending
operations with a domain error, and retains owners until driver-defined quiescence.
Duplicate suspend/resume is idempotent; stale generations cannot resurrect old surfaces.

D21 defines the interface/state matrix. Future A23/A24 extension probes must use one
real UI loop and one real GPU mapping/submission path, owner-thread assertions,
device/window loss, out-of-memory, cancellation, lost wakeup, late callback, shutdown,
and AOT application execution on each declared target. An abstract queue model would
not substitute for those future device tests. Current absence of GPU/display/mobile
devices is an implementation-platform limitation, not an unresolved architecture
choice for this bounded future-extension study.
