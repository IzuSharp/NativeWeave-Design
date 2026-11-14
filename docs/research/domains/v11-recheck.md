# Supplementary EF Core / Kestrel v11 Source Verification

Date: 2026-11-12. Status: source recheck; not compiled or executed.

This file supplements the historical observations explicitly pinned to v10 in the [initial research](initial-findings.md). The v10 records retain their original version and evidence strength; changing version labels must not disguise them as v11 research. Verification of current toolchain releases is handled by the independent [toolchain topic](../toolchain/report.md); this file verifies only the limited source scope under the corresponding v11 tags.

## 1. EF Core v11.0.0

Commit returned by the actual tag/ref: `9e685c7a52d1a344d133a3d370e458db97417b3f`.

Actually read in full: [QueryCompiler.cs](https://github.com/dotnet/efcore/blob/9e685c7a52d1a344d133a3d370e458db97417b3f/src/EFCore/Query/Internal/QueryCompiler.cs), blob SHA `7d59e4786702c632ff72f781ae88104c271265f2`.

Comparison of the mechanisms of interest with v10:

| Mechanism | Actual v11 observation | Supported conclusion |
| --- | --- | --- |
| Compilation of new queries | `ExecuteCore` still checks `RuntimeFeature.IsDynamicCodeSupported`; it throws `QueryNotPrecompiled` when dynamic generation is unavailable | The normal query compilation path still cannot be treated as an unconditional guarantee of AOT execution |
| Precompilation entry point | `PrecompileQuery` still has `Experimental(EFDiagnostics.PrecompiledQueryExperimental)` | At this specific entry point, the experimental annotation has not disappeared merely because a v11 tag exists |
| Parameter extraction signature | Compared with the v10 source read, `ExtractParameters` no longer exposes the optional `generateContextAccessors` parameter | Internal APIs evolve; NativeWeave public contracts should not bind to their internal method signatures |

These conclusions cover only the paths and annotations in this file. v11 provider support, design-time code generation, compiled models, SQL translation, and all AOT tests have not been fully investigated. It is therefore valid to state that "this v11 precompilation entry point is still marked experimental"; this must not be expanded into "all EF v11 AOT approaches have been proven unusable," nor can production readiness be declared directly.

## 2. ASP.NET Core / Kestrel v11.0.0

Commit returned by the actual tag/ref: `1def4cdc07dc10fc267136060e3ef5c1a96d4a99`.

Actually read in full:

- [HttpResponsePipeWriter.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/src/Internal/Http/HttpResponsePipeWriter.cs): blob `5e5078e05cc54865f02abfbed7a6396894f12e9d`.
- [HttpResponsePipeWriterTests.cs](https://github.com/dotnet/aspnetcore/blob/1def4cdc07dc10fc267136060e3ef5c1a96d4a99/src/Servers/Kestrel/Core/test/HttpResponsePipeWriterTests.cs): blob `8fb8cb261d0ae8eefeecc5471d9e79ab537fc2e3`.

These two blob SHAs are identical to those of the v10 files previously read. For these two specific files, the implementation and test contents can be confirmed unchanged: the Open/Closed/Aborted states, rejection of access after writes have stopped, and corresponding tests remain present.

This result cannot be extended to claim that Kestrel v10/v11 are identical overall, and certainly does not prove that all HTTP, TLS, AOT, middleware, and concurrency behavior has been verified.

## 3. Evidence and Unfinished Work

Machine-readable records are in [v11-evidence.json](v11-evidence.json). This round adds two pinned versions and reads of three specific files; the historical research remains the original 7 projects / 20 files or excerpts. Combined counts should distinguish "distinct paths" from "reads by version."

The next step should use the verified .NET 11 toolchain for minimal Native AOT publication of provider/ORM/server examples and actual execution on Windows/Linux. Guards and experimental annotations in source code only help identify risks; they cannot replace that execution evidence.

