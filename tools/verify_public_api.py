#!/usr/bin/env python3
"""Verify the current API design and preserve the frozen accepted history.

Structural/hash checks are not independent semantic review. The acceptance index
and actual scoped reviewer reports provide that separate decision.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'a0f6bca1f55ddf456fe931886da8be19e94a1413'
DOMAINS = ('foundation','database','server','interop')

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def headings(path):
    result=set()
    for line in path.read_text().splitlines():
        if re.match(r'^#{1,6} ',line):
            value=re.sub(r'^#+ ','',line).lower()
            value=re.sub(r'[^\w\- ]','',value)
            result.add(value.replace(' ','-'))
    return result

def verify(history=False, require_acceptance=False):
    ids=set(); coverage={}
    for domain in DOMAINS:
        matrix=read(ROOT/f'docs/api/{domain}-coverage.json')
        coverage[domain]=len(matrix['rows'])
        for row in matrix['rows']:
            assert row['id'] not in ids, row['id']
            ids.add(row['id'])
            for field in ('feature','reference_apis','reference_version','public_api','rust_engine',
                          'adapter_operations','support','aot','cost','limitations','specification','tasks'):
                if field in {'public_api','adapter_operations'} and row.get('support') in {'planned','unsupported'}:
                    assert field in row and isinstance(row[field],list), (row['id'],field)
                else:
                    assert row.get(field), (row['id'],'missing coverage field',field)
            assert row['support'] in {'full','equivalent','limited','planned','unsupported'}, row['id']
            assert row.get('product_implemented',False) is False, row['id']
            assert all(re.fullmatch('[AB][0-9]{2}',x) for x in row['tasks']), row['id']
            assert (ROOT/row['specification']).is_file(), row['id']
    inventory=read(ROOT/'docs/api/public-api.json')
    assert inventory['product_implemented'] is False
    assert inventory['sdk']=='11.0.100' and inventory['language']=='15.0'
    for source in inventory['declaration_sources']:
        assert digest(ROOT/source['path'])==source['sha256'], ('stale declaration inventory',source['path'])
    symbols=inventory['symbols']; symbol_ids=[s['id'] for s in symbols]
    assert len(symbol_ids)==len(set(symbol_ids)) and len(symbols)>500
    # Foundation rows use fully-qualified symbols: reject an illustrative name
    # that no longer exists in the exact declarations, without treating a
    # domain's explicitly descriptive capability label as a C# identifier.
    declared_names={re.sub(r'`+[0-9]+','',s['id'].split(':',1)[1].split('(',1)[0]) for s in symbols}
    for row in read(ROOT/'docs/api/foundation-coverage.json')['rows']:
        for name in row['public_api']:
            normalized=re.sub(r'<[^<>]*>','',name)
            assert normalized in declared_names, (row['id'],'unknown public API symbol',name)
    policies={}
    for domain in DOMAINS[1:]:
        data=read(ROOT/f'docs/api/{domain}-symbol-policies.json')
        for key,value in data['types'].items():
            assert key not in policies,key
            policies[key]=value
            path,fragment=value['semantic_section'].split('#',1)
            assert (ROOT/path).is_file() and fragment in headings(ROOT/path),(key,'bad semantic anchor',fragment)
            assert value['native_operations'] and value['tasks'] and value['package'] and value['capability'] and value['cost_profile'],key
    used=set()
    for symbol in symbols:
        key=symbol['semantic_policy']; used.add(key)
        assert key in policies and inventory['semantic_policies'][key]==policies[key],('stale semantic inventory',symbol['id'])
        assert symbol['design_only'] is True and symbol['product_implemented'] is False
    assert used==set(policies),('missing/stale type policies',sorted(set(policies)-used))
    # Every old raw experiment, original-language snapshot and English acceptance
    # wrapper remains byte-for-byte available; current contract indices may evolve.
    manifest=read(ROOT/'english-translation-manifest.json')
    immutable={row['path'] for row in manifest['immutable_originals']}
    baseline_files=git('ls-tree','-r','--name-only',BASELINE).decode().splitlines()
    immutable.update(p for p in baseline_files if p.startswith(('verification/','docs/traceability/reviews/')))
    for path in sorted(immutable):
        assert (ROOT/path).read_bytes()==git('show',BASELINE+':'+path),('historical evidence modified',path)
    from local_host_raw_evidence import verified_raw_exceptions, check_tracked_language
    current=git('ls-files','--cached','--others','--exclude-standard').decode().splitlines()
    check_tracked_language(ROOT,current,immutable|verified_raw_exceptions(ROOT))
    if history:
        with tempfile.TemporaryDirectory(prefix='nw-api-history-') as temp:
            work=Path(temp)/'NativeWeave-Design'
            subprocess.run(['git','worktree','add','--detach',str(work),BASELINE],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
            try:
                subprocess.run(['python3','tools/verify_english_translation.py'],cwd=work,check=True)
            finally:
                subprocess.run(['git','worktree','remove',str(work)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    registry=read(ROOT/'docs/contracts/registry.json')
    assert len(registry['contracts'])==21
    if require_acceptance:
        index=read(ROOT/'docs/contracts/acceptance-index.json')
        assert index['state']=='accepted_research_and_detailed_design'
        assert index['product_implementation_authorized'] is False
        for c in registry['contracts']:
            assert c['version']=='0.4.0' and c['status']=='accepted',c['id']
            assert c['content_sha256']==digest(ROOT/c['spec_path']),c['id']
            for ref in c['evidence']+c['reviews']:
                repository,path=ref['manifest_path'].split(':',1)
                assert repository=='NativeWeave-Design' and digest(ROOT/path)==ref['sha256'],path
    result={'passed':True,'coverage_rows':coverage,'public_symbols':len(symbols),
            'public_type_policy_keys':len(policies),'historical_files_preserved':len(immutable),
            'historical_english_gate_executed':history,'accepted_contracts_required':require_acceptance,
            'product_implementation_authorized':False}
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',action='store_true')
    parser.add_argument('--require-acceptance',action='store_true')
    args=parser.parse_args()
    verify(args.history,args.require_acceptance)
