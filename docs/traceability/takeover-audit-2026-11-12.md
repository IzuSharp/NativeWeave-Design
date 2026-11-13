# Complete takeover audit and execution order

Baseline: Design `ba21ecb5c2299b303584b120f2e6bd1c6d74783a`, Plan
`5b346ebb5acdb387077d0faae16b00bbc77cb299`; product main
`658ed6a410783de356a7b9b2cd6601336fff5148`, PR1 closed without merge.
These were read from GitHub before edits. The machine-readable
[per-ID inventory](takeover-audit-2026-11-12.json) records actual baseline bytes, not a directory-count estimate.

## Starting evidence

17 Research tasks already have all three canonical report/evidence/coverage files:
R07–R09, R11, R19–R31. R01/R03 also have substantive specialised studies and actual
experiments outside the canonical triplet. The other 15 R scopes lack canonical triplets.
File presence is not a completeness or independent-acceptance claim.

16 D outputs already exist: D01,D02,D04–D08,D10,D11,D14–D20. D03,D09,D12,D13,D21,
the ten D22–D31 fragments and D32's declared review output are missing. D19 exists although
C-PROTOCOL's registry spec path is still null. This is a concrete registration gap.

All 21 contracts are proposed; 10 R partially_evidenced /24 planned and 4 D partially_evidenced /
28 draft_ready are the registered starting states. There are no accepted task manifests to inherit.

## Architecture findings

| Finding | Actual conflict | Correction owner |
|---|---|---|
| ALIGN-01 | C# First and Rust-when-justified wording lets required native domains become managed | Charter, ADR-0003, current policies and all packets |
| ALIGN-02 | Kestrel/Rust remain selectable product Hosts; B15/B17 are alternatives | D18/D19, B15/B17 and dependent graph/policy checks |
| ALIGN-03 | Earlier DB reports still select schema-specific SeaORM and per-entity native builds | R19–R25, D14–D17 and DB task fragments |
| ALIGN-04 | Dynamic SeaORM projections are easy to overstate as complete runtime-typed relations | Source-level loader/Entity constraints and explicit native relation scope |
| ALIGN-05 | Old LINQ/managed-query wording conflicts with typed native-backed Fluent | R23/R24, D16/D17, B09–B14 |
| ALIGN-06 | Existing research and specs absent from progress/registry bookkeeping | Per-ID evidence audit, exact hash and actual review before state change |
| ALIGN-07 | Research/design acceptance and future production tests are intermixed | Scoped acceptance with separate concrete Delivery obligations |
| ALIGN-08 | Missing ten implementation fragments leave packets without integrated worktree instructions | D22–D31, preserving the 48 task IDs and exclusive scope |
| ALIGN-09 | Historical current/latest/unsupported claims can outlive later facts | Dated source/toolchain recheck; preserve historical observations |

## Execution order on the existing graphs

Four parallel owners work in disjoint directories: Interop (R02–R12,R15,R16 and related D),
Database (R19–R25,R31 and related D), Server/extensions (R26–R30,R32–R34 and related D),
integration/platform (R01,R13,R14,R17,R18,D01,D10,D11,D13 and Plan fragments).
Owners first reconcile existing facts and identify missing source/experiment evidence.

ABI/ownership/async/callback/buffer/error/runtime interfaces form the shared review frontier.
DB and Server source analysis and documentation continue in parallel; they only wait on precise
interface decisions when finalising dependent contracts. Toolchain, packaging, performance method,
extension boundaries and future task steps likewise proceed in parallel.

After each substantive batch, freeze source/artifact identities, independently review the actual
changed bytes, save to GitHub and propagate exact Design pins into Plan. Conclude with per-ID
acceptance or specific blockers, cross-domain review, all 114 packets/three graphs validation and
unchanged product verification. This is an execution order, not an additional planning graph.
