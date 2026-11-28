# Korda-Design

Design specifications, interface contracts, architecture decisions and research
conclusions for [Korda](https://github.com/IzuSharp/Korda). Korda is a strongly typed
C# Fluent ORM for PostgreSQL and SQLite, with Native AOT and a C++20/libpq/sqlite3
execution layer. [Plan](https://github.com/IzuSharp/Plan) owns task plans, progress
and final delivery conclusions.

## Start here

The independent [Korda.Orm architecture study](docs/korda-orm/README.md) proposes a
jOOQ-derived pure C# SQL language with mature .NET execution and Native AOT.
It is under review and is not the currently implemented C++ product. Its design,
contracts and implementation plan do not inherit historical task dependencies.

| Document | Purpose |
| --- | --- |
| [Current phase](CURRENT-PHASE.md) | Current design and measured experiment boundaries |
| [API index](docs/api/README.md) and [compiled reference index](docs/api/reference.md) | Current public surface and reference ownership |
| [Database product](docs/database/current-product.md) and [Fluent ORM](docs/database/fluent-orm.md) | Behavior and implementation boundaries |
| [Execution strategy](docs/database/execution-parity-01.md) | Retained and rejected experiments, reasons and limitations |
| [Query semantics](docs/database/query-semantics.md) | Fixed and dynamic query paths |
| [Attribute naming](docs/database/db-attribute-names.md) | `Db` names and compatibility |
| [Contract registry](docs/contracts/registry.json) | Design contract identities and dependencies |
| [Architecture decisions](docs/decisions/) | Scope and architectural rationale |
| [C# API standard](docs/standards/csharp-public-api-and-documentation.md) | API and documentation requirements |
| [Research reports](docs/research/topics/) | The 34 authored topic conclusions |
| [CI registration guide](eng/ci/README.md) and [AGENTS.md](AGENTS.md) | Document placement and local validation |

## Documentation CI

The single workflow uses [eng/ci/registry.py](eng/ci/registry.py) to map paths to
additive types and their checks. An ordinary article under `docs/` or `templates/`
selects no checks. Current structured checks cover contract IDs/dependencies and
specification targets, the API coverage schema and references, and historical
declaration catalog consistency. CI infrastructure changes also run real-Git
self-tests. Schema changes recheck the current coverage documents.

```bash
python3 -m pip install -r eng/ci/requirements.txt
python3 eng/ci/run.py --all
python3 eng/ci/run.py --base origin/main --head HEAD --event pull_request
```

PR and main-push selection share the same Python runner. There is one shallow
checkout, no historical acceptance replay, no product builds or benchmarks, and
no artifact upload. Full history is unnecessary for CI. See the guide for exact
local diff semantics and adding a new type.

## Retained history and repository contents

The current tree keeps useful specifications, decisions, research conclusions and
one canonical catalog of historical declaration signatures and semantic policies.
Historical statuses retain their original scope; they do not accept changed bytes
or claim product execution. [The history entry](docs/history/pre-db-scope-01/README.md)
identifies the prior scope without duplicating its full snapshot.

Raw verification output, copied snapshots, recovery receipts, experiment binaries,
archives and scripts used only to collect or replay those materials have been
removed from the current tree through normal commits. Git history is unchanged.
Temporary material stays on the execution machine and can be regenerated.
