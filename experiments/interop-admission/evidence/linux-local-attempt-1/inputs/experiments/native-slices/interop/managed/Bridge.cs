using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace NativeWeave.Experiments;

[StructLayout(LayoutKind.Sequential)]
public struct AbiInfo
{
    public uint Version, StructSize, PointerSize, MaxBytes;
    public uint SampleSize, SampleAlignment, CountOffset, ValueOffset;
}
[StructLayout(LayoutKind.Sequential)]
public struct SampleLayout { public byte Tag; public uint Count; public ulong Value; }

// Experiment-only imports, not an accepted NativeWeave public ABI.
public static unsafe partial class Native
{
    private const string Library = "nw_interop_probe";
    [LibraryImport(Library, EntryPoint = "nw_abi_info")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial uint Info(out AbiInfo info, nuint size);
    [LibraryImport(Library, EntryPoint = "nw_buffer_new")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial uint Create(nuint count, uint failMode, out nint handle);
    [LibraryImport(Library, EntryPoint = "nw_buffer_drop")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial void Release(nint handle);
    [LibraryImport(Library, EntryPoint = "nw_buffer_sum")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial uint Sum(OwnedBuffer handle, out ulong value);
    [LibraryImport(Library, EntryPoint = "nw_buffer_sum_held")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    internal static partial uint SumHeld(OwnedBuffer handle, out ulong value);
    [LibraryImport(Library, EntryPoint = "nw_live_buffers")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial nuint Live();
    [LibraryImport(Library, EntryPoint = "nw_hold_reset")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial void HoldReset();
    [LibraryImport(Library, EntryPoint = "nw_hold_entered")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial uint HoldEntered();
    [LibraryImport(Library, EntryPoint = "nw_hold_release")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial void HoldRelease();
    [LibraryImport(Library, EntryPoint = "nw_callback_apply")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
    public static partial uint Callback(uint value, nuint context,
        delegate* unmanaged[Cdecl]<uint, nuint, uint> callback, out uint result);
}

public sealed class OwnedBuffer : SafeHandle
{
    private OwnedBuffer() : base(nint.Zero, true) { }
    public override bool IsInvalid => handle == nint.Zero;
    protected override bool ReleaseHandle() { Native.Release(handle); return true; }
    public static OwnedBuffer Create(nuint length, uint failMode = 0)
    {
        // Construct managed owner first. Success publishes one native owner into it.
        var owner = new OwnedBuffer();
        var status = Native.Create(length, failMode, out var raw);
        if (status != 0)
        {
            owner.Dispose();
            if (raw != nint.Zero)
            {
                Native.Release(raw);
                throw new InvalidOperationException("Failure published an unexpected owner");
            }
            throw new NativeStatusException(status);
        }
        if (raw == nint.Zero) { owner.Dispose(); throw new InvalidOperationException("Null success"); }
        owner.SetHandle(raw);
        return owner;
    }
    public ulong Sum()
    {
        var status = Native.Sum(this, out var value);
        if (status != 0) throw new NativeStatusException(status);
        return value;
    }
    public ulong SumHeld()
    {
        var status = Native.SumHeld(this, out var value);
        if (status != 0) throw new NativeStatusException(status);
        return value;
    }
}
public sealed class NativeStatusException(uint status) : Exception($"Native status {status}")
{
    public uint Status { get; } = status;
}
