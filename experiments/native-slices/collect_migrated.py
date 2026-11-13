"""Collect this Design run's six relocated results; never re-label historical runs."""
from pathlib import Path,PurePosixPath
import hashlib,io,json,os,subprocess,urllib.request,urllib.error,zipfile
D=Path.cwd();run=os.environ['GITHUB_RUN_ID'];repo='IzuSharp/NativeWeave-Design'
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def api(path):
 with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+'/'+path,headers=headers),timeout=120) as r:return json.load(r)
def download(url):
 assert url.startswith('https://api.github.com/repos/'+repo+'/actions/artifacts/')
 try:
  with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers=headers),timeout=120) as r:return r.read()
 except urllib.error.HTTPError as e:
  if e.code not in (301,302,303,307,308):raise
  location=e.headers['Location'];assert location.startswith('https://')
  with urllib.request.urlopen(location,timeout=120) as r:return r.read()
def sha(b):return hashlib.sha256(b).hexdigest()
arts=api('actions/runs/'+run+'/artifacts?per_page=100')['artifacts']
arts=[a for a in arts if a['name'].startswith('relocated-')]
expected={f'relocated-{f}-{o}' for f in ('interop','database','server') for o in ('ubuntu-24.04','windows-2022')}
assert {a['name'] for a in arts}==expected
records=[]
for a in sorted(arts,key=lambda x:x['name']):
 raw=download(a['archive_download_url']);assert a['digest']=='sha256:'+sha(raw)
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist();results=[n for n in names if n.endswith('/result.json')];assert len(results)==1
 result=json.loads(z.read(results[0]));assert result['success'] and result['source_commit']==head,(a['name'],result)
 prefix=results[0][:-len('result.json')];cmds=json.loads(z.read(prefix+'commands.json'));assert all(x['exit_code']==0 for x in cmds)
 for path,digest in result['source_files'].items():
  path=path.replace('\\','/');gitpath='experiments/native-slices/'+path
  source=subprocess.check_output(['git','show',head+':'+gitpath]);assert sha(source)==digest,gitpath
 if a['name'].startswith('relocated-interop'):
  assert 'SUCCESS assertions=185 aot=True' in z.read(prefix+'aot-run.stdout').decode()
  packs=[n for n in names if n.endswith('.nupkg')];assert len(packs)==1
  assert sha(z.read(packs[0]))==result['package_sha256']
  pkg=zipfile.ZipFile(io.BytesIO(z.read(packs[0])));assets=[n for n in pkg.namelist() if n.startswith('runtimes/') and n.endswith(('.so','.dll'))];assert len(assets)==1
  assert sha(pkg.read(assets[0]))==result['native_sha256']
  exe=prefix+'publish/'+('Consumer.exe' if 'windows' in a['name'] else 'Consumer')
  assert sha(z.read(exe))==result['aot_executable_sha256']
 else:
  count=6 if a['name'].startswith('relocated-database') else 4
  assert f'{count} passed; 0 failed' in z.read(prefix+'tests.stdout').decode()
 files=[]
 for name in names:
  path=PurePosixPath(name)
  if name.endswith('/'):continue
  assert not path.is_absolute() and '..' not in path.parts
  if path.suffix not in ('.json','.stdout','.stderr','.lock','.toml','.rs','.cs','.csproj','.py','.md'):continue
  data=z.read(name);data.decode('utf-8');assert len(data)<2_000_000
  dest=Path('verification/native-slices/migrated')/run/a['name']/Path(*path.parts)
  (D/dest).parent.mkdir(parents=True,exist_ok=True);(D/dest).write_bytes(data)
  files.append({'path':str(dest),'sha256':sha(data),'bytes':len(data)})
 records.append({'artifact':a['name'],'artifact_id':a['id'],'artifact_zip_sha256':sha(raw),'tested_design_commit':head,'success':True,'files':files})
report={'repository':repo,'run_id':run,'tested_design_commit':head,'migration_map_sha256':sha((D/'verification/native-slices/migration-map.json').read_bytes()),'all_six_jobs_passed':True,'records':records,'original_history_relabelled':False,'independent_review':False,'product_delivery_executed':False,'binary_assets':'verified from artifacts; raw text and binary hashes persisted; not product releases'}
(D/'verification/native-slices/migration-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'run_id':run,'tested_design_commit':head,'all_six_jobs_passed':True,'raw_files':sum(len(r['files']) for r in records)}))
