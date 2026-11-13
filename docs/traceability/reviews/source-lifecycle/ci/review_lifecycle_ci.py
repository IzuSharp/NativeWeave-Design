from pathlib import Path,PurePosixPath
import json,hashlib,subprocess,zipfile,re,datetime,yaml
R=Path('/workspace/scratch/a64c8260e732/nativeweave');D=R/'NativeWeave-Design-research';O=R/'recovery/migration-evidence';Z=R/'recovery/source-lifecycle/ci-43375871731';A=D/'verification/source-lifecycle';COMMIT='de43481581df9876cb2d0aed5de2db796d048c9d';RUN=43375871731
api=json.loads((O/'source-lifecycle-live-api.json').read_text());summary=json.loads((A/'results.json').read_text());checks=[];inputs=[];archives=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def gitbytes(path):return subprocess.check_output(['git','show',COMMIT+':'+path],cwd=D)
def check(n,p,detail=None):checks.append({'check':n,'passed':bool(p),**({'detail':detail} if detail is not None else {})})
check('fresh_api_run_exact_success',api['run']['id']==RUN and api['run']['head_sha']==COMMIT and api['run']['status']=='completed' and api['run']['conclusion']=='success')
jobs=api['jobs']['jobs'];arts=api['artifacts']['artifacts']
check('fresh_api_four_successful_jobs',api['jobs']['total_count']==len(jobs)==4 and all(j['head_sha']==COMMIT and j['conclusion']=='success' and j['status']=='completed' for j in jobs))
check('fresh_api_exact_four_artifacts',api['artifacts']['total_count']==len(arts)==len(summary['records'])==4 and {a['id'] for a in arts}=={r['artifact_id'] for r in summary['records']})
check('archive_summary_identity',summary['repository']=='IzuSharp/NativeWeave-Design' and summary['run_id']==RUN and summary['tested_source_commit']==COMMIT and summary['successful_jobs']==4 and summary['formal_contract_accepted'] is False and summary['product_delivery_executed'] is False)
wfraw=gitbytes('.github/workflows/source-lifecycle-research.yml');wf=yaml.load(wfraw,Loader=yaml.BaseLoader);job=wf['jobs']['lifecycle'];steps=job['steps'];upload=next(s for s in steps if s.get('uses','').startswith('actions/upload-artifact@'))
check('executed_workflow_sha256',sha(wfraw)==summary['workflow_sha256'])
check('executed_matrix_only_missing_db_server',set(job['strategy']['matrix']['fixture'])=={'database-retirement','server-retained-bytes'} and set(job['strategy']['matrix']['os'])=={'ubuntu-24.04','windows-2022'})
check('executed_workflow_no_repeat_interop',not any('interop-admission' in s.get('run','') for s in steps))
check('artifact_upload_preserves_all_raw_inputs',upload['if']=='always()' and upload['with'].get('include-hidden-files')=='true' and all(t in upload['with']['path'] for t in ['*.json','*.stdout','*.stderr','inputs/**','binaries/**']))
check('workflow_readonly_exact_head_and_actions',wf['permissions']=={'contents':'read'} and steps[0]['with']['ref']=='${{ github.sha }}' and steps[0]['with']['persist-credentials']=='false' and all(re.fullmatch(r'.+@[0-9a-f]{40}',s['uses']) for s in steps if 'uses' in s))
rawcount=0;names=set()
for record in summary['records']:
 art=next(a for a in arts if a['id']==record['artifact_id']);blob=(Z/(str(art['id'])+'.zip')).read_bytes();digest=sha(blob);tag=art['name'];fixture=record['fixture']
 check(tag+'_api_run_identity',art['workflow_run']['id']==RUN and art['workflow_run']['head_sha']==COMMIT and not art['expired'])
 check(tag+'_download_digest_and_size',art['digest']=='sha256:'+digest and record['artifact_zip_sha256']==digest and len(blob)==record['artifact_bytes']==art['size_in_bytes'])
 with zipfile.ZipFile(Z/(str(art['id'])+'.zip')) as z:
  members=[n for n in z.namelist() if not n.endswith('/')];check(tag+'_safe_unique_zip_members',len(members)==len(set(members)) and all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in members))
  prefix='verification/source-lifecycle/'+str(RUN)+'/'+tag+'/'
  saved={f['path'][len(prefix):]:f for f in record['files'] if f['path'].startswith(prefix)}
  check(tag+'_exact_preserved_member_set',set(saved)==set(members) and len(saved)==len(record['files']))
  for member in members:
   b=z.read(member);f=saved[member];target=D/f['path'];rawcount+=1;names.add(f['path'])
   check(tag+'/'+member+'_actual_zip_saved_sha',target.read_bytes()==b and len(b)==f['bytes'] and sha(b)==f['sha256'])
  result=json.loads(z.read('result.json'))
  current_tests=sorted(re.findall(r'#\[tokio::test\]\s+async fn ([a-z_0-9]+)',gitbytes('experiments/'+fixture+'/src/lib.rs').decode()))
  if fixture=='database-retirement':
   check(tag+'_real_named_test_result',result['passed'] and result['input_bytes_unchanged'] and result['github_run_id']==str(RUN) and result['github_head_sha']==COMMIT and sorted(result['passed_test_names'])==current_tests==sorted(record['tests_passed']) and len(current_tests)==6)
   commands=json.loads(z.read('commands.json')); source=json.loads(z.read('source-inputs.json'));reported={n:v['sha256'] for n,v in source.items()};stdout=z.read('tests.stdout').decode()
  else:
   check(tag+'_real_named_test_result',result['success'] and result['github_run_id']==str(RUN) and result['git_head']==COMMIT and sorted(result['named_tests_passed'])==current_tests==sorted(record['tests_passed']) and len(current_tests)==6)
   commands=result['commands'];reported=result['source_sha256_before'];check(tag+'_input_before_after_same',reported==result['source_sha256_after']);stdout=z.read('2.stdout').decode()
   for log,h in result['logs_sha256'].items():check(tag+'/'+log+'_recorded_log_hash',sha(z.read(log))==h)
  check(tag+'_commands_succeeded',all(c['exit_code']==0 for c in commands))
  check(tag+'_raw_test_output_six',sorted(re.findall(r'^test tests::([a-z_0-9]+) \.\.\. ok\r?$',stdout,re.M))==current_tests and '6 passed; 0 failed' in stdout)
  check(tag+'_five_source_inputs',len(reported)==5 and reported==record['source_inputs'] and set(reported)==set(record['source_input_identities']))
  for name,expected in reported.items():
   b=z.read('inputs/'+name);g=gitbytes('experiments/'+fixture+'/'+name);identity=record['source_input_identities'][name];same=b==g
   converted=(b'\r' not in g and g.replace(b'\n',b'\r\n')==b and b.replace(b'\r\n',b'\n')==g and len(b)-len(g)==g.count(b'\n'))
   expected_relation='exact_LF_to_CRLF_checkout_conversion' if fixture=='database-retirement' and tag.endswith('windows-2022') else 'byte_exact'
   check(tag+'/'+name+'_source_identity',sha(b)==expected==identity['checkout_sha256'] and sha(g)==identity['git_blob_sha256'] and identity['relationship']==expected_relation and (converted and not same if expected_relation!='byte_exact' else same))
   inputs.append({'artifact':tag,'fixture':fixture,'path':name,'git_blob_sha256':sha(g),'checkout_sha256':sha(b),'git_bytes':len(g),'checkout_bytes':len(b),'LF_count':g.count(b'\n'),'relationship':expected_relation})
 archives.append({'id':art['id'],'name':tag,'zip_sha256':digest,'bytes':len(blob),'api_digest_verified':True,'raw_members':len(members)})
