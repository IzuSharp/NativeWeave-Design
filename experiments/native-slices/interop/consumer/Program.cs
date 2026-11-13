using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using NativeWeave.Experiments;

internal static unsafe class Program
{
    private static int assertions;
    private static void Check(bool ok, string label)
    {
        if (!ok) throw new InvalidOperationException(label);
        assertions++;
    }
    private static void Group(string name, Action test)
    {
        test();
        Console.WriteLine("PASS " + name);
    }
    private static void Status(uint expected, Action action)
    {
        try { action(); }
        catch (NativeStatusException ex) { Check(ex.Status == expected, "native status"); return; }
        throw new InvalidOperationException("Expected native status " + expected);
    }
    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    private static uint Add(uint value, nuint context)
    {
        // This fixture is synchronous, contains no managed object pointer and cannot throw.
        return unchecked(value + (uint)context);
    }
    private static ulong Expected(int count)
    {
        ulong total = 0;
        for (int i = 0; i < count; i++) total += (ulong)(i % 251);
        return total;
    }
    public static int Main(string[] args)
    {
        bool requireAot = Array.IndexOf(args, "--expect-aot") >= 0;
        Check(!requireAot || !RuntimeFeature.IsDynamicCodeSupported, "AOT run must not support dynamic code");
        Group("layout-and-size-negatives", () =>
        {
            Check(Native.Info(out AbiInfo info, (nuint)Unsafe.SizeOf<AbiInfo>()) == 0, "ABI info");
            Check(info.Version == 1 && info.StructSize == Unsafe.SizeOf<AbiInfo>(), "ABI version/size");
            Check(info.PointerSize == IntPtr.Size && IntPtr.Size == 8, "x64-only fixture");
            Check(info.SampleSize == Unsafe.SizeOf<SampleLayout>() && info.SampleAlignment == 8, "sample layout");
            Check(info.CountOffset == (uint)Marshal.OffsetOf<SampleLayout>(nameof(SampleLayout.Count)).ToInt32(), "count offset");
            Check(info.ValueOffset == (uint)Marshal.OffsetOf<SampleLayout>(nameof(SampleLayout.Value)).ToInt32(), "value offset");
            Check(Native.Info(out _, 0) == 1, "short ABI output rejected");
        });
        Group("buffer-empty-and-owned", () =>
        {
            foreach (int n in new[] { 0, 1, 256, 65536 })
            {
                using (var b = OwnedBuffer.Create((nuint)n)) Check(b.Sum() == Expected(n), "sum");
                Check(Native.Live() == 0, "reclaimed after Dispose");
            }
        });
        Group("failure-before-publication", () =>
        {
            Status(2, () => { using var b = OwnedBuffer.Create(1024 * 1024 + 1); });
            Status(1, () => { using var b = OwnedBuffer.Create(10, 2); });
            Status(3, () => { using var b = OwnedBuffer.Create(10, 1); });
            Check(Native.Live() == 0, "DropGuard rollback after contained panic");
        });
        Group("synchronous-reverse-call", () =>
        {
            Check(Native.Callback(7, 3, &Add, out uint result) == 0 && result == 10, "UCO callback");
            Check(Native.Callback(7, 3, null, out result) == 1 && result == 0, "null callback rejected");
        });
        Group("disposed-wrapper-rejects-reuse", () =>
        {
            var b = OwnedBuffer.Create(12);
            b.Dispose();
            b.Dispose();
            Check(Native.Live() == 0, "idempotent managed Dispose");
            try { b.Sum(); }
            catch (ObjectDisposedException) { assertions++; return; }
            throw new InvalidOperationException("Disposed wrapper admitted call");
        });
        Group("safehandle-inflight-lease-32-rounds", () =>
        {
            for (int i = 0; i < 32; i++)
            {
                Native.HoldReset();
                var b = OwnedBuffer.Create(4096);
                Task<ulong> running = Task.Run(b.SumHeld);
                try
                {
                    Check(SpinWait.SpinUntil(() => Native.HoldEntered() == 1, TimeSpan.FromSeconds(5)), "native entered");
                    b.Dispose();
                    // The generated SafeHandle call lease must keep the Rust owner alive.
                    Check(Native.Live() == 1, "Dispose must not free in-flight owner");
                }
                finally
                {
                    Native.HoldRelease();
                    b.Dispose();
                }
                Check(running.Wait(TimeSpan.FromSeconds(5)), "native returned after release");
                Check(running.GetAwaiter().GetResult() == Expected(4096), "in-flight sum");
                Check(Native.Live() == 0, "last call lease releases owner");
            }
        });
        Check(Native.Live() == 0, "no remaining buffers");
        Console.WriteLine($"SUCCESS assertions={assertions} aot={!RuntimeFeature.IsDynamicCodeSupported}");
        return 0;
    }
}
