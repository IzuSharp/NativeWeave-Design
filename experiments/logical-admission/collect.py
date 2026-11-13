"""Archive this experiment's actual Design runs; no independent or production claim."""
from pathlib import Path,PurePosixPath
import hashlib,io,json,os,subprocess,urllib.request,urllib.error,zipfile
D=Path.cwd();REPO='IzuSharp/NativeWeave-Design';RUN=os.environ['GITHUB_RUN_ID'];HEAD=os.environ['GITHUB_SHA']
H={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}
def sha(data):return hashlib.sha256(data).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
def download(url):
 assert url.startswith('https://api.github.com/repos/'+REPO+'/actions/artifacts/')
 try:
  with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers=H),timeout=120) as r:return r.read()
 except urllib.error.HTTPError as e:
  if e.code not in (301,302,303,307,308):raise
  url=e.headers['Location'];assert url.startswith('https://')
  with urllib.request.urlopen(url,timeout=120) as r:return r.read()
with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+REPO+'/actions/runs/'+RUN+'/artifacts?per_page=100',headers=H),timeout=120) as r:arts=json.load(r)['artifacts']
arts=[a for a in arts if a['name'].startswith('logical-admission-')]
assert {a['name'] for a in arts}=={'logical-admission-ubuntu-24.04','logical-admission-windows-2022'}
root=D/'verification/logical-admission';root.mkdir(parents=True,exist_ok=True)
(root/'.gitattributes').write_text('* -text\n')
records=[]
for a in arts:
 raw=download(a['archive_download_url']);assert a['digest']=='sha256:'+sha(raw)
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist();rnames=[n for n in names if n.endswith('/result.json')];assert len(rnames)==1
 result=json.loads(z.read(rnames[0]));assert result['success'] and result['design_commit']==HEAD
 prefix=rnames[0][:-len('result.json')]
 assert all(c['exit_code']==0 for c in json.loads(z.read(prefix+'commands.json')))
 for path,digest in result['source_files'].items():
  assert sha(subprocess.check_output(['git','show',HEAD+':'+path]))==digest,path
 for name,aot in [('normal-run',False),('aot-run',True)]:
  text=z.read(prefix+name+'.stdout').decode()
  assert f'SUCCESS logical-admission assertions=653 aot={aot} gate_rounds=64' in text
  assert 'OBSERVED negative-control post-Dispose call admitted' in text
 native=prefix+'publish/'+('nw_interop_probe.dll' if 'windows' in a['name'] else 'libnw_interop_probe.so')
 exe=prefix+'publish/'+('Admission.exe' if 'windows' in a['name'] else 'Admission')
 assert sha(z.read(native))==result['native_sha256'] and sha(z.read(exe))==result['aot_executable_sha256']
 files=[]
 for name in names:
  p=PurePosixPath(name)
  if name.endswith('/'):continue
  assert not p.is_absolute() and '..' not in p.parts
  if p.suffix not in ('.json','.stdout','.stderr'):continue
  data=z.read(name);data.decode();assert len(data)<2_000_000
  dest=root/RUN/a['name']/Path(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  files.append({'path':str(dest.relative_to(D)),'sha256':sha(data)})
 records.append({'artifact_id':a['id'],'artifact':a['name'],'zip_sha256':sha(raw),'result':result,'files':files})
url='https://raw.githubusercontent.com/dotnet/runtime/deae2e32bf0e018e09d64597b7c59b62b73bb3ce/src/libraries/System.Private.CoreLib/src/System/Runtime/InteropServices/SafeHandle.cs'
with urllib.request.urlopen(url,timeout=60) as r:source=r.read()
blob=hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest();assert blob=='2d1f9313b485c57afab1f187e00a180df7fad3ba'
(root/'upstream').mkdir(exist_ok=True);(root/'upstream/SafeHandle.cs').write_bytes(source)
report={'run_id':RUN,'tested_design_commit':HEAD,'both_platforms_passed':True,'source_review':{'url':url,'git_blob_sha1':blob,'sha256':sha(source),'path':'verification/logical-admission/upstream/SafeHandle.cs','file_lines':len(source.splitlines())},'records':records,'independent_review':False,'formal_contract_accepted':False,'product_delivery_executed':False,'scope':'Synchronous logical admission only; not async retirement, arbitrary invalid pointers, performance or production acceptance'}
(root/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'run_id':RUN,'source':HEAD,'platforms':2,'assertions_per_execution':653,'positive_gate_rounds_per_execution':64,'raw_files':sum(len(r['files']) for r in records)}))
