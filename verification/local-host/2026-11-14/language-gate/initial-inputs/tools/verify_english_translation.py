#!/usr/bin/env python3
"""Check exact English coverage, preserved source bytes, and actual review pins.

This verifies recorded review linkage, not human identity or translation quality.
The corresponding independent reviews provide the semantic-equivalence decisions.
"""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import subprocess
from local_host_raw_evidence import check_tracked_language, verified_raw_exceptions

ROOT=Path(__file__).resolve().parents[1]
CJK=re.compile('[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]')
HAN=re.compile('[\u3400-\u9fff]')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def resolve(value):
    repository,path=value.split(':',1)
    assert repository in {'NativeWeave-Design','Plan'}
    root=ROOT if repository==ROOT.name else ROOT.parent/repository
    target=(root/path).resolve()
    assert target.is_relative_to(root.resolve()) and target.is_file(),value
    return target

def same_machine_values(before,after,path=''):
    assert type(before) is type(after),(path,'type changed')
    if isinstance(before,dict):
        assert list(before)==list(after),(path,'keys/order changed')
        for key in before:same_machine_values(before[key],after[key],path+'/'+key)
    elif isinstance(before,list):
        assert len(before)==len(after),(path,'array length changed')
        for i,(a,b) in enumerate(zip(before,after)):same_machine_values(a,b,path+'/'+str(i))
    elif isinstance(before,str) and HAN.search(before):
        assert not CJK.search(after),(path,'untranslated string')
    else:assert before==after,(path,'non-language scalar changed')

def json_projection(data,path):
    data=json.loads(json.dumps(data))
    if path.endswith('-graph.json'):
        for node in data['nodes']:
            for key in ('packet_sha256','source_commit','acceptance_evidence','independent_reviewers'):
                node.pop(key,None)
    elif path=='docs/contracts/registry.json':
        for contract in data['contracts']:
            for key in ('content_sha256','source_commit','evidence','reviews','reviewers'):
                contract.pop(key,None)
    return data

def projection_sha(raw,path):
    return sha(json.dumps(json_projection(json.loads(raw),path),sort_keys=True,
                          ensure_ascii=False,separators=(',',':')).encode())

def markdown_structure(source,target,path):
    # Preserve identifiers, link destinations, numeric occurrences, and code.
    assert re.findall(r'\]\(([^)]+)\)',source)==re.findall(r'\]\(([^)]+)\)',target),(path,'link destinations changed')
    # Numbers inside current input hashes legitimately migrate; other numbers stay.
    a=source;b=target
    if path in MANIFEST.get('binding_text_paths',[]):
        a=re.sub(r'(SHA-256 `)[0-9a-f]{64}(`)',r'\1HASH\2',a)
        b=re.sub(r'(SHA-256 `)[0-9a-f]{64}(`)',r'\1HASH\2',b)
    if path=='research-tasks/R31.md':
        # The independently reviewed translation spells the source quantity 3
        # as "three" in this exact phrase. This does not waive other numbers.
        b=b.replace('compare three technical paths','compare 3 technical paths')
    assert Counter(re.findall(r'`([^`\n]+)`',a))==Counter(re.findall(r'`([^`\n]+)`',b)),(path,'inline code changed')
    assert Counter(re.findall('[0-9]+(?:\\.[0-9]+)*',a))==Counter(re.findall('[0-9]+(?:\\.[0-9]+)*',b)),(path,'numeric occurrences changed')
    blocks=lambda text:re.findall(r'^```[^\n]*\n(.*?)^```\s*$',text,re.M|re.S)
    aa=blocks(source);bb=blocks(target);assert len(aa)==len(bb),(path,'code-block count changed')
    for i,(a,b) in enumerate(zip(aa,bb)):
        if a!=b:
            # Only an actually Chinese comment may change. Keep the code prefix;
            # never remove comment-looking tokens inside an unchanged string.
            al=a.splitlines();bl=b.splitlines();assert len(al)==len(bl),(path,'code lines changed',i)
            for left,right in zip(al,bl):
                if left==right:continue
                allowed=False
                for marker in ('//','--'):
                    if marker not in left or marker not in right:continue
                    lp,lc=left.split(marker,1);rp,rc=right.split(marker,1)
                    # Source commentary is the only CJK-bearing suffix here;
                    # a string literal cannot serve as a translation escape hatch.
                    if lp==rp and HAN.search(lc) and not CJK.search(rc) and not lp.strip():allowed=True
                    elif (marker=='//' and lp==rp and HAN.search(lc) and not CJK.search(rc)
                          and '"' not in lp and "'" not in lp and lp.rstrip().endswith((';','{','}'))):allowed=True
                assert allowed,(path,'executable example code changed',i,left,right)
    assert len(source.splitlines())==len(target.splitlines()),(path,'paragraph/row line count changed')

