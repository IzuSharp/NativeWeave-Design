using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace NativeWeave.Research;
public static partial class Codec
{
    [StructLayout(LayoutKind.Sequential)]
    private unsafe struct NativeBuffer { public nint Owner; public byte* Data; public nuint Length; }
    [LibraryImport("nw_codec_research", EntryPoint = "nw_codec_run")]
    private static unsafe partial uint Run(byte* data, nuint length, uint mode, out NativeBuffer output);
    [LibraryImport("nw_codec_research", EntryPoint = "nw_codec_release")]
    private static partial void Release(nint owner);
    private sealed class Owner : SafeHandleZeroOrMinusOneIsInvalid
    {
        internal Owner(nint value) : base(true) => SetHandle(value);
        protected override bool ReleaseHandle() { Release(handle); return true; }
    }
    public static byte[] Compress(ReadOnlySpan<byte> input) => Transform(input, 0);
    public static byte[] Decompress(ReadOnlySpan<byte> input) => Transform(input, 1);
    private static unsafe byte[] Transform(ReadOnlySpan<byte> input, uint mode)
    {
        NativeBuffer output;
        uint status;
        fixed (byte* p = input) status = Run(p, (nuint)input.Length, mode, out output);
        if (status != 0) throw new InvalidDataException($"Native codec rejected input: {status}");
        using var owner = new Owner(output.Owner);
        bool leased = false;
        try
        {
            owner.DangerousAddRef(ref leased);
            return new ReadOnlySpan<byte>(output.Data, checked((int)output.Length)).ToArray();
        }
        finally { if (leased) owner.DangerousRelease(); }
    }
}
