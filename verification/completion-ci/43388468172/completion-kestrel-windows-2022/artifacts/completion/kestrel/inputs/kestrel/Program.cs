// Managed comparator only. This is not a NativeWeave product host.
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Server.Kestrel.Core;

var builder = WebApplication.CreateSlimBuilder(args);
builder.WebHost.ConfigureKestrel(options => {
    options.Listen(System.Net.IPAddress.Loopback, 0, listen => listen.Protocols = HttpProtocols.Http1);
    options.Limits.MaxRequestBodySize = 1024;
    options.Limits.MaxConcurrentConnections = 8;
});
var app = builder.Build();
var disconnected = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
app.MapGet("/health", () => "ok");
app.MapPost("/echo", async (HttpContext context) => {
    try {
        using var body = new MemoryStream();
        await context.Request.Body.CopyToAsync(body, context.RequestAborted);
        await context.Response.Body.WriteAsync(body.ToArray(), context.RequestAborted);
    } catch (Microsoft.AspNetCore.Http.BadHttpRequestException ex) { context.Response.StatusCode = ex.StatusCode; }
});
app.MapGet("/slow", async (HttpContext context) => {
    try {
        await context.Response.Body.WriteAsync(new byte[] { 1 }, context.RequestAborted);
        await context.Response.Body.FlushAsync(context.RequestAborted);
        await Task.Delay(TimeSpan.FromSeconds(10), context.RequestAborted);
    } catch (OperationCanceledException) { disconnected.TrySetResult(); }
});
await app.StartAsync();
var address = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.Single();
using var client = new HttpClient { BaseAddress = new Uri(address), Timeout = TimeSpan.FromSeconds(5) };
if (await client.GetStringAsync("/health") != "ok") throw new Exception("health");
var bytes = Enumerable.Range(0, 256).Select(i => (byte)i).ToArray();
using (var response = await client.PostAsync("/echo", new ByteArrayContent(bytes))) {
    if (!response.IsSuccessStatusCode || !(await response.Content.ReadAsByteArrayAsync()).SequenceEqual(bytes)) throw new Exception("binary echo");
}
using (var response = await client.PostAsync("/echo", new ByteArrayContent(new byte[1025]))) {
    if ((int)response.StatusCode != 413) throw new Exception("request limit: " + response.StatusCode);
}
using (var response = await client.GetAsync("/slow", HttpCompletionOption.ResponseHeadersRead)) {
    var stream = await response.Content.ReadAsStreamAsync();
    if (stream.ReadByte() != 1) throw new Exception("stream first byte");
}
await disconnected.Task.WaitAsync(TimeSpan.FromSeconds(5));
using var stop = new CancellationTokenSource(TimeSpan.FromSeconds(5));
await app.StopAsync(stop.Token);
await app.DisposeAsync();
Console.WriteLine("Kestrel comparator: health, binary echo, body limit, disconnect cancellation, bounded shutdown PASS (5 cases)");
