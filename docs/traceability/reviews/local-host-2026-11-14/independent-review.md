# Independent review of local-host evidence — 2026-11-14

**Decision: accept this supplemental research evidence and its stated limits. No
blocking finding remains in the reviewed scope.** This decision does not accept a
product implementation, release, new contract version or Delivery task.

Reviewer: `/root/supplement_review`. The execution authors are
`/root/windows_validation` and `/root/linux_validation`; `/root` wrote the combined
Design and Plan supplements. I did not author those experiments, execution records
or supplements. This is an independent technical-executor review, not approval by
another GitHub account. I did not rerun the native experiments.

## Inputs and checks

The executed Design source is
`4c5c385779b753a4f06e59d07f80ad27ca10a841`; the inspected Plan baseline is
`dacaab7fc346da5b649e943a4d937a756345c492`. The accompanying
`independent-review.json` binds the exact new report, index, per-host evidence,
review readbacks and Plan supplement bytes. Its source-read table identifies the
fixture code read. Existing upstream source reviews are retained; I do not claim
to have repeated all of their source inspection or historical native executions.

I checked all 12 fixture attempts and recomputed the hashes of 142 runner output
streams covering 71 command records, including the expected compiler negatives
and the four failed fixture attempts. I also checked the combined index's 16
references, all 167 Linux payload entries, all 40 Linux source snapshots and all
37 Windows source-snapshot entries. The runner manifests contain 76 source
identity entries for 25 distinct source paths: 41 match the immutable Git bytes
directly and 35 are exact LF-to-CRLF checkout conversions. These counts include
repeated snapshots across attempts; they are not distinct tests.

The original-host binary readbacks independently recompute seven Linux and twelve
Windows package/native/executable/compiler-assembly identities. The Linux
readback used ArcForges Linux MCP; the Windows readback inspected the original
local output files. The values agree with their execution and omission manifests.
The binary bytes remain local, with content identities and reproduction commands
preserved. No downloadable archive or byte-identical rebuild is claimed.

## Technical conclusions

| Scope | Review conclusion and boundary |
| --- | --- |
| Current protocol fixture | Both raw test outputs report 19 passed and zero failed. The source includes real HTTP/1 and HTTP/2 loopback, in-memory rustls handshake/ALPN/close checks, Tonic cardinality negatives before Handler invocation and per-request reset, and rmcp public service cases. These are Rust research components; they do not execute a C# Handler bridge or establish complete TLS transport interoperability. |
| Codec package and consumer | Both hosts execute three native tests, NuGet packaging, RID-free consumer build/run with Rust discovery removed from the child PATH, an offline build after adding an ordinary C# type, and actual AOT execution with 17 checks. The ordinary run has 16 checks. The same native content hash is retained. The added type is a basic application declaration, not proof of the future ORM entity or Server Handler integration. The developer hosts still have Rust installed. |
| Modern C# fixture | Successful final runs report nine ordinary checks and ten checks in each of the default and runtime-async AOT executables. The intended external closed-type rejection remains a compiler negative. The separate metadata outputs show generated state-machine types in the default assembly and none in the runtime-async assembly for this fixture. This is not application performance evidence. |
| Database metadata fixture | Both raw outputs report five passed and zero failed. Source assertions exercise actual in-memory SQLite operations, SeaORM runtime projection/shape boundaries, native query behavior, savepoints and migration failures. This is not execution of a complete C# ORM facade or a PostgreSQL service. |
| Plan closure | The new Plan supplement maps the observations to the existing A14/A15/A16/A17/A18/A22 and B04/B11/B14/B17–B19/B21–B24 responsibilities. Existing B21 complete integration, B22 30-minute/24-hour/72-hour profiles, B23 measurements and B24 release obligations remain explicit. No new graph or Delivery authorization is needed for this evidence addition. |

## Findings and dispositions

`LH-REVIEW-001` — **Evidence collection initially omitted raw publish logs.** The
first Linux payload classified six `publish-*.stdout`/`.stderr` files as omitted
binaries because their filenames shared the publish-directory prefix. This hid
the full initial platform linker failure and later publication logs. The author
restored all six original files, restricted binary omission to directory
components, removed the logs from the omission list, and regenerated the payload
manifest. I rehashed the restored streams against every runner reference and the
167-entry payload manifest. **Closed by actual byte restoration; no native rerun
was used to manufacture the missing evidence.**

`LH-REVIEW-002` — **Windows summary understated native test count.** Its initial
README said one native unit test while the retained output contains three. The
author corrected the summary to three and aligned the Windows finding IDs with
the combined report. I checked the final bytes. **Closed.**

The authors' `LH-LINUX-001` linker-dependency diagnosis is supported by the retained
failed link logs, exact package-install records and successful new-directory AOT
attempts. Their `LH-WINDOWS-001` diagnostic-language and `LH-WINDOWS-002` inherited
MSBuild-platform diagnoses agree with the compiler output, failed lookup and
launcher changes. Earlier failed attempts remain failed. The setup-only Windows
launcher failure is retained separately and excluded from test counts.

## Review boundary

The new combined report, host instructions and Plan supplement accurately limit
the evidence to finite local research. They do not infer pristine no-Rust OS
consumption, complete HTTP-to-C#-to-Rust-Database behavior, product memory or speed
advantages, production soak, signing, mobile/GPU support or release acceptance.
No existing fixture, accepted specification, registry, graph or task packet is
changed. The existing exact acceptance remains separate from this new review.

Plan's subsequently generated gate/index records are outside this report's exact
input binding; their own review is recorded separately. New changes to any bound
input require rechecking the affected review scope.
