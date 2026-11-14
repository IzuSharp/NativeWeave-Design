# API Reference, examples and documentation maintenance

Version: 0.4.0. This is the normative design of the future product documentation system. The current Design reference is generated from compileable design declarations, not a published product assembly.

## 1. A single public symbol inventory

Every public/protected type and member receives its compiler XML documentation ID. The inventory includes namespaces, visibility, type kind, base types/interfaces, generic constraints, nullable annotations, parameters and defaults, return type, attributes that affect consumption, owning package, capability/platform, semantic profile, native operation mapping and Delivery owner. Property accessors are represented by their property's access level and get/set/init shape; synthesized record members and inherited BCL members are identified as such rather than accidentally omitted or advertised as new NativeWeave operations.

The declaration source and domain semantics together are the design authority. The reference exporter renders exact signatures from compiler symbols. It must fail on unknown namespaces, duplicate IDs, unassigned semantic coverage or stale generated output. An implementation will replace this design fixture as the assembly authority; it must not copy the fixture's throwing method bodies into product code.

Members inherit a named type/domain policy for common null/ownership/error/concurrency rules and specify exceptions. This is explicit semantic inheritance, not a reason to omit a member. The reference provides a direct link from every symbol to its policy and relevant domain operation table. All user-visible symbols, including optional protocol and maintainer extension APIs, receive the same documentation review.

## 2. Required XML documentation

The product build emits XML alongside each managed assembly. `GenerateDocumentationFile=true`, nullable annotations, and missing/malformed XML warnings are enabled; blanket CS1591 suppression is prohibited in product projects. A design declaration fixture may have an explicit fixture-only suppression while complete normative prose and the generated symbol catalog are reviewed. Such a suppression must not appear in the product adoption template.

Required tags are `summary`, `param` for every parameter, `typeparam` for each generic parameter, `returns` for non-void methods, `value` for nontrivial properties, relevant `exception` entries, and `remarks`. Remarks identify resource/borrow lifetime, disposal, thread safety/reentrancy, cancellation/timeout behavior, platform/capability and significant allocation/copy/complexity costs. Enum fields describe their semantic meaning and unknown-value policy. Public constants/default options document units and limits.

`inheritdoc` is permitted only when the build resolves it to an actual compatible contract and retains NativeWeave-specific exceptions. It cannot substitute BCL Stream documentation for a borrowed request body's lifetime. Generated public symbols receive generator-produced XML and the same checks. Diagnostics have stable IDs, severity, trigger, example, remedy, and suppression policy.

## 3. Publication pipeline

Future product documentation uses .NET's compiled assemblies and XML as inputs to DocFX metadata generation and then the HTML build. DocFX 2.81.0 is the observed stable candidate for the pinned tool manifest; its official documentation describes separate metadata and build stages. The adopting task must execute the chosen version against actual .NET 11 assemblies before accepting it; a release-page claim of RC support is not proof of full NativeWeave output compatibility. The Design fixture's compiler-symbol exporter provides an independently reproducible reference without assuming a product DocFX build has happened.

Release workflow, owned by A13/A16 and each module:

1. Restore locked dependencies and build public reference/implementation assemblies with XML.
2. Compare the public symbol set with the reviewed API baseline and compiled consumer fixtures.
3. Resolve XML IDs, inheritance and cross-reference links; fail missing required docs or parameter/type-parameter mismatch.
4. Generate metadata from the exact assemblies and XML, then build guides/reference HTML with warnings treated as errors.
5. Compile included sample projects using packed NuGet artifacts, not repository ProjectReference shortcuts; run the designated required-platform samples and AOT consumers.
6. Verify the documentation's declared package/RID/version against the packages being released and archive all hashes.
7. Publish versioned documentation only with the corresponding authorized package release. Keep previous versions and migration links.

Generated YAML/HTML can be archived as CI artifacts; source XML/guides/sample projects remain reviewed source. Avoid committing another hand-edited copy of signatures. The reference must label version, support status, package and evidence state prominently. Preview/future content is separated from the stable version.

## 4. Information architecture

