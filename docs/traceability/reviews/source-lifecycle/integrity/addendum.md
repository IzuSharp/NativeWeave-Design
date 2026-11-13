# Independent addendum: source-lifecycle evidence integrity

**Decision: approve the evidence archive and verifier at the exact hashes in `final-review.json`. No integrity finding remains open.** This is evidence preservation and gate review, not another Rust/C# execution, independent approval of the reviewer's own Database implementation, or product acceptance.

Reviewer: `/root/design_source_review`. The reviewed verifier and integrity workflow were authored by `/root`.

## Provenance and raw bytes

The reviewer independently retrieved the official GitHub run, jobs and artifacts metadata for run `43375871731`. The run and all four jobs report success for source `de43481581df9876cb2d0aed5de2db796d048c9d`. The four original ZIP files had already been downloaded by the author; the reviewer independently computed their SHA256 and sizes against the freshly retrieved official API records, opened each ZIP, and compared every member with the repository archive.

All **56 raw members match exactly**. The two Server artifacts contain 12 members each, and the two Database artifacts contain 16 members each. Both Server artifacts include the hidden `.gitattributes` input; no build cache is archived. Original ZIPs, fresh provider identities and the independent comparison result are retained in this bundle.

The twenty per-job source inputs comprise **15 byte-exact matches and five explicit LF-to-CRLF conversions**, all five in Database Windows. The verifier checks both Git-blob and real checkout hashes and permits only that exact transformation in the declared Database Windows case. Raw Windows input/log bytes remain unchanged. The earlier strict byte-identity audit failure is honestly recorded as an audit finding rather than a Rust-test failure.

The archived output supports **12 distinct tests and 24 platform test executions**. Preservation of those results does not create a new execution, and the evidence/merge commit is not substituted for the tested source commit.

## Verifier and workflow

The reviewer read the final verifier and independently executed it successfully. Its final result checks 56 raw files, 20 input identities, 24 platform test executions, 15 specification hashes, 50 historical review files, 10 frozen Server source/doc/workflow files with their raw/supporting review evidence, the 59-file Database review list, and six Interop replication-review inputs. Registry contracts remain proposed; the run reports zero accepted contracts and no product Delivery.

The verifier checks current **committed** fixture inputs against the tested source. It is intended to run in a clean CI checkout; this is not a general detector for arbitrary uncommitted workspace edits. It checks the declared manifests and exact preserved bytes. The separate fresh-provider/ZIP comparison above supplies the independent provenance check performed during this review.

Two findings were closed:

| ID | Finding | Disposition |
| --- | --- | --- |
| EVID-REV-001 | The integrity workflow initially omitted fixture/source-workflow changes from its path trigger, allowing a checked input to change without this gate running. | Added both new fixture paths, the source-lifecycle workflow, Interop replication, native-slices assets and their verification mappings. This invokes read-only integrity checks and does not repeat Interop experiments. |
| EVID-REV-002 | The initial verifier covered historical migration reviews but not the new review copies described by the surrounding documentation. | Final verifier binds the Server manifest/raw/supporting files, Database file-list digest and checks, and Interop reviewed-input hashes. |

Final frozen hashes:

| File | SHA256 |
| --- | --- |
| `verification/source-lifecycle/verify.py` | `3ef508dcf44cdd623663620a9cf0b568dcde3664592ca340fd8a6189275012e2` |
| `.github/workflows/source-lifecycle-integrity.yml` | `d5cb982d0657c1acd2ed63c7ec1ab04da313f551f1d3823a74928e54a8c12578` |
| `verification/source-lifecycle/results.json` | `a08300281336fca4a6ca89d067b4dac49f767ffa34c738288c50998d74365d0f` |
| `verification/source-lifecycle/README.md` | `beae555a88f46ab47d4ca1505a9c3176487c7be75748ebe165331d49693fe11c` |

The four-job source workflow remains the separately reviewed `81177ac3cce246b402db7275076f26be86c1ac4aa7d47ca8f7c44836c0e40965` version. The addendum does not claim a future integrity CI run has already completed; it records the independent local execution of the final verifier and actual previously completed four-job research run.
