# Initial delivery: independent review, validation results, and boundaries

Date: 2026-11-12. Status: **research-bootstrap / proposed**. This record was compiled by the integrator; independent review comments remain in the respective reviewers' own files. It records the basis on which this bootstrap package may be reviewed and distributed; it does not accept the NativeWeave product architecture, ABI, or platform capabilities.

## 1. Actual deliverables in this round

Design contains the requirements charter, 28 requirement mappings, a source catalog, preliminary research with pinned versions, candidate boundaries, a registry of 21 proposed contracts, verification obligations, templates, a finite model, and review records. Plan contains 34 Research tasks, 32 Documentation tasks, 48 candidate Delivery tasks, three independent graphs, and 114 self-contained task packets.

After the initial Draft PR publication, the task packets were uniformly revised to 0.1.1 to specify where to locate inputs before merging. Contract versions remain 0.1.0-draft; all research/documentation/product statuses and route selections remain unchanged.

ArcForges Design/Plan are used only as references for formatting and organization. The content, dependencies, research obligations, and acceptance mechanisms in this bootstrap package come from the current NativeWeave goals; ArcForges technical choices and execution rules have not been inherited.

## 2. Actual independent review

| Review record | Author relationship and scope | Current disposition |
| --- | --- | --- |
| [toolchain-review.md](reviews/toolchain-review.md) | toolchain_verification reviewed root's candidate design, evidence policy, and model, and reviewed parallel_plan's three graphs/gates with synthetic fixtures; its own toolchain report does not count as independently accepted | The fixes and corresponding rechecks described for RV-TC-001–009 are complete within the stated scope |
| [domain-review.md](reviews/domain-review.md) | domain_research reviewed root's candidate domain boundaries and local domain dependencies in Plan; it did not treat its own domain report as independently accepted | DR-001–005 textual ambiguities and DP-001–004 local planning dependencies/start entry points are closed; detailed history and recheck hashes are preserved |

The final candidate-boundaries content SHA256 is `432fa9cb1863485e928b6a5dc5ecf3752afa5465cbf9b4c519b3247216122264`. The toolchain review snapshot predates the final precise-definition supplement for DR-003; the domain reviewer actually rechecked that delta. Old review snapshots have not been rewritten as reviews of the new file.

The main corrections include:

- Distinguishing Task results, local memory quiescence, connection-protocol reusability, and remote transaction effects; Unknown outcomes are retained in independent recovery records, and connections not confirmed clean are discarded.
- Defining the atomic idempotency boundary, multidimensional validation of typed queries, and logical memory budgets separately from measured RSS.
- Listing ordinary managed callback exceptions separately from invalid UCO-signature fail-fast behavior; native quiescence does not replace draining managed cancellation registrations.
- Binding specifications, task bodies, dependency implementation commits, evidence, and independent reviews to their actual content; checking output scopes with one-way containment.
- Removing false dependencies of foundational desktop specifications on entire mobile/GUI topics, of foundational DB codecs on complete ORM contracts, and of HTTP diagnostics on optional protocols.
- Including selected native/protocol packages in the conditional dependencies of the corresponding integration and release tasks; unselected routes do not block pure C# paths.

## 3. Validation actually executed in this round

