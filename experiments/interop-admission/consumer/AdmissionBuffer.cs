using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using NativeWeave.Experiments;

namespace NativeWeave.Research.Admission;

// R07/D04 research candidate. No product API, async retirement or accepted contract.
internal sealed partial class AdmissionBuffer : IDisposable
{
    private readonly object _admission = new();
    private readonly OwnedBuffer _owner;
    private bool _closing;

    internal AdmissionBuffer(nuint length) => _owner = OwnedBuffer.Create(length);
    internal bool PhysicalOwnerClosed => _owner.IsClosed; // Observation only; not admission.
    internal ulong Sum() => Invoke(held: false);
    internal ulong SumHeld() => Invoke(held: true);

    private ulong Invoke(bool held)
    {
        bool lease = false;
        try
        {
            nint pointer;
            lock (_admission)
            {
                ObjectDisposedException.ThrowIf(_closing, this);
                _owner.DangerousAddRef(ref lease);
                pointer = _owner.DangerousGetHandle();
            }
            // Both FFI entry points accept raw pointers only after obtaining the lease.
            uint status = held ? Raw.SumHeld(pointer, out ulong value)
                               : Raw.Sum(pointer, out value);
            if (status != 0) throw new NativeStatusException(status);
            return value;
        }
        finally
        {
            if (lease) _owner.DangerousRelease();
        }
    }

    public void Dispose()
    {
        lock (_admission)
        {
            if (_closing) return;
            _closing = true; // Linearization point: later business admission must fail.
        }
        // Never release a native owner, wait, or call user code under the admission gate.
        _owner.Dispose();
    }

    private static partial class Raw
    {
        [LibraryImport("nw_interop_probe", EntryPoint = "nw_buffer_sum")]
        [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
        internal static partial uint Sum(nint pointer, out ulong value);

        [LibraryImport("nw_interop_probe", EntryPoint = "nw_buffer_sum_held")]
        [UnmanagedCallConv(CallConvs = new[] { typeof(CallConvCdecl) })]
        internal static partial uint SumHeld(nint pointer, out ulong value);
    }
}
