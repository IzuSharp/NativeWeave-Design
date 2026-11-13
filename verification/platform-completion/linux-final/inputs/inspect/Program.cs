using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;

using var file = File.OpenRead(args[0]);
using var pe = new PEReader(file);
var reader = pe.GetMetadataReader();
var stateMachines = reader.TypeDefinitions
    .Select(h => reader.GetTypeDefinition(h))
    .Where(t => t.GetInterfaceImplementations().Any(h =>
    {
        var iface = reader.GetInterfaceImplementation(h).Interface;
        if (iface.Kind != HandleKind.TypeReference) return false;
        var reference = reader.GetTypeReference((TypeReferenceHandle)iface);
        return reader.GetString(reference.Name) == "IAsyncStateMachine"
            && reader.GetString(reference.Namespace) == "System.Runtime.CompilerServices";
    }))
    .Select(t => reader.GetString(t.Name))
    .ToArray();
Console.WriteLine(JsonSerializer.Serialize(new { assembly = args[0], stateMachineTypes = stateMachines }));
if (args[1] == "default" && stateMachines.Length < 3) return 2;
if (args[1] == "runtime-async" && stateMachines.Length != 0) return 3;
return 0;