| Check | Actual result | Evidence and limitations |
| --- | --- | --- |
| Plan graphs and gates | 114 nodes; 0 structural errors; no detected dependency cycles or exclusive write-scope conflicts; Research ready 34, Documentation ready 32, Delivery ready 0; accepted contracts 0 | Plan:verification/graph-validation.json; rerun by the integrator using the final files |
| Author fault injection | All 14 cases met expectations; invalid inputs emptied the ready set | Plan:verification/mutation-checks.json; rerun by the integrator |
| Schema | Self-checks of both schemas and Draft2020-12 validation of all three graphs passed | Plan:verification/schema-validation.json; actual execution record by parallel_plan |
| Integrated-file consistency | 28 requirements cover all 114 nodes with no unknown IDs; 22 JSON files parse; all 177 local Markdown link targets exist | The integrator actually checked both final directories; remote webpage availability and link-anchor validation are excluded |
| Independent gate counterexamples | Missing specifications, incorrect hashes, stale reviews, self-review, empty identities, out-of-scope outputs, changed task bodies, dependency changes, and similar cases were rejected as expected | [Original structural checks](reviews/evidence/nativeweave-independent-validator-review.json), [final recheck](reviews/evidence/nativeweave-validator-final-followup.json) |
| Independent execution-evidence checks | After correcting the log-format fixtures, all 13 groups of positive/negative controls met expectations | [Raw follow-up results](reviews/evidence/nativeweave-independent-evidence-followup.json); synthetic data, not actual AOT execution |
| Finite asynchronous state model | The negative control found access after free; the candidate had no checked violation within 159 explored states, with 9 reclaimed states | [Model and author results](../../experiments/async-quiescence/README.md), [independent rerun results](reviews/evidence/async-quiescence-independent-review.json) |

In the initial 25 independent gate fixtures, one positive control was rejected because it used the old log-array format; the original result was 24/25. The fixture was then corrected to the current stdout/stderr schema, and the 13 execution-evidence check groups passed. The original failure and explanation are preserved; historical executions are not all relabelled as passing. Final validator SHA256: `d4e393016bd75de523b78f2df9c989eb417dbc7bdd05ca9f23a1fbefb58888c9`.

The finite model's negative control explored 226 states, pruning violating paths after the first violation; this count is not the complete unpruned state space. The absence of candidate counterexamples is limited to one operation, one callback, sequential consistency, and the declared atomicity assumptions. It does not prove liveness, weak-memory behavior, multiple operations, actual GC/FFI, cancellation-registration callbacks, or the product implementation.

## 4. Items not yet executed or accepted

This environment provided no callable dotnet/rustc/cargo/clang and no Windows execution environment. This round performed no C#/Rust compilation, actual Native AOT publication or execution, database fault experiments, server workloads, performance comparisons, or product package releases. Reading tests in source files and actually executing tests are recorded separately. Preliminary research does not mean all 34 topics are complete.

All 21 technical contracts remain proposed. All product tasks remain planned_candidate. This review permits continued research, documentation drafts, and local change proposals; formal acceptance still requires evidence for exact versions and independent substantive review.

The graph validator checks only structure, file hashes, and manifest relationships. It cannot authenticate author identities or prove that commands actually ran merely from self-reported manifests. Formal evidence must be supported by trusted CI, obtainable artifacts/raw logs, or independent replay.

## 5. GitHub delivery boundaries

Design and Plan each use a `research/bootstrap-2026-11-12` branch and a Draft PR for this batch. Git trees retain upstream main as the parent commit and preserve the existing LICENSE; only this batch's files are added. The product repository is outside this batch's write scope. The main branch, repository permissions, and protection rules are outside this batch's modification scope.

Subsequent workers use their own task branches and Draft PRs; the integrator handles shared graphs, the registry, and root indexes. Starting a draft and accepting a specification are evaluated separately; neither “all research finished” nor “all of phase A complete” is imposed as a universal prerequisite. Actual GitHub records determine the latest remote commits and PR statuses.

After the initial Draft publication, the integrator found that default main did not yet contain the bootstrap files, so self-contained prompts needed explicit input entry points. All 114 task packets, the README, task index, and independent Review entry point now include the research branches and PR locations for both documentation repositories. At startup, workers must resolve and record each full commit SHA, verify the graph revision and packet hash, and then create task branches from their respective snapshots. Branches are for navigation only and do not replace immutable evidence; the two repositories are not assumed to update atomically. All task revisions, dependency versions, and packet hashes were updated together, and graph and Schema checks were rerun. Independent rechecking of this bounded supplement is recorded as DP-004 in domain-review; historical review snapshots are preserved.

