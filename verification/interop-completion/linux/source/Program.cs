using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Numerics;

internal static unsafe partial class Native
{
    const string Lib = "nw_interop_completion_probe";
    [LibraryImport(Lib, EntryPoint = "nw_ic_create")] internal static partial uint Create(delegate* unmanaged[Cdecl]<nuint, uint, void> callback, nuint cookie, out nint op);
    [LibraryImport(Lib, EntryPoint = "nw_ic_start")] internal static partial uint Start(nint op, uint background);
    [LibraryImport(Lib, EntryPoint = "nw_ic_cancel")] internal static partial uint Cancel(nint op);
    [LibraryImport(Lib, EntryPoint = "nw_ic_try_retire")] internal static partial uint Retire(nint op);
    [LibraryImport(Lib, EntryPoint = "nw_ic_take")] internal static partial uint Take(nint op, out nint result);
    [LibraryImport(Lib, EntryPoint = "nw_ic_duplicate_terminal")] internal static partial uint Duplicate(nint op);
    [LibraryImport(Lib, EntryPoint = "nw_ic_release")] internal static partial uint Release(nint op);
    [LibraryImport(Lib, EntryPoint = "nw_ic_result_value")] internal static partial ulong Value(nint result);
    [LibraryImport(Lib, EntryPoint = "nw_ic_result_release")] internal static partial void ReleaseResult(nint result);
    [LibraryImport(Lib, EntryPoint = "nw_ic_live_operations")] internal static partial nuint LiveOperations();
    [LibraryImport(Lib, EntryPoint = "nw_ic_live_results")] internal static partial nuint LiveResults();
    [LibraryImport(Lib, EntryPoint = "nw_ic_validate_extent")] internal static partial uint Extent(ulong count, ulong width, ulong budget);
}

internal sealed class Context
{
    internal nint Operation;
    internal int Calls, Faults;
    internal uint Status;
    internal bool Hold, Throw;
    internal readonly ManualResetEventSlim Entered = new(), Exit = new();
}

internal static class Program
{
    static int assertions;
    static void Check(bool condition, string name)
    { assertions++; if (!condition) throw new Exception(name); }

    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    static void Callback(nuint cookie, uint status)
    {
        Context? c = null;
        try
        {
            c = (Context)GCHandle.FromIntPtr((nint)cookie).Target!;
            Interlocked.Increment(ref c.Calls); c.Status = status;
            c.Entered.Set();
            // Controlled test barrier only; production callbacks are nonblocking.
            if (c.Hold && !c.Exit.Wait(TimeSpan.FromSeconds(10))) throw new TimeoutException();
            if (c.Throw) throw new InvalidOperationException("injected callback mapping fault");
        }
        catch { if (c is not null) Interlocked.Increment(ref c.Faults); }
    }

