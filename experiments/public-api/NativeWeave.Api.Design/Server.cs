// Design-only signature fixture. No method performs product work.
#nullable enable
using System;
using System.Buffers;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Net;
using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace NativeWeave.Server
{
    /// <summary>Creates independently owned applications using the required Rust host.</summary>
    public static class NativeServer
    {
        /// <summary>Creates a builder with finite loopback defaults; arguments populate configuration.</summary>
        public static NativeServerBuilder CreateBuilder(string[]? args = null) => throw new NotSupportedException("Design-only API fixture.");
    }

    /// <summary>Configures one application before Build; not thread safe.</summary>
    public sealed class NativeServerBuilder
    {
        internal NativeServerBuilder() { }
        /// <summary>Gets mutable configuration copied and validated by Build.</summary>
        public ServerOptions Options => throw new NotSupportedException();
        /// <summary>Gets service registrations; the owned provider is built once.</summary>
        public IServiceCollection Services => throw new NotSupportedException();
        /// <summary>Gets configuration; no file watching or secrets scanning is enabled by default.</summary>
        public ConfigurationManager Configuration => throw new NotSupportedException();
        /// <summary>Gets logging configuration; no sink is installed by default.</summary>
        public ILoggingBuilder Logging => throw new NotSupportedException();
        /// <summary>Applies supported server keys from a configuration section using a static binder immediately.</summary>
        public NativeServerBuilder Configure(IConfiguration section) => throw new NotSupportedException();
        /// <summary>Registers an explicit listener; the first explicit listener replaces the default.</summary>
        public NativeServerBuilder Listen(IPAddress address, int port, Action<ServerListenOptions>? configure = null) => throw new NotSupportedException();
        /// <summary>Registers IPv4/IPv6 loopback listeners with the same policy.</summary>
        public NativeServerBuilder ListenLocalhost(int port = 5000, Action<ServerListenOptions>? configure = null) => throw new NotSupportedException();
        /// <summary>Registers static JSON metadata; missing DTO metadata is a build-time configuration error.</summary>
        public NativeServerBuilder UseJson(JsonSerializerContext context) => throw new NotSupportedException();
        /// <summary>Uses an external provider and its scope factory; ownership is explicit.</summary>
        public NativeServerBuilder UseServiceProvider(IServiceProvider provider, bool disposeWithServer = false) => throw new NotSupportedException();
        /// <summary>Registers an application authenticator; instance lifetime remains caller-owned.</summary>
        public NativeServerBuilder UseAuthentication(IServerAuthenticator authenticator) => throw new NotSupportedException();
        /// <summary>Registers named-policy authorization; instance lifetime remains caller-owned.</summary>
        public NativeServerBuilder UseAuthorization(IServerAuthorizer authorizer) => throw new NotSupportedException();
        /// <summary>Builds once, validates options and loads the selected native module; starts no listener.</summary>
        public NativeServerApplication Build() => throw new NotSupportedException();
    }

    /// <summary>Mutable startup options, frozen by Build.</summary>
    public sealed class ServerOptions
    {
        /// <summary>Gets or sets application payload and admission budgets.</summary>
        public ServerBudgetOptions Budget { get; set; } = new();
        /// <summary>Gets or sets the finite whole-request timeout; default 30 seconds.</summary>
        public TimeSpan RequestTimeout { get; set; } = TimeSpan.FromSeconds(30);
        /// <summary>Gets or sets the graceful close wait; default 30 seconds.</summary>
        public TimeSpan ShutdownTimeout { get; set; } = TimeSpan.FromSeconds(30);
        /// <summary>Gets or sets the default total request-body limit; default 1 MiB.</summary>
        public long MaxRequestBodyBytes { get; set; } = 1_048_576;
        /// <summary>Gets or sets the buffered JSON wire limit; default 1 MiB.</summary>
        public int MaxJsonBytes { get; set; } = 1_048_576;
        /// <summary>Gets or sets the aggregate header limit; default 32 KiB.</summary>
        public int MaxHeaderBytes { get; set; } = 32_768;
        /// <summary>Gets or sets the header-receive timeout; default 10 seconds.</summary>
        public TimeSpan HeaderReadTimeout { get; set; } = TimeSpan.FromSeconds(10);
        /// <summary>Gets or sets idle keep-alive timeout; default 60 seconds.</summary>
        public TimeSpan KeepAliveTimeout { get; set; } = TimeSpan.FromSeconds(60);
        /// <summary>Gets or sets trusted forwarding policy; null ignores forwarded identity headers.</summary>
        public TrustedProxyOptions? TrustedProxies { get; set; }
    }

    /// <summary>Finite application-owned credits; these are not process RSS limits.</summary>
    public sealed class ServerBudgetOptions
    {
        /// <summary>Gets or sets the connection limit, default 512.</summary>
        public int MaxConnections { get; set; } = 512;
        /// <summary>Gets or sets HTTP/2 streams per connection, default 32.</summary>
        public int MaxHttp2StreamsPerConnection { get; set; } = 32;
        /// <summary>Gets or sets active and retiring request slots, default 256.</summary>
        public int MaxActiveRequests { get; set; } = 256;
        /// <summary>Gets or sets metadata-only admission waiters, default 128.</summary>
        public int MaxQueuedRequests { get; set; } = 128;
        /// <summary>Gets or sets managed payload credit, default 64 MiB.</summary>
        public long ManagedPayloadBytes { get; set; } = 67_108_864;
        /// <summary>Gets or sets native payload credit, default 64 MiB.</summary>
        public long NativePayloadBytes { get; set; } = 67_108_864;
        /// <summary>Gets or sets each request's per-side retained-byte limit, default 4 MiB.</summary>
        public long RetainedBytesPerRequest { get; set; } = 4_194_304;
        /// <summary>Gets or sets maximum body chunk capacity, default 32 KiB.</summary>
        public int MaxChunkBytes { get; set; } = 32_768;
    }

    /// <summary>HTTP protocol selection without implicit upgrades.</summary>
    [Flags] public enum ServerProtocols
    {
        /// <summary>No protocol selected; invalid for a listener.</summary>
        None = 0,
        /// <summary>HTTP/1.1 transport.</summary>
        Http1 = 1,
        /// <summary>HTTP/2 transport.</summary>
        Http2 = 2,
        /// <summary>HTTP/1.1 and HTTP/2 negotiated by TLS ALPN.</summary>
        Http1AndHttp2 = 3
    }
    /// <summary>Immutable runtime lifecycle observations.</summary>
    public enum ServerState
    {
        /// <summary>Configured but no listeners started.</summary>
        Created,
        /// <summary>Startup has accepted responsibility.</summary>
        Starting,
        /// <summary>All listeners accept requests.</summary>
        Running,
        /// <summary>New admission is closed while owners retire.</summary>
        Stopping,
        /// <summary>All instance work has retired.</summary>
        Stopped,
        /// <summary>A host failure has been observed; cleanup still applies.</summary>
        Faulted,
        /// <summary>Owned application services and native instance are released.</summary>
        Disposed
    }
    /// <summary>Whether all managed/native work has retired before close returned.</summary>
    public enum ServerCloseStatus
    {
        /// <summary>The safe retirement join completed.</summary>
        Completed,
        /// <summary>The wait ended while owners and credits remain retained.</summary>
        Pending
    }
    /// <summary>Negotiated optional host capabilities.</summary>
    [Flags] public enum ServerCapabilities : ulong
    {
        /// <summary>No capability bits.</summary>
        None = 0,
        /// <summary>Native HTTP/1.1 capability.</summary>
        Http1 = 1,
        /// <summary>Native HTTP/2 capability.</summary>
        Http2 = 2,
        /// <summary>Native rustls capability.</summary>
        Tls = 4,
        /// <summary>Validated HTTP trailer capability.</summary>
        Trailers = 8,
        /// <summary>Native Tonic method capability.</summary>
        Grpc = 16,
        /// <summary>Native rmcp capability.</summary>
        Mcp = 32,
        /// <summary>Native Axum SSE formatting capability.</summary>
        ServerSentEvents = 64
    }
    /// <summary>One listener's mutable startup policy.</summary>
    public sealed class ServerListenOptions
    {
        /// <summary>Gets or sets a unique listener name; generated when null.</summary>
        public string? Name { get; set; }
        /// <summary>Gets or sets protocols; default HTTP/1.1.</summary>
        public ServerProtocols Protocols { get; set; } = ServerProtocols.Http1;
        /// <summary>Gets or sets native TLS configuration; null means cleartext.</summary>
        public ServerTlsOptions? Tls { get; set; }
    }
    /// <summary>Native rustls configuration; no managed TLS transport is created.</summary>
    public sealed class ServerTlsOptions
    {
        /// <summary>Creates PEM-file configuration; paths must resolve to readable regular files.</summary>
        public static ServerTlsOptions FromPemFiles(string certificateChainFile, string privateKeyFile) => throw new NotSupportedException();
        private ServerTlsOptions() { }
        /// <summary>Gets or sets the handshake timeout; default 10 seconds.</summary>
        public TimeSpan HandshakeTimeout { get; set; } = TimeSpan.FromSeconds(10);
        /// <summary>Gets or sets concurrent handshakes; default 64.</summary>
        public int MaxConcurrentHandshakes { get; set; } = 64;
        /// <summary>Gets or sets a PEM client trust-root file; null disables client-certificate authentication.</summary>
        public string? ClientCertificateAuthorityFile { get; set; }
    }
    /// <summary>Explicit forwarding trust; unlisted direct peers cannot supply effective identity.</summary>
    public sealed class TrustedProxyOptions
    {
        /// <summary>Gets exact trusted peer IP addresses.</summary>
        public IList<IPAddress> KnownProxies { get; } = new List<IPAddress>();
        /// <summary>Gets or sets the maximum trusted forwarded hops, default one.</summary>
        public int ForwardLimit { get; set; } = 1;
    }
    /// <summary>Close observation; Pending retains roots, native owners and credits.</summary>
    public sealed record ServerCloseResult(ServerCloseStatus Status, int PendingRequests, long RetainedManagedBytes, long RetainedNativeBytes);

    /// <summary>Maps typed endpoints before the first Start; all mapping members are configuration-only.</summary>
    public abstract class ServerRoutes
    {
        internal ServerRoutes() { }
        /// <summary>Maps a synchronous GET result without a per-request async state machine.</summary>
        public ServerEndpointBuilder MapGet(string pattern, Func<ServerResult> handler) => throw new NotSupportedException();
        /// <summary>Maps a synchronous GET result with explicit request access.</summary>
        public ServerEndpointBuilder MapGet(string pattern, Func<RequestContext, ServerResult> handler) => throw new NotSupportedException();
        /// <summary>Maps an asynchronous GET result.</summary>
        public ServerEndpointBuilder MapGet(string pattern, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps a synchronous POST result.</summary>
        public ServerEndpointBuilder MapPost(string pattern, Func<RequestContext, ServerResult> handler) => throw new NotSupportedException();
        /// <summary>Maps an asynchronous POST result.</summary>
        public ServerEndpointBuilder MapPost(string pattern, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps a statically serialized asynchronous JSON POST.</summary>
        public ServerEndpointBuilder MapPost<TRequest, TResponse>(string pattern, Func<TRequest, CancellationToken, Task<TResponse>> handler, JsonTypeInfo<TRequest>? requestTypeInfo = null, JsonTypeInfo<TResponse>? responseTypeInfo = null) => throw new NotSupportedException();
        /// <summary>Maps JSON POST with request context and statically resolved metadata.</summary>
        public ServerEndpointBuilder MapPost<TRequest, TResponse>(string pattern, JsonRequestHandler<TRequest, TResponse> handler, JsonTypeInfo<TRequest>? requestTypeInfo = null, JsonTypeInfo<TResponse>? responseTypeInfo = null) => throw new NotSupportedException();
        /// <summary>Maps a JSON POST returning an explicit HTTP result.</summary>
        public ServerEndpointBuilder MapPost<TRequest>(string pattern, JsonResultHandler<TRequest> handler, JsonTypeInfo<TRequest>? requestTypeInfo = null) => throw new NotSupportedException();
        /// <summary>Maps an asynchronous PUT result.</summary>
        public ServerEndpointBuilder MapPut(string pattern, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps an asynchronous PATCH result.</summary>
        public ServerEndpointBuilder MapPatch(string pattern, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps an asynchronous DELETE result.</summary>
        public ServerEndpointBuilder MapDelete(string pattern, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps explicitly listed HTTP methods; duplicate registrations are rejected.</summary>
        public ServerEndpointBuilder MapMethods(string pattern, IReadOnlyList<string> methods, ResponseHandler handler) => throw new NotSupportedException();
        /// <summary>Maps a typed JSON body/result for explicitly listed methods.</summary>
        public ServerEndpointBuilder MapJson<TRequest, TResponse>(string pattern, IReadOnlyList<string> methods, JsonRequestHandler<TRequest, TResponse> handler, JsonTypeInfo<TRequest>? requestTypeInfo = null, JsonTypeInfo<TResponse>? responseTypeInfo = null) => throw new NotSupportedException();
        /// <summary>Maps a low-level handler that writes the response directly.</summary>
        public ServerEndpointBuilder MapRaw(string pattern, IReadOnlyList<string> methods, RequestHandler handler) => throw new NotSupportedException();
        /// <summary>Creates a prefix group; policy metadata is frozen with its routes.</summary>
        public RouteGroupBuilder MapGroup(string prefix) => throw new NotSupportedException();
    }
    /// <summary>Returns one result for execution within the current request lifetime.</summary>
    public delegate Task<ServerResult> ResponseHandler(RequestContext context, CancellationToken cancellationToken);
    /// <summary>Writes a response directly; completion ends application dispatch.</summary>
    public delegate Task RequestHandler(RequestContext context, CancellationToken cancellationToken);
    /// <summary>Processes one typed JSON request and response without dynamic binding.</summary>
    public delegate Task<TResponse> JsonRequestHandler<TRequest, TResponse>(TRequest request, RequestContext context, CancellationToken cancellationToken);
    /// <summary>Processes one typed JSON request and chooses an HTTP result.</summary>
    public delegate Task<ServerResult> JsonResultHandler<TRequest>(TRequest request, RequestContext context, CancellationToken cancellationToken);
    /// <summary>Composes asynchronous application middleware; next is single-invocation.</summary>
    public delegate Task ServerMiddleware(RequestContext context, RequestHandler next, CancellationToken cancellationToken);
    /// <summary>Composes result filters without object-array argument boxing.</summary>
    public delegate Task<ServerResult> ServerFilter(RequestContext context, ResponseHandler next, CancellationToken cancellationToken);

    /// <summary>Owns one Rust host instance, immutable routing and optional owned services.</summary>
    public sealed class NativeServerApplication : ServerRoutes, IAsyncDisposable
    {
        internal NativeServerApplication() { }
        /// <summary>Gets application services, never a request scope.</summary>
        public IServiceProvider Services => throw new NotSupportedException();
        /// <summary>Gets the current lifecycle snapshot.</summary>
        public ServerState State => throw new NotSupportedException();
        /// <summary>Gets capabilities from the loaded native module.</summary>
        public ServerCapabilities Capabilities => throw new NotSupportedException();
        /// <summary>Gets listener addresses after successful start, including assigned ephemeral ports.</summary>
        public IReadOnlyList<Uri> BoundAddresses => throw new NotSupportedException();
        /// <summary>Adds middleware before routing is frozen; first registration is outermost.</summary>
        public NativeServerApplication Use(ServerMiddleware middleware) => throw new NotSupportedException();
        /// <summary>Starts once; successful completion means all listeners are accepting.</summary>
        public Task StartAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Starts and waits until shutdown, then performs the unbounded safe retirement join.</summary>
        public Task RunAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Closes admission and waits up to timeout; Pending is not disposal.</summary>
        public Task<ServerCloseResult> CloseAsync(TimeSpan timeout, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Validates and atomically replaces one listener's TLS snapshot; existing connections keep theirs.</summary>
        public Task ReloadTlsAsync(string listenerName, ServerTlsOptions options, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Closes and joins managed/native retirement; cannot be canceled or called inside this server's handler.</summary>
        public ValueTask DisposeAsync() => throw new NotSupportedException();
    }
    /// <summary>Configures metadata of one registered endpoint; not thread safe.</summary>
    public sealed class ServerEndpointBuilder
    {
        internal ServerEndpointBuilder() { }
        /// <summary>Assigns a unique diagnostic/OpenAPI operation name.</summary>
        public ServerEndpointBuilder WithName(string name) => throw new NotSupportedException();
        /// <summary>Assigns bounded documentation tags.</summary>
        public ServerEndpointBuilder WithTags(params string[] tags) => throw new NotSupportedException();
        /// <summary>Assigns documentation summary text.</summary>
        public ServerEndpointBuilder WithSummary(string summary) => throw new NotSupportedException();
        /// <summary>Overrides the finite whole-request timeout.</summary>
        public ServerEndpointBuilder WithTimeout(TimeSpan timeout) => throw new NotSupportedException();
        /// <summary>Overrides total upload length without increasing retained-byte limits.</summary>
        public ServerEndpointBuilder WithMaxRequestBodyBytes(long bytes) => throw new NotSupportedException();
        /// <summary>Overrides buffered JSON length within the existing peak budget.</summary>
        public ServerEndpointBuilder WithMaxJsonBytes(int bytes) => throw new NotSupportedException();
        /// <summary>Attaches a named authorization requirement.</summary>
        public ServerEndpointBuilder RequireAuthorization(string policy) => throw new NotSupportedException();
        /// <summary>Explicitly removes inherited authorization requirements.</summary>
        public ServerEndpointBuilder AllowAnonymous() => throw new NotSupportedException();
        /// <summary>Adds a result filter, executed in registration order.</summary>
        public ServerEndpointBuilder AddFilter(ServerFilter filter) => throw new NotSupportedException();
        /// <summary>Declares a statically serializable response shape for documentation.</summary>
        public ServerEndpointBuilder Produces<T>(int statusCode = 200, JsonTypeInfo<T>? typeInfo = null, string contentType = "application/json") => throw new NotSupportedException();
    }
    /// <summary>Configures routes sharing a prefix and inherited policies.</summary>
    public sealed class RouteGroupBuilder : ServerRoutes
    {
        internal RouteGroupBuilder() { }
        /// <summary>Adds an inherited authorization policy.</summary>
        public RouteGroupBuilder RequireAuthorization(string policy) => throw new NotSupportedException();
        /// <summary>Adds inherited documentation tags.</summary>
        public RouteGroupBuilder WithTags(params string[] tags) => throw new NotSupportedException();
        /// <summary>Adds a group result filter.</summary>
        public RouteGroupBuilder AddFilter(ServerFilter filter) => throw new NotSupportedException();
    }

    /// <summary>Borrowed application request context, invalid after dispatch and result execution end.</summary>
    public sealed class RequestContext
    {
        internal RequestContext() { }
        /// <summary>Gets the immutable parsed request and its single-reader body.</summary>
        public ServerRequest Request => throw new NotSupportedException();
        /// <summary>Gets the single-writer response.</summary>
        public ServerResponse Response => throw new NotSupportedException();
        /// <summary>Gets a lazily created per-request service scope.</summary>
        public IServiceProvider Services => throw new NotSupportedException();
        /// <summary>Gets the authenticated principal; unauthenticated requests have an empty principal.</summary>
        public ClaimsPrincipal User => throw new NotSupportedException();
        /// <summary>Gets disconnect/deadline/shutdown cancellation intent.</summary>
        public CancellationToken RequestAborted => throw new NotSupportedException();
        /// <summary>Gets the remaining monotonic whole-request budget.</summary>
        public TimeSpan TimeRemaining => throw new NotSupportedException();
        /// <summary>Gets the bounded correlation identifier, not an authorization identity.</summary>
        public string TraceIdentifier => throw new NotSupportedException();
        /// <summary>Gets request-local application storage, allocated on first use.</summary>
        public IDictionary<object, object?> Items => throw new NotSupportedException();
        /// <summary>Requests transport abort; does not synchronously retire native resources.</summary>
        public void Abort() => throw new NotSupportedException();
    }
    /// <summary>Read-only HTTP metadata with bounded lazy text decoding.</summary>
    public sealed class ServerRequest
    {
        internal ServerRequest() { }
        /// <summary>Gets the exact validated method token.</summary>
        public string Method => throw new NotSupportedException();
        /// <summary>Gets effective scheme after explicitly trusted forwarding.</summary>
        public string Scheme => throw new NotSupportedException();
        /// <summary>Gets validated host authority.</summary>
        public string Host => throw new NotSupportedException();
        /// <summary>Gets the path with encoded separators preserved.</summary>
        public string Path => throw new NotSupportedException();
        /// <summary>Gets the raw query string, including its leading question mark when nonempty.</summary>
        public string QueryString => throw new NotSupportedException();
        /// <summary>Gets protocol name HTTP/1.1 or HTTP/2.</summary>
        public string Protocol => throw new NotSupportedException();
        /// <summary>Gets bounded case-insensitive headers; repeated values remain distinct.</summary>
        public HeaderCollection Headers => throw new NotSupportedException();
        /// <summary>Gets route values decoded once after matching.</summary>
        public ParameterValues RouteValues => throw new NotSupportedException();
        /// <summary>Gets query values with repeats preserved.</summary>
        public ParameterValues Query => throw new NotSupportedException();
        /// <summary>Gets Content-Length if declared; never substitutes for the streaming cap.</summary>
        public long? ContentLength => throw new NotSupportedException();
        /// <summary>Gets Content-Type if present.</summary>
        public string? ContentType => throw new NotSupportedException();
        /// <summary>Gets the direct native peer address, unaffected by forwarding.</summary>
        public IPEndPoint? RemoteEndPoint => throw new NotSupportedException();
        /// <summary>Gets an async-only, nonseekable request-owned body stream.</summary>
        public Stream Body => throw new NotSupportedException();
        /// <summary>Reads one owned bounded native chunk; null denotes observed body EOF.</summary>
        public Task<BodyChunk?> ReadChunkAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Reads bounded JSON with explicit static metadata; a JSON null root is returned as null for reference types.</summary>
        public Task<T?> ReadJsonAsync<T>(JsonTypeInfo<T> typeInfo, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Gets validated trailers after body EOF; before EOF this throws InvalidOperationException.</summary>
        public HeaderCollection GetTrailers() => throw new NotSupportedException();
    }
    /// <summary>Header collection preserving repeated values; request instances are read-only.</summary>
    public sealed class HeaderCollection
    {
        internal HeaderCollection() { }
        /// <summary>Gets the number of distinct case-insensitive names.</summary>
        public int Count => throw new NotSupportedException();
        /// <summary>Gets all values; an absent name returns an empty list.</summary>
        public IReadOnlyList<string> this[string name] => throw new NotSupportedException();
        /// <summary>Gets one value only when exactly one is present; repeated values cause an error.</summary>
        public string? GetSingle(string name) => throw new NotSupportedException();
        /// <summary>Tests whether a header name is present.</summary>
        public bool Contains(string name) => throw new NotSupportedException();
        /// <summary>Replaces response header values before headers are committed.</summary>
        public void Set(string name, string value) => throw new NotSupportedException();
        /// <summary>Appends a distinct response value without comma folding.</summary>
        public void Append(string name, string value) => throw new NotSupportedException();
        /// <summary>Removes a response header before commit.</summary>
        public bool Remove(string name) => throw new NotSupportedException();
        /// <summary>Copies a bounded metadata snapshot whose lifetime is caller-owned.</summary>
        public IReadOnlyDictionary<string, IReadOnlyList<string>> ToDictionary() => throw new NotSupportedException();
    }
    /// <summary>Typed invariant-culture parameter access without runtime reflection.</summary>
    public sealed class ParameterValues
    {
        internal ParameterValues() { }
        /// <summary>Gets exactly one required value or throws RequestBindingException.</summary>
        public T Get<T>(string name) where T : IParsable<T> => throw new NotSupportedException();
        /// <summary>Attempts to parse exactly one value; false means missing, repeated or malformed.</summary>
        public bool TryGet<T>(string name, [MaybeNullWhen(false)] out T value) where T : IParsable<T> => throw new NotSupportedException();
        /// <summary>Returns all raw decoded values; an absent name returns an empty list.</summary>
        public IReadOnlyList<string> GetValues(string name) => throw new NotSupportedException();
    }
    /// <summary>Owns one charged native body allocation; copy methods never expose an escaping native span.</summary>
    public sealed class BodyChunk : IDisposable
    {
        internal BodyChunk() { }
        /// <summary>Gets visible byte length while undisposed.</summary>
        public int Length => throw new NotSupportedException();
        /// <summary>Copies all bytes synchronously into a sufficiently large destination.</summary>
        public void CopyTo(Span<byte> destination) => throw new NotSupportedException();
        /// <summary>Creates a caller-owned managed copy charged during overlap.</summary>
        public byte[] ToArray() => throw new NotSupportedException();
        /// <summary>Releases the native owner exactly once and returns its retained-byte credit.</summary>
        public void Dispose() => throw new NotSupportedException();
    }
    /// <summary>Mutable until headers start; supports one pending body write.</summary>
    public sealed class ServerResponse
    {
        internal ServerResponse() { }
        /// <summary>Gets or sets an HTTP status code; default 200.</summary>
        public int StatusCode { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        /// <summary>Gets headers mutable only before StartAsync or the first write.</summary>
        public HeaderCollection Headers => throw new NotSupportedException();
        /// <summary>Gets response trailers when negotiated; cannot contain forbidden HTTP fields.</summary>
        public HeaderCollection Trailers => throw new NotSupportedException();
        /// <summary>Gets or sets the media type before headers start.</summary>
        public string? ContentType { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        /// <summary>Gets or sets a fixed body length; mismatches terminate the response.</summary>
        public long? ContentLength { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        /// <summary>Gets whether response headers have been committed.</summary>
        public bool HasStarted => throw new NotSupportedException();
        /// <summary>Gets an async-only, nonseekable request-owned output stream.</summary>
        public Stream Body => throw new NotSupportedException();
        /// <summary>Commits headers exactly once after starting callbacks.</summary>
        public Task StartAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Writes bounded input; input must remain unchanged until terminal completion.</summary>
        public Task WriteAsync(ReadOnlyMemory<byte> data, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Flushes to the native flow-controlled body, not proof of peer consumption.</summary>
        public Task FlushAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Writes statically serialized JSON under the route's total and peak limits.</summary>
        public Task WriteJsonAsync<T>(T value, JsonTypeInfo<T> typeInfo, CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Closes response output with validated trailers; idempotent after successful completion.</summary>
        public Task CompleteAsync(CancellationToken cancellationToken = default) => throw new NotSupportedException();
        /// <summary>Registers a bounded callback before headers commit; callbacks run in reverse registration order.</summary>
        public void OnStarting(Func<CancellationToken, Task> callback) => throw new NotSupportedException();
        /// <summary>Registers application completion work; it is not native-retirement notification.</summary>
        public void OnCompleted(Func<Task> callback) => throw new NotSupportedException();
        /// <summary>Transfers a managed asynchronous disposable to request cleanup.</summary>
        public void RegisterForDisposeAsync(IAsyncDisposable resource) => throw new NotSupportedException();
    }
    /// <summary>Executes an HTTP result inside the request lifetime.</summary>
    public abstract class ServerResult
    {
        /// <summary>Allows application-defined result composition without owning network transport.</summary>
        protected ServerResult() { }
        /// <summary>Writes this result; the response accepts one terminal result.</summary>
        public abstract Task ExecuteAsync(RequestContext context, CancellationToken cancellationToken = default);
    }
    /// <summary>Creates natural HTTP results with explicit serialization and stream ownership.</summary>
    public static class Results
    {
        /// <summary>Creates UTF-8 text; immutable text is encoded during request execution.</summary>
        public static ServerResult Text(string text, string contentType = "text/plain; charset=utf-8", int statusCode = 200) => throw new NotSupportedException();
        /// <summary>Creates an empty result with the supplied status.</summary>
        public static ServerResult StatusCode(int statusCode) => throw new NotSupportedException();
        /// <summary>Creates an empty 204 result.</summary>
        public static ServerResult NoContent() => throw new NotSupportedException();
        /// <summary>Creates an empty 404 result.</summary>
        public static ServerResult NotFound() => throw new NotSupportedException();
        /// <summary>Creates explicit AOT-safe JSON; value is borrowed until result execution completes.</summary>
        public static ServerResult Json<T>(T value, JsonTypeInfo<T> typeInfo, int statusCode = 200) => throw new NotSupportedException();
        /// <summary>Creates a 201 JSON result and validated Location header.</summary>
        public static ServerResult Created<T>(string location, T value, JsonTypeInfo<T> typeInfo) => throw new NotSupportedException();
        /// <summary>Creates a bounded RFC 9457-style problem response using framework-owned static metadata.</summary>
        public static ServerResult Problem(int statusCode = 500, string? title = null, string? detail = null, string? type = null, string? instance = null) => throw new NotSupportedException();
        /// <summary>Creates a validation problem from bounded field messages.</summary>
        public static ServerResult ValidationProblem(IReadOnlyDictionary<string, string[]> errors) => throw new NotSupportedException();
        /// <summary>Creates a validated redirect; external locations require explicit caller selection.</summary>
        public static ServerResult Redirect(string location, bool permanent = false, bool preserveMethod = false) => throw new NotSupportedException();
        /// <summary>Copies response bytes at construction; the result owns the bounded managed copy.</summary>
        public static ServerResult Bytes(ReadOnlySpan<byte> bytes, string contentType = "application/octet-stream") => throw new NotSupportedException();
        /// <summary>Executes a producer within request lifetime; the output Stream is borrowed.</summary>
        public static ServerResult Stream(Func<Stream, CancellationToken, Task> write, string contentType = "application/octet-stream") => throw new NotSupportedException();
        /// <summary>Streams an input; result execution disposes it unless leaveOpen is true.</summary>
        public static ServerResult Stream(Stream source, string contentType = "application/octet-stream", bool leaveOpen = false) => throw new NotSupportedException();
        /// <summary>Streams an AOT-safe JSON array with one element in flight.</summary>
        public static ServerResult JsonStream<T>(IAsyncEnumerable<T> source, JsonTypeInfo<T> typeInfo) => throw new NotSupportedException();
        /// <summary>Streams SSE through native Axum formatting with bounded event credit.</summary>
        public static ServerResult ServerSentEvents(IAsyncEnumerable<ServerEvent> source) => throw new NotSupportedException();
    }
    /// <summary>One immutable SSE event; each string is bounded by the endpoint chunk policy.</summary>
    public sealed record ServerEvent(string Data, string? Event = null, string? Id = null, TimeSpan? Retry = null);
    /// <summary>Authentication over parsed application metadata; no transport ownership is transferred.</summary>
    public interface IServerAuthenticator
    {
        /// <summary>Returns a principal on success or null when no supported credentials are present.</summary>
        Task<ClaimsPrincipal?> AuthenticateAsync(RequestContext context, CancellationToken cancellationToken = default);
    }
    /// <summary>Evaluates application policies after authentication and before body binding.</summary>
    public interface IServerAuthorizer
    {
        /// <summary>Returns whether the principal is permitted by the named policy.</summary>
        Task<bool> AuthorizeAsync(RequestContext context, string policy, CancellationToken cancellationToken = default);
    }
    /// <summary>Server-domain failure; native panic/poison/ABI failures use NativeEngineException.</summary>
    public class ServerException : Exception
    {
        /// <summary>Creates a domain exception with a stable code and optional cause.</summary>
        public ServerException(string code, string message, Exception? innerException = null) : base(message, innerException) { Code = code; }
        /// <summary>Gets the stable domain error code.</summary>
        public string Code { get; }
    }
    /// <summary>Malformed, missing or repeated bound input; default response is HTTP 400.</summary>
    public sealed class RequestBindingException : ServerException
    {
        /// <summary>Creates a binding error without including the raw input value.</summary>
        public RequestBindingException(string parameterName, string message) : base("binding_failed", message) { ParameterName = parameterName; }
        /// <summary>Gets the safe parameter identifier.</summary>
        public string ParameterName { get; }
    }

    /// <summary>Marks a static partial endpoint class for compile-time binding generation.</summary>
    [AttributeUsage(AttributeTargets.Class)] public sealed class ServerEndpointsAttribute : Attribute { }
    /// <summary>Declares a route on a supported static method; arbitrary Delegate reflection is prohibited.</summary>
    [AttributeUsage(AttributeTargets.Method, AllowMultiple = true)] public sealed class ServerRouteAttribute : Attribute
    {
        /// <summary>Declares one HTTP method and pattern.</summary>
        public ServerRouteAttribute(string method, string pattern) { Method = method; Pattern = pattern; }
        /// <summary>Gets the method token.</summary>
        public string Method { get; }
        /// <summary>Gets the route template.</summary>
        public string Pattern { get; }
    }
    /// <summary>Explicit scalar route binding for generated adapters.</summary>
    [AttributeUsage(AttributeTargets.Parameter)] public sealed class RouteParameterAttribute : Attribute
    {
        /// <summary>Uses the supplied name, or the parameter name when null.</summary>
        public RouteParameterAttribute(string? name = null) { Name = name; }
        /// <summary>Gets the explicit name.</summary>
        public string? Name { get; }
    }
    /// <summary>Explicit scalar or repeated-array query binding for generated adapters.</summary>
    [AttributeUsage(AttributeTargets.Parameter)] public sealed class QueryParameterAttribute : Attribute
    {
        /// <summary>Uses the supplied name, or the parameter name when null.</summary>
        public QueryParameterAttribute(string? name = null) { Name = name; }
        /// <summary>Gets the explicit name.</summary>
        public string? Name { get; }
    }
    /// <summary>Explicit scalar header binding for generated adapters.</summary>
    [AttributeUsage(AttributeTargets.Parameter)] public sealed class HeaderParameterAttribute : Attribute
    {
        /// <summary>Uses one validated case-insensitive header name.</summary>
        public HeaderParameterAttribute(string name) { Name = name; }
        /// <summary>Gets the header name.</summary>
        public string Name { get; }
    }
    /// <summary>Marks the one statically serialized JSON body parameter.</summary>
    [AttributeUsage(AttributeTargets.Parameter)] public sealed class BodyParameterAttribute : Attribute { }
    /// <summary>Marks a required per-request DI service; its type is statically rooted.</summary>
    [AttributeUsage(AttributeTargets.Parameter)] public sealed class ServiceParameterAttribute : Attribute { }
}

namespace NativeWeave.Server.Hosting
{
    /// <summary>Optional Generic Host integration; the Rust server remains the only network host.</summary>
    public static class NativeServerServiceCollectionExtensions
    {
        /// <summary>Registers one app factory as a singleton and hosted service; host async disposal owns its join.</summary>
        public static IServiceCollection AddNativeWeaveServer(this IServiceCollection services, Func<IServiceProvider, NativeWeave.Server.NativeServerApplication> factory) => throw new NotSupportedException();
    }
}

namespace NativeWeave.Server.Grpc
{
    /// <summary>gRPC method cardinalities.</summary>
    public enum GrpcMethodKind
    {
        /// <summary>Exactly one request and response.</summary>
        Unary,
        /// <summary>Many requests and exactly one response.</summary>
        ClientStreaming,
        /// <summary>Exactly one request and many responses.</summary>
        ServerStreaming,
        /// <summary>Independently streaming requests and responses.</summary>
        DuplexStreaming
    }
    /// <summary>Wire-compatible gRPC statuses.</summary>
    public enum GrpcStatusCode
    {
        /// <summary>Successful protocol result.</summary>
        Ok = 0,
        /// <summary>Call cancellation confirmed.</summary>
        Cancelled = 1,
        /// <summary>Unclassified protocol failure.</summary>
        Unknown = 2,
        /// <summary>Invalid request argument.</summary>
        InvalidArgument = 3,
        /// <summary>Whole-call deadline expired.</summary>
        DeadlineExceeded = 4,
        /// <summary>Requested entity was not found.</summary>
        NotFound = 5,
        /// <summary>Entity already exists.</summary>
        AlreadyExists = 6,
        /// <summary>Authenticated principal is not permitted.</summary>
        PermissionDenied = 7,
        /// <summary>Protocol resource limit reached.</summary>
        ResourceExhausted = 8,
        /// <summary>Required application state is absent.</summary>
        FailedPrecondition = 9,
        /// <summary>Operation aborted by protocol or application.</summary>
        Aborted = 10,
        /// <summary>Value or encoded length is outside supported range.</summary>
        OutOfRange = 11,
        /// <summary>Requested method is not implemented.</summary>
        Unimplemented = 12,
        /// <summary>Internal protocol or application failure.</summary>
        Internal = 13,
        /// <summary>Service is unavailable.</summary>
        Unavailable = 14,
        /// <summary>Unrecoverable data loss reported.</summary>
        DataLoss = 15,
        /// <summary>Valid credentials are required.</summary>
        Unauthenticated = 16
    }
    /// <summary>Statically bound message decoder, never stored as an escaping native span.</summary>
    public delegate T GrpcDecoder<T>(ReadOnlySpan<byte> payload);
    /// <summary>Statically bound encoder writing to a budgeted managed buffer writer.</summary>
    public delegate void GrpcEncoder<T>(T value, IBufferWriter<byte> destination);
    /// <summary>Generated protobuf codec pair; ordinary new messages do not require Rust recompilation.</summary>
    public sealed class GrpcMarshaller<T>
    {
        /// <summary>Creates an explicit codec from statically reachable delegates.</summary>
        public GrpcMarshaller(GrpcEncoder<T> encode, GrpcDecoder<T> decode) { }
    }
    /// <summary>One immutable generated method descriptor.</summary>
    public sealed class GrpcMethod<TRequest, TResponse>
    {
        /// <summary>Creates a method descriptor with canonical /package.Service/Method path.</summary>
        public GrpcMethod(string fullName, GrpcMethodKind kind, GrpcMarshaller<TRequest> requestMarshaller, GrpcMarshaller<TResponse> responseMarshaller) { }
    }
    /// <summary>Finite gRPC message/stream policy; frozen during registration.</summary>
    public sealed class GrpcMethodOptions
    {
        /// <summary>Gets or sets encoded message cap, default 1 MiB.</summary>
        public int MaxEncodedMessageBytes { get; set; } = 1_048_576;
        /// <summary>Gets or sets decompressed message cap, default 1 MiB.</summary>
        public int MaxDecodedMessageBytes { get; set; } = 1_048_576;
        /// <summary>Gets or sets whole-stream bytes in each direction, default 64 MiB.</summary>
        public long MaxStreamBytes { get; set; } = 67_108_864;
        /// <summary>Gets or sets whole-stream deadline, default 30 seconds.</summary>
        public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(30);
    }
    /// <summary>Typed call context borrowed through completion of both stream directions.</summary>
    public sealed class GrpcCallContext
    {
        internal GrpcCallContext() { }
        /// <summary>Gets the underlying request services and authenticated identity.</summary>
        public NativeWeave.Server.RequestContext RequestContext => throw new NotSupportedException();
        /// <summary>Gets canonical method path.</summary>
        public string Method => throw new NotSupportedException();
        /// <summary>Gets the native whole-call cancellation token.</summary>
        public CancellationToken CancellationToken => throw new NotSupportedException();
        /// <summary>Gets remaining monotonic deadline.</summary>
        public TimeSpan TimeRemaining => throw new NotSupportedException();
        /// <summary>Gets incoming text and binary metadata.</summary>
        public GrpcMetadata RequestHeaders => throw new NotSupportedException();
        /// <summary>Gets mutable trailing metadata until terminal completion.</summary>
        public GrpcMetadata ResponseTrailers => throw new NotSupportedException();
        /// <summary>Commits initial response metadata once.</summary>
        public Task WriteResponseHeadersAsync(GrpcMetadata headers, CancellationToken cancellationToken = default) => throw new NotSupportedException();
    }
    /// <summary>Bounded metadata preserving repeated names and binary values.</summary>
    public sealed class GrpcMetadata
    {
        /// <summary>Creates an empty managed metadata collection.</summary>
        public GrpcMetadata() { }
        /// <summary>Appends a validated ASCII metadata value.</summary>
        public void Add(string name, string value) => throw new NotSupportedException();
        /// <summary>Copies binary metadata for a name ending in -bin.</summary>
        public void AddBinary(string name, ReadOnlySpan<byte> value) => throw new NotSupportedException();
        /// <summary>Gets text values, preserving repetition.</summary>
        public IReadOnlyList<string> GetValues(string name) => throw new NotSupportedException();
        /// <summary>Gets caller-owned binary copies, preserving repetition.</summary>
        public IReadOnlyList<byte[]> GetBinaryValues(string name) => throw new NotSupportedException();
    }
    /// <summary>Generated service registration contract, implemented without runtime scanning.</summary>
    public interface IGeneratedGrpcService
    {
        /// <summary>Maps generated method descriptors and typed delegates before Start.</summary>
        void Map(NativeWeave.Server.ServerRoutes routes);
    }
    /// <summary>Registers Tonic-backed protocol methods on the existing Rust host.</summary>
    public static class GrpcEndpointExtensions
    {
        /// <summary>Maps one generated service without a new native runtime.</summary>
        public static void MapGrpc(this NativeWeave.Server.ServerRoutes routes, IGeneratedGrpcService service) => throw new NotSupportedException();
        /// <summary>Maps a unary method.</summary>
        public static NativeWeave.Server.ServerEndpointBuilder MapGrpcUnary<TRequest, TResponse>(this NativeWeave.Server.ServerRoutes routes, GrpcMethod<TRequest, TResponse> method, Func<TRequest, GrpcCallContext, Task<TResponse>> handler, GrpcMethodOptions? options = null) => throw new NotSupportedException();
        /// <summary>Maps a server-streaming method; one output element is encoded at a time.</summary>
        public static NativeWeave.Server.ServerEndpointBuilder MapGrpcServerStreaming<TRequest, TResponse>(this NativeWeave.Server.ServerRoutes routes, GrpcMethod<TRequest, TResponse> method, Func<TRequest, GrpcCallContext, IAsyncEnumerable<TResponse>> handler, GrpcMethodOptions? options = null) => throw new NotSupportedException();
        /// <summary>Maps a client-streaming method with one active inbound MoveNext.</summary>
        public static NativeWeave.Server.ServerEndpointBuilder MapGrpcClientStreaming<TRequest, TResponse>(this NativeWeave.Server.ServerRoutes routes, GrpcMethod<TRequest, TResponse> method, Func<IAsyncEnumerable<TRequest>, GrpcCallContext, Task<TResponse>> handler, GrpcMethodOptions? options = null) => throw new NotSupportedException();
        /// <summary>Maps full duplex with one read and one write allowed concurrently.</summary>
        public static NativeWeave.Server.ServerEndpointBuilder MapGrpcDuplex<TRequest, TResponse>(this NativeWeave.Server.ServerRoutes routes, GrpcMethod<TRequest, TResponse> method, Func<IAsyncEnumerable<TRequest>, GrpcCallContext, IAsyncEnumerable<TResponse>> handler, GrpcMethodOptions? options = null) => throw new NotSupportedException();
    }
    /// <summary>Explicit protocol status emitted by application code.</summary>
    public sealed class GrpcException : Exception
    {
        /// <summary>Creates a gRPC failure; Ok is rejected.</summary>
        public GrpcException(GrpcStatusCode statusCode, string detail, GrpcMetadata? trailers = null) : base(detail) { StatusCode = statusCode; Trailers = trailers; }
        /// <summary>Gets the protocol status.</summary>
        public GrpcStatusCode StatusCode { get; }
        /// <summary>Gets optional bounded trailing metadata.</summary>
        public GrpcMetadata? Trailers { get; }
    }
}

namespace NativeWeave.Server.Mcp
{
    /// <summary>Explicitly enabled modern protocol revision; no legacy fallback.</summary>
    public enum McpProtocolVersion
    {
        /// <summary>Modern stateless protocol revision 2026-07-28 without legacy fallback.</summary>
        V2026_07_28
    }
    /// <summary>Finite modern stateless MCP endpoint configuration.</summary>
    public sealed class McpEndpointOptions
    {
        /// <summary>Gets or sets the exact advertised protocol version.</summary>
        public McpProtocolVersion ProtocolVersion { get; set; } = McpProtocolVersion.V2026_07_28;
        /// <summary>Gets explicit allowed host authorities; loopback defaults derive from listener addresses.</summary>
        public IList<string> AllowedHosts { get; } = new List<string>();
        /// <summary>Gets explicit browser origins; empty rejects requests carrying Origin.</summary>
        public IList<string> AllowedOrigins { get; } = new List<string>();
        /// <summary>Gets or sets wire-body limit, default 1 MiB subject to peak-allocation admission.</summary>
        public int MaxRequestBytes { get; set; } = 1_048_576;
        /// <summary>Gets or sets the maximum JSON depth, default 32.</summary>
        public int MaxJsonDepth { get; set; } = 32;
        /// <summary>Gets or sets JSON structural node limit, default 4096.</summary>
        public int MaxJsonNodes { get; set; } = 4096;
        /// <summary>Gets or sets aggregate decoded string bytes, default 256 KiB.</summary>
        public int MaxJsonStringBytes { get; set; } = 262_144;
    }
    /// <summary>Request-scoped MCP metadata, authorization identity and cancellation.</summary>
    public sealed class McpCallContext
    {
        internal McpCallContext() { }
        /// <summary>Gets request identity and services without creating protocol sessions.</summary>
        public NativeWeave.Server.RequestContext RequestContext => throw new NotSupportedException();
        /// <summary>Gets the current tool/resource/prompt name.</summary>
        public string Name => throw new NotSupportedException();
        /// <summary>Gets cancellation intent; not a durable side-effect outcome.</summary>
        public CancellationToken CancellationToken => throw new NotSupportedException();
        /// <summary>Gets the remaining request deadline.</summary>
        public TimeSpan TimeRemaining => throw new NotSupportedException();
    }
    /// <summary>Tool execution result, distinct from JSON-RPC protocol errors.</summary>
    public sealed class McpToolResult<T>
    {
        private McpToolResult() { }
        /// <summary>Creates a structured success response.</summary>
        public static McpToolResult<T> Success(T value) => throw new NotSupportedException();
        /// <summary>Creates a bounded, safe tool-execution failure with isError true.</summary>
        public static McpToolResult<T> Error(string message) => throw new NotSupportedException();
    }
    /// <summary>One bounded text resource response; URI and media type are validated.</summary>
    public sealed record McpTextResource(string Uri, string Text, string MimeType = "text/plain");
    /// <summary>One prompt argument; requiredness is enforced before application dispatch.</summary>
    public sealed record McpPromptArgument(string Name, string? Description = null, bool Required = false);
    /// <summary>A text-only prompt message in the initial profile.</summary>
    public sealed record McpPromptMessage(string Role, string Text);
    /// <summary>Explicit immutable registrations, frozen when MapMcp returns.</summary>
    public sealed class McpRegistry
    {
        /// <summary>Creates an empty registry; metadata generation runs only during registration.</summary>
        public McpRegistry() { }
        /// <summary>Registers a typed tool with static JSON codecs and bounded schema generation.</summary>
        public McpRegistry AddTool<TInput, TOutput>(string name, string description, JsonTypeInfo<TInput> inputTypeInfo, JsonTypeInfo<TOutput> outputTypeInfo, Func<TInput, McpCallContext, Task<McpToolResult<TOutput>>> handler) => throw new NotSupportedException();
        /// <summary>Registers a fixed URI resource with bounded text content.</summary>
        public McpRegistry AddResource(string uri, string name, string mimeType, Func<McpCallContext, Task<McpTextResource>> handler, string? description = null) => throw new NotSupportedException();
        /// <summary>Registers one prompt with statically described string arguments.</summary>
        public McpRegistry AddPrompt(string name, string description, IReadOnlyList<McpPromptArgument> arguments, Func<IReadOnlyDictionary<string, string>, McpCallContext, Task<IReadOnlyList<McpPromptMessage>>> handler) => throw new NotSupportedException();
    }
    /// <summary>Maps the native rmcp service into the selected Rust host.</summary>
    public static class McpEndpointExtensions
    {
        /// <summary>Maps an immutable registry; nonloopback use requires explicit Host/Origin policy.</summary>
        public static NativeWeave.Server.ServerEndpointBuilder MapMcp(this NativeWeave.Server.ServerRoutes routes, string pattern, McpRegistry registry, McpEndpointOptions? options = null) => throw new NotSupportedException();
    }
}
