using System.Diagnostics.CodeAnalysis;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Serialization;

public sealed record Record(int Id, string Name);
[JsonSerializable(typeof(Record))]
internal partial class Metadata : JsonSerializerContext { }
internal static class AotRestrictions
{
    static int checks;
    static void Check(bool condition, string label) { checks++; if (!condition) throw new Exception(label); }
    static T Identity<T>(T value) => value;
    // This function is an intentional isolated negative test, not a product suppression.
    // The runtime assertion verifies the forbidden operation fails on the published executable.
    [UnconditionalSuppressMessage("Aot", "IL3050", Justification = "Intentional negative test of dynamic code rejection")]
    static void RejectDynamicCode()
    {
        if (RuntimeFeature.IsDynamicCodeSupported) return;
        try { _ = new DynamicMethod("NoDynamicCode", typeof(void), Type.EmptyTypes); }
        catch (PlatformNotSupportedException) { checks++; return; }
        throw new Exception("DynamicMethod unexpectedly supported");
    }
    static void Main(string[] args)
    {
        bool aot = !RuntimeFeature.IsDynamicCodeSupported;
        if (args.Contains("--expect-aot")) Check(aot,"native executable");
        var source = new Record(7,"μ");
        string json = JsonSerializer.Serialize(source,Metadata.Default.Record);
        Check(JsonSerializer.Deserialize(json,Metadata.Default.Record)==source,"static JSON roundtrip");
        Check(Identity(42)==42 && Identity("typed")=="typed","closed generic instantiations");
        Check(!JsonSerializer.IsReflectionEnabledByDefault,"reflection serializer disabled");
        try { _=JsonSerializer.Serialize<object>(new Version(1,2)); }
        catch (InvalidOperationException) { checks++; goto ReflectionRejected; }
        throw new Exception("reflection JSON unexpectedly succeeded");
    ReflectionRejected:
        RejectDynamicCode();
        Console.WriteLine($"SUCCESS aot-restrictions assertions={checks} aot={aot}");
    }
}