    static unsafe (Context c, GCHandle root) Create(bool hold = false, bool fault = false)
    {
        var c = new Context { Hold = hold, Throw = fault };
        var root = GCHandle.Alloc(c);
        Check(Native.Create(&Callback, (nuint)GCHandle.ToIntPtr(root), out c.Operation) == 0, "create");
        return (c, root);
    }
    static void Cleanup(Context c, GCHandle root)
    {
        Check(SpinWait.SpinUntil(() => Native.Retire(c.Operation) == 0, TimeSpan.FromSeconds(10)), "native retirement");
        Check(Native.Release(c.Operation) == 0, "owner release");
        root.Free(); // All managed/native test calls have returned; source permanently retired.
        Check(SpinWait.SpinUntil(() => Native.LiveOperations() == 0, TimeSpan.FromSeconds(10)), "zero live operations");
        c.Entered.Dispose(); c.Exit.Dispose();
    }
    static void Main(string[] args)
    {
        bool aot = !RuntimeFeature.IsDynamicCodeSupported;
        if (args.Contains("--expect-aot")) Check(aot, "actual native aot execution");
        for (int round = 0; round < 32; round++)
        {
            var (c, root) = Create(hold: true);
            Check(Native.Start(c.Operation, 1) == 0, "background accepted");
            Check(c.Entered.Wait(TimeSpan.FromSeconds(10)), "callback entered");
            Check(Native.Retire(c.Operation) == 1, "callback prevents retirement");
            GC.Collect(); GC.WaitForPendingFinalizers();
            Check(root.Target == c, "root retained through callback");
            Check(Native.Cancel(c.Operation) == 0, "late cancel request");
            c.Exit.Set();
            Check(SpinWait.SpinUntil(() => Native.Retire(c.Operation) == 0, TimeSpan.FromSeconds(10)), "quiescent after callback");
            Check(c.Calls == 1 && c.Status == 0, "success terminal not replaced by cancel");
            Check(Native.Duplicate(c.Operation) == 2, "duplicate terminal rejected");
            Check(Native.Take(c.Operation, out nint result) == 0 && result != 0, "take once");
            Check(Native.Take(c.Operation, out nint second) == 2 && second == 0, "second take no owner");
            Cleanup(c, root);
            Check(Native.Value(result) == 42 && Native.LiveResults() == 1, "transferred result outlives operation");
            try { throw new FormatException("injected DTO conversion failure"); }
            catch (FormatException) { }
            finally { Native.ReleaseResult(result); }
            Check(Native.LiveResults() == 0, "conversion fault releases result");
        }
        {
            var (c, root) = Create(fault: true);
            Check(Native.Cancel(c.Operation) == 0, "prestart cancel");
            Check(Native.Start(c.Operation, 0) == 0, "synchronous completion accepted");
            Check(c.Calls == 1 && c.Status == 3 && c.Faults == 1, "cancel terminal and contained callback exception");
            Check(Native.Take(c.Operation, out nint result) == 3 && result == 0, "cancel has no result owner");
            Cleanup(c, root);
        }
        CancellationRegistrationBarrier();
        ExtentProperties();
        Console.WriteLine($"SUCCESS interop-completion assertions={assertions} aot={aot} callback_rounds=32");
    }

    static void CancellationRegistrationBarrier()
    {
        using var already = new CancellationTokenSource(); already.Cancel();
        bool published = false, sawUnpublished = false;
        var r = already.Token.UnsafeRegister(_ => sawUnpublished = !published, null); published = true;
        Check(sawUnpublished, "pre-cancel callback runs before registration publication"); r.Dispose();
        using var source = new CancellationTokenSource();
        using var entered = new ManualResetEventSlim(); using var leave = new ManualResetEventSlim();
        var registration = source.Token.UnsafeRegister(_ => { entered.Set(); leave.Wait(TimeSpan.FromSeconds(10)); }, null);
        var cancel = Task.Run(source.Cancel);
        Check(entered.Wait(TimeSpan.FromSeconds(10)), "managed cancel callback entered");
        var drain = registration.DisposeAsync();
        Check(!drain.IsCompleted, "DisposeAsync waits for active callback");
        leave.Set(); drain.AsTask().GetAwaiter().GetResult(); cancel.GetAwaiter().GetResult();
        Check(drain.IsCompletedSuccessfully, "managed cancellation registration drained");
    }

    static void ExtentProperties()
    {
        ulong seed = 0x4e61746976655765UL;
        ulong Next() { seed = unchecked(seed * 6364136223846793005UL + 1442695040888963407UL); return seed; }
        for (int i=0; i<10000; i++)
        {
            ulong count = i%2==0 ? Next() : Next()%1024;
            ulong width = i%3==0 ? Next() : Next()%17;
            ulong budget = Next();
            BigInteger exact = (BigInteger)count * width;
            bool expected = width != 0 && exact <= budget && exact <= long.MaxValue;
            Check((Native.Extent(count,width,budget)==0)==expected,"BigInteger extent differential");
        }
        Check(Native.Extent(0,1,0)==0,"empty extent");
        Check(Native.Extent(ulong.MaxValue,2,ulong.MaxValue)==2,"u64 multiplication overflow");
        Check(Native.Extent(1UL<<63,1,ulong.MaxValue)==2,"isize bound");
        Check(Native.Extent(1,0,10)==2,"zero element width rejected");
    }
}
