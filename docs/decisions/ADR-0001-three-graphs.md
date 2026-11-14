# ADR-0001: Three separate graphs for research, documentation, and development

- Status: Proposed
- Date: 2026-11-12
- Decision layer: collaboration and traceability
- Basis: the user explicitly required three independently modeled forms of parallel work; this does not transplant external specification content
- Formal product technical contracts: this ADR does not select specific ORM, Runtime, or ABI implementations

## Problem

Discovering evidence through research, writing specifications, and implementing the product have different outputs and entry conditions. Combining them into a single chain of “finish research → write Design → write Plan → develop tasks one by one” creates unnecessary waiting; counting files alone can also mistake a candidate plan for an accepted design.

## Proposed decision

1. The Research graph uses questions, source coverage, and evidence outputs as nodes.
2. The Documentation graph separately manages Design chapters and Plan domain task fragments; drafting may begin with candidate inputs, but acceptance must satisfy specific evidence requirements.
3. The Delivery graph manages future implementation, verification, integration, and release tasks, with explicit local contract versions, file paths, and actual technical dependencies.
4. Separate start dependencies, acceptance dependencies, and versioned contract inputs; do not maintain the same status fact redundantly across the three graphs.
5. Partition file ownership by task. Integration tasks generate/update shared indexes and graphs, while independent domains write fragments.
6. There is no global single-task lock; schedule conflicts over the same file or scarce physical-machine resources locally.
7. Phase B documentation and research proceed in parallel now; formal integration still uses the verified foundational mechanisms from phase A.
8. All technical contracts are currently proposed and product Delivery nodes are candidates; the existence of the graphs must not be interpreted as implementation authorization.

## Alternatives

A single combined graph can confuse statuses; a strict phase waterfall blocks unrelated work; a task list without dependencies conceals safety gates. Three graphs add a small maintenance cost, controlled by schema, cross-reference, and consistency checks.

## Verification

Validate unique IDs, references, acyclicity, file conflicts, the set of tasks eligible to start, contract versions, and evidence gates. Inject cycles, missing dependencies, acceptance without evidence, and path conflicts to verify rejection. Graph tools validate data conditions only; they do not determine whether technical conclusions are true.

## Consequences and open issues

A stable contract registry and a unified evidence format are required. Explicit rules are needed for local invalidation propagation caused by compatibility upgrades, task splitting/retirement, and concurrent PR merges. This ADR remains proposed until it passes review; parallel research already has user authorization and does not need to wait for ADR acceptance.
