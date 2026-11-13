using System.Diagnostics;
using System.Runtime.InteropServices;

static void Check(bool ok, string name)
{
    if (!ok) throw new InvalidOperationException(name);
    Console.WriteLine($"PASS {name}");
}

Check(Marshal.SizeOf<TraceContextV1>() == 32, "trace_context_size_32");
Check(Marshal.OffsetOf<TraceContextV1>(nameof(TraceContextV1.TraceId)).ToInt32() == 8,
    "trace_id_offset_8");
Check(Marshal.OffsetOf<TraceContextV1>(nameof(TraceContextV1.ParentSpanId)).ToInt32() == 24,
    "parent_span_offset_24");

using var source = new ActivitySource("NativeWeave.Research.Diagnostics");
Check(!source.HasListeners(), "no_observer_before_registration");
for (var i = 0; i < 10_000; i++) source.StartActivity("request")?.Dispose();
const int samples = 200_000;
var nullCount = 0;
var startAllocated = GC.GetAllocatedBytesForCurrentThread();
var start = Stopwatch.GetTimestamp();
for (var i = 0; i < samples; i++)
{
    using var span = source.StartActivity("request");
    if (span is null) nullCount++;
}
var elapsed = Stopwatch.GetElapsedTime(start);
var allocated = GC.GetAllocatedBytesForCurrentThread() - startAllocated;
Check(nullCount == samples, "no_observer_returns_null");
Check(allocated == 0, "no_observer_steady_loop_zero_thread_allocations");
Console.WriteLine($"OBSERVATION samples={samples} elapsed_ns={elapsed.TotalNanoseconds:F0} ns_per_call={elapsed.TotalNanoseconds / samples:F3} allocated_bytes={allocated}");

var lazyTagCalls = 0;
if (source.HasListeners())
{
    lazyTagCalls++;
    using var never = source.StartActivity("expensive", ActivityKind.Internal, default(ActivityContext),
        tags: [new("payload", new string('x', 1024))]);
}
Check(lazyTagCalls == 0, "observer_gate_does_not_format_tags");

using (var listener = new ActivityListener
{
    ShouldListenTo = item => ReferenceEquals(item, source),
    Sample = (ref ActivityCreationOptions<ActivityContext> _) => ActivitySamplingResult.AllDataAndRecorded
})
{
    ActivitySource.AddActivityListener(listener);
    var parent = new ActivityContext(ActivityTraceId.CreateRandom(), ActivitySpanId.CreateRandom(), ActivityTraceFlags.Recorded, isRemote: true);
    using var active = source.StartActivity("managed_handler", ActivityKind.Server, parent);
    Check(active is not null && active.TraceId == parent.TraceId && active.ParentSpanId == parent.SpanId,
        "explicit_remote_parent_preserved");
    await Task.Yield();
    Check(Activity.Current == active, "managed_async_context_preserved");
    await Task.Run(() =>
    {
        using var child = source.StartActivity("child");
        Check(child is not null && child.ParentSpanId == active!.SpanId, "managed_task_child_parent_preserved");
    });
}
Check(!source.HasListeners(), "observer_disposal_restores_disabled_state");
Console.WriteLine("RESEARCH_ONLY: thread-local allocation counter excludes native memory; single-process timing is not a production benchmark or cross-language propagation proof.");

[StructLayout(LayoutKind.Sequential)]
unsafe struct TraceContextV1
{
    public uint Size;
    public ushort Version;
    public byte TraceFlags;
    public byte Reserved;
    public fixed byte TraceId[16];
    public fixed byte ParentSpanId[8];
}
