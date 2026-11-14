# EXP-ASYNC-QUIESCENCE-001: A cancellation result does not imply resource quiescence

Status: **research model actually executed; not product implementation verification**. Author: root; 2026-11-12. Source: [model.py](model.py); actual results: [result.json](result.json).

## Problem and counterexample

A native operation may still have a completion callback pending after the C# side has published a Canceled result to the application. If Dispose releases the callback context after checking only the Task terminal state, a later native callback entry will access the freed context.

This model enumerates finite interleavings of one operation, one native callback, one cancellation request, an optional call lease, and Dispose. The negative-control model explores 226 states (pruning when a safety counterexample is encountered, rather than exploring the full unpruned state space) and produces this counterexample:

1. Dispose closes admission for new calls.
2. The cancellation result is published to the application.
3. Native completion queues the callback.
4. The context is reclaimed based only on the terminal state.
5. The callback enters and dereferences the context, producing access_after_free.

## Results of the candidate fix within the model

The candidate reclamation condition additionally requires acknowledgement of native quiescence and zero active call leases. Exhaustive traversal finds 159 reachable states and 9 reclaimed states, with no counterexample for access to a freed object, duplicate terminal-result publication, or double release.

Safety is not “satisfied” by waiting forever: the model does contain reclaimed terminal states. However, checking only the existence of reclaimed states does not prove liveness; eventual progress under an actual scheduler still requires a proof of fairness, notification, and shutdown protocols.

## Assumptions

The cancellation event is abstracted only as result publication; it does not model the CancellationTokenRegistration callback itself, context leases, or unregistration waiting. Native quiescence does not replace quiescence of managed cancellation sources. State transitions are treated as sequentially consistent atomic steps; publish is abstracted as a correct CAS; native code issues no further callbacks after acknowledging quiescence; callback obligations remain until return; Dispose and call admission are mutually exclusive. A real implementation must implement each of these assumptions separately; atomic steps in the model cannot replace machine memory ordering or GCHandle protocols.

Not covered: multiple operations, multiple callbacks, reentrancy, start not yet returned, synchronous execution during cancellation registration, repeated malicious notifications, ABA/generation overflow, lost notifications, weak memory, deadlock, C#/Rust types and ABI, performance, or AOT on a real machine.

## Reproduction

```bash
python3 experiments/async-quiescence/model.py
```

The script requires the negative control to find a counterexample, checks the candidate model's safety counts, and checks for a nonzero number of reclaimable states. Exit code 0 means only that these finite checks succeeded. The results record Python/OS/architecture and the model SHA256. Subsequent R15 work may express a more complete protocol in an appropriate model such as TLA+/Loom; merely increasing the number of tools is not required.