| Section | Required content | Owner |
| --- | --- | --- |
| Getting Started | SQLite and PostgreSQL package choice, namespaces, first query, first Rust-backed HTTP server, dotnet run and AOT publish | B01/B04/B13/B15/B17; composition A16/B24 |
| Database guide | Connections/pools, commands, typed parameters, NULL, result cardinality, streaming, errors and cancellation | B01–B07 |
| ORM/query guide | Static descriptors, Entity/DTO creation, Fluent operations, joins/projections/grouping/pagination, relations/concurrency, safe dynamic expressions | B09–B14 |
| Transactions/migrations | Commit outcome versus cleanup, savepoints, retries/idempotency, schema/version ledger | B05/B08 |
| Server guide | Builder/config/DI, endpoints, route binding, request/response, filters/middleware, JSON, streaming, TLS and shutdown | B15–B17/B20 |
| Protocol guide | Tonic gRPC, rmcp tools/resources/prompts/transports, static serializers, auth boundary and capability errors | B18/B19 |
| Async/resources | Ownership, cancellation, deadlines, body/batch leases, bounded close and native quiescence | A03–A08/B06/B16/B20 |
| Engine extension guide | Descriptor/bootstrap, version/capability negotiation, adapter/SPI, thread affinity, conformance and packaging | A09–A12/A23/A24 |
| Native AOT/deployment | Static metadata, generators/analyzers, RID/assets/loading, no-Rust consumption and diagnostics | A10/A12–A16/B10/B24 |
| Performance | Explicit cost ledger, allocation/copy/batch tradeoffs, comparable workloads and measured limits | A21/B23 |
| Compatibility/upgrades | Managed/native/domain version matrix, API diff, Obsolete/migration and supported platforms | A22/B24 |
| API Reference | Every public/protected symbol, exact signature, XML semantics and linked examples | Owning module; A13 infrastructure |

There is no separate unowned documentation phase after code acceptance. The task implementing a symbol also owns its XML, guide updates, examples and reviewed reference diff.

## 5. Sample identity and evidence

Each sample record includes ID, source paths, intended packages, supported RID, command, expected behavior, evidence state, owning task and exact source/command/log/artifact hashes where executed. Source is included by file or generated region reference; a code fence copied manually into several guides is not the source of truth.

| State | Allowed statement |
| --- | --- |
| draft/static-reviewed | Intended design; syntax or behavior is not proven by review alone |
| design-compiled | Exact design declarations and consumer compile; native behavior is not implemented |
| design-executed | A named finite design experiment actually ran; only its observed assertions are claimed |
| design-native-aot-executed | That finite design executable published and ran with Native AOT on the recorded platform |
| product-compiled | Consumer compiled against an actual product package; execution still unproven |
| product-executed | Exact product sample ran with its stated services, RID and environment |

A successful run on Linux cannot mark Windows execution passed. A local JIT run cannot mark AOT passed. Running an AOT program that never invokes a stubbed Database/Server member proves build/link reachability only if that member was rooted; it does not prove a Rust Engine was called. Negative compilation samples identify the expected compiler/analyzer diagnostic rather than accepting any nonzero exit code.

## 6. Compatibility review

Keep a versioned public API baseline and enable .NET package validation, including baseline, compatible framework and runtime validators where applicable. Run negative checks by removing a symbol, changing a nullable/default parameter, and introducing ambiguous overload consumption. API comparison is one input: review behavior, ownership, timeouts, exception categories, query semantics, source generator output and native capability changes separately.

The four identities remain separate: native source/version, C ABI, managed API/package, and domain semantics. A compatible C ABI does not guarantee a compatible C# overload set; an unchanged C# signature does not permit changing a transaction's unknown-result rule. Deprecation requires a stable diagnostic ID, replacement example and migration period recorded by A22/B24.

## 7. Actual enforcement and historical evidence

This round adds an executable design declaration/consumer check, reference generation and matrix/task consistency verification. The paired Plan validator retains the existing task and contract evidence rules. Historical English-translation checks run unchanged at their original accepted commits; current English text and new exact content are checked separately. No old translation acceptance is rewritten to approve new API semantics.

All future Delivery packets reference the standard and have explicit documentation/consumer/API acceptance. The adoption templates must be copied or pinned into a new repository. An AGENTS.md link in Design alone has no effect on an unrelated project.

## Sources

- [.NET package validation](https://learn.microsoft.com/en-us/dotnet/fundamentals/package-validation/overview)
- [NuGet package compatibility](https://learn.microsoft.com/en-us/dotnet/standard/library-guidance/nuget-package-compatibility-rules)
- [DocFX metadata and build](https://dotnet.github.io/docfx/docs/dotnet-api-docs.html)
- [DocFX releases](https://github.com/dotnet/docfx/releases)
- Fixed runtime breaking-change rules and actual read ranges: `foundation-sources.json`.
