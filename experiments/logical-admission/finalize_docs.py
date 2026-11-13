"""Verify completed R07 evidence and add non-normative detail to existing documents."""
from pathlib import Path
import hashlib,json,os,subprocess,urllib.request
D=Path.cwd();e=D/'verification/logical-admission';r=json.loads((e/'primary-results.json').read_text())
assert r['both_platforms_passed'] and r['tested_design_commit']=='28f6cf7e6e4e80b9f32a92ad587a528d82911bd0'
def sha(b):return hashlib.sha256(b).hexdigest()
count=0
for record in r['records']:
 result=record['result'];assert result['success'] and result['managed_assertions_per_execution']==653 and result['positive_gate_rounds_per_execution']==64
 for p,h in result['source_files'].items():assert sha((D/p).read_bytes())==h,p
 for f in record['files']:assert sha((D/f['path']).read_bytes())==f['sha256'];count+=1
assert len(r['records'])==2 and count==32
assert sha((D/r['source_review']['path']).read_bytes())==r['source_review']['sha256']
assert r['source_review']['file_lines']==265
# New review excerpts retain full-source identity separately from excerpt identity.
sources=[
 ('SeaQL/sea-query','f2d5e04d30919c342da1f8845ff1fde46e3308fc','src/query/select.rs','f5d48689a7b88e3b17f855b67ad3b40af05c2940',[(40,64)]),
 ('SeaQL/sea-query','f2d5e04d30919c342da1f8845ff1fde46e3308fc','src/query/traits.rs','7527dab633c156e6918bc4404b7d98b923760452',[(5,25),(83,87)]),
 ('tower-rs/tower','4b0a6b0e688bd177eb2c9c97f5268dd9703c66fc','tower/src/limit/concurrency/future.rs','2d8833692e3434f533900e2ae8cd637995eaf13e',[(1,1000)]),
 ('rust-lang/rust','0ef1bc386059596dada8fb65b50425aab2ea637a','library/std/src/sync/poison/mutex.rs','42c5fcf3e27c02adf3d2143e30b5c77d2bf05491',[(1,110)])]
review=[]
for index,(repo,commit,path,blob,ranges) in enumerate(sources):
 url=f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
 with urllib.request.urlopen(url,timeout=60) as response:raw=response.read()
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,(repo,path)
 lines=raw.decode().splitlines();parts=[];actual=[]
 for lo,hi in ranges:
  hi=min(hi,len(lines));actual.append([lo,hi]);parts.extend(f'{i}: {lines[i-1]}' for i in range(lo,hi+1))
 data=('Source: '+url+'\nOriginal copyright and license remain those of the upstream repository.\n\n'+'\n'.join(parts)+'\n').encode()
 out=e/'upstream'/f'review-{index+1}.txt';out.write_bytes(data)
 review.append({'repository':repo,'commit':commit,'path':path,'blob_sha1':blob,'full_source_sha256':sha(raw),'read_ranges':actual,'excerpt_path':str(out.relative_to(D)),'excerpt_sha256':sha(data),'upstream_tests_executed':False})
