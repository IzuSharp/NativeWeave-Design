# Independent follow-up: localized raw-output classification

**Decision: accept the scoped checker repair and its verification. No blocking
finding remains.** Reviewer: `/root/supplement_review`; repair/check executor:
`/root/audit_scope`; integration author: `/root`. I did not author the helper,
exception manifest or regression programs. This is technical review, not another
GitHub account's approval.

The previous local research review remains unchanged at Design
`9f771b704b120823197884125597bb528a77c4b0`. The reported first PR12 English-gate
failure concerned seven preserved Windows stdout files containing localized .NET
output. Their raw bytes must remain intact. This follow-up reviews the subsequent
checker changes, not another native execution or contract acceptance.

## Scope and identity

The helper, checker, seven-entry exception manifest, regression source/results,
complete English-gate records and initial-input snapshots are bound by
`language-gate-review.json`. Research inputs remain Design
`4c5c385779b753a4f06e59d07f80ad27ca10a841`; the new checker is identified by exact
file hashes over the later `9f771b7` baseline, not misattributed to that research
commit. The final regression record correctly leaves its uncommitted checker
commit null. Current checker/helper bytes use canonical LF.

I read the complete helper and regression/capture programs and reviewed the
checker diff. The original translation, immutable-baseline, exact review and
contract-binding checks remain unchanged. The replacement final text classifier
keeps the existing rejection behavior while explicitly decoding text as UTF-8.

## Checks and conclusions

The helper permits only canonical relative stdout/stderr paths in this date's
Windows/Linux run directories. It verifies every entry's exact length/hash before
allowing any exception, rejects paths already in the stated source tree, and
checks the same-directory runner manifest, source commit, host, unique command
and matching stream digest. Path resolution must stay inside the repository.
Neither whole directories nor new prose, JSON metadata or source files receive
an exemption. All seven registered raw files still equal their earlier committed
execution bytes.

I checked all 23 regression outcomes and their exact source hashes. Each case
first establishes a valid seven-entry control, then tests the actual helper and
final classifier. The negatives cover tampering, malformed identity, host/source
mismatch, unbound or ambiguous commands, escaping paths, forbidden file types,
duplicates and unregistered CJK text. The historical-backfill case preserves the
other valid bindings and directly exercises source-tree membership rejection.
I also independently invoked the current helper against the seven actual files
and verified that an unregistered CJK prose file is rejected in an isolated
temporary directory.

The final complete English check exited zero with all six candidate input files
indexed in an isolated standard-name checkout. I rehashed those six inputs, both
raw output streams and all four regression source references. Its output records
64 translated files, 16 historical immutable originals, required independent
review and unchanged product authorization. This establishes the complete current
checker path, not just a helper-only test.

The earlier complete pass used a CRLF checker representation and earlier
regression metadata. I checked both runs' four output streams and the six exact
initial input snapshots; the earlier run is not presented as a current-byte pass.
The first PR failure record explicitly identifies its report source and does not
claim this executor downloaded the CI artifact.

## Finding disposition

`LH-REVIEW-003` — **New localized raw evidence lacked an English-classifier
category.** The seven streams are now admitted only through byte-exact,
runner-bound raw-evidence records. Arbitrary new CJK prose remains rejected; all
original English and immutable-source checks still run. The 23 regressions and
the final full check provide the actual resolution. **Closed.**

No native suite was rerun for this repair. No historical raw output, original
acceptance attestation, product source, task graph or Delivery authorization was
changed. Later GitHub CI status is separate from these exact local inputs.
