// Design-time API signatures only. Native operations deliberately throw.
#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;

namespace NativeWeave.Interop
{
    /// <summary>Identifies the major and minor version of a NativeWeave C ABI.</summary>
    /// <param name="Major">The incompatible representation/semantics version.</param>
    /// <param name="Minor">The backward-compatible optional extension version.</param>
    public readonly record struct AbiVersion(uint Major, uint Minor);

    /// <summary>A case-sensitive, versioned capability name, for example db.query.v1.</summary>
    public readonly record struct EngineCapability
    {
        private readonly string? _name;
        /// <summary>Creates a capability identifier; empty, null, non-ASCII and malformed names are rejected.</summary>
        /// <param name="name">A lower-case dotted identifier, at most 128 ASCII bytes.</param>
        public EngineCapability(string name) { _name = name; throw new NotSupportedException("Design-only signature"); }
        /// <summary>Gets the identifier, or an empty string for the invalid default value.</summary>
        public string Name => _name ?? string.Empty;
        /// <summary>Returns the identifier for diagnostics without loading an engine.</summary>
        /// <returns>The identifier, or an empty string for the invalid default value.</returns>
        public override string ToString() => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>The declared execution profile of an engine; it does not imply public thread safety.</summary>
    public enum EngineThreadingModel
    {
        /// <summary>Bounded native work runs on the calling thread without a runtime.</summary>
        Synchronous = 0,
        /// <summary>Asynchronous work uses an instance-owned native executor.</summary>
        EngineLocalAsync = 1,
        /// <summary>Mutable native state runs on a designated serialized worker.</summary>
        SerializedWorker = 2,
        /// <summary>An explicitly supplied external event loop controls progress.</summary>
        ExternalLoop = 3
    }

    /// <summary>An immutable snapshot obtained after a native module passed bootstrap validation.</summary>
    public sealed class EngineInfo
    {
        internal EngineInfo() { }
        /// <summary>Gets the manifest engine identity, not an instance identifier.</summary>
        public string EngineId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the managed facade package identity.</summary>
        public string PackageId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the normalized NuGet version, which is not a System.Version.</summary>
        public string PackageVersion => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the ABI reported by the validated native bootstrap.</summary>
        public AbiVersion AbiVersion => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the selected portable runtime identifier.</summary>
        public string RuntimeIdentifier => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the declared execution profile; inspecting it does not create an executor.</summary>
        public EngineThreadingModel ThreadingModel => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets known capabilities advertised by the actual loaded binary.</summary>
        public IReadOnlyList<EngineCapability> Capabilities => throw new NotSupportedException("Design-only signature");
        /// <summary>Tests a named capability without native work or allocation after initialization.</summary>
        /// <param name="capability">The capability to test; the default value is rejected.</param>
        /// <returns>True only when this actual binary advertises the capability.</returns>
        public bool Supports(EngineCapability capability) => throw new NotSupportedException("Design-only signature");
        /// <summary>Requires a named capability before creating dependent domain resources.</summary>
        /// <param name="capability">The capability required by the caller.</param>
        /// <exception cref="NotSupportedException">The capability is absent.</exception>
        public void Require(EngineCapability capability) => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>A generated, immutable package descriptor; ordinary domain factories use their own descriptor automatically.</summary>
    public sealed class EngineDescriptor
    {
        internal EngineDescriptor() { }
        /// <summary>Gets the stable manifest engine identity.</summary>
        public string EngineId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the managed package identity.</summary>
        public string PackageId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the normalized package version.</summary>
        public string PackageVersion => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets explicitly packaged runtime identifiers; this is not a fallback graph.</summary>
        public IReadOnlyList<string> SupportedRuntimeIdentifiers => throw new NotSupportedException("Design-only signature");
        /// <summary>Loads and validates this module for preflight, without starting any domain instance or executor.</summary>
        /// <param name="options">Optional immutable load policy; null selects package defaults.</param>
        /// <returns>The cached validated metadata for the process-resident module.</returns>
        /// <exception cref="EngineLoadException">Asset, identity, platform or ABI validation fails.</exception>
        public EngineInfo Inspect(EngineLoadOptions? options = null) => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>Advanced first-use loading options. Domain builders snapshot these before construction.</summary>
    public sealed class EngineLoadOptions
    {
        /// <summary>Creates options using the package manifest and no additional required capabilities.</summary>
        public EngineLoadOptions() { }
        /// <summary>Gets or initializes an optional absolute asset path, still required to match the packaged hash and RID.</summary>
        public string? NativeAssetPath { get; init; }
        /// <summary>Gets or initializes additional capabilities required before a module can be used.</summary>
        public IReadOnlyList<EngineCapability> RequiredCapabilities { get; init; } = Array.Empty<EngineCapability>();
    }

    /// <summary>An optional immutable index of explicitly supplied descriptors; it never scans assemblies or directories.</summary>
    public sealed class EngineCatalog
    {
        /// <summary>Snapshots descriptors and rejects null entries and duplicate engine identities.</summary>
        /// <param name="descriptors">Already compiled, explicitly selected package descriptors.</param>
        public EngineCatalog(IEnumerable<EngineDescriptor> descriptors) => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets descriptors in ordinal engine-identity order without loading native code.</summary>
        public IReadOnlyList<EngineDescriptor> Engines => throw new NotSupportedException("Design-only signature");
        /// <summary>Finds a descriptor without loading a module.</summary>
        /// <param name="engineId">The case-sensitive manifest identity.</param>
        /// <param name="descriptor">The matching descriptor, or null when absent.</param>
        /// <returns>True when the explicit catalog contains the identity.</returns>
        public bool TryGet(string engineId, [NotNullWhen(true)] out EngineDescriptor? descriptor) => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets a descriptor without loading a module.</summary>
        /// <param name="engineId">The case-sensitive manifest identity.</param>
        /// <returns>The matching descriptor.</returns>
        /// <exception cref="KeyNotFoundException">The descriptor is not registered in this catalog.</exception>
        public EngineDescriptor Get(string engineId) => throw new NotSupportedException("Design-only signature");
        /// <summary>Performs the same preflight as the selected descriptor's Inspect method.</summary>
        /// <param name="engineId">An identity contained in this catalog.</param>
        /// <param name="options">Optional first-use load policy.</param>
        /// <returns>Validated engine metadata; no domain runtime is started.</returns>
        public EngineInfo Inspect(string engineId, EngineLoadOptions? options = null) => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>A synchronous consumer of a native read lease; the span must not escape the invocation.</summary>
    /// <param name="bytes">Read-only native bytes, valid only until the delegate returns.</param>
    public delegate void NativeBufferReader(ReadOnlySpan<byte> bytes);

    /// <summary>A synchronous projection from a native read lease to independently owned managed data.</summary>
    /// <typeparam name="TResult">A non-ref-like result that cannot retain the borrowed span in safe code.</typeparam>
    /// <param name="bytes">Read-only native bytes, valid only until the delegate returns.</param>
    /// <returns>A scalar or independently owned managed result.</returns>
    public delegate TResult NativeBufferReader<TResult>(ReadOnlySpan<byte> bytes);

    /// <summary>An immutable native byte owner with scoped reads and explicit copies; it never exposes naked native-backed Memory.</summary>
    public sealed class NativeBuffer : IDisposable
    {
        internal NativeBuffer() { }
        /// <summary>Gets the immutable byte length; remains available after disposal.</summary>
        public int Length => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets whether new reads are closed, without asserting all admitted reads have retired.</summary>
        public bool IsDisposed => throw new NotSupportedException("Design-only signature");
        /// <summary>Copies the entire buffer into a sufficiently large destination.</summary>
        /// <param name="destination">Destination whose length is at least Length.</param>
        public void CopyTo(Span<byte> destination) => throw new NotSupportedException("Design-only signature");
        /// <summary>Copies a range whose length equals destination.Length.</summary>
        /// <param name="sourceOffset">Zero-based offset in bytes.</param>
        /// <param name="destination">The exact requested range destination.</param>
        public void CopyTo(int sourceOffset, Span<byte> destination) => throw new NotSupportedException("Design-only signature");
        /// <summary>Copies all bytes if the destination is large enough; a short destination is left untouched.</summary>
        /// <param name="destination">Destination span.</param>
        /// <returns>False only for insufficient destination length; disposal still throws.</returns>
        public bool TryCopyTo(Span<byte> destination) => throw new NotSupportedException("Design-only signature");
        /// <summary>Allocates an independently owned managed array and copies all bytes into it.</summary>
        /// <returns>An array independent of this native owner.</returns>
        public byte[] ToArray() => throw new NotSupportedException("Design-only signature");
        /// <summary>Invokes a synchronous managed reader while holding the native owner lease.</summary>
        /// <param name="reader">A non-null reader, invoked outside all admission locks.</param>
        public void Read(NativeBufferReader reader) => throw new NotSupportedException("Design-only signature");
        /// <summary>Projects a synchronous read while holding the native owner lease.</summary>
        /// <typeparam name="TResult">The independently owned result type.</typeparam>
        /// <param name="reader">A non-null synchronous reader.</param>
        /// <returns>The reader's result.</returns>
        public TResult Read<TResult>(NativeBufferReader<TResult> reader) => throw new NotSupportedException("Design-only signature");
        /// <summary>Copies through a bounded managed staging buffer while keeping this owner leased for the complete copy.</summary>
        /// <param name="destination">A writable stream, left open after success or failure.</param>
        /// <param name="cancellationToken">Cancels writes and the caller's copy, without undoing bytes already written.</param>
        /// <returns>A task for copy completion and end of staging-array use.</returns>
        public Task CopyToAsync(Stream destination, CancellationToken cancellationToken = default) => throw new NotSupportedException("Design-only signature");
        /// <summary>Closes new read admission and drops this owner's reference; admitted reads keep their leases.</summary>
        public void Dispose() => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>A native panic, poison or interop-contract error; ordinary domain failures use domain-specific exceptions.</summary>
    public class NativeEngineException : Exception
    {
        /// <summary>Creates an exception without a native diagnostic record.</summary>
        public NativeEngineException() { }
        /// <summary>Creates an exception without a native diagnostic record.</summary>
        /// <param name="message">The diagnostic message, or null.</param>
        public NativeEngineException(string? message) : base(message) { }
        /// <summary>Creates an exception preserving the managed cause, without inventing a wire status.</summary>
        /// <param name="message">The diagnostic message, or null.</param>
        /// <param name="innerException">The managed cause, or null.</param>
        public NativeEngineException(string? message, Exception? innerException) : base(message, innerException) { }
        private protected NativeEngineException(string engineId, string operation, string? message, Exception? innerException)
            : base(message, innerException) { }
        /// <summary>Creates an exception from a complete native failure record.</summary>
        /// <param name="engineId">The engine identity.</param>
        /// <param name="operation">The stable adapter operation name.</param>
        /// <param name="statusCode">The original non-success wire status, including unknown values.</param>
        /// <param name="errorDomain">The original native error domain.</param>
        /// <param name="nativeCode">The original signed provider code.</param>
        /// <param name="correlationId">An opaque diagnostic correlation identifier; zero is permitted.</param>
        /// <param name="message">A bounded, redacted message.</param>
        /// <param name="innerException">An optional managed bridge cause.</param>
        public NativeEngineException(string engineId, string operation, uint statusCode, uint errorDomain,
            int nativeCode, ulong correlationId, string? message, Exception? innerException = null)
            : base(message, innerException) => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the engine identity, or null when no native context was supplied.</summary>
        public string? EngineId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the operation name, or null when no native context was supplied.</summary>
        public string? Operation => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the unmodified wire status, or null for a failure before a native call.</summary>
        public uint? StatusCode => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the error domain, or null without a native record.</summary>
        public uint? ErrorDomain => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the provider code, or null without a native record.</summary>
        public int? NativeCode => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the native correlation value, or null without a native record.</summary>
        public ulong? CorrelationId => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>A reason a native module failed preflight; numeric values are a managed diagnostic contract only.</summary>
    public enum EngineLoadFailure
    {
        /// <summary>No supported current RID entry exists.</summary>
        UnsupportedPlatform = 1,
        /// <summary>The selected native asset or a required OS dependency is missing.</summary>
        MissingAsset = 2,
        /// <summary>The binary format, architecture or CPU baseline is incompatible.</summary>
        InvalidBinary = 3,
        /// <summary>The content does not match the expected package manifest.</summary>
        AssetIntegrityMismatch = 4,
        /// <summary>The mandatory bootstrap export is absent.</summary>
        MissingExport = 5,
        /// <summary>The native ABI major or required shape is incompatible.</summary>
        IncompatibleAbi = 6,
        /// <summary>A required capability is unavailable.</summary>
        MissingCapability = 7,
        /// <summary>The process already selected another content identity for the same engine.</summary>
        ConflictingModule = 8,
        /// <summary>The packaged manifest is malformed or contradicts the selected asset.</summary>
        InvalidManifest = 9
    }

    /// <summary>An actionable module-loading failure; it never silently selects another engine.</summary>
    public sealed class EngineLoadException : NativeEngineException
    {
        /// <summary>Creates an engine-load failure before domain resources have been published.</summary>
        /// <param name="failure">The classified load failure.</param>
        /// <param name="engineId">The requested engine identity.</param>
        /// <param name="runtimeIdentifier">The requested RID.</param>
        /// <param name="message">A redacted message including an installation or compatibility remedy.</param>
        /// <param name="innerException">An optional loader exception.</param>
        public EngineLoadException(EngineLoadFailure failure, string engineId, string runtimeIdentifier,
            string message, Exception? innerException = null) : base(engineId, "load", message, innerException)
            => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the managed preflight failure classification.</summary>
        public EngineLoadFailure Failure => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the requested RID.</summary>
        public string RuntimeIdentifier => throw new NotSupportedException("Design-only signature");
    }
}

namespace NativeWeave.Interop.Extensibility
{
    /// <summary>A maintainer-defined mapping from a named capability to an engine-local bootstrap bit.</summary>
    /// <param name="Capability">The stable name.</param>
    /// <param name="BitIndex">A unique bit from 0 through 63 within this engine ABI major.</param>
    public readonly record struct EngineCapabilityDefinition(Interop.EngineCapability Capability, int BitIndex);

    /// <summary>A maintainer-generated native asset descriptor; no file is loaded by its constructor.</summary>
    public sealed class NativeAssetDescriptor
    {
        /// <summary>Creates one exact RID asset entry.</summary>
        /// <param name="runtimeIdentifier">The supported portable RID.</param>
        /// <param name="relativePath">A canonical package-relative native path without traversal.</param>
        /// <param name="sha256">The 64-character lower-case asset SHA-256.</param>
        /// <param name="cpuBaseline">The declared instruction-set baseline.</param>
        public NativeAssetDescriptor(string runtimeIdentifier, string relativePath, string sha256, string cpuBaseline)
            => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the supported portable RID.</summary>
        public string RuntimeIdentifier => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the canonical package-relative asset path.</summary>
        public string RelativePath => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the expected asset digest.</summary>
        public string Sha256 => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the published CPU baseline.</summary>
        public string CpuBaseline => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>Immutable loader inputs generated from the complete maintainer release manifest.</summary>
    public sealed class EnginePackageManifest
    {
        /// <summary>Validates and snapshots the loader-relevant subset of a release manifest.</summary>
        /// <param name="engineId">Stable lower-case engine identity.</param>
        /// <param name="packageId">Managed facade NuGet identity.</param>
        /// <param name="packageVersion">Normalized release version.</param>
        /// <param name="abiVersion">The required ABI major and minimum minor.</param>
        /// <param name="bootstrapSymbol">The exact engine-specific get_abi_v1 export.</param>
        /// <param name="threadingModel">The declared executor profile.</param>
        /// <param name="assets">Unique RID entries.</param>
        /// <param name="capabilities">Unique capability names and bit indices.</param>
        public EnginePackageManifest(string engineId, string packageId, string packageVersion,
            Interop.AbiVersion abiVersion, string bootstrapSymbol, Interop.EngineThreadingModel threadingModel,
            IReadOnlyList<NativeAssetDescriptor> assets, IReadOnlyList<EngineCapabilityDefinition> capabilities)
            => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the stable engine identity.</summary>
        public string EngineId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the facade package ID.</summary>
        public string PackageId => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the normalized package version.</summary>
        public string PackageVersion => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the required ABI version.</summary>
        public Interop.AbiVersion AbiVersion => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the exact bootstrap symbol.</summary>
        public string BootstrapSymbol => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets the executor profile.</summary>
        public Interop.EngineThreadingModel ThreadingModel => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets immutable asset entries.</summary>
        public IReadOnlyList<NativeAssetDescriptor> Assets => throw new NotSupportedException("Design-only signature");
        /// <summary>Gets immutable named-capability definitions.</summary>
        public IReadOnlyList<EngineCapabilityDefinition> Capabilities => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>The explicit AOT-safe maintainer entry point; generated package code invokes it once on demand.</summary>
    public static class EnginePackage
    {
        /// <summary>Creates a descriptor from a statically rooted manifest and assembly without scanning or loading native code.</summary>
        /// <param name="manifest">A validated generated manifest.</param>
        /// <param name="assembly">The already compiled facade assembly owning its LibraryImport resolver.</param>
        /// <returns>An immutable descriptor for explicit catalog or ordinary domain use.</returns>
        public static Interop.EngineDescriptor CreateDescriptor(EnginePackageManifest manifest, Assembly assembly)
            => throw new NotSupportedException("Design-only signature");
    }

    /// <summary>A maintainer-only adoption seam for generated engine bindings; application code normally receives NativeBuffer results.</summary>
    public static class NativeBufferFactory
    {
        /// <summary>Adopts exactly one immutable native buffer owner after successful native transfer.</summary>
        /// <param name="engine">Validated metadata retaining the creating module.</param>
        /// <param name="owner">The creating engine's sole SafeHandle; ownership transfers only on successful return.</param>
        /// <param name="address">A stable readable address for length bytes, or zero only for empty data.</param>
        /// <param name="length">Length between zero and the negotiated Int32-bounded limit.</param>
        /// <returns>A public buffer that releases through the supplied owner's creating module.</returns>
        public static Interop.NativeBuffer Adopt(Interop.EngineInfo engine, SafeHandle owner, nint address, int length)
            => throw new NotSupportedException("Design-only signature");
    }
}
