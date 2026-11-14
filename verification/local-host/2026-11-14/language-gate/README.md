# Supplemental raw-output language gate

The [initial PR12 failure](pr12-initial-ci-failure.json) concerns classification
of original localized Windows command output. The native fixtures did not need
their output translated or rewritten. Seven exact stdout files are now registered
in [raw-execution-language-exceptions.json](../raw-execution-language-exceptions.json).

`tools/local_host_raw_evidence.py` verifies every entry before granting any
exception: canonical relative paths within this date's Windows/Linux run trees,
only stdout/stderr extensions, no path in the declared existing source tree,
exact byte count and SHA-256, same-directory runner-manifest hash, actual source
commit and host identity, unique command name and the corresponding stream hash.
The allowed paths are added to the old immutable-original exceptions only for
the final tracked-text classifier. The original translation, immutable-history,
review and contract-binding checks remain in place. New prose, metadata or source
files receive no language exemption.

[negative-results.json](negative-results.json) records 23 actual checks against
isolated copies and the same final classifier used by the English gate. Each
case first validates the complete seven-entry control. The cases reject altered
bytes/lengths/hashes, changed runner identity, ambiguous or unbound commands,
traversal/absolute/historical paths, source and Markdown exceptions, duplicate
entries, invalid commits/authority and unregistered CJK prose or raw streams.
The source-tree backfill case preserves every other valid binding and checks
that membership itself rejects a raw file already in the later source commit.

The research input remains `4c5c385779b753a4f06e59d07f80ad27ca10a841`.
The validator is an uncommitted overlay on `9f771b704b120823197884125597bb528a77c4b0`,
identified by its exact source hashes; the research commit does not contain this
new helper. Both tool files use LF bytes matching Git's canonical representation.

`full-english.json` preserves an earlier successful complete run using the initial
CRLF representation of the checker. Its recorded overlay hashes distinguish that
execution from the final LF inputs; [initial-inputs.json](initial-inputs.json)
binds its six exact inputs, including the earlier regression metadata before the
research/checker identity fields were separated. It is not a current-byte pass.
The definitive final-input check is recorded
separately as `full-english-final.json` with its raw stdout/stderr. Both runs use a
standard-name isolated checkout and index the candidate validator/regression
inputs listed in each record before the actual tracked-text check. Neither run
rebuilds native fixtures or accepts new contracts.
