#!/usr/bin/env python3
"""Use in-memory mutations of actual accepted inputs; never rewrite accepted files."""
from pathlib import Path
import copy
import hashlib
import json
from verify_contract_acceptance import verify

ROOT=Path(__file__).resolve().parents[1]
def raw(value):return (json.dumps(value,indent=2)+'\n').encode()
def digest(value):return hashlib.sha256(value).hexdigest()
def relative(ref):return ref['path'].split(':',1)[1]

def main():
    cache={};positive=verify(ROOT,source_cache=cache);cases=[]
    index_path='docs/contracts/acceptance-index.json'
    index=json.loads((ROOT/index_path).read_bytes())
    registry=json.loads((ROOT/'docs/contracts/registry.json').read_bytes())
    def reject(name,overrides):
        try:verify(ROOT,overrides,cache)
        except AssertionError as error:cases.append({'case':name,'passed':True,'rejection':str(error)})
        else:raise AssertionError(('invalid acceptance passed',name))
    path='docs/api/interop.md'
    reject('changed_accepted_api_semantics',{path:(ROOT/path).read_bytes()+b'\nChanged semantic bytes in memory.\n'})
    changed=copy.deepcopy(index);changed['binding_attestations']=[]
    reject('missing_binding_attestations',{index_path:raw(changed)})
    changed=copy.deepcopy(index);changed['binding_attestations'][0]['sha256']='0'*64
    reject('stale_binding_attestation_hash',{index_path:raw(changed)})
    wrapper=json.loads((ROOT/registry['contracts'][0]['reviews'][0]['manifest_path'].split(':',1)[1]).read_bytes())
    path=relative(wrapper['independent_report'])
    reject('changed_independent_review_report',{path:(ROOT/path).read_bytes()+b'\n'})
    for name,change in (
        ('foreign_attesting_reviewer',lambda data:data.update(reviewer='synthetic/unrelated-reviewer')),
        ('changed_exact_attested_subject',lambda data:data['subjects'][0].update(evidence_sha256=['0'*64]))):
        changed=copy.deepcopy(index);ref=changed['binding_attestations'][0];path=relative(ref)
        data=json.loads((ROOT/path).read_bytes());change(data);value=raw(data);ref['sha256']=digest(value)
        reject(name,{index_path:raw(changed),path:value})
    result={'passed':True,'actual_positive_binding':positive,'negative_cases':cases,
        'scope':'In-memory integrity mutations of actual accepted Design records; no accepted file or product state changed.'}
    output=ROOT/'artifacts/public-api-contract-integrity.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
