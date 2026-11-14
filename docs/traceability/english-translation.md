# Authoritative English documentation

The current technical documentation is maintained in English. This migration renders the accepted Chinese content one-to-one; it does not change the architecture, interfaces, numeric constraints, dependencies, technical versions, acceptance criteria, or authorization to implement the product.

## Source and scope

- Accepted Design source: `08e3aaee73aad174620dcff18ed21b3b14c5e632`.
- Accepted Plan source: `eff98a38068478cd4c2abb4ea66c62330156941b`.
- Design translation scope: 64 existing files, including current research, specifications, requirements, traceability, templates, registry titles, and evidence navigation.
- Plan translation scope: 139 documentation, graph, fragment, and renderer files, plus the completion validator's corresponding English heading literal.
- All 34 Research tasks, 32 Documentation tasks, and 21 contracts retain their accepted technical meaning. All 48 Delivery tasks retain `planned_candidate` / `not_authorized`.

The [translation manifest](../../english-translation-manifest.json) enumerates every source and target content hash, actual translation author, independent review, and retained original-language evidence file. The current [contract acceptance index](../contracts/acceptance-index.json) records the exact acceptance bindings; file existence alone is not acceptance.

## Independent semantic review

Translators worked in separate worktrees. Other executors compared the complete source and target changes, checked repeated text against every occurrence, and reviewed requirement strength, uncertainty, historical status, ownership, cancellation, quiescence, commit admission, numeric constraints, identifiers, links, code, and cross-file terminology. The [English review records](reviews/english-translation/) preserve their actual scope, exact input hashes, findings, author corrections, and subsequent rechecks.

The registry and task graphs contain acceptance references to reports about their contents. To avoid a hash-reference cycle, review of those files uses `semantic_projection_v1`: only their content/source/evidence/review binding fields are removed from the projection. IDs, versions, statuses, architecture and authorization values, dependencies, paths, and all prose remain in the independently reviewed projection. The manifest pins the final complete file bytes; input snapshots and independent binding attestations validate the removed binding fields separately.

## Preservation of prior acceptance and evidence

The original technical acceptance is preserved at the accepted source commits and in the original evidence/review directories. New input snapshots, evidence manifests, and review wrappers use a separate `verification/english-translation/` directory. Reviewer-authored binding attestations are stored under `docs/traceability/reviews/english-translation/`. Each new subject identifies its original accepted subject and the exact old evidence and review hashes. Validation compares these provenance claims with the actual accepted Git objects.

Original experiment sources, commands, stdout/stderr, failures, toolchain identities, Windows/Linux results, and frozen reviews remain unchanged. Sixteen Design files retain original-language content only as immutable historical reviews, captured patches, executed migration/recovery programs, or an observed takeover audit. They are listed individually with exact hashes and reasons in the manifest. They are historical evidence, not a second authoritative documentation edition. The evidence-directory README is current navigation and has been translated.

No research experiment is rerun or relabelled as a run against the English commit. No formal Delivery task is executed, and no product repository, license, permissions, or protection rules are changed. Existing source requirements that describe historical candidate routes remain faithful to that historical context.

## Terminology

| Term | Usage in this translation |
| --- | --- |
| Source-Driven Deep Native Integration | The existing NativeWeave integration approach |
| Native AOT | The existing .NET publication and execution mode |
| Ownership / lifetime | Resource ownership and the interval in which its use is valid |
| Logical admission / physical lease | The distinct admission and physical-lifetime concepts in the accepted contracts |
| Quiescence / retirement / reclamation | The separate quiescence, retirement, and reclamation conditions defined by the original protocols |
| Task packet | One of the 114 existing self-contained task instructions |
| Acceptance binding | Exact subject, source, dependency, evidence, and review linkage |
| Independent review | An actual different executor's scoped review; not a second GitHub account or fabricated approval |

## Verification and merge order

`python3 tools/verify_english_translation.py` checks coverage, exact source and target bytes, immutable originals, machine values, numeric/code/link preservation, independent translation review, and contract acceptance bindings. `--preflight` omits acceptance and independent-review enforcement and is never the final CI gate.

Merge Design after its complete review, binding attestations, and CI pass. Plan then pins the exact Design merge commit and passes its existing graph, mutation, historical-evidence, schema, and complete-acceptance checks together with the English translation and provenance checks before merging.
