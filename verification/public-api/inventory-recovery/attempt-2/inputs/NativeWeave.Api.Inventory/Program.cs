using System.Collections.Immutable;
using System.Globalization;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

if (args.Length != 3)
    throw new ArgumentException("Usage: inventory <design-source-directory> <dotnet-root> <output-directory>");
string source = Path.GetFullPath(args[0]);
string runtimeRoot = Path.GetFullPath(args[1]);
string output = Path.GetFullPath(args[2]);
Directory.CreateDirectory(output);
var policies = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
foreach (string domain in new[] { "database", "server", "interop" })
{
    using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, domain + "-symbol-policies.json")));
    foreach (var entry in document.RootElement.GetProperty("types").EnumerateObject())
        if (!policies.TryAdd(entry.Name, entry.Value.Clone()))
            throw new InvalidOperationException("Duplicate semantic type policy: " + entry.Name);
}
var documentedIds = new HashSet<string>(StringComparer.Ordinal);
var sourceFiles = Directory.GetFiles(source, "*.cs", SearchOption.AllDirectories)
    .Where(x => !x.Split(Path.DirectorySeparatorChar).Any(p => p is "obj" or "bin"))
    .OrderBy(x => x, StringComparer.Ordinal).ToArray();
var trees = sourceFiles.Select(x => CSharpSyntaxTree.ParseText(File.ReadAllText(x),
    new CSharpParseOptions(LanguageVersion.CSharp15, DocumentationMode.Parse), path: x)).ToArray();
var referenceFiles = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
foreach (string pack in new[] { "Microsoft.NETCore.App.Ref", "Microsoft.AspNetCore.App.Ref" })
{
    string path = Path.Combine(runtimeRoot, "packs", pack, "11.0.0", "ref", "net11.0");
    foreach (string file in Directory.GetFiles(path, "*.dll"))
        referenceFiles.TryAdd(Path.GetFileName(file), file);
}
var compilation = CSharpCompilation.Create("NativeWeave.Api.Design.Inventory", trees,
    referenceFiles.Values.Select(x => MetadataReference.CreateFromFile(x)),
    new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, nullableContextOptions: NullableContextOptions.Enable, allowUnsafe: true));
var failures = compilation.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).ToArray();
if (failures.Length != 0)
    throw new InvalidOperationException(string.Join(Environment.NewLine, failures.Select(x => x.ToString())));

// A type used in a signature is not a type declaration. In particular, base types,
// interfaces and return types must not acquire "class", variance or constraints.
var typeFormat = new SymbolDisplayFormat(
    globalNamespaceStyle: SymbolDisplayGlobalNamespaceStyle.Omitted,
    typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameAndContainingTypesAndNamespaces,
    genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters,
    miscellaneousOptions: SymbolDisplayMiscellaneousOptions.IncludeNullableReferenceTypeModifier | SymbolDisplayMiscellaneousOptions.UseSpecialTypes | SymbolDisplayMiscellaneousOptions.EscapeKeywordIdentifiers);
var typeNameFormat = typeFormat.WithGenericsOptions(SymbolDisplayGenericsOptions.IncludeTypeParameters | SymbolDisplayGenericsOptions.IncludeVariance);
var format = new SymbolDisplayFormat(
    globalNamespaceStyle: SymbolDisplayGlobalNamespaceStyle.Omitted,
    typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameAndContainingTypesAndNamespaces,
    genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters | SymbolDisplayGenericsOptions.IncludeTypeConstraints | SymbolDisplayGenericsOptions.IncludeVariance,
    memberOptions: SymbolDisplayMemberOptions.IncludeAccessibility | SymbolDisplayMemberOptions.IncludeModifiers | SymbolDisplayMemberOptions.IncludeContainingType | SymbolDisplayMemberOptions.IncludeType | SymbolDisplayMemberOptions.IncludeParameters | SymbolDisplayMemberOptions.IncludeExplicitInterface | SymbolDisplayMemberOptions.IncludeConstantValue | SymbolDisplayMemberOptions.IncludeRef,
    parameterOptions: SymbolDisplayParameterOptions.IncludeType | SymbolDisplayParameterOptions.IncludeName | SymbolDisplayParameterOptions.IncludeDefaultValue | SymbolDisplayParameterOptions.IncludeParamsRefOut | SymbolDisplayParameterOptions.IncludeExtensionThis,
    propertyStyle: SymbolDisplayPropertyStyle.ShowReadWriteDescriptor,
    kindOptions: SymbolDisplayKindOptions.IncludeTypeKeyword | SymbolDisplayKindOptions.IncludeMemberKeyword,
    miscellaneousOptions: SymbolDisplayMiscellaneousOptions.IncludeNullableReferenceTypeModifier | SymbolDisplayMiscellaneousOptions.UseSpecialTypes | SymbolDisplayMiscellaneousOptions.EscapeKeywordIdentifiers);
