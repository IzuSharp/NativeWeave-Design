# Public API change record

Status: template, not evidence. Replace all fields before review.

| Field | Required content |
| --- | --- |
| Scenario and owner | Complete developer operation, existing task ID and responsible module |
| Stable references | Runtime/SDK/C# versions, official release, upstream SHA/path/symbol/read ranges |
| Public declaration | Namespace, package, exact signatures, constraints, nullability/defaults |
| Semantics | Validation, results, errors, cancellation, lifetime, concurrency, reentrancy, capabilities |
| Native path | Managed adapter, ABI operation/layout/status, Rust adapter, Engine call/state/release |
| Cost | Calls, allocations, copies, pins, retained bytes, queues/runtime, complexity and measurement plan |
| Consumer experience | Install/using/minimum config; manual/DI; minimal and advanced source |
| Compatibility | Source/binary/behavior/native ABI, migration/Obsolete policy |
| Documentation | XML symbol IDs, generated reference, guides, sample evidence states |
| Validation | Actual commands/platforms/toolchains/logs/hashes; unexecuted obligations separate |
| Independent review | Findings, actual remediation, final exact-content confirmation |

Do not treat this form's existence as passing review or product acceptance.
