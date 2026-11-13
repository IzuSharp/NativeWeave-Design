"""Keep the original successful study and incidental CI rerun distinguishable."""
from pathlib import Path
import hashlib,json,subprocess
D=Path.cwd();E=D/'verification/logical-admission'
primary=subprocess.check_output(['git','show','a8025a738cfff90a4f8360aa7000f14e4f86a522:verification/logical-admission/results.json'])
p=json.loads(primary);latest=json.loads((E/'results.json').read_text())
assert p['run_id']=='43373306474' and latest['run_id']=='43374127432'
assert p['tested_design_commit']=='28f6cf7e6e4e80b9f32a92ad587a528d82911bd0' and latest['tested_design_commit']=='9fed6f510479622229cef6e917645f6510f7e3c0'
count=0
for report in (p,latest):
 assert report['both_platforms_passed']
 for r in report['records']:
  for f in r['files']:
   assert hashlib.sha256((D/f['path']).read_bytes()).hexdigest()==f['sha256'];count+=1
# All test/runtime inputs were identical; the added docs-finalization helper caused the extra run.
for old in p['records']:
 new=next(r for r in latest['records'] if r['artifact']==old['artifact'])
 assert old['result']['source_files']==new['result']['source_files']
(E/'primary-results.json').write_bytes(primary)
incident={'primary_run':p['run_id'],'incidental_rerun':latest['run_id'],'both_runs_passed':True,'same_test_input_hashes':True,'raw_files_verified':count,'reason':'Initial workflow paths matched all experiment files, including a documentation finalization helper. A normal push triggered an unnecessary extra execution.','correction':'Execution paths now list actual C#/project/runner/native/toolchain inputs; documentation helpers no longer trigger tests. The extra result is retained, not counted as new research.','independent_review':False}
(E/'ci-trigger-correction.json').write_text(json.dumps(incident,indent=2)+'\n')
# Correct the finalizer's evidence reference to the original primary run, without discarding the later run.
f=D/'experiments/logical-admission/finalize_docs.py';s=f.read_text()
old="r=json.loads((e/'results.json').read_text())";new="r=json.loads((e/'primary-results.json').read_text())"
assert old in s;s=s.replace(old,new,1).replace("'verification/logical-admission/results.json'","'verification/logical-admission/primary-results.json'")
f.write_text(s)
subprocess.run(['python3',str(f)],check=True)
f=D/'docs/research/topics/R07/logical-admission.md';s=f.read_text().replace('verification/logical-admission/results.json','verification/logical-admission/primary-results.json')
s+='\n## CI trigger correction\n\nA documentation-helper push unintentionally triggered run43374127432 with exactly the same tested inputs. It also passed and its separate32 raw files are preserved. It is not additional research coverage. `primary-results.json` retains the original run43373306474; `results.json` remains the actual latest run, and `ci-trigger-correction.json` records both. Execution triggers were narrowed; final documentation checks do not rerun native/managed scenarios.\n'
f.write_text(s)
print(json.dumps(incident,indent=2))
