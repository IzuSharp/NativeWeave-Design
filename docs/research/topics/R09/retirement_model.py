#!/usr/bin/env python3
"""Finite protocol model, not a C#/Rust/GC/FFI implementation proof."""
from collections import deque
from dataclasses import dataclass, replace, asdict
from hashlib import sha256
from pathlib import Path
import json
import platform
import sys


@dataclass(frozen=True)
class State:
    setup: int = 0  # 0 created, 1 registering, 2 registered, 3 start frame, 4 returned
    accepted: bool = False
    rejected: bool = False
    registration_live: bool = False
    registration_drained: bool = False
    cancel: int = 0  # 0 not invoked, 1 executing, 2 exited
    callback: int = 0  # 0 absent, 1 queued, 2 entered, 3 notice recorded, 4 returned
    terminal: bool = False
    publications: int = 0
    closing: bool = False
    control: int = 0  # 0 not acquired, 1 lease, 2 access performed, 3 exited
    retired: bool = False
    freed: bool = False
    frees: int = 0
    invalid_access: bool = False


def transitions(s, omitted):
    if s.setup == 0:
        yield "Begin cancellation registration", replace(s, setup=1, registration_live=True)
    if s.setup == 1:
        yield "Publish returned registration", replace(s, setup=2)
    if s.registration_live and s.cancel == 0:
        yield "Cancellation callback enters (possibly during Register)", replace(s, cancel=1)
    if s.cancel == 1:
        yield "Cancellation callback exits", replace(s, cancel=2)
    if s.setup == 2:
        # The protocol permits an already requested cancellation to skip start.
        if s.cancel != 0:
            yield "Skip start after observed cancellation", replace(
                s, setup=4, rejected=True, terminal=True, publications=1)
        yield "Enter native start frame", replace(s, setup=3)
    if s.setup == 3 and not s.accepted and not s.rejected:
        yield "Commit native start", replace(s, accepted=True)
        yield "Reject start with no callback obligation", replace(
            s, setup=4, rejected=True, terminal=True, publications=1,
            invalid_access=s.invalid_access or s.freed)
    if s.setup == 3 and s.accepted:
        yield "Native start frame accesses operation and returns", replace(
            s, setup=4, invalid_access=s.invalid_access or s.freed)
    if s.accepted and s.callback == 0:
        yield "Native work finishes and queues terminal callback", replace(s, callback=1)
    if s.callback == 1:
        yield "Native terminal callback enters and resolves cookie", replace(
            s, callback=2, invalid_access=s.invalid_access or s.freed)
    if s.callback == 2:
        yield "Record terminal notice", replace(s, callback=3)
    if s.callback == 3:
        yield "Native terminal callback returns", replace(s, callback=4)
    if s.callback >= 3 and not s.terminal:
        yield "Managed completion worker publishes Task outcome", replace(
            s, terminal=True, publications=s.publications + 1)
    if not s.closing and s.control == 0 and s.setup >= 1 and not s.freed:
        yield "Acquire an optional ordinary control-call lease", replace(s, control=1)
    if s.control == 1:
        yield "Control call accesses native operation", replace(
            s, control=2, invalid_access=s.invalid_access or s.freed)
    if s.control == 2:
        yield "Release control-call lease", replace(s, control=3)
    if s.terminal and not s.closing:
        yield "Close ordinary managed admission", replace(s, closing=True)
    if s.closing and s.setup >= 2 and s.registration_live:
        yield "External cleanup unregisters cancellation callback", replace(s, registration_live=False)
    if (s.closing and s.setup >= 2 and not s.registration_live
            and s.cancel != 1 and not s.registration_drained):
        yield "External DisposeAsync observes cancellation callback drained", replace(s, registration_drained=True)
    # Native retirement concerns native work/callback sources. A managed caller
    # may still hold an ordinary call lease or the start frame, checked separately.
    if not s.retired and (s.rejected or (s.accepted and s.callback == 4)):
        yield "Native try_retire confirms no future native callback", replace(s, retired=True)
    allowed = s.closing and s.terminal and s.retired and not s.freed
    if "start_return" not in omitted:
        allowed = allowed and s.setup == 4
    if "control_lease" not in omitted:
        allowed = allowed and s.control not in (1, 2)
    if "registration" not in omitted:
        allowed = allowed and s.registration_drained
    if allowed:
        yield "Reclaim and publish cleanup success", replace(s, freed=True, frees=s.frees + 1)


