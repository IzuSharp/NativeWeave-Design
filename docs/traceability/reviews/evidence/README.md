# Raw independent review results

The following JSON files were produced by toolchain_verification's independent review process and archived byte for byte by the integrator. They are not product acceptance manifests and must not be used as proof of C#/Rust or Native AOT execution.

| File | Meaning |
| --- | --- |
| [nativeweave-independent-validator-review.json](nativeweave-independent-validator-review.json) | Initial 25 groups of structural/synthetic-evidence checks; 24 groups met expectations. One positive control was rejected because it used the old log-array format |
| [nativeweave-independent-evidence-followup.json](nativeweave-independent-evidence-followup.json) | All 13 check groups met expectations after correction to the stdout/stderr log schema |
| [nativeweave-validator-final-followup.json](nativeweave-validator-final-followup.json) | Rechecks of dependency commit/hash changes, route selection, paths, and identity fields against the final validator |
| [async-quiescence-independent-review.json](async-quiescence-independent-review.json) | Output from the independent rerun of root's finite model, including assumptions and unproven scope |

See [toolchain-review.md](../toolchain-review.md) for complete findings, fixes, and recheck descriptions. Synthetic subjects and repeated-letter hashes are test fixtures; they do not indicate that corresponding Git commits or accepted evidence exist.