check('exact_56_raw_files',rawcount==len(names)==summary['preserved_raw_files']==56)
check('source_identity_distribution',len(inputs)==20 and sum(i['relationship']=='byte_exact' for i in inputs)==15 and sum(i['relationship']=='exact_LF_to_CRLF_checkout_conversion' for i in inputs)==5)
first=json.loads((A/'artifact-verification-attempt-1.json').read_text());check('strict_first_attempt_failure_retained',first['success'] is False and 'Cargo.toml' in first['failure'] and (A/'artifact-verification-attempt-1.json').is_file())
result={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'/root/migration_evidence','review_scope':'Independent archive/API/source-byte verification only; no fixture reruns, no remote writes','run_id':RUN,'tested_source_commit':COMMIT,'results_manifest_sha256':sha((A/'results.json').read_bytes()),'workflow_sha256':sha(wfraw),'fresh_api_snapshot_sha256':sha((O/'source-lifecycle-live-api.json').read_bytes()),'archives':archives,'raw_files':rawcount,'source_inputs':inputs,'source_input_counts':{'total':20,'byte_exact':15,'exact_LF_to_CRLF_checkout_conversion':5},'checks':checks,'passed_checks':sum(c['passed'] for c in checks),'total_checks':len(checks),'errors':[c for c in checks if not c['passed']],'independent_code_review':'DB/D15 separately in DATABASE-LIFECYCLE-REVIEW.json. Server code/protocol reviewed by the other assigned agent. This file does not independently review the reviewer-authored Interop supplemental prototype.','acceptance':'Finite research evidence only; not product contracts, Delivery, architectural acceptance or another GitHub account approval.'}
(O/'SOURCE-LIFECYCLE-CI-REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','source_inputs']},indent=2))
raise SystemExit(bool(result['errors']))