def violations(s, check_cleanup_contract):
    found = []
    if s.invalid_access:
        found.append("access_after_free")
    if s.publications > 1:
        found.append("multiple_task_publications")
    if s.frees > 1:
        found.append("multiple_frees")
    if check_cleanup_contract and s.freed and not s.registration_drained:
        found.append("cleanup_success_without_managed_registration_drain")
    return found


def explore(omitted, check_cleanup_contract=True):
    initial = State()
    work = deque([initial])
    previous = {initial: None}
    edge = {}
    count = 0
    failures = {}
    reclaimed = 0
    while work:
        s = work.popleft()
        bad = violations(s, check_cleanup_contract)
        if bad:
            for property_name in bad:
                if property_name not in failures:
                    trace = []
                    cursor = s
                    while previous[cursor] is not None:
                        trace.append(edge[cursor])
                        cursor = previous[cursor]
                    failures[property_name] = {"trace": list(reversed(trace)), "state": asdict(s)}
            continue  # safety violation branches are deliberately pruned
        reclaimed += int(s.freed)
        for label, target in transitions(s, omitted):
            count += 1
            if target not in previous:
                previous[target] = s
                edge[target] = label
                work.append(target)
    return {
        "omitted_guards": sorted(omitted),
        "exploration": "breadth-first; prune a branch on its first checked violation",
        "states": len(previous),
        "transitions": count,
        "reclaimed_states_without_checked_violation": reclaimed,
        "counterexamples": failures,
        "checked_properties": ["access_after_free", "multiple_task_publications", "multiple_frees"]
        + (["cleanup_success_without_managed_registration_drain"] if check_cleanup_contract else []),
    }


def main():
    cases = {
        "candidate_all_guards": explore(set()),
        "negative_omit_start_return": explore({"start_return"}),
        "negative_omit_control_lease": explore({"control_lease"}),
        "negative_omit_registration_drain": explore({"registration"}),
    }
    candidate = cases["candidate_all_guards"]
    assert not candidate["counterexamples"]
    assert candidate["reclaimed_states_without_checked_violation"] > 0
    assert "access_after_free" in cases["negative_omit_start_return"]["counterexamples"]
    assert "access_after_free" in cases["negative_omit_control_lease"]["counterexamples"]
    assert "cleanup_success_without_managed_registration_drain" in cases["negative_omit_registration_drain"]["counterexamples"]
    report = {
        "experiment_id": "R09-MODEL-RETIREMENT-002",
        "status": "model_executed",
        "model_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {"python": platform.python_version(), "os": platform.system(), "architecture": platform.machine()},
        "cases": cases,
        "assumptions": [
            "Each transition is atomic and sequentially consistent; this is not a machine-memory model.",
            "One operation, one native terminal callback, one cancellation registration/invocation, one optional ordinary control call.",
            "Start rejection has no native callback or work obligation; start commitment and terminal publication are correct atomic protocol actions.",
            "Native retirement is trusted to prohibit future native work/callback access; library bugs violating that promise are not modeled.",
            "Ordinary managed admission is atomically closed with lease acquisition; each acquired lease is balanced.",
            "The cancellation delegate holds a managed state reference; a late callback blocked by admission is not automatically a native use-after-free.",
        ],
        "not_proven": [
            "Liveness, scheduling fairness, shutdown deadlock, retry policy or bounded queue implementation.",
            "Weak memory, C#/Rust atomics, GCHandle implementation, real P/Invoke, thread affinity or AOT.",
            "Multiple callbacks/operations, duplicate malicious callbacks, pooling/ABA, counter overflow.",
            "Result ownership transfer, data pinning/copy, allocation failure, panic or fatal runtime behavior.",
            "Registration drain omission is checked as a DisposeAsync cleanup-contract failure, not falsely labeled native UAF when admission/leases already protect native access.",
        ],
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("retirement-result.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: {"states": v["states"], "counterexamples": list(v["counterexamples"]),
                            "reclaimed": v["reclaimed_states_without_checked_violation"]}
                      for name, v in cases.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
