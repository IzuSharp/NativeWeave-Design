// Design-only package-flow experiment. This is not the NativeWeave model generator.
using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Text;

[Generator(LanguageNames.CSharp)]
public sealed class ProbeGenerator : IIncrementalGenerator
{
    private static readonly DiagnosticDescriptor Unsupported = new(
        "NWPKGPROBE001", "Unsupported probe shape",
        "The package probe cannot encode '{0}': {1}", "NativeWeave.Design.Probe",
        DiagnosticSeverity.Error, true);

    // Small value-only input: symbols/Compilation/SyntaxNode are not retained in the pipeline.
    private sealed record Shape(string Identity, string Kind, string Fields, string? Error);

    public void Initialize(IncrementalGeneratorInitializationContext context)
    {
        var entities = Find(context, "NativeWeave.Design.Probe.ProbeEntityAttribute", "entity");
        var dtos = Find(context, "NativeWeave.Design.Probe.ProbeDtoAttribute", "dto");
        var handlers = Find(context, "NativeWeave.Design.Probe.ProbeHandlerAttribute", "handler");
        context.RegisterSourceOutput(entities.Collect().Combine(dtos.Collect()).Combine(handlers.Collect()),
            static (output, values) => Emit(output, values.Left.Left.Concat(values.Left.Right).Concat(values.Right)));
    }

    private static IncrementalValuesProvider<Shape> Find(
        IncrementalGeneratorInitializationContext context, string attribute, string kind)
        => context.SyntaxProvider.ForAttributeWithMetadataName(attribute,
            static (syntax, _) => syntax is TypeDeclarationSyntax || syntax is MethodDeclarationSyntax,
            (ctx, token) =>
            {
                token.ThrowIfCancellationRequested();
                var symbol = ctx.TargetSymbol;
                string identity = symbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
                if (symbol is INamedTypeSymbol type)
                {
                    if (type.TypeParameters.Length != 0)
                        return new Shape(identity, kind, "", "open generic model");
                    var properties = type.GetMembers().OfType<IPropertySymbol>()
                        .Where(p => !p.IsStatic && p.DeclaredAccessibility == Accessibility.Public)
                        .OrderBy(p => p.Name, StringComparer.Ordinal).ToArray();
                    foreach (var property in properties)
                    {
                        token.ThrowIfCancellationRequested();
                        if (property.IsIndexer || !Scalar(property.Type))
                            return new Shape(identity, kind, "", "unsupported property " + property.Name);
                    }
                    return new Shape(identity, kind, string.Join(";", properties.Select(p =>
                        p.Name + ":" + p.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)
                        + ":nullable=" + p.NullableAnnotation)), null);
                }
                if (symbol is IMethodSymbol method && method.IsStatic && method.TypeParameters.Length == 0
                    && Scalar(method.ReturnType) && method.Parameters.All(p => p.RefKind == RefKind.None && Scalar(p.Type)))
                    return new Shape(identity, kind, string.Join(";", method.Parameters.Select(p =>
                        p.Name + ":" + p.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)))
                        + "->" + method.ReturnType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), null);
                return new Shape(identity, kind, "", "expected a scalar static handler");
            });

    private static bool Scalar(ITypeSymbol type)
    {
        if (type is INamedTypeSymbol named && named.OriginalDefinition.SpecialType == SpecialType.System_Nullable_T)
            return Scalar(named.TypeArguments[0]);
        return type.SpecialType is SpecialType.System_String or SpecialType.System_Int32
            or SpecialType.System_Int64 or SpecialType.System_Boolean or SpecialType.System_Decimal;
    }

    private static void Emit(SourceProductionContext output, IEnumerable<Shape> inputs)
    {
        var shapes = inputs.OrderBy(s => s.Identity, StringComparer.Ordinal).ThenBy(s => s.Kind, StringComparer.Ordinal).ToArray();
        foreach (var shape in shapes)
        {
            output.CancellationToken.ThrowIfCancellationRequested();
            if (shape.Error is not null)
                output.ReportDiagnostic(Diagnostic.Create(Unsupported, Location.None, shape.Identity, shape.Error));
        }
        if (shapes.Any(s => s.Error is not null)) return;
        string canonical = string.Join("\n", shapes.Select(s => s.Kind + "|" + s.Identity + "|" + s.Fields));
        string fingerprint = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonical))).ToLowerInvariant();
        string text = "// Design package probe: static metadata only, no product ORM/handler implementation.\n"
            + "namespace NativeWeave.Design.Probe.Generated;\n"
            + "public static class ProbeRegistry { public const int ShapeCount = " + shapes.Length
            + "; public const string Fingerprint = \"" + fingerprint + "\"; }\n";
        output.AddSource("NativeWeave.Design.Probe.Registry.g.cs", SourceText.From(text, Encoding.UTF8));
    }
}
