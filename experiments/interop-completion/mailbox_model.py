"""Finite SC model of one coalesced notification racing a worker's unschedule.
Not a weak-memory or scheduler liveness proof. Queue capacity is one pre-reserved slot.
"""
from collections import deque
from pathlib import Path
import hashlib,json

# dirty, scheduled, worker_phase, wake_done, check_snapshot, processed
def explore(fixed):
    initial=(True,True,0,False,False,0)
    q=deque([(initial,[])]);seen={initial};edges=0;bad=None;nonvacuous=0
    while q:
        s,trace=q.popleft();dirty,scheduled,phase,wake,snapshot,processed=s
        if wake and dirty and not scheduled and phase==3:
            bad=bad or trace;continue
        if wake and not dirty and not scheduled and phase==3 and processed==2:nonvacuous+=1
        choices=[]
        if not wake:choices.append(('notify_dirty_and_schedule',(True,True,phase,True,snapshot,processed)))
        if phase==0:
            choices.append(('consume_dirty',(False,scheduled,1,wake,False,processed+int(dirty))))
        elif phase==1:
            if fixed:
                choices.append(('atomic_recheck_unschedule',(dirty,True if dirty else False,0 if dirty else 3,wake,False,processed)))
            else:choices.append(('read_dirty_before_unschedule',(dirty,scheduled,2,wake,dirty,processed)))
        elif phase==2:
            choices.append(('unschedule_using_stale_read',(dirty,True if snapshot else False,0 if snapshot else 3,wake,False,processed)))
        elif phase==3 and scheduled:
            choices.append(('dispatch_reserved_slot',(dirty,scheduled,0,wake,False,processed)))
        for label,n in choices:
            edges+=1
            if n not in seen:seen.add(n);q.append((n,trace+[label]))
    return dict(states=len(seen),transitions=edges,counterexample=bad,completed_two_notification_states=nonvacuous)

if __name__=='__main__':
    old=explore(False);fixed=explore(True)
    assert old['counterexample'] is not None
    assert fixed['counterexample'] is None and fixed['completed_two_notification_states']>0
    src=Path(__file__);out=src.parents[2]/'verification/interop-completion/mailbox-model.json'
    result=dict(scope='One worker, one extra wake, atomic SC events; pre-reserved single slot; no weak-memory/FFI or liveness claim',source_commit=None,source_path=str(src.relative_to(src.parents[2])),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),negative=old,candidate=fixed)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
