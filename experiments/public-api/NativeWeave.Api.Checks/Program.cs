using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

if (args.Length != 3) throw new ArgumentException("Usage: checks <declarations> <dotnet-root> <output-json>");
string source = Path.GetFullPath(args[0]);
var options = new CSharpParseOptions(LanguageVersion.CSharp15, DocumentationMode.Parse);
var declarations = Directory.GetFiles(source, "*.cs", SearchOption.TopDirectoryOnly)
    .OrderBy(x => x, StringComparer.Ordinal)
    .Select(x => CSharpSyntaxTree.ParseText(File.ReadAllText(x), options, path: x)).ToArray();
var references = new Dictionary<string, MetadataReference>(StringComparer.OrdinalIgnoreCase);
foreach (string pack in new[] { "Microsoft.NETCore.App.Ref", "Microsoft.AspNetCore.App.Ref" })
    foreach (string file in Directory.GetFiles(Path.Combine(args[1], "packs", pack, "11.0.0", "ref", "net11.0"), "*.dll"))
        references.TryAdd(Path.GetFileName(file), MetadataReference.CreateFromFile(file));
var compilationOptions = new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary,
    nullableContextOptions: NullableContextOptions.Enable, allowUnsafe: true);
var baseCompilation = CSharpCompilation.Create("NativeWeave.Design.NegativeConsumers", declarations,
    references.Values, compilationOptions);
var baselineErrors = baseCompilation.GetDiagnostics().Where(x => x.Severity == DiagnosticSeverity.Error).ToArray();
if (baselineErrors.Length != 0) throw new InvalidOperationException(string.Join("\n", baselineErrors.Select(x => x.ToString())));
const string imports = "#nullable enable\nusing System; using System.Threading; using System.Threading.Tasks; using NativeWeave.Data; using NativeWeave.Database; using NativeWeave.Query; using NativeWeave.Server; using NativeWeave.Interop;\nsealed class Student { } sealed class Enrollment { }\n";
var cases = new (string Id, string Code, string[] Expected)[] {
    ("typed-column-value", "static class Case { static void Check(Column<Student,int> age) { new Changes<Student>().Set(age, \"eighteen\"); } }", new[] { "CS0411", "CS1503" }),
    ("entity-column-owner", "static class Case { static void Check(Column<Enrollment,int> credits) { new Changes<Student>().Set(credits, 1); } }", new[] { "CS0411", "CS1503" }),
    ("nullable-reference", "static class Case { static void Check(Column<Student,string> name) { new Changes<Student>().Set<string>(name, null); } }", new[] { "CS8625" }),
    ("aggregate-scalar-type", "static class Case { static void Check(SqlExpression<string> text) { _ = SqlFunctions.Sum(text); } }", new[] { "CS1503" }),
    ("nullable-lift-reverse", "static class Case { static void Check(SqlExpression<long> value) { SqlExpression<long> narrowed = value.AsNullable(); } }", new[] { "CS0029" }),
    ("nullable-lift-repeat", "static class Case { static void Check(SqlExpression<long> value) { _ = value.AsNullable().AsNullable(); } }", new[] { "CS0453" }),
    ("handler-return-type", "static class Case { static void Check(NativeServerApplication app) { app.MapGet(\"/\", static () => 42); } }", new[] { "CS0029", "CS1662", "CS1503" }),
    ("span-capture", "static class Case { static Func<int> Check(ReadOnlySpan<byte> span) => () => span.Length; }", new[] { "CS9108", "CS8175" }),
    ("resource-not-copyable-value", "static class Case { static void Value<T>(T value) where T : struct { } static void Check(NativeBuffer buffer) { Value(buffer); } }", new[] { "CS0453" })
};
var results = new List<object>();
foreach (var test in cases)
{
    var tree = CSharpSyntaxTree.ParseText(imports + test.Code, options, path: test.Id + ".cs");
    var diagnostics = baseCompilation.AddSyntaxTrees(tree).GetDiagnostics()
        .Where(x => x.Location.SourceTree == tree && x.Severity is DiagnosticSeverity.Error or DiagnosticSeverity.Warning).ToArray();
    bool passed = diagnostics.Any(x => test.Expected.Contains(x.Id, StringComparer.Ordinal));
    results.Add(new { id = test.Id, passed, expected_diagnostic_ids = test.Expected,
        diagnostics = diagnostics.Select(x => new { id = x.Id, severity = x.Severity.ToString(), message = x.GetMessage() }).ToArray() });
    if (!passed) throw new InvalidOperationException(test.Id + " did not produce its expected diagnostic: " + string.Join("\n", diagnostics.Select(x => x.ToString())));
}
File.WriteAllText(args[2], JsonSerializer.Serialize(new { scope = "design-only negative consumer compilation", sdk = "11.0.100", language = "15.0", passed = true, product_execution = false, cases = results }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"Passed {results.Count} negative consumer cases; no product execution claimed.");
