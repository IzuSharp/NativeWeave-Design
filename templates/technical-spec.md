# Module specification

Status: design-draft; version: ; contract ID: ; author/reviewer: ; input evidence: .

1. Requirement IDs, applicable scenarios, and non-goals.
2. Actual source evidence, alternatives, and selection rationale.
3. Boundaries and dependencies; responsibilities of pure C# and optional Rust.
4. Public C# API; Rust interfaces; C ABI; generated bindings. Mark the validation status of each code block.
5. Types, layouts, parameter validity, ownership, thread affinity, cancellation, and errors.
6. Normal and error flows, state machines, linearization points, safety invariants, and liveness assumptions.
7. Memory/copy/FFI/thread/runtime/startup/package-size costs.
8. Differences between Windows/Linux and other targets; AOT and build/packaging commands.
9. Version/binary compatibility rules, upgrades, and old/new combinations.
10. Test matrix, negative cases, fault injection, performance methodology, and applicability boundaries for formal methods.
11. Implementation tasks, file ownership, acceptance evidence, and open items.
12. Independent review and disposition; accepted status must bind the exact content version and evidence.

Qualify every “supported” claim by a specific platform/version/feature. Illustrative code cannot replace compilation records.
