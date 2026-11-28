# Current design and outcome boundaries

## Independent proposed direction

[Korda-Orm-01](docs/korda-orm/README.md) studies a new pure C# SQL framework derived
from jOOQ semantics, with independent rendering and mature .NET driver execution.
Its research probes and proposed contracts are separate from the existing product
below. Design review does not authorize implementation, cutover, deletion or merge.
The [Plan handoff](https://github.com/IzuSharp/Plan/blob/task/Korda-Orm-01-linux/ledger/evidence/batches/Korda-Orm-01/handoff-linux.md)
owns progress and the independent implementation graph.

## Existing product

Korda's current product boundary is a C# Fluent ORM for PostgreSQL and SQLite,
with Native AOT, C++20/libpq/sqlite3 execution and independent provider packages.
[ADR-0006](docs/decisions/ADR-0006-database-cpp-native.md),
[ADR-0007](docs/decisions/ADR-0007-fluent-orm-experience.md) and the
[database contracts](docs/database/current-product.md) explain those decisions.

## Execution parity experiments

[DB-Exec-Parity-01](docs/database/execution-parity-01.md) retains the measured
strategy, rejected experiments and their reasons. Its latest recorded scope is
finite local diagnostics and ordinary short comparisons; the unexecuted long
campaign was cancelled. Final-frame rental08 and pull-local07 were rejected after
short results. Proposed or provisional changes are not product acceptance or proof
of Dapper.AOT parity. These historical task records do not authorize new work.

## Earlier implemented execution path

[The 17da execution record](docs/database/execution-path-17da.md) describes the
command, native batch, generated reader, completion and Find paths of Korda
`17da07e391ba867bbf195baa2e9fdc0bdc0cc0aa`. The
[cursor-pull decision](docs/database/cursor-pull-execution.md) and
[command completion decision](docs/database/command-completion-execution.md)
retain earlier design alternatives and ownership reasoning.

Plan's [final report](https://github.com/IzuSharp/Plan/blob/main/ledger/evidence/batches/DB-Perf-01/execution-refactor/continuation-8/final-report.md)
records the earlier four-cell local campaign and its limitations. It does not
establish framework-only zero allocation, Dapper parity or exhaustion of all
optimization possibilities. Product implementation, current checks and delivery
status are owned by Korda and Plan, not by this document's CI result.

## Repository maintenance

Design CI now validates current registered structured documents only, selected by
the actual PR or main-push diff. It does not replay accepted historical commits,
run benchmarks or store execution material. See [the CI guide](eng/ci/README.md).
