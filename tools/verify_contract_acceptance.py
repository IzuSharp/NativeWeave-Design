#!/usr/bin/env python3
"""Verify Design's complete exact contract acceptance without a mutable Plan checkout.

These integrity checks do not authenticate human identity or execute product code.
The actual independent technical decisions and attributable attestations remain
separate inputs. Every reviewed Design byte is checked at its immutable source.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import subprocess

ACCEPT={'accepted','accept_research_design','recommend_accept_research_design',
        'recommend_accept_research_and_detailed_design'}
BLOCKERS=('open_blocking_findings','unresolved_blocking_findings',
          'remaining_blocking_findings','blocking_findings')
ROOT=Path(__file__).resolve().parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()

def verify(root=ROOT, overrides=None, source_cache=None):
    root=Path(root).resolve();overrides=overrides or {};source_cache={} if source_cache is None else source_cache
    current={};reports={};input_count=0
    def relative(ref):
        repository,path=ref.split(':',1);pure=PurePosixPath(path)
        assert repository=='NativeWeave-Design' and not pure.is_absolute() and '..' not in pure.parts and str(pure)==path and '\\' not in path,ref
        assert (root/path).resolve().is_relative_to(root),ref
        return path
    def raw(path):
        if path not in current:current[path]=overrides[path] if path in overrides else (root/path).read_bytes()
        return current[path]
    def read(path):return json.loads(raw(path))
    def exact(ref,key='path'):
        path=relative(ref[key]);value=raw(path)
        assert sha(value)==ref['sha256'],('changed accepted file',path)
        return json.loads(value)
    def committed(commit,path):
        assert re.fullmatch('[0-9a-f]{40}',commit),commit
        key=(commit,path)
        if key not in source_cache:source_cache[key]=subprocess.check_output(['git','show',commit+':'+path],cwd=root)
        return source_cache[key]
    def pins(report):
        result={}
        def add(path,value):
            assert ':' in path and (path not in result or result[path]==value),('conflicting review pin',path)
            result[path]=value
        for path,value in report.get('review_inputs_sha256',{}).items():add(path,value)
        for key in ('reviewed_inputs','reviewed_outputs','supporting_inputs'):
            for row in report.get(key,[]):
                path=row['path']
                if ':' not in path:path=row['repository'].split('/')[-1]+':'+path
                add(path,row['sha256'])
        return result
    registry=read('docs/contracts/registry.json');contracts=registry['contracts']
    assert len(contracts)==21 and registry['status']=='accepted_research_and_detailed_design'
    by_key={(c['id'],c['version']):c for c in contracts};assert len(by_key)==21
    index=read('docs/contracts/acceptance-index.json')
    assert index['state']=='accepted_research_and_detailed_design' and index['product_implementation_authorized'] is False
    expected=[];actors={}
    for c in contracts:
        identity=c['id'];assert c['version']=='0.4.0' and c['status']=='accepted',identity
        assert sha(raw(c['spec_path']))==c['content_sha256'],('changed contract',identity)
        assert c['source_commit']==index['design_source_commit'],('index source',identity)
        subject={'kind':'contract','id':identity,'version':c['version'],'content_sha256':c['content_sha256']}
        evidence_hashes=[r['sha256'] for r in c['evidence']]
        review_hashes=[r['sha256'] for r in c['reviews']]
        assert evidence_hashes and review_hashes and len(evidence_hashes)==len(set(evidence_hashes)) and len(review_hashes)==len(set(review_hashes)),identity
        expected.append({'kind':'contract','id':identity,'evidence_sha256':evidence_hashes,'review_sha256':review_hashes})
        dependencies={};required={'NativeWeave-Design:'+c['spec_path'],*c.get('api_specification_inputs',[])}
        for dep in c['dependencies']:
            other=by_key[(dep['id'],dep['version'])]
            required.add('NativeWeave-Design:'+other['spec_path'])
            dependencies[other['id']+'@'+other['version']]={
                'spec_path':other['spec_path'],'content_sha256':other['content_sha256'],
                'evidence_sha256':[r['sha256'] for r in other['evidence']],
                'review_sha256':[r['sha256'] for r in other['reviews']]}
        reviewed_files={}
        for ref in c['evidence']:
            evidence=exact(ref,'manifest_path')
            assert evidence['subject']==subject and evidence['status']=='passed' and evidence['kind']=='design_analysis' and evidence['is_template'] is False,identity
            snapshot=exact(evidence['artifact'])
            assert snapshot['record_kind']=='research_design_input_snapshot' and snapshot['product_execution'] is False and snapshot['subject']==subject,identity
            assert snapshot['source_commits']=={'NativeWeave-Design':c['source_commit']},identity
            assert snapshot['contract_dependency_snapshot']==dependencies,('dependency snapshot',identity)
            seen=set()
            for row in snapshot['files']:
                path=relative(row['path']);assert row['path'] not in seen,('duplicate accepted input',path)
                seen.add(row['path']);value=raw(path)
                assert row['source_commit']==c['source_commit'],('input source',path)
                assert len(value)==row['bytes'] and sha(value)==row['sha256'],('changed accepted input',path)
                assert value==committed(row['source_commit'],path),('uncommitted accepted input',path)
                assert row['path'] not in reviewed_files or reviewed_files[row['path']]==row['sha256'],path
                reviewed_files[row['path']]=row['sha256'];input_count+=1
            assert required<=seen,('incomplete contract input snapshot',identity,sorted(required-seen))
        actors[identity]=set()
        for ref in c['reviews']:
            wrapper=exact(ref,'manifest_path')
            assert wrapper['subject']==subject and wrapper['verdict']=='accepted' and wrapper['blocking_findings']==[] and wrapper['is_template'] is False,identity
            assert wrapper['author']==c['author'] and wrapper['reviewer']!=c['author'],('self review',identity)
            assert set(wrapper['reviewed_evidence_sha256'])==set(evidence_hashes),('reviewed evidence',identity)
            assert wrapper['review_kind']=='binding_of_actual_independent_technical_review' and wrapper['recorded_by']=='/root',identity
            report_ref=wrapper['independent_report'];report=exact(report_ref)
            reports[report_ref['path']]=report_ref['sha256']
            assert report['reviewer']==wrapper['reviewer'] and report['decision'] in ACCEPT,identity
            present=[key for key in BLOCKERS if key in report]
            assert present and all(report[key]==[] for key in present),('blocked review',identity)
            rows=[r for r in report.get('contract_reviews',[]) if r.get('id')==identity]
            assert len(rows)==1 and rows[0]['decision'] in ACCEPT,('missing contract review',identity)
            for key in ('version','spec_path','content_sha256'):assert rows[0][key]==c[key],(identity,key)
            review_pins=pins(report)
            assert reviewed_files.keys()<=review_pins.keys(),('incomplete actual review inputs',identity)
            for path,value in reviewed_files.items():assert review_pins[path]==value,('stale actual review input',identity,path)
            actors[identity].add(wrapper['reviewer'])
        assert set(c['reviewers'])==actors[identity],('attribution mismatch',identity)
    assert index['subjects']==expected,'Acceptance index does not describe current contracts'
    expected={r['id']:r for r in expected};covered=set();seen=set();paths=set()
    refs=index.get('binding_attestations');assert isinstance(refs,list) and refs,'Missing independent binding attestations'
    for ref in refs:
        assert ref['path'] not in paths,('duplicate attestation',ref['path']);paths.add(ref['path'])
        data=exact(ref);assert data['verdict']=='accepted' and data['blocking_findings']==[],ref['path']
        actor=data['reviewer'];assert data['subjects'],ref['path']
        for subject in data['subjects']:
            identity=subject['id'];key=(actor,identity)
            assert key not in seen,('duplicate attested subject',key);seen.add(key)
            assert identity in expected and subject==expected[identity],('inexact attested subject',identity)
            assert actor in actors[identity],('unattributable attestation',identity,actor)
            covered.add(identity)
    assert covered==set(expected),('incomplete exact attestations',sorted(set(expected)-covered))
    return {'accepted_contracts':len(contracts),'exact_input_entries':input_count,
            'independent_reports':len(reports),'binding_attestations':len(refs),
            'product_implementation_authorized':False}

if __name__=='__main__':print(json.dumps(verify(),indent=2))
