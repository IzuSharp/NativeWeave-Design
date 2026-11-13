from pathlib import Path
import subprocess,json,hashlib,re,collections,yaml,datetime
ROOT=Path('/workspace/scratch/a64c8260e732/nativeweave'); O=ROOT/'recovery/migration-evidence'; P=O/'merged-plan-review/Plan'; D=ROOT/'NativeWeave-Design'
BASE='f6ed91dddba62b9eba246f2af56ca5b93cc2593b'; HEAD='04c2f043c0ec60a2d49dd3ca8ea4ad1c8c888d89'; DESIGN='c7e123a74405a92dc3de1ef450355b08d1c05ceb'; SOURCE='267364a440074a61e193cf33315f1b9d0fa8126b'
def git(*a):return subprocess.check_output(['git',*a],cwd=P)
def data(rel,rev=HEAD):return git('show',rev+':'+rel)
def doc(rel,rev=HEAD):return json.loads(data(rel,rev))
def sha(b):return hashlib.sha256(b).hexdigest()
checks=[]
def check(name,ok,detail=None):checks.append({'check':name,'passed':bool(ok),**({'detail':detail} if detail is not None else {})})
snap=json.loads((O/'merged-plan-review-input.json').read_text()); cp=doc('ledger/checkpoints/research-assets-migration.json'); baseline=doc('source-driven-baseline.json')
check('exact_merged_commit_and_tree',git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse',HEAD+'^{tree}').decode().strip()==snap['tree'])
check('merge_first_parent_is_review_base',git('rev-parse',HEAD+'^1').decode().strip()==BASE)
check('all_49_snapshot_file_hashes',len(snap['files'])==49 and all(sha(data(f['path']))==f['sha256'] and len(data(f['path']))==f['bytes'] for f in snap['files']))
check('patch_hash',sha(git('diff','--binary',BASE,HEAD,'--'))==snap['diff_sha256'])
old={};new={};kinds={};states={};direct={'D01','D02','D07','R03','R04','R07','R10','R13','R22','R25','R27','R29'}
for kind in ['research','documentation','delivery']:
 a=doc(kind+'-graph.json',BASE);b=doc(kind+'-graph.json')
 check(kind+'_same_ids_order',[n['id'] for n in a['nodes']]==[n['id'] for n in b['nodes']])
 check(kind+'_same_graph_metadata',{k:v for k,v in a.items() if k!='nodes'}=={k:v for k,v in b.items() if k!='nodes'})
 states[kind]=dict(collections.Counter(n['status'] for n in b['nodes']))
 for x,y in zip(a['nodes'],b['nodes']):old[x['id']]=x;new[y['id']]=y;kinds[y['id']]=kind
check('same_114_nodes',collections.Counter(kinds.values())=={'research':34,'documentation':32,'delivery':48})
closure=set(direct)
while True:
 before=set(closure)
 for tid,n in old.items():
  deps=set(n['start_dependencies'])|set(n['acceptance_dependencies'])|{c['task_id'] for c in n['conditional_dependencies']}
  if deps&closure:closure.add(tid)
 if before==closure:break
changed=[];unchanged=[];allowed={'revision','packet_sha256','dependency_pins','continuation_evidence'}
suffix='\nCurrent phase: research/design/planning only. Read Design `experiments/native-slices/README.md`, `verification/native-slices/migration-map.json` and `migration-results.json`. Historical NativeWeave source/run identities remain provenance, not current write targets. New experiments belong in Design; do not execute A/B Delivery, write product code or merge product PR1. Its closure is allowed only after verified Design/Plan migration.\n'
for tid,n in new.items():
 a=old[tid];original=data(n['prompt'],BASE);final=data(n['prompt']);is_changed=original!=final
 (changed if is_changed else unchanged).append(tid)
 check(tid+'_same_state_and_other_semantics',{k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in n.items() if k not in allowed})
 check(tid+'_packet_sha256_matches_actual_bytes',sha(final)==n['packet_sha256'])
 check(tid+'_same_dependency_ids',set(a['dependency_pins'])==set(n['dependency_pins']))
 check(tid+'_exact_dependency_revisions',all(rev==new[dep]['revision'] for dep,rev in n['dependency_pins'].items()))
 if not is_changed:
  check(tid+'_same_revision_and_packet_hash',a['revision']==n['revision'] and a['packet_sha256']==n['packet_sha256'])
  check(tid+'_same_evidence',a.get('continuation_evidence')==n.get('continuation_evidence'))
  continue
 version=a['revision'].split('.');version[-1]=str(int(version[-1])+1)
 check(tid+'_one_patch_increment',n['revision']=='.'.join(version))
 expected=original.decode().replace('Revision: **'+a['revision']+'**','Revision: **'+n['revision']+'**',1)
 for dep,rev in a['dependency_pins'].items():expected=expected.replace(dep+'@'+rev,dep+'@'+n['dependency_pins'][dep])
 if tid in direct:
  prefix,footer=expected.split('## Native slice execution checkpoint')
  footer=footer.replace('d4ad42df26ee9378817aa8ee94cd1853d66eb0ae',DESIGN).replace('and NativeWeave `verification/native-slices/manifest.json` at `'+SOURCE+'`','and Design `verification/native-slices/original-pr1/manifest.json` at `'+DESIGN+'`')
  expected=prefix+'## Native slice execution checkpoint'+footer+suffix
  old_e=a['continuation_evidence'];new_e=n['continuation_evidence']
  check(tid+'_evidence_record_count_preserved',len(old_e)==len(new_e))
  for i,(x,y) in enumerate(zip(old_e,new_e)):
   renamed=dict(x);renamed['historical_native_evidence_commit']=renamed.pop('native_evidence_commit');renamed['historical_design_commit']=renamed['design_commit'];renamed.update(design_commit=DESIGN,evidence_repository='IzuSharp/NativeWeave-Design',evidence_manifest='verification/native-slices/original-pr1/manifest.json',migration_map='verification/native-slices/migration-map.json',migration_results='verification/native-slices/migration-results.json')
   check(tid+'_explicit_relocation_and_history_'+str(i),y==renamed)
   check(tid+'_evidence_path_exists_'+str(i),(D/y['path']).is_file() and (D/y['evidence_manifest']).is_file())
 else:check(tid+'_same_evidence',a.get('continuation_evidence')==n.get('continuation_evidence'))
 check(tid+'_packet_changes_only_revision_dependencies_relocation_and_phase',final.decode()==expected)
check('direct_12_exact',sorted(direct)==cp['direct_tasks'])
check('changed_33_exact_dependency_closure',set(changed)==closure==set(cp['changed_packets']) and len(changed)==33)
check('81_other_packets_unchanged',len(unchanged)==81)
check('48_delivery_packet_bytes_unchanged',all(data(n['prompt'])==data(n['prompt'],BASE) for tid,n in new.items() if kinds[tid]=='delivery'))
check('delivery_graph_bytes_unchanged',data('delivery-graph.json')==data('delivery-graph.json',BASE))
check('no_delivery_authorized',all(n['implementation_authorization']['status']=='not_authorized' and n['implementation_authorization']['approval_record'] is None for tid,n in new.items() if kinds[tid]=='delivery'))
check('old_checkpoint_bytes_retained',data('ledger/checkpoints/native-slices-2026-11-12.json')==data('ledger/checkpoints/native-slices-2026-11-12.json',BASE))
check('baseline_research_only',baseline['current_phase']=='research_design_planning' and baseline['product_implementation_authorized'] is False)
check('baseline_exact_design_source',baseline['design_merge_commit']==DESIGN and baseline['research_asset_commit']==DESIGN and baseline['historical_native_slice_evidence_commit']==SOURCE and baseline['research_asset_repository']=='IzuSharp/NativeWeave-Design')
check('baseline_exact_registry_hash',sha((D/'docs/contracts/registry.json').read_bytes())==baseline['contract_registry_sha256']=='6dccbba3a8d813b90d0f847156450f3ab2c1db0eeb166c7e16101d71f4272ce1')
m=json.loads((D/baseline['migration_map']).read_bytes());fresh=json.loads((D/baseline['migration_results']).read_bytes())
check('same_independently_audited_map',sha((D/baseline['migration_map']).read_bytes())=='1f306d8f4625421360f4e324f1e83f1382d53155f9b6748a7c11682af7b9c1c8')
check('same_independently_audited_results',sha((D/baseline['migration_results']).read_bytes())=='b3ad8b53f4c5aa80107e4b7b63489bd46a319040d58af3ced6dba8b19863a220')
check('executed_design_commit_and_run_preserved',fresh['repository']=='IzuSharp/NativeWeave-Design' and fresh['tested_design_commit']=='67b48674e469c98f2f73f1c9ff0d63b113abc47b' and str(fresh['run_id'])==cp['new_design_run']=='43371161177' and fresh['all_six_jobs_passed'] and len(fresh['records'])==6)
check('old_139_map_source_identity',m['source_repository']=='IzuSharp/NativeWeave' and m['source_head']==SOURCE and m['source_base']==cp['source_native_main']=='658ed6a410783de356a7b9b2cd6601336fff5148' and m['mapped_files']==139 and m['byte_exact_files']==137 and m['adapted_files']==2)
previous=json.loads((O/'integrity-audit.json').read_text())
check('previous_1240_source_artifact_checks_still_apply',previous['errors']==[] and previous['passed_checks']==previous['total_checks']==1240 and previous['design_head']==DESIGN and previous['source_head']==SOURCE)
check('original_history_not_relabelled',fresh['original_history_relabelled'] is False and fresh['product_delivery_executed'] is False and fresh['independent_review'] is False)
check('current_phase_explicit',all(x in data('CURRENT-PHASE.md').decode() for x in ['Do not execute A/B Delivery','Do not merge PR1 or delete its history','Self-review and CI are not independent review','separately authorized phase transition']))
wf=yaml.load(data('.github/workflows/native-slices-final-check.yml'),Loader=yaml.BaseLoader)
steps=wf['jobs']['paired-integrity']['steps'];co=[s for s in steps if s.get('uses','').startswith('actions/checkout@')]
check('ci_exact_plan_head',co[0]['with']['ref']=='${{ github.event.pull_request.head.sha || github.sha }}')
check('ci_uses_exact_baseline_design_commit',co[1]['with']['repository']=='IzuSharp/NativeWeave-Design' and co[1]['with']['ref']=='${{ steps.input.outputs.design_sha }}' and any("b['design_merge_commit']" in s.get('run','') and "re.fullmatch('[0-9a-f]{40}',sha)" in s.get('run','') for s in steps))
check('ci_no_product_checkout_or_write',len(co)==2 and wf['permissions']=={'contents':'read'} and all(s['with'].get('persist-credentials')=='false' for s in co))
check('ci_preserves_failure_and_pins_action_hashes',all(re.fullmatch(r'.+@[0-9a-f]{40}',s['uses']) for s in steps if 'uses' in s) and not any('continue-on-error' in s or '|| true' in s.get('run','') or '--admin' in s.get('run','') for s in steps))
check('ci_runs_graph_safety_and_three_schemas',all(any(term in s.get('run','') for s in steps) for term in ['verify_research_assets.py','validate_graphs.py','mutation_checks.py','rust1100_checks.py','Draft202012Validator']))
mwf=yaml.load(data('.github/workflows/research-assets-reference-migration.yml'),Loader=yaml.BaseLoader);job=mwf['jobs']['align']
check('one_shot_workflow_only_plan_research_branch',mwf['on']['push']['branches']==['research/pr1-asset-migration'] and job['if']=="github.repository == 'IzuSharp/Plan' && github.ref == 'refs/heads/research/pr1-asset-migration'" and any('git push origin HEAD:refs/heads/research/pr1-asset-migration' in s.get('run','') for s in job['steps']))
check('one_shot_migration_no_product_checkout',all(s.get('with',{}).get('repository') in [None,'IzuSharp/NativeWeave-Design'] for s in job['steps'] if s.get('uses','').startswith('actions/checkout@')))
check('core_graph_gate_implementations_unchanged',all(data(rel)==data(rel,BASE) for rel in ['tools/validate_graphs.py','tools/mutation_checks.py','tools/rust1100_checks.py','schemas/graph-v1.schema.json']))
vals=json.loads((O/'merged-plan-validations.json').read_text());mut=json.loads((P/'verification/mutation-checks.json').read_text());rust=json.loads((P/'verification/rust1100-checks.json').read_text())
check('all_six_commands_passed',len(vals)==6 and all(v['exit_code']==0 for v in vals))
check('14_mutation_cases_passed',len(mut['results'])==14 and mut['all_passed'] and all(x['passed'] and x['ready_fail_closed'] for x in mut['results']))
check('four_rust_gate_regressions_passed',len(rust['regressions'])==4 and all(x['passed'] for x in rust['regressions']))
check('no_accepted_contracts_no_ready_or_continuable_delivery',rust['accepted_contracts']==0 and rust['ready']['delivery']==rust['continuable']['delivery']==[])
result={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent post-merge review of actual Plan PR #4; concurrent recovery superseded duplicate PR #5 patch review. No source edits or remote writes.','reviewer':{'agent':'/root/migration_evidence','independent_of_patch_author':True,'github_separate_account_approval':False,'contract_or_product_acceptance':False},'base':BASE,'reviewed_commit':HEAD,'tree':snap['tree'],'file_count':49,'content_sha256':snap['content_sha256'],'diff_sha256':snap['diff_sha256'],'task_states':states,'changed_packet_ids':sorted(changed),'unchanged_packets':81,'delivery_packets_unchanged':48,'source_artifact_audit':'INDEPENDENT-MIGRATION-AUDIT.md and integrity-audit.json (1240/1240)','checks':checks,'passed_checks':sum(c['passed'] for c in checks),'total_checks':len(checks),'errors':[c for c in checks if not c['passed']],'validation_commands':vals,'limitations':['Local review does not independently certify historical GitHub rule enforcement or another GitHub account approval. Root integrator checks live PR/Actions/rules separately.','No native Rust/C# experiment rerun was performed. Existing source and artifact preservation was independently audited.','Fixed 33-packet checkpoint in verify_research_assets.py is a historical migration invariant; a later legitimate packet change with baseline updates may require explicitly scoping this check rather than falsely preserving 33.','Historical closure checkpoint text remains a pre-merge observation; root integrator separately verifies actual PR #1 closed state.']}
(O/'PLAN-MIGRATION-REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','validation_commands','limitations']},ensure_ascii=False,indent=2))
raise SystemExit(bool(result['errors']))
