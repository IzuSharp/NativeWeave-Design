# EF Core / Kestrel v11 supplemental source verification

Date: 2026-11-12. Status: source review; not compiled or executed.

This file supplements the historical observations explicitly pinned to v10 in the [initial research](initial-findings.md). The v10 records retain their original versions and evidence strength; changing version labels must not disguise them as v11 research. Current toolchain release verification belongs to the separate [toolchain topic](../toolchain/report.md); this file verifies only the scoped source files under the corresponding v11 tags.

## 1. EF Core v11.0.0

Commit returned by the actual tag/ref: `9e685c7a52d1a344d133a3d370e458db97417b3f`.

Actually read in full: [QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs), blob SHA `7d59e4786702c632ff72f781ae88104c271265f2`.

Mechanisms examined and comparison with v10:

| Mechanism | Actual v11 observation | Supported conclusion |
| --- | --- | --- |
| New query compilation | `ExecuteCore` still checks `RuntimeFeature.IsDynamicCodeSupported`; it throws `QueryNotPrecompiled` when dynamic generation is unavailable | The ordinary query compilation path still cannot be treated as an unconditional guarantee of AOT execution |
| Precompilation entry point | `PrecompileQuery` still has `Experimental(EFDiagnostics.PrecompiledQueryExperimental)` | For this specific entry point, the experimental annotation has not disappeared merely because a v11 tag exists |
| Parameter extraction signature | Compared with the v10 source read, `ExtractParameters` no longer exposes the optional `generateContextAccessors` parameter | Internal APIs evolve; NativeWeave public contracts should not be bound to their internal method signatures |

These conclusions cover only the paths and annotations in the current file. Provider support, design-time code generation, compiled models, SQL translation and all AOT tests in v11 have not been comprehensively investigated. It is therefore valid to state that "this v11 precompilation entry point is still marked experimental," but not to extend that to "all EF v11 AOT approaches have been proven unusable" or directly declare production readiness.

## 2. ASP.NET Core / Kestrel v11.0.0

Commit returned by the actual tag/ref: `1def4cdc07dc10fc267136060e3ef5c1a96d4a99`.

Actually read in full:

- [HttpResponsePipeWriter.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs)：blob `5e5078e05cc54865f02abfbed7a6396894f12e9d`。
- [HttpResponsePipeWriterTests.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs)：blob `8fb8cb261d0ae8eefeecc5471d9e79ab537fc2e3`。

These two blob SHAs match those of the v10 files actually read earlier. For these two scoped files, the implementation and test content is confirmed unchanged: the Open/Closed/Aborted states, rejection of access after writes stop and the corresponding tests remain present.

This result cannot be extended to equivalence of Kestrel v10/v11 as a whole, much less prove that all HTTP, TLS, AOT, middleware and concurrency behavior has been verified.

## 3. Evidence and unfinished work

Machine-readable records are in [v11-evidence.json](v11-evidence.json). This round adds two pinned versions and three scoped file reads; the historical research remains the original 7 projects/20 files or excerpts. Combined statistics must distinguish "distinct paths" from "reads by version."

The next step should perform minimal provider/ORM/server Native AOT publication and actual Windows/Linux execution on the verified .NET 11 toolchain. Source-level guards and experimental annotations only help identify risks; they cannot replace this execution evidence.

