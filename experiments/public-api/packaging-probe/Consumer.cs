using NativeWeave.Design.Probe;
using NativeWeave.Design.Probe.Generated;
using NativeWeave.Research;
using System.Runtime.CompilerServices;

byte[] input = "NativeWeave package-flow probe"u8.ToArray();
if (!Codec.Decompress(Codec.Compress(input)).AsSpan().SequenceEqual(input))
    throw new Exception("The inherited precompiled codec did not round-trip.");
int expectedCount = int.Parse(args[0], System.Globalization.CultureInfo.InvariantCulture);
if (ProbeRegistry.ShapeCount != expectedCount)
    throw new Exception("Transitive model/DTO/handler generator was not applied.");
if (args.Contains("--aot") && RuntimeFeature.IsDynamicCodeSupported)
    throw new Exception("The Native AOT check was invoked on a JIT executable.");
Console.WriteLine($"shape_count={ProbeRegistry.ShapeCount} fingerprint={ProbeRegistry.Fingerprint} native_roundtrip=true aot={!RuntimeFeature.IsDynamicCodeSupported}");

namespace Example
{
    [ProbeEntity]
    public sealed class User
    {
        public long Id { get; init; }
        public string? Name { get; init; }
    }

    [ProbeDto]
    public sealed class UserSummary
    {
        public long Id { get; init; }
        public string? Name { get; init; }
    }

    public static class Handlers
    {
        [ProbeHandler]
        public static string Greeting(long id) => $"user {id}";
    }
}
