"""Finite logical-byte model, NOT a Tokio/.NET/native runtime test.

Three producers, one consumer, fixed item sizes, bounded queue and byte credit.
Cancellation of an in-flight item records intent; only consumer release returns
credit. Enumerate every reachable abstract state under these finite rules.
"""
from collections import deque
import json
import platform
import sys

SIZES = (1, 2, 2)
GLOBAL_CREDIT = 3
QUEUE_CAPACITY = 1
# 0 waiting, 1 credit reserved, 2 materialized, 3 queued, 4 consuming, 5 done


def successors(state):
    phase, cancel = state
    credit = sum(n for n, p in zip(SIZES, phase) if 1 <= p <= 4)
    queued = phase.count(3)
    consuming = phase.count(4)
    for i, current in enumerate(phase):
        next_values = []
        if current == 0 and credit + SIZES[i] <= GLOBAL_CREDIT:
            next_values.append((1, cancel))
        if current == 1:
            next_values.append((2, cancel))
        if current == 2 and queued < QUEUE_CAPACITY:
            next_values.append((3, cancel))
        if current == 3 and consuming == 0:
            next_values.append((4, cancel))
        if current == 4:
            next_values.append((5, cancel))  # actual owner release
            if not cancel & (1 << i):
                next_values.append((4, cancel | (1 << i)))  # cancellation only
        if current in (0, 1, 2, 3):
            next_values.append((5, cancel | (1 << i)))
        for target, new_cancel in next_values:
            updated = list(phase)
            updated[i] = target
            yield (tuple(updated), new_cancel)


def main():
    initial = ((0, 0, 0), 0)
    visited = {initial}
    pending = deque([initial])
    reverse = {}
    transitions = 0
    max_allocated = 0
    terminal = set()
    while pending:
        state = pending.popleft()
        phase, cancel = state
        reserved = sum(n for n, p in zip(SIZES, phase) if 1 <= p <= 4)
        allocated = sum(n for n, p in zip(SIZES, phase) if 2 <= p <= 4)
        assert 0 <= allocated <= reserved <= GLOBAL_CREDIT
        assert phase.count(3) <= QUEUE_CAPACITY
        assert phase.count(4) <= 1
        for i, current in enumerate(phase):
            if current == 4 and cancel & (1 << i):
                assert reserved >= SIZES[i]  # cancel never frees in-flight owner
        max_allocated = max(max_allocated, allocated)
        if all(p == 5 for p in phase):
            terminal.add(state)
        for next_state in successors(state):
            transitions += 1
            reverse.setdefault(next_state, set()).add(state)
            if next_state not in visited:
                visited.add(next_state)
                pending.append(next_state)
    # Existential reachability: each state has a finishing path. This does NOT
    # prove scheduler fairness or completion under endless external stalls.
    can_finish = set(terminal)
    pending = deque(terminal)
    while pending:
        for previous in reverse.get(pending.popleft(), ()):
            if previous not in can_finish:
                can_finish.add(previous)
                pending.append(previous)
    assert can_finish == visited
    queue_only_example = {
        "queue_capacity": 1, "chunk_size": 4,
        "queued_items": 1, "producers_waiting_with_materialized_payload": 3,
        "retained_payload_bytes": (1 + 3) * 4,
        "queue_capacity_times_chunk_size": 1 * 4,
    }
    assert queue_only_example["retained_payload_bytes"] > queue_only_example["queue_capacity_times_chunk_size"]
    print(json.dumps({
        "experiment": "R29 finite credit and cancellation model",
        "status": "passed", "states": len(visited), "transitions": transitions,
        "terminal_states": len(terminal), "all_states_have_finishing_path": True,
        "global_credit": GLOBAL_CREDIT, "max_allocated_bytes": max_allocated,
        "producer_sizes": SIZES, "queue_capacity": QUEUE_CAPACITY,
        "queue_only_counterexample": queue_only_example,
        "python": sys.version, "os": platform.platform(),
        "limitations": ["Finite abstract logical-byte state space only",
                        "Not a memory allocator, RSS or runtime scheduling model",
                        "No Tokio or .NET execution; no AOT verification",
                        "Existence of finish path does not prove fairness/liveness under arbitrary stalls",
                        "Native-copy double-credit and callback retirement need separate product tests"]
    }, indent=2))


if __name__ == "__main__":
    main()
