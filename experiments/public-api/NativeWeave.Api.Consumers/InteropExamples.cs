// Compile-only consumption examples; these are not released NativeWeave APIs.
#nullable enable
using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using NativeWeave.Interop;

internal static class InteropExamples
{
    internal static int ReadAndCopy(NativeBuffer result, Span<byte> destination)
    {
        using (result)
        {
            int size = result.Read(static bytes => bytes.Length);
            if (!result.TryCopyTo(destination)) throw new ArgumentException("Destination is too short.");
            return size;
        }
    }

    internal static async Task ExportAsync(NativeBuffer result, Stream output, CancellationToken cancellationToken)
    {
        using (result)
            await result.CopyToAsync(output, cancellationToken);
    }

    internal static EngineInfo Preflight(EngineDescriptor descriptor)
    {
        // Optional advanced preflight; ordinary database/server factories do this themselves.
        var catalog = new EngineCatalog([descriptor]);
        if (!catalog.TryGet(descriptor.EngineId, out var found))
            throw new InvalidOperationException("Explicit descriptor is missing.");
        return found.Inspect();
    }
}
