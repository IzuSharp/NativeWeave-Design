// Expected compiler rejection: a typed JSON response cannot silently become another type.
using System.Threading.Tasks;
using NativeWeave.Server;
public static class WrongServerResponse
{
    private sealed record Input(string Name);
    private sealed record Output(string Message);
    public static void Register(NativeServerApplication app)
    {
        app.MapPost<Input, Output>("/wrong-response", static (input, token) => Task.FromResult(42));
    }
}
