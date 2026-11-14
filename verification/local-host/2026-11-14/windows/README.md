# Windows local host replication, 2026-11-14

These bounded research runs were started through ArcForges Windows MCP on the authorized Windows host. The source checkout was `4c5c385779b753a4f06e59d07f80ad27ca10a841`; no existing fixture source, accepted contract, task packet or historical evidence was modified. Actual input hashes and source snapshots remain in each run directory. Windows checkout bytes may differ from Git blobs by line endings.

| Run | Actual result | Evidence |
| --- | --- | --- |
| engine-attempt-1 | Passed: three Rust unit tests; NuGet-only independent consumer; RID-free build/run; Rust tools undiscoverable in the consumer PATH; added ordinary C# type rebuilt offline against the same native asset; Native AOT published and executed with 17 checks | `result.json`, command streams and `mcp-console.txt` |
| protocol-attempt-1 | Passed: 19 Rust tests, including real loopback HTTP/1 and HTTP/2, verified TLS/ALPN and rejection cases, Tonic framing/cardinality, and MCP dispatch/body restrictions | `run.json`, `test.stdout.txt` |
| metadata-attempt-1 | Passed: five native database/metadata tests, including SQLite execution and SeaORM public dynamic projection | `manifest.json`, `stdout.log` |
| platform-attempt-1 | Runner failed after the intended compiler rejection CS9382: localized Chinese diagnostics did not contain the runner's English word `closed` | `results.json`, `external-closed-negative.stdout`, `mcp-console.txt` |
| platform-attempt-2 | Runner failed after successful AOT publication: MSVC's inherited `Platform=x64` changed the compiler assembly path to `bin/x64/Release`, while the runner searched `bin/Release` | `results.json`, `publish-default.stdout`, `mcp-console.txt` |
| platform-attempt-3 | Passed after the environment corrections below: ordinary execution, intended CS9382 rejection, and both default and RuntimeAsync Native AOT publication plus actual execution; each AOT executable reported 10 checks | `results.json`, both `aot-*.stdout` streams |

The host was Windows 11 x64, OS build 26300, Scoop `dotnet-sdk` 11.0.100 with runtime 11.0.0, Rust 1.100.0/Cargo 1.100.0 through Scoop `rustup`, and Python 3.15.2. Existing Visual Studio 2026 Community supplied MSVC 14.51.36231 and Windows SDK 10.0.28000.0. No new dependency installation was needed. `host-environment.json` records selected executables, resolved paths, versions and only the necessary compiler environment.

## Reproduction and findings

`launchers/` preserves the exact command files used through MCP. They initialize the existing `VC/Auxiliary/Build/vcvars64.bat`, put the Scoop SDK and Rust/Python executables first on PATH, explicitly select the Scoop `DOTNET_ROOT`, and disable .NET telemetry/first-run output. They contain this host's workspace path; adapt that path and use a new output directory on another machine. Invoke from MCP with `cmd /d /c "<launcher path>"`.

| Finding | Impact and evidence | Disposition |
| --- | --- | --- |
| LH-WINDOWS-001 | The platform runner assumes English diagnostic text. The first run correctly produced CS9382, but its postcondition rejected the Chinese message before AOT began. | Set `DOTNET_CLI_UI_LANGUAGE=en-US` for this existing runner; preserved the failed run and its raw diagnostic. This is a reproduction prerequisite. |
| LH-WINDOWS-002 | `vcvars64.bat` sets `Platform=x64` on this host. The second run's AOT publish succeeded, but the runner's subsequent assembly lookup found no file at its fixed path. `host-environment.json` confirms the inherited variable. | Clear `Platform` after MSVC initialization (`set "Platform="`) for the platform runner. Third run passed both AOT configurations. MSVC linker/SDK variables remain initialized. |
| LH-WINDOWS-003 | An initial launcher write/launch failed because its temporary parent directory did not yet exist; no fixture started. | Created the temporary directory before writing the launcher. `bootstrap-console.txt` preserves the failed launch. This setup failure is excluded from test counts. |

The successful platform launcher is `platform-english-anycpu.cmd`. The other launchers retain the earlier environments to make the observed failures inspectable. Compiler failure in the negative test is expected; runner failures in attempts 1 and 2 are retained as failures. No attempt is relabelled as successful.

## Evidence retention and limits

`collection-check.json` verifies 64 recorded stdout/stderr streams against their original runner hashes, including both failed attempts. `runner-snapshots/` preserves the four executed runner byte sequences. Published binaries and the NuGet package remain available locally but are omitted from Git; `omitted-artifacts.json` records their exact sizes and SHA-256 identities. Its directory-based selection preserves `publish-default.stdout` and all other publish logs. Build intermediates remain local. Reproduction commands rebuild artifacts; byte-identical rebuilds are not asserted.

The consumer test hides Rust discovery through its PATH and removes Rust environment overrides; this host itself still has Rust installed. It is not a pristine runtime-only machine. The protocol and metadata suites execute native Rust research fixtures, not a complete C# Server/Database product bridge. No full product, production soak, release signing, cross-platform performance advantage, weak-memory proof or GPU/mobile support is established. Existing future Delivery obligations remain necessary and unauthorized in this phase.
