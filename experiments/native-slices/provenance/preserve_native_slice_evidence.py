"""Persist exact already-executed CI evidence. Never rebuild or rerun fixtures.
Repository token is not forwarded to the temporary artifact storage host.
"""
from pathlib import Path, PurePosixPath
import datetime,hashlib,io,json,os,subprocess,urllib.request,urllib.error,zipfile
ROOT=Path.cwd();OUT=ROOT/'verification/native-slices';OUT.mkdir(parents=True,exist_ok=True)
# label,run,artifact,ZIP digest,executed source,expected success
ITEMS=[
('interop-linux',43363045559,14009370861,'42d197ed6ceb6ab1b7879079fe6a487b7f59c15ad203eb66a6d8d02200abf124','4a4adc883b80719d2a9b2bfb03be5ec86b543f3c',True),
('interop-windows',43363045559,14008494778,'7f4bb0600182d1092882725217a253f6b6d5edff3fb62dd7133a1fd7a84cb4e1','4a4adc883b80719d2a9b2bfb03be5ec86b543f3c',True),
('server-linux',43363994414,14009482437,'5b73ec1bc9287da6c7eae2140939a1f54800601e3959cbe74f425e82efd0459b','5dd696725afe75f2b8b03b104c8275db50dcf2c7',True),
('server-windows',43363994414,14009078546,'d4377b992bd5b2822b791cfefbe749823ce9402f9cf7556c988dd7a37002ba63','5dd696725afe75f2b8b03b104c8275db50dcf2c7',True),
('database-first-failure-linux',43363994414,14010040740,'75d35d974758f024d1510d1dcae26df7998c7065037b16e650a485ad6bb56dd0','5dd696725afe75f2b8b03b104c8275db50dcf2c7',False),
('database-first-failure-windows',43363994414,14009881379,'d1164166ab2932d68de478fd1e046e3df339a8c4fb8d4408f2b5ec5492ce2986','5dd696725afe75f2b8b03b104c8275db50dcf2c7',False),
('database-linux',43364366610,14009114165,'b40f0ae6fad80d44aa867579a4cd256496194f622f1711a69185bbf5aa76543d','43e4fbcbe0417165c0f7df03507bfa1da8a53049',True),
('database-windows',43364366610,14009902007,'dcf513ca31bde0b3d7e6aa273e2ca6e2e2220002ede2ad97d9d3fb42510e2e2f','43e4fbcbe0417165c0f7df03507bfa1da8a53049',True)]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
def download(aid):
 req=urllib.request.Request(f'https://api.github.com/repos/IzuSharp/NativeWeave/actions/artifacts/{aid}/zip',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=120) as r:return r.read()
 except urllib.error.HTTPError as e:
  if e.code not in (301,302,303,307,308):raise
  target=e.headers['Location']
  if not target.startswith('https://'):raise RuntimeError('unsafe redirect')
  with urllib.request.urlopen(target,timeout=120) as r:return r.read()
