> **Current phase:** research and detailed design, not product implementation. All executable research assets belong here. See [CURRENT-PHASE.md](CURRENT-PHASE.md) and [migration provenance](docs/traceability/research-asset-migration.md).

# NativeWeave Design

> Complete Public API design and version 0.4.0 refinement. Historical 2026-11-13 acceptance remains preserved; the current revision requires its own actual independent review and bindings. See the [contract registry](docs/contracts/registry.json) and [exact acceptance index](docs/contracts/acceptance-index.json) for the formal status, pinned versions, and evidence of all 21 contracts; task acceptance for R01–R34 / D01–D32 is recorded in Plan. **Research/design acceptance does not authorize product implementation or release.**

NativeWeave aims to let application developers work primarily in modern C#, using Native AOT and independent Rust Native Engines to obtain measurable performance, memory, and development-efficiency benefits. Database must use Rust underneath, and ordinary new entities reuse precompiled native assets. Server must also use Rust underneath, with the internal Rust composition selected through source inspection and experiments; Kestrel is used only for comparison. Independent managed components retain a pure C# path; interop infrastructure is composed by capability without requiring a unified native runtime.

## Reading entry points

1. [Requirements and boundaries](docs/requirements/charter.md): user authorization, latest clarifications, and the complete scope of phases A/B.
2. [34 research topics](docs/research/topics/): each report, evidence record, and coverage record preserves pinned source, actual experiments, failures, and applicability boundaries; [R01 toolchain facts](docs/research/topics/R01/report.md).
3. [21 versioned contracts](docs/contracts/registry.json): Core, Rust Database/ORM, Rust Server/protocols, platforms, verification, and extensions; the status in each specification heading is interpreted through the exact-content acceptance record in the registry.
4. [Current independent Public API reviews](docs/traceability/reviews/public-api-final/) and [historical final reviews](docs/traceability/reviews/final-2026-11-13/): scoped technical findings, cross-repository conclusions, and exact binding attestations written by their actual independent reviewers.
5. [Design conclusions and future verification](docs/traceability/open-questions.md), [models and acceptance matrix](docs/verification/models-and-matrix.md), and [ADR-0003](docs/decisions/ADR-0003-rust-engine-mandate-and-design-acceptance.md).
6. [Plan final D32 summary](https://github.com/IzuSharp/Plan/blob/main/ledger/reviews/D32.md) and [Plan acceptance register](https://github.com/IzuSharp/Plan/blob/main/acceptance-register.md): 34 Research tasks, 32 Documentation tasks, 114 task packets, and 48 future Codex tasks.
7. Historical recovery basis: [takeover audit](docs/traceability/takeover-audit-2026-11-12.md), [actual recovery record for this round](docs/traceability/final-takeover-2026-11-13.json), and [lifecycle checkpoint](docs/traceability/source-lifecycle-followup.md). Interpret proposed/partial states and previous Host selections in old snapshots at their historical point in time.

## Formal status and evidence boundaries

This round retains the existing 34R / 32D / 48Delivery system and preserves complete research and detailed specifications, technical reviews by genuinely distinct executors, and exact source bindings. Contract acceptance binds the specification version, content hash, immutable Commit, dependencies, and actual review; Plan additionally binds each R/D node, task packet, source, dependency acceptance evidence, and independent attestation. File existence or CI success alone cannot replace independent technical review.

Passed research experiments retain their actual execution versions, platforms, and raw results. Subsequent changes limited to documentation and acceptance records reuse this evidence without relabelling it as execution on a new Commit. Production workloads, complete product composition, a genuinely clean consumption environment without Rust, release signing, and performance benefits must be demonstrated by the existing A/B acceptance tasks.

All 48 Delivery tasks remain planned_candidate / not_authorized. The NativeWeave product repository remains unchanged; PR1 was closed without merging. Future phase transitions and actual product acceptance are separate from the research/design acceptance recorded here.

## Documentation conventions

- English prose, with accurate API names, symbols, and paths; each document identifies its status, version, and responsible topic.
- The original requirements are the content authority. **ArcForges Design / Plan are references only for document formatting and organization; their technical content, working rules, and acceptance policies are not inherited.**
- Official materials, external source code, and experiments are evidence; they do not automatically become architecture decisions for this project.
- Every accepted decision requires pinned inputs and independent review; revisions use local version increments rather than replacing coordination with a global pause.
- The original repository LICENSE remains unchanged; external source code has not been copied into the product. Check the applicable licenses and provenance separately before reuse.

## Checks

With the two repositories in adjacent directories, run the following from Plan:

```bash
python3 tools/validate_graphs.py
python3 tools/verify_completion.py --require-complete
```

First check out the Design Commit pinned by Plan's source-driven-baseline.json; complete-phase validation requires formal acceptance of all 34R / 32D / 21 contracts. Historical checks run in full at their original paired Commits; current checks verify current versions and independent bindings. The tools do not authenticate real-world identities or prove future product safety or platform compatibility. Research models and verification records are identified separately in each topic.


## Source-driven integration continuation

PRs #5–#7 preserve the preceding research, Rust 1.100 work and product-repository research-asset migration. Read [ADR-0002](docs/decisions/ADR-0002-source-driven-native-integration.md), [SeaQuery](docs/research/topics/R25/source-driven-seaquery.md), [Server](docs/research/topics/R27/source-driven-server.md), [Engine integration](docs/extension/engine-integration.md), [precompiled build/maintenance](docs/platforms/build-package-release.md), and [impact/recovery](docs/traceability/source-driven-impact.md). The finite Linux SQLite AOT query probe was recovered, not relabelled as new work or promoted to production. New finite experiments address [logical admission](docs/research/topics/R07/logical-admission-probe.md), [SQLx retirement](docs/database/sqlx-retirement-study.md), and [Body/retained-byte retirement](docs/server/body-retirement-protocol.md). Database is mandatory Rust; supported ordinary entity changes reuse precompiled native assets. Lifecycle, transaction safety and independent review remain mandatory.

## Complete public API design and long-term standard

Start with the [Public API specification](docs/api/README.md), [C# API and documentation standard](docs/standards/csharp-public-api-and-documentation.md), [NuGet/consumption design](docs/api/nuget-and-consumption.md), [documentation system](docs/api/documentation-system.md), and [new-repository adoption templates](templates/public-api/). Exact declarations and consumer checks live in [experiments/public-api](experiments/public-api/). This is design evidence; no product SDK is released by these files.
