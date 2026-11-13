using System;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading;
using NativeWeave.Experiments;
using NativeWeave.Research.Admission;

internal static class Program
{
    private const int Rounds = 32;
    private static int _assertions;
    private static int _negativeAccepted;
    private static int _candidateRejected;
    private static string _case = "process";
    private static int _round = -1;

    private static void Check(string id, bool condition, object expected, object actual)
    {
        _assertions++;
        Console.WriteLine($"ASSERT case={_case} round={_round} id={id} pass={condition} expected={expected} actual={actual}");
        if (!condition) throw new InvalidOperationException($"{_case}/{_round}/{id}: expected {expected}, actual {actual}");
    }

    private static ulong Expected(nuint length)
    {
        ulong total = 0;
        for (nuint i = 0; i < length; i++) total += (ulong)(i % 251);
        return total;
    }

    private static void Race(bool candidate, int round)
    {
        _case = candidate ? "admission_gate" : "safehandle_only_negative_control";
        _round = round;
        Check("initial_live_zero", Native.Live() == 0, 0, Native.Live());
        Native.HoldReset();
        nuint length = (nuint)(257 + round);
        ulong expected = Expected(length);
        using OwnedBuffer? simple = candidate ? null : OwnedBuffer.Create(length);
        using AdmissionBuffer? gated = candidate ? new AdmissionBuffer(length) : null;
        Func<ulong> held = candidate ? gated!.SumHeld : simple!.SumHeld;
        Func<ulong> sum = candidate ? gated!.Sum : simple!.Sum;
        Action dispose = candidate ? gated!.Dispose : simple!.Dispose;
        Func<bool> physicallyClosed = candidate ? () => gated!.PhysicalOwnerClosed : () => simple!.IsClosed;
        ulong oldValue = 0;
        Exception? oldError = null;
        var worker = new Thread(() =>
        {
            try { oldValue = held(); }
            catch (Exception error) { oldError = error; }
        }) { IsBackground = true, Name = "native-held-call" };
        worker.Start();
        try
        {
            bool entered = SpinWait.SpinUntil(() => Native.HoldEntered() == 1, TimeSpan.FromSeconds(5));
            Check("native_call_entered", entered, true, entered);
            Check("held_call_alive_before_dispose", worker.IsAlive, true, worker.IsAlive);
            Check("owner_live_before_dispose", Native.Live() == 1, 1, Native.Live());
            // This controller thread serializes Dispose and the subsequent new call,
            // while the other thread remains blocked inside the real Rust function.
            dispose();
            dispose(); // Idempotence while the physical call lease still exists.
            Check("held_call_alive_after_dispose", worker.IsAlive, true, worker.IsAlive);
            Check("physical_owner_not_closed_yet", !physicallyClosed(), false, physicallyClosed());
            Check("lease_keeps_native_owner_live", Native.Live() == 1, 1, Native.Live());
            bool rejected = false;
            ulong newValue = 0;
            try { newValue = sum(); }
            catch (ObjectDisposedException) { rejected = true; }
            if (candidate)
            {
                Check("new_call_rejected_after_closing", rejected, true, rejected);
                _candidateRejected++;
            }
            else
            {
                Check("negative_new_call_is_still_admitted", !rejected, false, rejected);
                Check("negative_new_call_really_reads_native", newValue == expected, expected, newValue);
                _negativeAccepted++;
            }
            Check("new_call_does_not_release_held_owner", Native.Live() == 1, 1, Native.Live());
        }
        finally
        {
            Native.HoldRelease();
            if (!worker.Join(TimeSpan.FromSeconds(5)))
                throw new TimeoutException("Held native call did not leave after release; no success can be recorded.");
        }
        Check("admitted_old_call_has_no_error", oldError is null, "none", oldError?.GetType().Name ?? "none");
        Check("admitted_old_call_completes", oldValue == expected, expected, oldValue);
        Check("physical_owner_closed_after_lease", physicallyClosed(), true, physicallyClosed());
        Check("native_live_zero_after_drain", Native.Live() == 0, 0, Native.Live());
        dispose();
        Check("repeat_dispose_after_drain", Native.Live() == 0, 0, Native.Live());
        Console.WriteLine($"ROUND case={_case} round={round} length={length} expected_sum={expected} pass=True");
    }

    private static int Main(string[] args)
    {
        try
        {
            bool expectAot = Array.IndexOf(args, "--expect-aot") >= 0;
            bool aot = !RuntimeFeature.IsDynamicCodeSupported && !RuntimeFeature.IsDynamicCodeCompiled;
            Console.WriteLine($"ENV runtime={RuntimeInformation.FrameworkDescription} os={RuntimeInformation.OSDescription} arch={RuntimeInformation.ProcessArchitecture} aot={aot}");
            if (expectAot) Check("native_aot_execution", aot, true, aot);
            for (int round = 0; round < Rounds; round++) Race(candidate: false, round);
            for (int round = 0; round < Rounds; round++) Race(candidate: true, round);
            _case = "summary"; _round = -1;
            Check("negative_rounds_observed", _negativeAccepted == Rounds, Rounds, _negativeAccepted);
            Check("candidate_rounds_observed", _candidateRejected == Rounds, Rounds, _candidateRejected);
            Check("final_live_zero", Native.Live() == 0, 0, Native.Live());
            Console.WriteLine($"SUCCESS assertions={_assertions} negative_rounds={_negativeAccepted} candidate_rounds={_candidateRejected} live={Native.Live()} aot={aot}");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            Console.Error.WriteLine($"FAILED assertions={_assertions} negative_rounds={_negativeAccepted} candidate_rounds={_candidateRejected}");
            return 1;
        }
    }
}
