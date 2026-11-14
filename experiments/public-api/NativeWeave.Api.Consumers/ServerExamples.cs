// Design-consumer compilation witnesses. Do not run: referenced APIs are stubs.
#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using NativeWeave.Server;
using NativeWeave.Server.Grpc;
using NativeWeave.Server.Hosting;
using NativeWeave.Server.Mcp;

namespace NativeWeave.Api.Consumers;

public static class ServerExamples
{
    public static async Task MinimalAsync(CancellationToken cancellationToken)
    {
        await using var app = NativeServer.CreateBuilder().Build();
        app.MapGet("/", static () => Results.Text("Hello from Rust + C#"));
        await app.RunAsync(cancellationToken);
    }

    public static async Task TypedJsonAsync(CancellationToken cancellationToken)
    {
        var builder = NativeServer.CreateBuilder();
        builder.UseJson(ServerJsonContext.Default);
        await using var app = builder.Build();
        app.MapPost<CreateGreeting, Greeting>("/greetings",
            static (request, token) => Task.FromResult(new Greeting(request.Name)));
        app.MapPost<CreateGreeting>("/created", static (request, context, token) =>
            Task.FromResult(Results.Created("/created/1", new Greeting(request.Name), ServerJsonContext.Default.Greeting)));
        await app.RunAsync(cancellationToken);
    }

    public static async Task AdvancedAsync(string storageDirectory, CancellationToken cancellationToken)
    {
        var builder = NativeServer.CreateBuilder();
        builder.Services.AddScoped<GreetingService>();
        builder.UseJson(ServerJsonContext.Default);
        builder.ListenLocalhost(8080);
        await using var app = builder.Build();
        app.Use(static async (context, next, token) =>
        {
            context.Response.Headers.Set("X-Application", "sample");
            await next(context, token);
        });
        var api = app.MapGroup("/v1").WithTags("greetings");
        api.MapGet("/greetings/{id}", static (context, token) =>
        {
            long id = context.Request.RouteValues.Get<long>("id");
            GreetingService service = context.Services.GetRequiredService<GreetingService>();
            return Task.FromResult(Results.Json(service.Get(id), ServerJsonContext.Default.Greeting));
        }).WithName("GetGreeting").Produces<Greeting>();
        api.MapRaw("/uploads/{id}", new[] { "PUT" }, async (context, token) =>
        {
            Guid id = context.Request.RouteValues.Get<Guid>("id");
            string path = Path.Combine(storageDirectory, id.ToString("N") + ".bin");
            await using FileStream file = new(path, FileMode.CreateNew, FileAccess.Write,
                FileShare.None, 32_768, FileOptions.Asynchronous);
            await context.Request.Body.CopyToAsync(file, 32_768, token);
            context.Response.StatusCode = 201;
            // Successful dispatch awaits CompleteAsync before cleanup and preserves this201.
        }).WithMaxRequestBodyBytes(67_108_864).WithTimeout(TimeSpan.FromMinutes(2));
        app.MapGet("/events", static context => Results.ServerSentEvents(Events(context.RequestAborted)));
        await app.StartAsync(cancellationToken);
        ServerCloseResult close = await app.CloseAsync(TimeSpan.FromSeconds(10), cancellationToken);
        if (close.Status == ServerCloseStatus.Pending)
        {
            // await using below still joins. A Pending result never authorizes freeing callbacks.
        }
    }

    // The source is opened only when the producer actually executes. A replaced
    // result or suppressed HEAD response opens nothing; every admitted path closes it.
    public static ServerResult Download(string applicationSelectedPath) =>
        Results.Stream(async (output, token) =>
        {
            await using FileStream input = new(applicationSelectedPath, FileMode.Open,
                FileAccess.Read, FileShare.Read, 32_768, FileOptions.Asynchronous);
            await input.CopyToAsync(output, 32_768, token);
        });

    public static void HostedRegistration(IServiceCollection services)
    {
        services.AddNativeWeaveServer(static provider =>
        {
            var builder = NativeServer.CreateBuilder().UseServiceProvider(provider);
            var app = builder.Build();
            app.MapGet("/health/ready", static () => Results.Text("ready"));
            return app;
        });
    }

    public static void ProtocolRegistration(NativeServerApplication app)
    {
        var codec = new GrpcMarshaller<Greeting>(
            static (message, writer) => throw new NotSupportedException("Generated protobuf encoder witness."),
            static payload => throw new NotSupportedException("Generated protobuf decoder witness."));
        app.MapGrpcUnary(new GrpcMethod<Greeting, Greeting>("/sample.Greeter/Echo", GrpcMethodKind.Unary, codec, codec),
            static (request, context) => Task.FromResult(request));
        app.MapGrpcServerStreaming(new GrpcMethod<Greeting, Greeting>("/sample.Greeter/List", GrpcMethodKind.ServerStreaming, codec, codec),
            static (request, context) => Greetings(context.CancellationToken));
        app.MapGrpcClientStreaming(new GrpcMethod<Greeting, Greeting>("/sample.Greeter/Collect", GrpcMethodKind.ClientStreaming, codec, codec),
            static async (requests, context) =>
            {
                await foreach (Greeting request in requests.WithCancellation(context.CancellationToken))
                    return request;
                return new Greeting("empty");
            });
        app.MapGrpcDuplex(new GrpcMethod<Greeting, Greeting>("/sample.Greeter/Duplex", GrpcMethodKind.DuplexStreaming, codec, codec),
            static (requests, context) => requests);
        var tools = new McpRegistry().AddTool("greet", "Create a greeting",
            ServerJsonContext.Default.CreateGreeting, ServerJsonContext.Default.Greeting,
            static (request, context) => Task.FromResult(McpToolResult<Greeting>.Success(new Greeting(request.Name))));
        tools.AddResource("resource://example/readme", "readme", "text/plain",
            static context => Task.FromResult(new McpTextResource("resource://example/readme", "Example")));
        tools.AddPrompt("greeting", "Greeting prompt", new[] { new McpPromptArgument("name", Required: true) },
            static (args, context) => Task.FromResult<IReadOnlyList<McpPromptMessage>>(
                new[] { new McpPromptMessage("user", "Greet " + args["name"]) }));
        app.MapMcp("/mcp", tools);
    }

    private static async IAsyncEnumerable<ServerEvent> Events([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        yield return new ServerEvent("ready", Event: "state");
        await Task.Delay(1, cancellationToken);
        yield return new ServerEvent("done", Event: "state");
    }
    private static async IAsyncEnumerable<Greeting> Greetings([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        yield return new Greeting("one");
        await Task.Delay(1, cancellationToken);
        yield return new Greeting("two");
    }
}
public sealed record CreateGreeting(string Name);
public sealed record Greeting(string Message);
public sealed class GreetingService { public Greeting Get(long id) => new(id.ToString()); }
[JsonSerializable(typeof(CreateGreeting))]
[JsonSerializable(typeof(Greeting))]
public partial class ServerJsonContext : JsonSerializerContext { }

// The real generator will add GreetingEndpoints.Map(ServerRoutes). This witness does
// not claim generator execution; explicit context binding above is independently usable.
[ServerEndpoints]
public static partial class GreetingEndpoints
{
    [ServerRoute("GET", "/generated/{id}")]
    public static ServerResult Get([RouteParameter] long id, [ServiceParameter] GreetingService service)
        => Results.Json(service.Get(id), ServerJsonContext.Default.Greeting);
}