string TypeName(ITypeSymbol type) => type.ToDisplayString(typeFormat);
string[] Attributes(ImmutableArray<AttributeData> attributes) => attributes
    .Select(a => a.ToString() ?? throw new InvalidOperationException("Missing attribute display"))
    .OrderBy(x => x, StringComparer.Ordinal).ToArray();
string InlineAttributes(ImmutableArray<AttributeData> attributes) => string.Concat(Attributes(attributes).Select(a => "[" + a + "] "));
ImmutableArray<IParameterSymbol> Parameters(ISymbol symbol) => symbol switch {
    IMethodSymbol method => method.Parameters,
    IPropertySymbol property => property.Parameters,
    INamedTypeSymbol { DelegateInvokeMethod: { } invoke } => invoke.Parameters,
    _ => ImmutableArray<IParameterSymbol>.Empty
};
ImmutableArray<ITypeParameterSymbol> TypeParameters(ISymbol symbol) => symbol switch {
    IMethodSymbol method => method.TypeParameters,
    INamedTypeSymbol type => type.TypeParameters,
    _ => ImmutableArray<ITypeParameterSymbol>.Empty
};
ImmutableArray<AttributeData> ReturnAttributes(ISymbol symbol) => symbol switch {
    IMethodSymbol method => method.GetReturnTypeAttributes(),
    IPropertySymbol { GetMethod: { } getter } => getter.GetReturnTypeAttributes(),
    INamedTypeSymbol { DelegateInvokeMethod: { } invoke } => invoke.GetReturnTypeAttributes(),
    _ => ImmutableArray<AttributeData>.Empty
};
string[] ConstraintTypes(ITypeParameterSymbol parameter) => parameter.ConstraintTypes
    .Select((type, index) => TypeName(type.WithNullableAnnotation(parameter.ConstraintNullableAnnotations[index]))).ToArray();
