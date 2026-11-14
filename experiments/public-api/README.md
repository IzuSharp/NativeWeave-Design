# Public API design validation

These are isolated research fixtures. `NativeWeave.Api.Design` declares the future
API and deliberately throws from product-facing bodies. It must never be shipped
as the product implementation or used to claim executed ORM/HTTP behavior.

## Reproduce the full interface check

Install stable SDK 11.0.100 and the platform's normal Native AOT prerequisites:

```bash
python3 experiments/public-api/run.py --aot --output artifacts/public-api/run-1
python3 tools/verify_public_api.py --history
```

Use `--dotnet /absolute/path/to/dotnet` for an isolated SDK. Use a new output
directory for each attempt. The runner records exact commands, exit codes, logs,
source SHA-256, restored dependency locks, platform and the actual AOT executable
hash. It generates `docs/api/public-api.json` and `reference.md` from Roslyn symbols,
requiring an explicit semantic policy for every public type and all its members.

The checks cover:

1. All Database, Server and Interop declarations with nullable types, constraints,
   overloads and the real Extensions 11 package references.
2. All minimum/advanced consumer files and System.Text.Json generated contexts.
3. Nine independent negative compiler-diagnostic cases (the nullable-reference case requires CS8625; the others require their specified compiler errors): wrong scalar and entity columns, reverse/repeated nullable lifting,
   nullable references, invalid aggregation, incorrect handler results, span
   capture and attempting to treat an owning reference type as a copyable value.
4. The generated exact public inventory/reference, with per-type package, semantic
   section, operation family, capability, cost and existing Delivery ownership.
   A separate compiler-symbol regression fixture checks parameter/return attributes,
   named-type and delegate declarations, enum/constants, generic constraints and
   deterministic JSON/Markdown output. It does not add product APIs.
5. Native AOT publication and execution of static JSON/evidence code. Both the
   declaration assembly and consumer assembly are rooted so their bodies and
   closed generic uses participate in compilation. No declaration body is called
   as if it were an actual database/server operation.

`negative/` also preserves domain-specific C# counterexamples reviewed and compiled
in the domain checks. The native layout probes under `abi/` verify fixed records;
they do not prove a Rust adapter implements their behavior.

## Independent package and generator mechanism

The [packaging probe](packaging-probe/README.md) builds a finite real Roslyn generator
and isolated local NuGet packages, then consumes only their Facade reference.
It reuses the already compiled research native codec. The final Linux evidence in
`verification/public-api/interop-packaging/attempt-4/` proves transitive generator
loading, model/nullable DTO edits, rejected unsupported models, build/run/publish
and actual AOT/native-codec execution with unchanged native bytes. Earlier failed
attempts are retained. This is not the complete ORM metadata generator, public
Server or a pristine-machine product release test.

## Evidence interpretation

| State | What this repository can establish |
| --- | --- |
| Design declarations compiled | Exact C# signatures and supplied consumer shapes are legal on the pinned compiler |
| Negative cases observed | The specified incorrect shapes are rejected by actual diagnostics |
| Design fixture executed | Static managed JSON/evidence code runs; product bodies remain unimplemented |
| Design Native AOT executed | The actual published native executable runs on the recorded target |
| Packaging/native codec probe executed | A finite generator/package/native asset mechanism runs with recorded bytes |
| Product ORM/HTTP/AOT/release accepted | Requires future authorized Delivery evidence; never inferred here |

The optional `UseOfflineReferenceFixture=true` project mode uses local ASP.NET
reference assemblies only for isolated signature inspection. It is not the product
dependency graph and is not used by the full normal-package validation runner.
Do not use disabled trimming/AOT analyzers as proof of AOT compatibility.
