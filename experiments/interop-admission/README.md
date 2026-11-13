# R07 NS-01: physical call lease and logical admission

This Design-only experiment compares the unchanged `OwnedBuffer` facade in the
recovered local NuGet package with a small D04 admission-gate candidate. It adds no
product code and does not accept a contract or complete a Delivery task.

Run with Rust/Cargo 1.100.0, .NET SDK 11.0.100 and the platform's NativeAOT build
prerequisites available on PATH:

```sh
python experiments/interop-admission/run.py --out artifacts/interop-admission-linux
```

`--output` is an alias for `--out`. Choose a fresh output path for each attempt.
Windows and Linux x64 are the declared targets; the runner chooses `win-x64` or
`linux-x64`. It verifies the recovered source hashes against the existing migration
map, copies them into a private temporary build directory, rebuilds the native
library, and packs the original managed project with that native asset. The new
consumer uses only `PackageReference`, never `ProjectReference`.

The ordinary build/run deliberately receives no RID argument. A separate publish
uses an explicit RID and `PublishAot=true`, then runs the published executable with
an AOT assertion. Neither stage invokes the old consumer or the old Rust test suite.

Each execution has 32 negative-control rounds and 32 admission-candidate rounds.
One controller thread waits for a worker to enter the real native held call, calls
Dispose twice, and then attempts a new Sum before releasing the held call. The
negative control expects the plain SafeHandle facade to admit the new call while a
physical reference remains. The candidate must reject it while letting the older
call finish. All rounds check the native live counter returns to zero.

Output preserves actual command arguments, timestamps, exit codes, full stdout and
stderr, source input snapshots and SHA256 values, and a result marked false until
all expected checks pass. Binary paths relative to the output directory are:

- `binaries/NativeWeave.Interop.Probe.0.0.1.nupkg`
- `binaries/native/libnw_interop_probe.so` or `binaries/native/nw_interop_probe.dll`
- `binaries/aot/AdmissionProbe` or `binaries/aot/AdmissionProbe.exe`

The entire publish directory is retained under `binaries/aot`, including its native
library. Upload the whole output directory so Linux's executable without a filename
extension is included. Each actual binary path/length/SHA256 is in `result.json`.
Binary output is not committed to this research source directory; raw text evidence
and immutable input snapshots may be preserved there. Do not relabel an earlier
attempt with the hash of a later runner.

The first Linux local attempt and its limitations are described in
`docs/research/topics/R07/logical-admission-probe.md`. The build and consumer share
a host with Rust installed; this is not a clean Rust-free deployment experiment.
# Concurrent recovery note

This fixture was independently authored and executed locally before this session
learned that Design PR #8 had completed equivalent logical-admission coverage.
The primary study is now `docs/research/topics/R07/logical-admission.md` and its
Windows/Linux source/run evidence. This directory preserves the separately
produced Linux NuGet/NativeAOT replication and exact inputs, not new platform
coverage. It is intentionally excluded from the new source-lifecycle CI matrix.
See `docs/research/topics/R07/logical-admission-probe.md` for the provenance
distinction and the unexecuted archival runner revision.
