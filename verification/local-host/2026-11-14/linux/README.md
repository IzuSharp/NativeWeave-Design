# Linux local-host replication, 2026-11-14

Executed through ArcForges Linux MCP on Debian 13 x64, kernel 6.12.63+deb13-amd64, using the unchanged Design source commit `4c5c385779b753a4f06e59d07f80ad27ca10a841`. Homebrew .NET SDK 11.0.100 / runtime 11.0.0 and Rust/Cargo 1.100.0 were already installed. Clang 19.1.7 and GNU ld 2.44 were present. `environment/host.json` and its command outputs identify the tools; only task-relevant environment settings are recorded in the launcher scripts.

| Fixture | Result | Evidence |
| --- | --- | --- |
| Rust server protocol | 19 passed, 0 failed | `protocol/run.json`, `protocol/test.stdout.txt` |
| Rust database runtime metadata | 5 passed, 0 failed | `metadata/manifest.json`, `metadata/stdout.log` |
| Codec/NuGet consumer | Native tests, precompiled package, RID-free build/run with Rust tools removed from PATH, added ordinary C# type offline build, actual Native AOT execution with 17 checks passed | `engine-attempt-2/result.json`, `engine-attempt-2/actual-aot.stdout` |
| Modern C# platform | Normal 9 checks, external closed-type compiler rejection, default and runtime-async AOT execution with 10 checks each passed; default metadata has generated state machines, runtime-async metadata has none | `platform-attempt-2/results.json` and stdout logs |

## Resolved host prerequisite

Finding LH-LINUX-001: first `engine/` and `platform/` attempts reached AOT native linking and failed because `/usr/bin/ld.bfd` could not find `-lbrotlienc`, `-lbrotlidec`, `-lbrotlicommon`, or `-lzstd`. A Homebrew SDK installation alone did not supply these libraries to the Debian system linker. The initial failures, command exits and raw bytes are retained. The host already had zlib1g-dev and Clang.

Installed `libbrotli-dev` (`1.1.0-2+deb13u1`) and `libzstd-dev` (`1.5.7+dfsg-1`) using `sudo -n apt-get install -y --no-install-recommends libbrotli-dev libzstd-dev`. Installation logs and exact package versions are in `environment/`. The engine's first build work directory was moved outside the checkout before the second run so its independent consumer was freshly copied. Both AOT suites then passed in new `*-attempt-2/` directories with unchanged fixture source bytes. Disposition: resolved environment prerequisite; no product or accepted contract edit.

## Reproduction

Clone the pinned Design revision on an actual Linux x64 host. Ensure the recorded SDK, Rust and native linker prerequisites are available. These commands use this host's existing Homebrew prefix; adjust the prefix for another installation.

```bash
export PATH=/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/opt/rustup/bin:$PATH
export DOTNET_ROOT=/home/linuxbrew/.linuxbrew/opt/dotnet/libexec
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
python3 experiments/server-completion/run.py protocol --output /absolute/new-output/protocol
python3 experiments/engine-completion/run.py --out /absolute/new-output/engine --aot
python3 experiments/platform-completion/run.py --out /absolute/new-output/platform --aot
python3 experiments/database-completion/run.py --suite metadata --out /absolute/new-output/metadata
```

Use new output directories for every attempt. The actual orchestration scripts and exact argv/time/exit records are preserved as `environment/run-local.py`, `environment/retry-local.py`, `orchestration.json`, and `retry-orchestration.json`. `source-verification.json` checks retained source inputs against the immutable Git bytes. `payload-manifest.json` identifies all retained payload bytes. `omitted-binaries.json` identifies primary omitted executables, native assets, packages and inspected compiler assemblies by content hash; build intermediates are not evidence artifacts.

The protocol and database fixtures execute Rust research, without a C# product bridge. The codec test removes Rust tool discovery from its consumption environment; it does not establish a pristine no-Rust operating system or production package support. These bounded checks do not establish product performance, production soak, release or device-platform acceptance. No NativeWeave product repository work or Delivery execution was performed.
