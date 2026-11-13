#!/usr/bin/env python3
"""Finite abstract admission model, NOT an execution of Hyper/Tower/C#/Rust.
Two requests, one configured stream slot. A response head may complete before
its body and managed callback retire. No fairness, weak-memory or byte proof.
"""
from collections import deque
import json

# Each request is (phase, callback_pending); phase 0=not admitted,
# 1=waiting for response head, 2=streaming body, 3=body ended.
def held(r, policy):
    phase, callback = r
    return phase == 1 if policy == 'head_only' else phase != 0 and (phase < 3 or callback)

def explore(policy):
    initial=((0,False),(0,False)); todo=deque([initial]); paths={initial:[]}; transitions=0; violations=[]
    while todo:
        state=todo.popleft()
        live=sum(p != 0 and (p < 3 or c) for p,c in state)
        if live > 1: violations.append({'state':state,'trace':paths[state]})
        successors=[]
        for i,(phase,callback) in enumerate(state):
            if phase == 0 and sum(held(r,policy) for r in state) < 1:
                successors.append((i,(1,True),'admit'))
            if phase == 1: successors.append((i,(2,callback),'response_head'))
            if phase == 2: successors.append((i,(3,callback),'body_end'))
            if callback: successors.append((i,(phase,False),'callback_retired'))
        for i,request,event in successors:
            out=list(state);out[i]=request;out=tuple(out);transitions+=1
            if out not in paths:
                paths[out]=paths[state]+[f'{event}(request={i})'];todo.append(out)
    return {'policy':policy,'states':len(paths),'transitions':transitions,
            'violation_count':len(violations),'first_counterexample':violations[0] if violations else None,
            'both_retired_reachable':((3,False),(3,False)) in paths}

if __name__ == '__main__':
    bad=explore('head_only'); good=explore('body_and_callback')
    assert bad['violation_count'] > 0
    assert good['violation_count'] == 0 and good['both_retired_reachable']
    print(json.dumps({'scope':'finite sequentially-consistent two-request admission abstraction',
      'not_proven':['network implementation','native ABI','byte/RSS bounds','fairness/liveness','weak memory','Native AOT'],
      'negative_control':bad,'candidate':good},indent=2))
