using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using NativeWeave.Experiments;

namespace NativeWeave.Research.Admission;

internal static partial class Raw
{
    [LibraryImport("nw_interop_probe", EntryPoint = "nw_buffer_sum")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial uint Sum(nint owner, out ulong value);
    [LibraryImport("nw_interop_probe", EntryPoint = "nw_buffer_sum_held")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial uint SumHeld(nint owner, out ulong value);
}

// R07/D04 synchronous research facade. No async/callback-retirement guarantee.
// The SafeHandle is private: application callers cannot bypass logical admission.
internal sealed class GatedBuffer : IDisposable
{
    private readonly object admission = new();
    private readonly OwnedBuffer owner;
    private bool closing;
    internal GatedBuffer(nuint count) => owner = OwnedBuffer.Create(count);
    internal ulong Sum(bool held = false, bool injectAfterLease = false)
    {
        bool acquired = false;
        try
        {
            nint pointer;
            lock (admission)
            {
                ObjectDisposedException.ThrowIf(closing, this);
                owner.DangerousAddRef(ref acquired);
                pointer = owner.DangerousGetHandle();
            }
            // Outside the gate. The test-only fault exercises the same finally path.
            if (injectAfterLease) throw new InjectedFailure();
            ulong value;
            uint status = held ? Raw.SumHeld(pointer, out value) : Raw.Sum(pointer, out value);
            if (status != 0) throw new NativeStatusException(status);
            return value;
        }
        finally
        {
            if (acquired) owner.DangerousRelease();
        }
    }
    public void Dispose()
    {
        lock (admission)
        {
            if (closing) return;
            closing = true; // Linearization point: future ordinary calls fail.
        }
        owner.Dispose(); // No native call or release under the admission gate.
    }
}
internal sealed class InjectedFailure : Exception { }

internal static class Program
{
    private static int assertions;
    private static void Check(bool ok, string message)
    {
        if (!ok) throw new InvalidOperationException(message);
        assertions++;
    }
    private static void MustReject(Action call)
    {
        try { call(); }
        catch (ObjectDisposedException) { assertions++; return; }
        throw new InvalidOperationException("A post-close call was admitted");
    }
    private static void Entered() => Check(SpinWait.SpinUntil(() => Native.HoldEntered() == 1,
        TimeSpan.FromSeconds(5)), "native held call entered");
    private static ulong Expected()
    {
        ulong sum = 0;
        for (int i = 0; i < 4096; i++) sum += (ulong)(i % 251);
        return sum;
    }
    private static void NegativeControl()
    {
        Native.HoldReset();
        using var buffer = OwnedBuffer.Create(4096);
        Task<ulong> running = Task.Run(buffer.SumHeld);
        try
        {
            Entered();
            buffer.Dispose();
            Check(Native.Live() == 1, "existing lease still owns native memory");
            // Deliberate negative control: this is still safe memory, but violates
            // a higher-level policy that closes admission immediately on Dispose.
            Check(buffer.Sum() == Expected(), "raw SafeHandle still admits while another lease exists");
            Console.WriteLine("OBSERVED negative-control post-Dispose call admitted while physical lease remains");
        }
        finally { Native.HoldRelease(); }
        Check(running.Wait(TimeSpan.FromSeconds(5)), "negative control returned");
        Check(running.GetAwaiter().GetResult() == Expected(), "negative control old call completed");
        Check(Native.Live() == 0, "negative control reclaimed");
    }
    private static void PositiveGate()
    {
        for (int i = 0; i < 64; i++)
        {
            Native.HoldReset();
            using var buffer = new GatedBuffer(4096);
            Task<ulong> running = Task.Run(() => buffer.Sum(held: true));
            try
            {
                Entered();
                Task close = Task.Run(buffer.Dispose);
                // Dispose must not wait for FFI because that call is deliberately held.
                Check(close.Wait(TimeSpan.FromSeconds(3)), "close is not blocked behind held FFI");
                close.GetAwaiter().GetResult();
                Check(Native.Live() == 1, "physical lifetime retained after logical close");
                MustReject(() => buffer.Sum());
                MustReject(() => buffer.Sum(held: true));
                buffer.Dispose();
                Check(Native.Live() == 1, "second Dispose did not drop the admitted call lease");
            }
            finally { Native.HoldRelease(); }
            Check(running.Wait(TimeSpan.FromSeconds(5)), "old admitted call completed");
            Check(running.GetAwaiter().GetResult() == Expected(), "old call result correct");
            Check(Native.Live() == 0, "last lease reclaimed native allocation");
            MustReject(() => buffer.Sum());
        }
    }
    private static void ExceptionCompensation()
    {
        var buffer = new GatedBuffer(16);
        try
        {
            try { buffer.Sum(injectAfterLease: true); }
            catch (InjectedFailure) { assertions++; }
            Check(Native.Live() == 1, "owner remains after a failed admitted operation");
        }
        finally { buffer.Dispose(); }
        Check(Native.Live() == 0, "finally returned the failed operation lease");
        MustReject(() => buffer.Sum());
    }
    public static int Main(string[] args)
    {
        bool aot = !RuntimeFeature.IsDynamicCodeSupported;
        Check(Array.IndexOf(args, "--expect-aot") < 0 || aot, "actual AOT executable required");
        Check(Native.Live() == 0, "clean initial native count");
        NegativeControl(); Console.WriteLine("PASS negative-control");
        PositiveGate(); Console.WriteLine("PASS logical-gate-64-rounds");
        ExceptionCompensation(); Console.WriteLine("PASS exception-compensation");
        Check(Native.Live() == 0, "no remaining buffers");
        Console.WriteLine($"SUCCESS logical-admission assertions={assertions} aot={aot} gate_rounds=64");
        return 0;
    }
}
