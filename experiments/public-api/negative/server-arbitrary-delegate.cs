// Expected compiler rejection: the public API has no reflection-based Delegate overload.
using System;
using NativeWeave.Server;
public static class ArbitraryServerDelegate
{
    public static void Register(NativeServerApplication app)
    {
        Delegate handler = (Func<int, int>)(static value => value);
        app.MapGet("/arbitrary", handler);
    }
}