def review_rows(report):
    return report.get('translation_reviews',report.get('files',[]))

def verify_contract_bindings():
    registry=read(ROOT/'docs/contracts/registry.json')
    index=read(ROOT/'docs/contracts/acceptance-index.json')
    assert len(registry['contracts'])==21
    assert registry['status']==index['state']=='accepted_research_and_detailed_design'
    assert index['product_implementation_authorized'] is False
    original_registry=json.loads(git('show',MANIFEST['source_commit']+':docs/contracts/registry.json'))
    prior={c['id']:c for c in original_registry['contracts']}
    assert {c['id'] for c in registry['contracts']}==set(prior)
    old_index=git('show',MANIFEST['source_commit']+':docs/contracts/acceptance-index.json')
    assert json.loads(old_index)['state']=='accepted_research_and_detailed_design'
    assert index['translation_migration']['prior_acceptance']=={
        'repository':'NativeWeave-Design','commit':MANIFEST['source_commit'],
        'path':'docs/contracts/acceptance-index.json','sha256':sha(old_index)}
    attested=[]
    for ref in index['binding_attestations']:
        raw=resolve(ref['path']).read_bytes();assert sha(raw)==ref['sha256']
        report=json.loads(raw);assert report['verdict']=='accepted' and report['blocking_findings']==[]
        attested.extend((report['reviewer'],s) for s in report['subjects'])
    expected=[]
    for c in registry['contracts']:
        assert c['status']=='accepted' and c['source_commit']==index['design_source_commit']
        assert sha((ROOT/c['spec_path']).read_bytes())==c['content_sha256']
        subject={'kind':'contract','id':c['id'],'version':c['version'],'content_sha256':c['content_sha256']}
        evidence_hashes=[]
        for ref in c['evidence']:
            raw=resolve(ref['manifest_path']).read_bytes();assert sha(raw)==ref['sha256']
            e=json.loads(raw);assert e['subject']==subject and e['status']=='passed' and e['is_template'] is False
            artifact=resolve(e['artifact']['path']).read_bytes();assert sha(artifact)==e['artifact']['sha256']
            snap=json.loads(artifact);assert snap['subject']==subject and snap['product_execution'] is False
            old=prior[c['id']];assert old['status']=='accepted'
            expected_prior={'id':c['id'],'version':old['version'],'content_sha256':old['content_sha256'],
                            'source_commit':old['source_commit'],'evidence':old['evidence'],'reviews':old['reviews']}
            provenance=snap['translation_provenance']
            assert provenance['original_accepted_repository_commit']==MANIFEST['source_commit']
            assert provenance['original_accepted_subject']==expected_prior and provenance['native_experiments_rerun'] is False
            assert e['prior_accepted_evidence']==old['evidence'] and e['prior_accepted_reviews']==old['reviews']
            assert snap['source_commits']=={'NativeWeave-Design':c['source_commit']}
            paths=set()
            for row in snap['files']:
                assert row['path'] not in paths;paths.add(row['path'])
                value=resolve(row['path']).read_bytes()
                assert sha(value)==row['sha256'] and len(value)==row['bytes']
                repo,path=row['path'].split(':',1);assert repo=='NativeWeave-Design'
                assert row['source_commit']==c['source_commit']
                assert value==git('show',row['source_commit']+':'+path)
            assert 'NativeWeave-Design:'+c['spec_path'] in paths
            dependencies={p['id']+'@'+p['version']:{
                'spec_path':d['spec_path'],'content_sha256':d['content_sha256'],
                'evidence_sha256':[x['sha256'] for x in d['evidence']],
                'review_sha256':[x['sha256'] for x in d['reviews']]}
                for p in c['dependencies']
                for d in registry['contracts'] if (d['id'],d['version'])==(p['id'],p['version'])}
            assert snap['contract_dependency_snapshot']==dependencies
            evidence_hashes.append(ref['sha256'])
        reviewers=[]
        for ref in c['reviews']:
            raw=resolve(ref['manifest_path']).read_bytes();assert sha(raw)==ref['sha256']
            r=json.loads(raw);assert r['subject']==subject and r['verdict']=='accepted' and r['blocking_findings']==[]
            assert r['prior_accepted_source']==MANIFEST['source_commit']
            assert r['author']==c['author'] and r['reviewer']!=c['author']
            assert set(evidence_hashes)<=set(r['reviewed_evidence_sha256'])
            rr=resolve(r['independent_report']['path']).read_bytes();assert sha(rr)==r['independent_report']['sha256']
            report=json.loads(rr);assert report['reviewer']==r['reviewer']
            assert report['decision']=='accepted' and report['blocking_findings']==[]
            row=[x for x in report['contract_reviews'] if x['id']==c['id']]
            assert len(row)==1 and row[0]['decision']=='accepted'
            assert all(row[0][k]==c[k] for k in ('version','spec_path','content_sha256'))
            assert report['review_inputs_sha256']['NativeWeave-Design:'+c['spec_path']]==c['content_sha256']
            reviewers.append(r['reviewer'])
        assert c['reviewers']==reviewers,(c['id'],'reviewer display list mismatch')
        entry={'kind':'contract','id':c['id'],'evidence_sha256':evidence_hashes,
               'review_sha256':[x['sha256'] for x in c['reviews']]}
        assert any(actor in reviewers and item==entry for actor,item in attested),(c['id'],'unattested binding')
        expected.append(entry)
    assert index['subjects']==expected

