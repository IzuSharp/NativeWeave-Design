# Upstream provenance and reuse policy

Status: proposed engineering policy for `Korda-Orm-01`. This records the reviewed
public source baseline and the conditions for later implementation. No commercial
jOOQ source was acquired or used, and no upstream source archive is stored in this
documentation repository.

## Reviewed jOOQ baseline

| Item | Pinned reference |
| --- | --- |
| Release | [3.21.10](https://github.com/jOOQ/jOOQ/releases/tag/version-3.21.10), published 2026-11-17; observed latest stable release on 2026-11-28 |
| Tag and source commit | `version-3.21.10` → [`3c58109e7ab69772de75e640852935ee7e284177`](https://github.com/jOOQ/jOOQ/tree/3c58109e7ab69772de75e640852935ee7e284177) |
| Root license | [LICENSE](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/LICENSE) identifies Apache-2.0 and separately offered commercial licenses |
| Runtime license and attribution | [jOOQ/LICENSE.txt](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/LICENSE.txt), [jOOQ/NOTICE.txt](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/NOTICE.txt) |
| Metadata/codegen attribution | [jOOQ-meta/NOTICE.txt](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-meta/NOTICE.txt), [jOOQ-codegen/NOTICE.txt](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ-codegen/NOTICE.txt) |
| Reviewed semantic mapping | [Language model](language-model.md); [dialects and generation](dialects-and-generation.md) |
| Other dependency baselines | [Execution and AOT](execution-aot.md), including Dapper.AOT, Dapper and the selected .NET drivers |

The official [download archive](https://www.jooq.org/download/versions) confirms
the release series. A later patch or a mutable website is not an implicit source
upgrade: each implementation task uses the fixed commit in its input contract.

## Open-source and commercial boundaries

The root and reviewed runtime file headers allow the Apache-2.0 route for those
public files. This does not turn every feature mentioned in the manual, a Java
API comment, generated settings or a commercial distribution into available
Apache-licensed implementation material. The official
[edition comparison](https://www.jooq.org/download/) and
[licensing page](https://www.jooq.org/legal/licensing) distinguish open-source
and commercial offerings, including database/version support and third-party
components.

The distinction is visible in source. For example,
[Transformations](https://github.com/jOOQ/jOOQ/blob/3c58109e7ab69772de75e640852935ee7e284177/jOOQ/src/main/java/org/jooq/impl/Transformations.java)
contains commercial-gated paths, while many public node `accept` implementations
contain usable dialect-specific lowerings. Documentation of a transformation or
an empty generated branch is not its implementation. Such a capability must be
explicitly deferred, or implemented independently from SQL/database specifications
with its own evidence and tests. Record that distinction in its provenance entry.

Do not fetch commercial/trial source to fill public-source gaps. A future proposal
to use separately licensed material requires a distinct rights decision before
acquisition or incorporation. Do not claim this study inherits the complete
upstream regression suite: only test files actually present in an authorized
source can be reused. New conformance tests should specify SQL behavior and
identify the implementation or database reference used as their oracle.

## Obligations for translated or adapted code

Under [Apache-2.0 sections 2, 4 and 6](https://www.apache.org/licenses/LICENSE-2.0),
the engineering distribution rules are:

- Include the license with distributed copies or derivatives.
- Clearly identify modified/adapted source files and preserve relevant source
  copyright, patent, trademark and attribution notices.
- Preserve applicable NOTICE attribution in the distribution; omit only notices
  unrelated to incorporated material.
- Track third-party material separately. The reviewed jOOQ NOTICE files include
  Apache Commons Lang attribution; determine applicability from the actual files
  reused, not from the product name alone.
- Do not imply endorsement or acquire trademark rights through the source license.

A Java-to-C# translation is not a reason to erase provenance or attribution.
The product repository must maintain the actual license texts, applicable notices
and modified-source annotations when code is introduced. The present prose-only
study links those requirements; it does not distribute a translated runtime.

## Maintainable provenance records

Every substantive port or independently implemented replacement records these
fields alongside its maintained product/design entry:

| Field | Required content |
| --- | --- |
| Semantic operation | Stable operation or feature identifier and applicable SQL contexts |
| Origin | Repository, release, fixed commit, file and symbol; applicable file license |
| Reuse kind | Direct port, adapted implementation, specification-based implementation, or API inspiration only |
| Deliberate differences | C# idiom, dependency split, ownership change, explicit rejection of an upstream fallback, or supported version boundary |
| Tests | Maintained positive/negative semantic cases, differential reference and database profiles |
| Attribution | Applicable license/NOTICE source and product distribution location |
| Maintenance owner | Product module responsible for reviewing upstream fixes and regressions |

Keep one maintained record per meaningful operation family, not a raw output file
per experiment or agent. A short table in the module's specification is sufficient
until a structured catalogue has a real machine-validation consumer. Do not add
whole repositories, source dumps, generated hashes or intermediate research logs.

## Upgrade procedure

An upstream upgrade is an explicit bounded task. Resolve its tag to a commit,
review changes in the adopted operation families and inspect both implementation
and release-note bug fixes. Update semantic cases before changing the C# lowering.
Evaluate fixes involving NULL, alias scope, parameter ordering, nested rows and
query copying even when the public signature is unchanged. Do not assume a patch
release is behaviorally irrelevant.

Rerun affected pure semantic tests, the necessary real-database cases and native
consumers; select consumers through the product module dependency registry.
License/NOTICE changes and newly introduced third-party components are part of
the same review. Unrelated upstream changes do not force a full product rewrite.
Record retained deviations with reasons and keep the previous baseline visible
in ordinary Git history.

## Implementation acceptance boundary

An implementation slice is not accepted until its origin, rights, SQL behavior,
deliberate differences and applicable tests are reviewable. Documentation CI can
validate the maintained records; it cannot establish licensing rights for unseen
material, SQL correctness or product readiness. Source gaps and unexecuted tests
remain explicit limitations in the implementation plan.
