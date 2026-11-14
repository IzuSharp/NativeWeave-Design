// These markers belong only to the isolated design packaging experiment.
namespace NativeWeave.Design.Probe;

[System.AttributeUsage(System.AttributeTargets.Class | System.AttributeTargets.Struct)]
public sealed class ProbeEntityAttribute : System.Attribute { }
[System.AttributeUsage(System.AttributeTargets.Class | System.AttributeTargets.Struct)]
public sealed class ProbeDtoAttribute : System.Attribute { }
[System.AttributeUsage(System.AttributeTargets.Method)]
public sealed class ProbeHandlerAttribute : System.Attribute { }