(e/'source-review.json').write_text(json.dumps(review,indent=2)+'\n')
p=D/'experiments/logical-admission/README.md';s=p.read_text();s=s.replace('inspected lines130–281','inspected lines130–265');p.write_text(s)
p=D/'docs/research/topics/R07/logical-admission.md';s=p.read_text().replace('complete41-line implementation','complete ResponseFuture implementation');p.write_text(s)
p=D/'docs/research/topics/R07/report.md';s=p.read_text()
heading='## Post-migration executed logical-admission evidence'
assert heading not in s
p.write_text(s+'\n'+heading+'\n\nThe original report above is a historical source-analysis snapshot. [The new R07/D04 study](logical-admission.md) adds actual Windows/Linux normal and Native AOT negative/positive admission evidence: run43373306474,653 assertions and64 guided gate/Dispose rounds per invocation. It distinguishes logical admission, physical lifetime, native mutation and async retirement, and includes checked SeaQuery/Tower/Rust source implications. The local SafeHandle-only admission question is resolved; full task/contract acceptance and independent review remain pending. Research code and raw outputs are Design-owned, not product implementation.\n')
p=D/'docs/contracts/lifetime-v0.1.md';s=p.read_text();heading='## Supplemental execution evidence — logical admission only'
assert heading not in s
p.write_text(s+'\n'+heading+'\n\nThis non-normative update does not change the v0.1.0 admission protocol or accept the contract. The earlier uncompiled skeleton is now complemented by an equivalent synchronous research facade in `experiments/logical-admission/Program.cs`, tested at Design28f6cf7e6e4e80b9f32a92ad587a528d82911bd0/run43373306474. Both Windows/Linux passed normal and actual AOT runs with653 assertions and64 controlled gate/Dispose rounds each. The original SafeHandle-only facade admitted a new call while an old lease remained; the explicit Open/Closing gate rejected it while allowing the old call to complete. An injected managed failure returned its acquired reference.\n\nSee [R07 detailed study](../research/topics/R07/logical-admission.md) for exact source, traces, operation ordering, mutation-lock separation and future Codex test cases. The compiled fixture has no RequestStopIfApplicable, async callback, parent/child, finalizer or module-unload implementation, so those parts of this contract remain unverified by it. Keep native query mutation guards separate, avoid callbacks/await under them, and do not rely on Mutex poisoning for unsafe memory soundness. Research experiment success is not formal A03/A07/B11/B17 implementation or independent acceptance.\n')
p=D/'docs/contracts/registry.json';registry=json.loads(p.read_text())
for c in registry['contracts']:
 if c['id']=='C-LIFETIME-001':
  assert c['status']=='proposed' and not c['reviews']
  c['content_sha256']=sha((D/c['spec_path']).read_bytes())
  c['evidence']=['docs/research/topics/R07/logical-admission.md','verification/logical-admission/primary-results.json']
  c['version_note']='0.1.0-draft protocol unchanged; non-normative finite execution addendum updates exact content hash. Old reviews do not approve these new bytes. Independent and full contract acceptance remain pending.'
p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
checked=[]
for c in registry['contracts']:
 if c.get('spec_path') and c.get('content_sha256'):
  assert sha((D/c['spec_path']).read_bytes())==c['content_sha256'],c['id'];checked.append(c['id'])
assert all(c['status']!='accepted' for c in registry['contracts'])
# Confirm the authorized closure, without making any product-repository mutation.
def get(path):
 with urllib.request.urlopen('https://api.github.com/repos/IzuSharp/NativeWeave/'+path,timeout=60) as response:return json.load(response)
pr=get('pulls/1');main=get('git/ref/heads/main');branch=get('git/ref/heads/research/native-slices-rust-1100')
assert pr['state']=='closed' and not pr['merged'] and pr['head']['sha']=='267364a440074a61e193cf33315f1b9d0fa8126b'
assert main['object']['sha']=='658ed6a410783de356a7b9b2cd6601336fff5148' and branch['object']['sha']==pr['head']['sha']
closure={'product_pr':1,'state':pr['state'],'merged':pr['merged'],'closed_at':pr['closed_at'],'preserved_branch':branch['ref'],'preserved_head':branch['object']['sha'],'unchanged_main':main['object']['sha'],'design_migration_merge':'c7e123a74405a92dc3de1ef450355b08d1c05ceb','plan_migration_merge':'04c2f043c0ec60a2d49dd3ca8ea4ad1c8c888d89'}
(D/'docs/traceability/research-asset-closure.json').write_text(json.dumps(closure,indent=2)+'\n')
report={'input_commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'verified_new_raw_files':count,'inspected_upstream_sources':len(review)+1,'checked_specification_hashes':checked,'independent_review':False,'accepted_contracts':0,'formal_delivery_executed':False,'migration_closed_without_merge':True}
(e/'design-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
