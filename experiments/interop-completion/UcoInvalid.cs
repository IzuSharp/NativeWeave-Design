using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

// Deliberately invalid under enabled runtime marshalling. Never a product callback.
internal static unsafe partial class Program
{
    [LibraryImport("nw_uco_invalid", EntryPoint = "nw_uc_invoke")]
    private static partial int Invoke(nint callback);

    [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
    private static bool Invalid(char input)
    {
        Console.WriteLine("INVALID_CALLBACK_BODY_ENTERED");
        return input == 'x';
    }

    private static int Main()
    {
        Console.WriteLine("CALLING_INVALID_UCO");
        return Invoke((nint)(delegate* unmanaged[Cdecl]<char, bool>)&Invalid);
    }
}
