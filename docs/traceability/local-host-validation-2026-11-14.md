# Local Windows/Linux research verification — 2026-11-14

The existing research fixtures were executed on the user's actual Windows and
Linux hosts through ArcForges Windows MCP and ArcForges Linux MCP. The four
selected suites passed on both hosts after the environment corrections below.
This supplement preserves the failed attempts and adds local reproduction
evidence; it does not implement NativeWeave or replace formal product acceptance.

## Inputs and scope

The immutable Design input is `4c5c385779b753a4f06e59d07f80ad27ca10a841`.
Plan was inspected at `dacaab7fc346da5b649e943a4d937a756345c492`.
No fixture, existing specification, accepted contract, task packet, graph or
historical evidence was edited. Windows source snapshots include exact LF-to-CRLF
checkout conversions where recorded; Linux snapshots match the Git bytes.
The new per-host source manifests distinguish those identities.

The prior [final Server review](reviews/final-2026-11-13/server-review.md)
explicitly retained 13 protocol cases on the old Windows/Linux CI and 19 cases on
the later Linux execution. This run verifies the current 19-case fixture on both
local hosts. Existing successful PostgreSQL, interop, lifecycle and diagnostic
research is retained without unnecessary reruns or new claims about those suites.

| Host | Actual tools | Native build environment |
| --- | --- | --- |
| Windows x64 | Scoop .NET SDK 11.0.100 / runtime 11.0.0; Rust and Cargo 1.100.0 | Installed Visual Studio 2026 Community MSVC environment; explicit Scoop SDK selection |
| Debian 13 x64 | Homebrew .NET SDK 11.0.100 / runtime 11.0.0; Rust and Cargo 1.100.0 | Clang 19.1.7, GNU ld 2.44; Brotli and Zstd development packages added for this SDK's native link |

The host records preserve exact executable paths, versions and relevant command
settings. These two installed developer machines do not establish minimum-OS,
CPU, pristine-consumer, runtime-only or other-platform support.

## Executed results

Evidence root: [`verification/local-host/2026-11-14/`](../../verification/local-host/2026-11-14/).

| Existing fixture | Windows | Linux | What was actually exercised |
| --- | --- | --- | --- |
| `server-completion` protocol | [19 passed](../../verification/local-host/2026-11-14/windows/protocol-attempt-1/run.json) | [19 passed](../../verification/local-host/2026-11-14/linux/protocol/run.json) | Rust HTTP/1 and HTTP/2 loopback, TLS/ALPN positive and negative cases, Tonic message-cardinality handling and MCP cases. |
| `database-completion` metadata | [5 passed](../../verification/local-host/2026-11-14/windows/metadata-attempt-1/manifest.json) | [5 passed](../../verification/local-host/2026-11-14/linux/metadata/manifest.json) | Existing Rust runtime metadata and SQLite/query behavior; no C# ORM or PostgreSQL execution in this suite. |
| `engine-completion --aot` | [Passed, 17 AOT checks](../../verification/local-host/2026-11-14/windows/engine-attempt-1/result.json) | [Passed, 17 AOT checks](../../verification/local-host/2026-11-14/linux/engine-attempt-2/result.json) | Native codec tests/build, NuGet pack, separate RID-free consumer build/run, removal of Rust tool discovery, offline C# type addition with unchanged native asset, explicit-RID AOT publish and actual execution. Ordinary consumer: 16 checks per host. |
| `platform-completion --aot` | [Passed on attempt 3](../../verification/local-host/2026-11-14/windows/platform-attempt-3/results.json) | [Passed on attempt 2](../../verification/local-host/2026-11-14/linux/platform-attempt-2/results.json) | Ordinary execution: 9 checks; expected external closed-type compilation rejection; default and runtime-async actual AOT: 10 checks each; separate compiler-lowering inspection. |

The codec experiment supplies an end-to-end **research packaging and consumption**
path. Its filtered consumer PATH has no discoverable `cargo`, `rustc` or `rustup`,
but Rust remains installed elsewhere on the developer host. The protocol suite
does not execute a C# FFI Handler. These results do not establish the future
HTTP-to-C#-to-Rust-Database reference application, long-running resource stability,
performance advantages or release readiness.

## Findings and dispositions

| Finding | Impact and retained evidence | Resolution |
| --- | --- | --- |
| LH-LINUX-001 — native linker dependencies | Initial [engine](../../verification/local-host/2026-11-14/linux/engine/result.json) and [platform](../../verification/local-host/2026-11-14/linux/platform/results.json) AOT attempts failed to link `brotlienc`, `brotlidec`, `brotlicommon` and `zstd`. JIT success did not satisfy AOT. | Installed Debian `libbrotli-dev` 1.1.0-2+deb13u1 and `libzstd-dev` 1.5.7+dfsg-1. New output directories retain successful actual AOT runs. Existing zlib development files and Clang were sufficient otherwise. |
| LH-WINDOWS-001 — diagnostic language assumption | [Platform attempt 1](../../verification/local-host/2026-11-14/windows/platform-attempt-1/results.json) emitted the intended CS9382 compiler rejection, but the research runner additionally expects the English word `closed`; the Chinese diagnostic failed that assertion. | Set `DOTNET_CLI_UI_LANGUAGE=en-US` in the research child environment. The source and negative test remain unchanged. |
| LH-WINDOWS-002 — inherited MSBuild platform | [Platform attempt 2](../../verification/local-host/2026-11-14/windows/platform-attempt-2/results.json) published native code, then failed to find the compiler assembly: `vcvars64` injected `Platform=x64`, selecting `bin/x64/Release` while the fixture inspects `bin/Release`. It did not reach AOT execution. | Clear only the inherited `Platform` variable after MSVC initialization; retain the linker/SDK variables. Attempt 3 passed the negative case, both metadata checks and both actual AOT executions. |

The MCP service environment also required explicit selection of the installed
Scoop/Homebrew tools and matching `DOTNET_ROOT`; installation alone did not imply
that a long-running MCP process already had their PATH. These are scoped launcher
settings, not global SDK upgrades or changes to the accepted design.

## Reproduction and evidence preservation

Use the [Windows host instructions](../../verification/local-host/2026-11-14/windows/README.md)
and [Linux host instructions](../../verification/local-host/2026-11-14/linux/README.md).
They include the actual launcher commands and environment corrections. Select the
pinned source and tools, use new output directories, and retain any failed attempt
before retrying. The existing runners write command arguments, exits, raw output,
input snapshots and result hashes. The collection additionally preserves launcher
failures and omits build products explicitly rather than treating them as tested
source or silently dropping command logs.

Per-host manifests identify omitted native assets, NuGet packages, AOT executables
and inspected assemblies by content hash. Those binaries remain local and are not
included in this documentation PR. Reproduction rebuilds and re-executes the
fixture; it does not promise a byte-identical rebuild or downloadable release.
The raw logs and source snapshots are retained as bytes, including Windows CRLF.
The [independent supplement review](reviews/local-host-2026-11-14/independent-review.md)
is separate from the authors' execution and does not impersonate a different
GitHub approval account.

Plan's `local-validation-2026-11-14.md` maps this evidence to the existing
A14/A15/A16/A17/A18/A22 and B04/B11/B14/B17–B19/B21–B24 obligations. Existing
plans already assign pristine no-Rust consumption, complete C# integration,
30-minute/24-hour/72-hour resource checks, fair performance measurement and release
closure. This run does not add another graph or change any of the 48 Delivery
authorization states. The accepted baseline and its independent attestations
remain intact; these new observations have their own review and source identities.