def sha(data):return hashlib.sha256(data).hexdigest()
def git_bytes(commit,path):return subprocess.check_output(['git','show',commit+':'+path.replace('\\','/')])
manifest=[]
for label,run,aid,digest,commit,expected in ITEMS:
 raw=download(aid);assert sha(raw)==digest,(label,'ZIP mismatch')
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
 results=[n for n in names if n.endswith('/result.json')];assert len(results)==1,label
 result=json.loads(z.read(results[0]));assert result['success']==expected and result['source_commit']==commit,(label,result)
 prefix=results[0][:-len('result.json')]
 commands=json.loads(z.read(prefix+'commands.json'))
 assert (all(c['exit_code']==0 for c in commands))==expected,label
 # Source checkout bytes can differ only by text EOL on Windows. Record BOTH
 # executed-byte and Git-blob-byte identities; do not rewrite the raw evidence.
 source_checks=[]
 for path,d in result['source_files'].items():
  original=git_bytes(commit,path);matches=sha(original)==d;mode='exact'
  if not matches:
   crlf=original.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
   if sha(crlf)!=d:raise RuntimeError('Source digest does not match Git or checkout CRLF: '+path)
   mode='git-LF-to-checkout-CRLF'
  source_checks.append({'path':path,'executed_sha256':d,'git_blob_bytes_sha256':sha(original),'comparison':mode})
 files=[]
 for n in names:
  rel=PurePosixPath(n)
  if n.endswith('/'):continue
  if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('unsafe ZIP path')
  # Preserve raw text evidence, not executable/native packages.
  if rel.suffix not in ('.json','.stdout','.stderr','.lock','.toml','.rs','.cs','.csproj','.py','.md'):continue
  data=z.read(n)
  if len(data)>2_000_000:raise RuntimeError('unexpected evidence size')
  data.decode('utf-8')
  dest=OUT/label/Path(*rel.parts[1:]);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  files.append({'path':str(dest.relative_to(ROOT)),'sha256':sha(data),'bytes':len(data)})
 if label.startswith('interop'):
  assert 'SUCCESS assertions=185 aot=True' in z.read(prefix+'aot-run.stdout').decode()
  package=[n for n in names if n.endswith('.nupkg')];assert len(package)==1
  assert sha(z.read(package[0]))==result['package_sha256']
  pkg=zipfile.ZipFile(io.BytesIO(z.read(package[0])))
  native=[n for n in pkg.namelist() if n.startswith('runtimes/') and n.endswith(('.dll','.so'))];assert len(native)==1
  assert sha(pkg.read(native[0]))==result['native_sha256']
  executable=prefix+'publish/'+('Consumer.exe' if label.endswith('windows') else 'Consumer')
  assert sha(z.read(executable))==result['aot_executable_sha256']
 else:
  text=z.read(prefix+'tests.stdout').decode()
  if expected:
   count=4 if label.startswith('server') else 6
   assert f'{count} passed; 0 failed' in text,(label,text)
  else:assert 'E0271' in z.read(prefix+'tests.stderr').decode()
 manifest.append({'label':label,'run_id':run,'artifact_id':aid,'zip_sha256':digest,'source_commit':commit,'success':expected,'source_checks':source_checks,'files':files})
report={'preservation_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preservation_input_commit':os.environ.get('GITHUB_SHA'),'preservation_run_id':os.environ.get('GITHUB_RUN_ID'),'not_an_experiment_rerun':True,'independent_review':False,'records':manifest}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'README.md').write_text('''# Native slice execution evidence

Exact already-executed run artifacts, not reruns. `manifest.json` binds ZIP IDs/digests, tested commits, raw text bytes and source checkout identities. Git LF and Windows CRLF bytes are distinguished; raw evidence is not normalized. Executables/packages remain in the original artifacts, with hashes verified from their bytes; no binaries are published as product releases.

Interop: source4a4adc8, run43363045559, Linux+Windows; four native tests and185 managed assertions in each ordinary and actual AOT execution,32 controlled Dispose/call races, six groups. NuGet PackageReference consumers use no RID for local build/run. These are physical SafeHandle-lifetime tests, not logical post-close admission or async retirement. No pristine Rust-free host is claimed.

Server: source5dd6967, run43363994414, four native tests on each OS: actual Tower response-Future negative control, body/callback shared slot, bounded queue/EOF, actual Hyper HTTP1 Service/Body over Tokio duplex. Not C# handlers, external sockets/TLS, load or a retained-byte/RSS proof.

Database: first attempt5dd6967/run43363994414 failed E0271 at Value→Expr conversion. Corrected43e4fbc/run43364366610 passed six tests per OS using locked SeaQuery1.0.2/SQLx0.9/Tokio1.54.1: bound-count/bytes/u64 checks, injected partial encoder failure, native silent-row-lock negative/rejection, no database send after overflow, runtime-table native CRUD/parameterization/type errors and explicit rollback/schema error. No PostgreSQL/C# database binding or full ORM/streaming guarantee.

This evidence supports existing R03/R04/R07/R10/R22/R25/R27/R29. Formal A/B tasks and contracts are not automatically accepted. Independent D32 review, full async, multi-Engine production integration, fault/soak/performance and clean deployment remain separate obligations.
''')
print(json.dumps({'records':len(manifest),'preserved_files':sum(len(x['files']) for x in manifest),'success_records':sum(x['success'] for x in manifest),'failed_attempts_preserved':sum(not x['success'] for x in manifest)}))
