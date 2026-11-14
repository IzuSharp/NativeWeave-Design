using System.Text.Json;

// This executable never claims to query a database, serve HTTP or load Rust.
// TrimmerRootAssembly roots the declaration assembly for the AOT compile check.
Console.WriteLine("NativeWeave public API design consumer compiled and executed; product operations are unimplemented.");
Console.WriteLine(JsonSerializer.Serialize(new ProbeEvidence("design-only", 11), EvidenceJsonContext.Default.ProbeEvidence));

internal sealed record ProbeEvidence(string Scope, int RuntimeMajor);

[System.Text.Json.Serialization.JsonSerializable(typeof(ProbeEvidence))]
internal partial class EvidenceJsonContext : System.Text.Json.Serialization.JsonSerializerContext;
