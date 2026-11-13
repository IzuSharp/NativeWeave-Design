using System.Collections.Immutable;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

// This fixture studies Roslyn behaviour; it is not the product generator.
[Generator]
sealed class DescriptorGenerator : IIncrementalGenerator
{
    public void Initialize(IncrementalGeneratorInitializationContext context)
    {
        var models = context.SyntaxProvider.ForAttributeWithMetadataName("NativeModelAttribute",
            static (node, _) => node is ClassDeclarationSyntax,
            static (ctx, _) =>
            {
                var symbol = (INamedTypeSymbol)ctx.TargetSymbol;
                var fields = symbol.GetMembers().OfType<IPropertySymbol>()
                    .Where(x => !x.IsStatic).OrderBy(x => x.Name, StringComparer.Ordinal)
                    .Select(x => x.Name + ":" + x.Type.ToDisplayString());
                // Only value-equatable strings cross the semantic transform boundary.
                return (Name: symbol.Name, Shape: string.Join(";", fields));
            }).WithTrackingName("Model");
        context.RegisterSourceOutput(models, static (spc, m) =>
        {
            if (m.Shape.Contains("System.Action", StringComparison.Ordinal))
                spc.ReportDiagnostic(Diagnostic.Create(new DiagnosticDescriptor("NWPROBE001",
                    "Unsupported model", "Model '{0}' contains a delegate", "NativeWeaveResearch",
                    DiagnosticSeverity.Error, true), Location.None, m.Name));
            else
                spc.AddSource(m.Name+".native.g.cs", "internal static class "+m.Name+
                    "Descriptor { internal const string Shape = \""+m.Shape+"\"; }");
        });
    }
}

[Generator] sealed class ProducesType : IIncrementalGenerator
{
    public void Initialize(IncrementalGeneratorInitializationContext context) =>
        context.RegisterSourceOutput(context.CompilationProvider,
            static (spc, _) => spc.AddSource("produced.g.cs", "internal sealed class ProducedByPeer {}"));
}
[Generator] sealed class ObservesType : IIncrementalGenerator
{
    public void Initialize(IncrementalGeneratorInitializationContext context) =>
        context.RegisterSourceOutput(context.CompilationProvider.Select(static (c,_) => c.GetTypeByMetadataName("ProducedByPeer") is not null),
            static (spc, found) => spc.AddSource("observation.g.cs", "internal static class PeerObservation { internal const bool Seen = "+found.ToString().ToLowerInvariant()+"; }"));
}

static class GeneratorProbe
{
    static int checks;
    static void Check(bool condition, string name) { checks++; if (!condition) throw new Exception(name); }
    static readonly CSharpParseOptions Parse = new(LanguageVersion.Latest);
    static SyntaxTree Tree(string source) => CSharpSyntaxTree.ParseText(source, Parse);
    static void Main()
    {
        var references = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator)
            .Select(x => MetadataReference.CreateFromFile(x));
        var a=Tree("[NativeModel] public class A { public int Id {get;set;} }");
        var b=Tree("[NativeModel] public class B { public string Name {get;set;} = \"\"; }");
        var c=CSharpCompilation.Create("Probe", new[]{Tree("public sealed class NativeModelAttribute:System.Attribute {}"),a,b},references,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        GeneratorDriver driver=CSharpGeneratorDriver.Create(new[]{new DescriptorGenerator().AsSourceGenerator()},parseOptions:Parse,
            driverOptions:new GeneratorDriverOptions(IncrementalGeneratorOutputKind.None,trackIncrementalGeneratorSteps:true));
        driver=driver.RunGeneratorsAndUpdateCompilation(c,out var generated,out var diagnostics);
        Check(!diagnostics.Any(x=>x.Severity==DiagnosticSeverity.Error),"initial generator diagnostics");
        Check(!generated.GetDiagnostics().Any(x=>x.Severity==DiagnosticSeverity.Error),"generated sources compile");
        var first=driver.GetRunResult().GeneratedTrees.ToDictionary(x=>Path.GetFileName(x.FilePath),x=>x.ToString());
        Check(first.Count==2,"one descriptor per model");
        driver=driver.RunGeneratorsAndUpdateCompilation(c,out _,out _);
        var same=driver.GetRunResult();
        Check(same.Results.Single().TrackedSteps["Model"].SelectMany(x=>x.Outputs).All(x=>x.Reason==IncrementalStepRunReason.Cached),"unchanged models cached");
        var a2=Tree("[NativeModel] public class A { public long Id {get;set;} }");
        var changed=c.ReplaceSyntaxTree(a,a2);
        driver=driver.RunGeneratorsAndUpdateCompilation(changed,out generated,out _);
        var next=driver.GetRunResult().GeneratedTrees.ToDictionary(x=>Path.GetFileName(x.FilePath),x=>x.ToString());
        Check(first["A.native.g.cs"]!=next["A.native.g.cs"],"changed model changes descriptor");
        Check(first["B.native.g.cs"]==next["B.native.g.cs"],"unrelated descriptor unchanged");
        Check(!generated.GetDiagnostics().Any(x=>x.Severity==DiagnosticSeverity.Error),"changed generated sources compile");
        var invalid=changed.ReplaceSyntaxTree(a2,Tree("[NativeModel] public class A { public System.Action Callback {get;set;} = null!; }"));
        driver=driver.RunGeneratorsAndUpdateCompilation(invalid,out _,out diagnostics);
        Check(diagnostics.Any(x=>x.Id=="NWPROBE001"),"unsupported delegate diagnostic");
        var peers=CSharpGeneratorDriver.Create(new[]{new ProducesType().AsSourceGenerator(),new ObservesType().AsSourceGenerator()},parseOptions:Parse)
            .RunGeneratorsAndUpdateCompilation(c,out _,out _);
        Check(peers.GetRunResult().GeneratedTrees.Single(x=>x.FilePath.EndsWith("observation.g.cs")).ToString().Contains("Seen = false"),"peer generated type unavailable in same pass");
        Console.WriteLine($"SUCCESS generator-probe assertions={checks} compiler={typeof(CSharpCompilation).Assembly.GetName().Version}");
    }
}
