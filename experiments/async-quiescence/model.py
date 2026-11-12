#!/usr/bin/env python3
"""Finite research model only. No C#/Rust, OS or weak-memory verification."""
from collections import deque
from dataclasses import dataclass, replace, asdict
from hashlib import sha256
from pathlib import Path
import json
import platform
import sys

@dataclass(frozen=True)
class State:
    closing: bool = False
    cancel_seen: bool = False
    native_finished: bool = False
    callback: int = 0  # 0 absent, 1 queued, 2 entered, 3 published, 4 returned
    native_quiescent: bool = False
    result: str = "pending"
    publications: int = 0
    call: int = 0  # 0 not acquired, 1 active, 2 ended
    call_used: bool = False
    freed: bool = False
    free_count: int = 0
    invalid_access: bool = False

def publish(s, outcome):
    if s.result == "pending":
        return replace(s, result=outcome, publications=s.publications + 1)
    return s  # compare/exchange is abstracted as one atomic step

def transitions(s, guarded):
    if not s.closing:
        yield "Dispose/close admission", replace(s, closing=True)
    if not s.cancel_seen:
        yield "Publish cancellation if pending", replace(publish(s, "canceled"), cancel_seen=True)
    if not s.native_finished:
        yield "Native finishes and queues callback", replace(s, native_finished=True, callback=1)
    if s.callback == 1:
        yield "Enter callback/dereference context", replace(
            s, callback=2, invalid_access=s.invalid_access or s.freed)
    if s.callback == 2:
        yield "Publish completion if pending", replace(publish(s, "success"), callback=3)
    if s.callback == 3:
        yield "Callback exits", replace(s, callback=4)
    if s.native_finished and s.callback == 4 and not s.native_quiescent:
        yield "Native acknowledges no future callbacks", replace(s, native_quiescent=True)
    if s.call == 0 and not s.closing and not s.freed:
        yield "Acquire call lease", replace(s, call=1)
    if s.call == 1 and not s.call_used:
        yield "Use call lease", replace(
            s, call_used=True, invalid_access=s.invalid_access or s.freed)
    if s.call == 1:
        yield "Release call lease", replace(s, call=2)
    allowed = s.closing and s.result != "pending" and not s.freed
    if guarded:
        allowed = allowed and s.native_quiescent and s.call != 1
    if allowed:
        yield "Reclaim context", replace(s, freed=True, free_count=s.free_count + 1)

def violation(s):
    if s.invalid_access:
        return "access_after_free"
    if s.publications > 1:
        return "more_than_one_terminal_publication"
    if s.free_count > 1:
        return "double_free"
    return None

def explore(guarded):
    initial = State()
    q = deque([initial])
    paths = {initial: []}
    edges = 0
    violations = []
    reclaim_states = 0
    while q:
        s = q.popleft()
        problem = violation(s)
        if problem:
            violations.append({"property": problem, "trace": paths[s], "state": asdict(s)})
            continue
        if s.freed:
            reclaim_states += 1
        for event, target in transitions(s, guarded):
            edges += 1
            if target not in paths:
                paths[target] = paths[s] + [event]
                q.append(target)
    return {
        "reachable_states": len(paths),
        "exploration": "branches are pruned at the first safety violation",
        "transitions": edges,
        "reclaim_states": reclaim_states,
        "violating_states": len(violations),
        "first_counterexample": violations[0] if violations else None,
        "checked_properties": ["access_after_free", "terminal_publications<=1", "free_count<=1"],
    }

def main():
    naive, guarded = explore(False), explore(True)
    if not naive["first_counterexample"]:
        raise AssertionError("negative control failed: early reclaim was not rejected")
    if guarded["violating_states"] != 0 or guarded["reclaim_states"] == 0:
        raise AssertionError("candidate fails safety or never reaches any reclaim state")
    report = {
        "experiment_id": "EXP-ASYNC-QUIESCENCE-001",
        "status": "model_executed",
        "model_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine()},
        "scope": "one operation, one native callback, one cancel request, one optional call lease",
        "unsafe_early_reclaim": naive,
        "candidate_barrier": guarded,
        "assumptions": [
            "Transitions are atomic with sequential consistency; no machine memory model.",
            "Native owns a callback obligation until callback return and acknowledged quiescence.",
            "No callback is issued after the native quiescence acknowledgement.",
            "Completion publication abstracts a correct atomic compare/exchange.",
            "Call admission closes atomically with Dispose; each acquired lease releases at most once."
        ],
        "not_proven": [
            "liveness/fairness, progress under lost notifications, shutdown deadlock",
            "multiple operations/callbacks, duplicate malicious callbacks, ABA/token overflow",
            "start-return and cancellation-registration synchronous reentrancy",
            "managed cancellation callback/context leases and CancellationTokenRegistration disposal",
            "real SafeHandle/GCHandle implementation, pinning, weak memory, FFI/ABI",
            "C# or Rust compilation, Windows/Linux AOT, performance or production acceptance"
        ],
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("result.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output), "naive_states": naive["reachable_states"],
                      "counterexample": naive["first_counterexample"]["trace"],
                      "candidate_states": guarded["reachable_states"],
                      "candidate_violations": guarded["violating_states"],
                      "reclaim_states": guarded["reclaim_states"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