def verify(require_reviews=True):
    global MANIFEST
    MANIFEST=read(ROOT/'english-translation-manifest.json')
    baseline=MANIFEST['source_commit']
    assert re.fullmatch('[0-9a-f]{40}',baseline)
    assert MANIFEST['product_implementation_authorized'] is False
    translated={row['path']:row for row in MANIFEST['translated_files']}
    exceptions={row['path']:row for row in MANIFEST['immutable_originals']}
    assert len(translated)==len(MANIFEST['translated_files']) and not(set(translated)&set(exceptions))
    baseline_paths=set(git('ls-tree','-r','--name-only',baseline).decode().splitlines())
    assert set(translated)|set(exceptions)<=baseline_paths
    reviews=[]
    for ref in MANIFEST.get('independent_reviews',[]):
        raw=resolve(ref['path']).read_bytes();assert sha(raw)==ref['sha256']
        report=json.loads(raw)
        assert report['decision']=='accepted' and report['blocking_findings']==[]
        for row in review_rows(report):reviews.append((report['reviewer'],row))
    for path,row in translated.items():
        before=git('show',baseline+':'+path);after=(ROOT/path).read_bytes()
        assert sha(before)==row['source_sha256'] and sha(after)==row['target_sha256'],(path,'translation bytes drifted')
        assert not CJK.search(after.decode()),(path,'current authoritative text is not English')
        if path.endswith('.json'):same_machine_values(json_projection(json.loads(before),path),json_projection(json.loads(after),path),path)
        if path.endswith('.md'):markdown_structure(before.decode(),after.decode(),path)
        if require_reviews:
            ref=ROOT.name+':'+path
            def matches(actor,rr):
                if actor==row['translation_author'] or rr['path']!=ref or rr['decision']!='accepted':return False
                if path.endswith('-graph.json') or path=='docs/contracts/registry.json':
                    return (rr.get('mode')=='semantic_projection_v1' and
                            rr.get('source_projection_sha256')==projection_sha(before,path) and
                            rr.get('target_projection_sha256')==projection_sha(after,path))
                return rr.get('source_sha256')==row['source_sha256'] and rr.get('target_sha256')==row['target_sha256']
            assert any(matches(actor,rr) for actor,rr in reviews),(path,'missing exact independent translation review')
    for path,row in exceptions.items():
        raw=(ROOT/path).read_bytes()
        assert raw==git('show',baseline+':'+path) and sha(raw)==row['sha256'],(path,'immutable original changed')
        assert row['reason'] and row['authority']=='historical_evidence_only'
    allowed=set(translated)|set(MANIFEST['existing_metadata_changes'])
    # Every pre-existing file outside declared translation/metadata scope is immutable.
    for path in baseline_paths-allowed:
        assert (ROOT/path).is_file() and (ROOT/path).read_bytes()==git('show',baseline+':'+path),(path,'undeclared source mutation')
    raw_exceptions=verified_raw_exceptions(ROOT)
    check_tracked_language(ROOT,git('ls-files').decode().splitlines(),set(exceptions)|raw_exceptions)
    if require_reviews and ROOT.name=='NativeWeave-Design':verify_contract_bindings()
    return {'ok':True,'repository':ROOT.name,'source_commit':baseline,'translated_files':len(translated),
            'immutable_originals':len(exceptions),'independent_review_required':require_reviews,
            'native_experiments_rerun':False,'product_implementation_authorized':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true')
    args=p.parse_args();print(json.dumps(verify(require_reviews=not args.preflight),indent=2))

if __name__=='__main__':main()
