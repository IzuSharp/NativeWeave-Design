# Rxx — Topic title

Status: research-draft; author: ; date: ; input commit: .

## Research questions and boundaries
List the questions to confirm/refute, non-goals, and interfaces shared with other R tasks.

## Source evidence table
| Evidence ID | repo@full SHA (optional tag) | File/symbol/line range | Scope actually read | Conclusion category | Paths still missing |
| --- | --- | --- | --- | --- | --- |

## Call chain
Public API → adaptation → ABI → implementation → state → error → release → tests; distinguish steps actually traced from those still to be traced.

## Comparison
Cover at least pure C# AOT and reasonable native candidates; list correctness, costs, capabilities, licenses, and maintenance burden, not just advantages.

## Exceptions and races
List individually the counterexamples and expectations required by this task for cancellation, shutdown, reentrancy, disconnection, empty/oversized input, and similar cases.

## Experiments/proofs
Provide assumptions, invariants, code locations, commands, environments, exit codes, and logs; use not_run when not executed.

## Conclusions
Classify as source_confirmed/test_confirmed/official_doc_confirmed/inferred/pending/refuted.

## Design / Plan outputs
Contract IDs/versions, candidate APIs, D tasks to prepare, implementation acceptance, and impact scope.

## Coverage/licenses/independent review
Read/unread inventory; reuse risks; finding IDs and next steps. Do not unilaterally mark the original design as finally accepted.