string ConstraintClause(ITypeParameterSymbol parameter)
{
    var constraints = new List<string>();
    if (parameter.HasUnmanagedTypeConstraint) constraints.Add("unmanaged");
    else if (parameter.HasValueTypeConstraint) constraints.Add("struct");
    else if (parameter.HasReferenceTypeConstraint)
        constraints.Add(parameter.ReferenceTypeConstraintNullableAnnotation == NullableAnnotation.Annotated ? "class?" : "class");
    if (parameter.HasNotNullConstraint) constraints.Add("notnull");
    constraints.AddRange(ConstraintTypes(parameter));
    if (parameter.HasConstructorConstraint) constraints.Add("new()");
    if (parameter.AllowsRefLikeType) constraints.Add("allows ref struct");
    return constraints.Count == 0 ? "" : "where " + parameter.ToDisplayString(typeFormat) + " : " + string.Join(", ", constraints);
}
string[] Constraints(ISymbol symbol) => TypeParameters(symbol).Select(ConstraintClause).Where(x => x.Length != 0).ToArray();
string AccessibilityText(Accessibility accessibility) => accessibility switch {
    Accessibility.Public => "public", Accessibility.Protected => "protected",
    Accessibility.ProtectedOrInternal => "protected internal", Accessibility.ProtectedAndInternal => "private protected",
    Accessibility.Internal => "internal", Accessibility.Private => "private",
    _ => throw new InvalidOperationException("Unsupported declared accessibility: " + accessibility)
};
string[] TypeModifiers(INamedTypeSymbol type)
{
    var modifiers = new List<string> { AccessibilityText(type.DeclaredAccessibility) };
    if (type.IsStatic) modifiers.Add("static");
    else if (type.TypeKind == TypeKind.Class)
    {
        if (type.IsAbstract) modifiers.Add("abstract");
        if (type.IsSealed) modifiers.Add("sealed");
    }
    if (type.TypeKind == TypeKind.Struct)
    {
        if (type.IsReadOnly) modifiers.Add("readonly");
        if (type.IsRefLikeType) modifiers.Add("ref");
    }
    return modifiers.ToArray();
}
string RefPrefix(RefKind kind) => kind switch {
    RefKind.Ref => "ref ", RefKind.RefReadOnly => "ref readonly ", _ => ""
};
string NamedTypeDeclaration(INamedTypeSymbol type)
{
    string prefix = string.Join(" ", TypeModifiers(type)) + " ";
    string name = type.ToDisplayString(typeNameFormat);
    string declaration;
    if (type.TypeKind == TypeKind.Delegate)
    {
        var invoke = type.DelegateInvokeMethod ?? throw new InvalidOperationException("Missing delegate Invoke: " + name);
        declaration = prefix + "delegate " + RefPrefix(invoke.RefKind) + TypeName(invoke.ReturnType) + " " + name
            + "(" + string.Join(", ", invoke.Parameters.Select(p => InlineAttributes(p.GetAttributes()) + p.ToDisplayString(format))) + ")";
    }
    else
    {
        string kind = type.TypeKind switch {
            TypeKind.Class => type.IsRecord ? "record class" : "class",
            TypeKind.Struct => type.IsRecord ? "record struct" : "struct",
            TypeKind.Interface => "interface", TypeKind.Enum => "enum",
            _ => throw new InvalidOperationException("Unsupported public type kind: " + type.TypeKind)
        };
        declaration = prefix + kind + " " + name;
        var bases = new List<string>();
        if (type.TypeKind == TypeKind.Enum)
            bases.Add(TypeName(type.EnumUnderlyingType ?? throw new InvalidOperationException("Missing enum underlying type: " + name)));
        else
        {
            if (type.TypeKind == TypeKind.Class && type.BaseType is { SpecialType: not SpecialType.System_Object } baseType)
                bases.Add(TypeName(baseType));
            bases.AddRange(type.Interfaces.Select(TypeName));
        }
        if (bases.Count != 0) declaration += " : " + string.Join(", ", bases);
    }
    var constraints = Constraints(type);
    return declaration + (constraints.Length == 0 ? "" : " " + string.Join(" ", constraints));
}
string MemberDeclaration(ISymbol symbol)
{
    // Symbol display preserves operators, indexers, tuple element names, defaults,
    // ref/scoped modifiers and generic constraints. It omits attributes, so insert
    // each parameter's attributes at its own token boundary, never by text replace.
    var parts = symbol.ToDisplayParts(format);
    var insertions = new Dictionary<int, string>();
    var parameters = Parameters(symbol);
    for (int i = 0; i < parts.Length; i++)
    {
        if (symbol is IPropertySymbol property && parts[i].Kind == SymbolDisplayPartKind.Keyword && parts[i].ToString() == "get"
            && property.GetMethod is { } getter)
        {
            string annotations = InlineAttributes(getter.GetAttributes())
                + string.Concat(Attributes(getter.GetReturnTypeAttributes()).Select(a => "[return: " + a + "] "));
            if (annotations.Length != 0) insertions.Add(i, annotations);
        }
        if (parts[i].Kind != SymbolDisplayPartKind.ParameterName || parts[i].Symbol is not IParameterSymbol parameter
            || !parameters.Any(p => SymbolEqualityComparer.Default.Equals(p, parameter))) continue;
        string attributes = InlineAttributes(parameter.GetAttributes());
        if (attributes.Length == 0) continue;
        int angles = 0, parentheses = 0, brackets = 0, start = 0;
        for (int j = i - 1; j >= 0; j--)
        {
            string token = parts[j].ToString();
            if (token == ">") angles++;
            else if (token == "<") angles--;
            else if (token == "]") brackets++;
            else if (token == "[")
            {
                if (brackets == 0 && angles == 0 && parentheses == 0) { start = j + 1; break; }
                brackets--;
            }
            else if (token == ")") parentheses++;
            else if (token == "(")
            {
                if (parentheses == 0 && angles == 0 && brackets == 0) { start = j + 1; break; }
                parentheses--;
            }
            else if (token == "," && angles == 0 && parentheses == 0 && brackets == 0) { start = j + 1; break; }
        }
        while (start < i && parts[start].Kind == SymbolDisplayPartKind.Space) start++;
        insertions.Add(start, attributes);
    }
    var text = new StringBuilder();
    for (int i = 0; i < parts.Length; i++)
    {
        if (insertions.TryGetValue(i, out string? attributes)) text.Append(attributes);
        text.Append(parts[i].ToString());
    }
    return text.ToString();
}
string Declaration(ISymbol symbol)
{
    var text = new StringBuilder();
    foreach (string attribute in Attributes(symbol.GetAttributes())) text.Append('[').Append(attribute).Append("]\n");
    if (symbol is not IPropertySymbol)
        foreach (string attribute in Attributes(ReturnAttributes(symbol))) text.Append("[return: ").Append(attribute).Append("]\n");
    return text.Append(symbol is INamedTypeSymbol type ? NamedTypeDeclaration(type) : MemberDeclaration(symbol)).ToString();
}
object? ConstantValue(object? value) => value switch {
    float number when !float.IsFinite(number) => number.ToString("R", CultureInfo.InvariantCulture),
    double number when !double.IsFinite(number) => number.ToString("R", CultureInfo.InvariantCulture),
    _ => value
};
var rows = new List<object>();
var lines = new StringBuilder("# Generated C# API declaration reference\n\nDesign-only declarations, version 0.4.0. This file is generated by the compiler-symbol inventory; do not edit signatures here. No product API is released.\n\nEach symbol inherits the linked domain semantic rules for arguments, results, errors, lifetime, cancellation, threading, platform/capability and cost; domain tables specify member-family exceptions and exact native operations. Compiler-derived signatures retain type modifiers, inheritance, constraints, consumption attributes and constant values. Record constructors and other synthesized members are listed separately.\n\n");
void Add(ISymbol symbol, INamedTypeSymbol? containingType)
{
    if (symbol.DeclaredAccessibility is not (Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal)) return;
    if (symbol is IMethodSymbol m && m.MethodKind is MethodKind.PropertyGet or MethodKind.PropertySet or MethodKind.EventAdd or MethodKind.EventRemove or MethodKind.StaticConstructor) return;
    string? id = symbol.GetDocumentationCommentId();
    if (id is null) return;
    string ns = symbol.ContainingNamespace.ToDisplayString();
    string domain = ns.StartsWith("NativeWeave.Server", StringComparison.Ordinal) || ns.StartsWith("NativeWeave.Grpc", StringComparison.Ordinal) || ns.StartsWith("NativeWeave.Mcp", StringComparison.Ordinal)
        ? "server" : ns.StartsWith("NativeWeave.Interop", StringComparison.Ordinal) ? "interop"
        : ns.StartsWith("NativeWeave.Data", StringComparison.Ordinal) || ns.StartsWith("NativeWeave.Database", StringComparison.Ordinal) || ns.StartsWith("NativeWeave.Query", StringComparison.Ordinal) || ns == "Microsoft.Extensions.DependencyInjection" ? "database"
        : throw new InvalidOperationException("Unmapped public namespace: " + ns);
    var parameters = Parameters(symbol);
    string signature = Declaration(symbol);
    var attributes = Attributes(symbol.GetAttributes());
    if (!documentedIds.Add(id)) throw new InvalidOperationException("Duplicate public documentation ID: " + id);
    var ownerType = symbol as INamedTypeSymbol ?? containingType ?? throw new InvalidOperationException(id);
    string policyKey = ownerType.ContainingNamespace.ToDisplayString() + "." + ownerType.Name;
    if (!policies.TryGetValue(policyKey, out var policy))
        throw new InvalidOperationException("Missing explicit public type semantic policy: " + policyKey);
    foreach (string field in new[] { "package", "semantic_section", "native_operations", "tasks", "capability", "cost_profile" })
        if (!policy.TryGetProperty(field, out _)) throw new InvalidOperationException(policyKey + " is missing " + field);
    var namedType = symbol as INamedTypeSymbol;
    var constantField = symbol as IFieldSymbol;
    string? returns = symbol switch {
        IMethodSymbol methodSymbol => TypeName(methodSymbol.ReturnType),
        IPropertySymbol propertySymbol => TypeName(propertySymbol.Type),
        IFieldSymbol fieldSymbol => TypeName(fieldSymbol.Type),
        IEventSymbol eventSymbol => TypeName(eventSymbol.Type),
        INamedTypeSymbol { DelegateInvokeMethod: { } invoke } => TypeName(invoke.ReturnType),
        _ => null
    };
    RefKind returnRefKind = symbol switch {
        IMethodSymbol methodSymbol => methodSymbol.RefKind,
        IPropertySymbol propertySymbol => propertySymbol.RefKind,
        INamedTypeSymbol { DelegateInvokeMethod: { } invoke } => invoke.RefKind,
        _ => RefKind.None
    };
    rows.Add(new {
        id, name = symbol.Name, @namespace = ns, containing_type = containingType is null ? null : TypeName(containingType), kind = symbol.Kind.ToString(),
        signature, domain, specification = "docs/api/" + domain + ".md", implicit_member = symbol.IsImplicitlyDeclared,
        accessibility = symbol.DeclaredAccessibility.ToString(), attributes,
        type_kind = namedType?.TypeKind.ToString(),
        modifiers = namedType is null ? Array.Empty<string>() : TypeModifiers(namedType),
        is_static = symbol.IsStatic, is_abstract = symbol.IsAbstract, is_sealed = symbol.IsSealed,
        is_record = namedType?.IsRecord, is_readonly = namedType?.IsReadOnly, is_ref_like = namedType?.IsRefLikeType,
        return_or_value_type = returns,
        // Roslyn's RefReadOnly enum member aliases In; returns use the former
        // language meaning, whereas parameter ref_kind keeps its parameter meaning.
        return_ref_kind = returnRefKind == RefKind.RefReadOnly ? "RefReadOnly" : returnRefKind.ToString(),
        return_attributes = Attributes(ReturnAttributes(symbol)),
        base_type = namedType?.BaseType is { } parentType ? TypeName(parentType) : null,
        interfaces = namedType?.Interfaces.Select(TypeName).ToArray() ?? Array.Empty<string>(),
        enum_underlying_type = namedType?.EnumUnderlyingType is { } underlyingType ? TypeName(underlyingType) : null,
        is_const = constantField?.IsConst, has_constant_value = constantField?.HasConstantValue ?? false,
        constant_value = constantField?.HasConstantValue == true ? ConstantValue(constantField.ConstantValue) : null,
        constant_value_type = constantField?.HasConstantValue == true ? constantField.ConstantValue?.GetType().FullName : null,
        generic_constraints = Constraints(symbol),
        type_parameters = TypeParameters(symbol).Select(p => new {
            name = p.Name, ordinal = p.Ordinal, variance = p.Variance.ToString(), attributes = Attributes(p.GetAttributes()),
            has_reference_type_constraint = p.HasReferenceTypeConstraint,
            reference_type_constraint_nullable = p.ReferenceTypeConstraintNullableAnnotation.ToString(),
            has_value_type_constraint = p.HasValueTypeConstraint, has_unmanaged_type_constraint = p.HasUnmanagedTypeConstraint,
            has_notnull_constraint = p.HasNotNullConstraint, has_constructor_constraint = p.HasConstructorConstraint,
            allows_ref_like_type = p.AllowsRefLikeType, constraint_types = ConstraintTypes(p)
        }).ToArray(),
        semantic_policy = policyKey,
        parameters = parameters.Select(p => new {
            name = p.Name, type = TypeName(p.Type), nullable = p.NullableAnnotation.ToString(), attributes = Attributes(p.GetAttributes()),
            ref_kind = p.RefKind.ToString(), scoped_kind = p.ScopedKind.ToString(), optional = p.IsOptional, @params = p.IsParams,
            has_explicit_default_value = p.HasExplicitDefaultValue,
            default_value = p.HasExplicitDefaultValue ? Convert.ToString(p.ExplicitDefaultValue, CultureInfo.InvariantCulture) : null
        }).ToArray(),
        design_only = true, product_implemented = false
    });
    if (symbol is INamedTypeSymbol typeSymbol) lines.Append("## ").Append(typeSymbol.ToDisplayString(typeNameFormat)).Append("\n\n");
    else lines.Append("### ").Append(id.Replace("`", "\\`", StringComparison.Ordinal)).Append("\n\n");
    lines.Append("```csharp\n").Append(signature).Append("\n```\n\n");
    string semanticLink = policy.GetProperty("semantic_section").GetString()!;
    if (semanticLink.StartsWith("docs/api/", StringComparison.Ordinal)) semanticLink = semanticLink[9..];
    lines.Append("Semantics and native mapping: [").Append(policyKey).Append("](").Append(semanticLink).Append("). Documentation ID: `").Append(id).Append("`. ");
    lines.Append(symbol.IsImplicitlyDeclared ? "Compiler-synthesized member of the declared type; no independent native operation.\n\n" : "Design declaration; not an implemented product operation.\n\n");
    if (namedType is not null)
    {
        lines.Append("Package: `").Append(policy.GetProperty("package").GetString()).Append("`. Owning tasks: ")
            .Append(string.Join(", ", policy.GetProperty("tasks").EnumerateArray().Select(x => x.GetString()))).Append(".\n\n");
        lines.Append("Availability: ").Append(policy.GetProperty("capability").GetString()).Append("\n\n")
            .Append("Cost policy: ").Append(policy.GetProperty("cost_profile").GetString()).Append("\n\n");
    }
    if (namedType?.BaseType is { SpecialType: not SpecialType.System_Object } baseType)
        lines.Append("Base type: `").Append(TypeName(baseType)).Append("`.\n\n");
    if (namedType is not null && namedType.Interfaces.Length != 0)
        lines.Append("Interfaces: ").Append(string.Join(", ", namedType.Interfaces.Select(x => "`" + TypeName(x) + "`"))).Append(".\n\n");
}
void WalkType(INamedTypeSymbol type)
{
    if (type.DeclaredAccessibility is not (Accessibility.Public or Accessibility.Protected or Accessibility.ProtectedOrInternal)) return;
    Add(type, type.ContainingType);
    foreach (var member in type.GetMembers().OrderBy(x => x.GetDocumentationCommentId(), StringComparer.Ordinal))
        if (member is INamedTypeSymbol nested) WalkType(nested); else Add(member, type);
}
void WalkNamespace(INamespaceSymbol ns)
{
    foreach (var child in ns.GetNamespaceMembers().OrderBy(x => x.Name, StringComparer.Ordinal)) WalkNamespace(child);
    foreach (var type in ns.GetTypeMembers().OrderBy(x => x.Name, StringComparer.Ordinal)) WalkType(type);
}
WalkNamespace(compilation.Assembly.GlobalNamespace);
File.WriteAllText(Path.Combine(output, "public-api.json"), JsonSerializer.Serialize(new {
    schema_version = "1.0.0", version = "0.4.0", sdk = "11.0.100", language = "15.0",
    state = "design_declarations", product_implemented = false,
    declaration_sources = sourceFiles.Select(x => new {
        path = "experiments/public-api/NativeWeave.Api.Design/" + Path.GetFileName(x),
        sha256 = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(x))).ToLowerInvariant()
    }).ToArray(), semantic_policies = policies, symbols = rows
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
File.WriteAllText(Path.Combine(output, "reference.md"), lines.ToString());
Console.WriteLine(JsonSerializer.Serialize(new { symbols = rows.Count, source_files = sourceFiles.Length, product_implemented = false }));
