# NativeWeave Design collaboration rules

This repository preserves research, proposed specifications, accepted specifications, and all research experiments and raw evidence. The future implementation repository is IzuSharp/NativeWeave; tasks and execution status are maintained in IzuSharp/Plan. See [CURRENT-PHASE.md](CURRENT-PHASE.md) for the current phase boundaries.

1. Give priority to the user's current requirements. Use the ArcForges specifications only as a formatting reference; do not import their technical content or execution rules.
2. Research, documentation development, and future product development have three separate graphs. Work without technical dependencies or file conflicts may proceed in parallel; do not impose a global single-task lock.
3. Read the current task, pinned evidence, contract versions, and latest branch. Modify only the files declared by the task; the integration task updates shared indexes.
4. When citing source code, record the full commit SHA, actual files, symbols, line ranges, and read/unread coverage. Dynamic branch URLs are for navigation only.
5. Do not present candidate source paths as evidence of code already read, test source as tests already executed, or successful JIT or analyzer checks as successful execution on an AOT target.
6. Distinguish draft, static-reviewed, compiled, executed, native-aot-executed, and independently-verified states for critical examples. Each later state requires corresponding evidence and cannot be inferred from an earlier state.
7. Core must not introduce a default global Rust runtime; Database/ORM/Server must have Rust foundations. Select internal Rust components based on evidence, with Kestrel used only for comparison; use ArcForges only as a formatting reference. Reuse mature components deeply based on source inspection; ordinary C# entities must not require Rust recompilation by default.
8. Do not modify LICENSE, repository permissions, or protection rules. Proceed with branches and PRs under the existing authorization. On 2026-11-12, the user permitted Design PR5/Plan PR2 to merge after rigorous self-review and actual checks when no independent reviewer was available; the absence of independent review must be recorded and subsequent review retained. This exception does not change mandatory GitHub rules or automatically accept proposed product contracts. CURRENT-PHASE.md governs the current phase: advance only research, actual experiments, detailed design, and future Codex planning; do not execute formal Delivery or write NativeWeave product source code.
9. Do not record credentials, private user data, or unrelated environment variables in published evidence. Benchmark parameters and anonymized environment descriptions should be sufficient for reproduction.
10. Record defects with a finding ID, impact, evidence, and disposition; a promise to fix something later cannot close a blocker to formal acceptance.

## Mandatory C# public API and documentation standard

Read [the versioned standard](docs/standards/csharp-public-api-and-documentation.md) and [the complete API specification](docs/api/README.md) for every new or changed public API, native mapping, generator output or documented behavior.

1. Research the relevant current stable .NET/C# public API families and actual fixed source; never confuse Preview or upstream capability with NativeWeave product support.
2. Provide complete exact C# signatures, natural minimum/advanced consumers, nullability/defaults, ownership/lifetime, async/cancellation, errors, concurrency, capabilities and cost. Map the public member through managed adapter, C ABI, Rust adapter and actual Engine operation.
3. Keep SQL/network/domain execution in Rust and Core minimal; ordinary Entity/DTO/Handler additions must reuse precompiled native assets with normal dotnet build/run/publish.
4. The implementing task owns XML documentation, generated API Reference, guides, examples, compatibility and the required compilation/AOT/consumer checks. Record justified applicability for internal-only work; do not add unreviewed public scaffolding.
5. Independently review API completeness, usability, correctness, allocation/copy cost, compatibility and documentation. Preserve historical accepted inputs and bind materially changed content to fresh review and hashes.
6. New Engines and independent repositories must actually adopt the versioned standard and install its checks using the Design templates; AGENTS.md is not inherited across repositories. Product adoption is a future A13/A22/A24 obligation, not permission to write product code in this phase.
