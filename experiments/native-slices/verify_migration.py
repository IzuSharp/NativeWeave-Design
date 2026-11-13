"""Verify all mapped bytes; optionally execute one relocated research fixture."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
D=Path(__file__).resolve().parents[2]; E=D/'experiments/native-slices'
m=json.loads((D/'verification/native-slices/migration-map.json').read_text())
assert m['mapped_files']==139 and len(m['records'])==139
for r in m['records']:
 p=(D/r['destination_path']).resolve();assert p.is_relative_to(D.resolve())
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['destination_sha256'],r['destination_path']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==r['destination_blob_sha1']
 if r['byte_exact']:assert r['source_sha256']==r['destination_sha256']
mapping={r['source_path']:r['destination_path'] for r in m['records']}
old=json.loads((D/'verification/native-slices/original-pr1/manifest.json').read_text())
for r in old['records']:
 for f in r['files']:assert hashlib.sha256((D/mapping[f['path']]).read_bytes()).hexdigest()==f['sha256']
print('PASS139 mapped assets;112 original evidence files; historical identities unchanged',flush=True)
if len(sys.argv)==1:raise SystemExit(0)
fixture=sys.argv[1];assert fixture in ('interop','database','server')
head=subprocess.check_output(['git','-C',str(D),'rev-parse','HEAD'],text=True).strip()
env=os.environ.copy();env['WORKFLOW_INPUT_COMMIT']=env.get('GITHUB_SHA','');env['GITHUB_SHA']=head;env['FIXTURE_COMMIT']=head
args=[sys.executable,str(E/'interop/run.py')] if fixture=='interop' else [sys.executable,str(E/'run_domains.py'),fixture]
# Original driver now resolves the nested experimental root; cwd enforces its global.json.
rc=subprocess.run(args,cwd=E,env=env,timeout=1200).returncode
if rc:raise SystemExit(rc)
found=list((E/'artifacts').glob(f'{fixture}-*/result.json'));assert len(found)==1,found
result=json.loads(found[0].read_text());assert result['success'] and result['source_commit']==head
print('PASS relocated '+fixture+' at '+head,flush=True)
