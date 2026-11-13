"""R07 NS-01 admission probe using the unchanged recovered native/managed package.
Runs only the new controlled admission cases, not the old 185-assertion consumer.
Builds in a private temporary directory; original migrated bytes are checked and never edited.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, platform, re, shutil, subprocess, sys, tempfile, traceback, zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PIN = 'c7e123a74405a92dc3de1ef450355b08d1c05ceb'
RID = 'win-x64' if sys.platform == 'win32' else 'linux-x64'
parser = argparse.ArgumentParser()
parser.add_argument('--out', '--output', dest='out', type=Path, default=ROOT/'artifacts'/('interop-admission-'+RID))
args = parser.parse_args()
OUT = args.out.resolve()
if (OUT/'result.json').exists():
    raise SystemExit('Refusing to overwrite a previous attempt; choose a fresh --out path')
OUT.mkdir(parents=True, exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix='nw-admission-'))
records = []
env = os.environ.copy()
env.update(CARGO_TARGET_DIR=str(WORK/'target'), CARGO_BUILD_BUILD_DIR=str(WORK/'intermediates'), NUGET_PACKAGES=str(WORK/'packages'), DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(path, value): path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def run(name, command, cwd=WORK, timeout=600):
    started = utc()
    try:
        p = subprocess.run([str(x) for x in command], cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc = 124
        out = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
        err = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or '')
    except OSError as e:
        rc, out, err = 127, '', repr(e)
    (OUT/(name+'.stdout')).write_text(out, encoding='utf-8')
    (OUT/(name+'.stderr')).write_text(err, encoding='utf-8')
    records.append({'name':name, 'argv':[str(x) for x in command], 'cwd':str(cwd), 'exit_code':rc, 'started_utc':started, 'ended_utc':utc(), 'stdout_sha256':sha(OUT/(name+'.stdout')), 'stderr_sha256':sha(OUT/(name+'.stderr'))})
    dump(OUT/'commands.json', records)
    print(name, rc, flush=True)
    if rc: raise RuntimeError(f'{name} failed ({rc})\n{out[-3000:]}\n{err[-3000:]}')
    return out

def output_record(path):
    return {'path':path.relative_to(OUT).as_posix(), 'bytes':path.stat().st_size, 'sha256':sha(path)}

def parse_probe(name, text, aot):
    match = re.search(r'^SUCCESS assertions=(\d+) negative_rounds=(\d+) candidate_rounds=(\d+) live=(\d+) aot=(True|False)$', text, re.M)
    assert match, name+' has no successful probe summary'
    count, negative, candidate, live = map(int, match.groups()[:4])
    assertions = [line for line in text.splitlines() if line.startswith('ASSERT ')]
    rounds = [line for line in text.splitlines() if line.startswith('ROUND ')]
    assert (count, negative, candidate, live) == (932 if aot else 931, 32, 32, 0), match.groups()
    assert match[5] == str(aot), match.groups()
    assert len(assertions) == count and all(' pass=True ' in line for line in assertions)
    assert len(rounds) == 64 and all(line.endswith('pass=True') for line in rounds)
    return {'assertions':count, 'negative_new_calls_admitted':negative, 'candidate_new_calls_rejected':candidate, 'controlled_race_rounds':len(rounds), 'native_live_final':live, 'native_aot':aot}

result = {'repository':'IzuSharp/NativeWeave-Design', 'scope':'R07 NS-01 controlled admission experiment; not production ABI or completed Delivery', 'success':False, 'started_utc':utc(), 'rid':RID, 'platform':platform.platform(), 'architecture':platform.machine(), 'run_id':os.environ.get('GITHUB_RUN_ID'), 'workflow_trigger_sha':os.environ.get('GITHUB_SHA'), 'reused_design_snapshot':PIN, 'clean_rust_free_host':False, 'independent_review':False, 'product_delivery_executed':False}
try:
    result['source_commit'] = subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip()
    result['local_source_dirty'] = bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--',str(ROOT)], cwd=REPO, text=True).strip())
    assert platform.machine().lower() in ('x86_64','amd64'), 'This experiment currently declares x64 only'
    assert sys.platform == 'win32' or sys.platform.startswith('linux'), 'Only Windows/Linux are declared targets'
    migration_map = json.loads((REPO/'verification/native-slices/migration-map.json').read_text())
    mapped = {r['destination_path']:r['destination_sha256'] for r in migration_map['records']}
    original = REPO/'experiments/native-slices/interop'
    source_files = [ROOT/'run.py', ROOT/'global.json', *sorted((ROOT/'consumer').glob('*'))]
    reused = [original/'native/Cargo.toml', original/'native/Cargo.lock', original/'native/src/lib.rs', original/'managed/Bridge.cs', original/'managed/NativeWeave.Interop.Probe.csproj']
    for f in reused:
        assert f.is_file() and sha(f) == mapped[f.relative_to(REPO).as_posix()], 'Migrated source drift: '+str(f)
    for f in source_files+reused:
        target = OUT/'inputs'/f.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
    result['source_files'] = {f.relative_to(REPO).as_posix():sha(f) for f in source_files}
    result['reused_source_files'] = {f.relative_to(REPO).as_posix():sha(f) for f in reused}
    result['migration_map_sha256'] = sha(REPO/'verification/native-slices/migration-map.json')
    result['design_reference'] = {'path':'docs/contracts/lifetime-v0.1.md', 'sha256':sha(REPO/'docs/contracts/lifetime-v0.1.md'), 'acceptance':'proposed; no acceptance inferred'}
    shutil.copy2(ROOT/'global.json', WORK/'global.json')
    shutil.copytree(ROOT/'consumer', WORK/'consumer')
    for folder in ['native','managed']:
        shutil.copytree(original/folder, WORK/folder, ignore=shutil.ignore_patterns('bin','obj','target','__pycache__'))
    manifest = WORK/'native/Cargo.toml'
    run('rust-version',['rustc','+1.100.0','-Vv'])
    run('cargo-version',['cargo','+1.100.0','-Vv'])
    run('dotnet-info',['dotnet','--info'])
    # Only rebuild the dependency-free recovered library; do not rerun its old test suite.
    build = run('native-build',['cargo','+1.100.0','build','--locked','--offline','--release','--manifest-path',manifest,'--message-format=json'])
    libraries = []
    for line in build.splitlines():
        try: item = json.loads(line)
        except json.JSONDecodeError: continue
        if item.get('reason') == 'compiler-artifact' and item.get('target',{}).get('name') == 'nw_interop_probe':
            libraries.extend(Path(f) for f in item['filenames'] if f.endswith(('.so','.dll')))
    assert len(libraries) == 1, libraries
    native = libraries[0]
    native_hash = sha(native)
    binary = OUT/'binaries'
    (binary/'native').mkdir(parents=True, exist_ok=True)
    shutil.copy2(native,binary/'native'/native.name)
    result['native_sha256'] = native_hash
    feed = WORK/'feed'
    feed.mkdir()
    run('package-reused-managed',['dotnet','pack',WORK/'managed/NativeWeave.Interop.Probe.csproj','-c','Release','-o',feed,f'-p:NativeAsset={native}',f'-p:ProbeRid={RID}'])
    package = feed/'NativeWeave.Interop.Probe.0.0.1.nupkg'
    with zipfile.ZipFile(package) as z:
        assert hashlib.sha256(z.read(f'runtimes/{RID}/native/{native.name}')).hexdigest() == native_hash
    shutil.copy2(package,binary/package.name)
    result['package_sha256'] = sha(package)
    consumer = WORK/'consumer'
    project = (consumer/'AdmissionProbe.csproj').read_text()
    assert 'PackageReference' in project and 'ProjectReference' not in project
    (consumer/'NuGet.Config').write_text('<configuration><packageSources><clear/><add key="local" value="'+escape(str(feed), {'"':'&quot;'})+'"/><add key="nuget" value="https://api.nuget.org/v3/index.json"/></packageSources></configuration>', encoding='utf-8')
    run('consumer-build-no-rid',['dotnet','build','-c','Release'],cwd=consumer)
    normal = run('consumer-run-no-rid',['dotnet','run','-c','Release','--no-build'],cwd=consumer,timeout=180)
    result['normal'] = parse_probe('normal',normal,aot=False)
    publish = WORK/'publish'
    run('aot-publish',['dotnet','publish','-c','Release','-r',RID,'-p:PublishAot=true','-o',publish],cwd=consumer)
    exe = publish/('AdmissionProbe.exe' if sys.platform == 'win32' else 'AdmissionProbe')
    copied_native = list(publish.rglob(native.name))
    assert len(copied_native) == 1 and sha(copied_native[0]) == native_hash, copied_native
    shutil.copytree(publish,binary/'aot',dirs_exist_ok=True)
    result['aot_executable_sha256'] = sha(exe)
    aot = run('aot-run',[exe,'--expect-aot'],cwd=publish,timeout=180)
    result['native_aot'] = parse_probe('native_aot',aot,aot=True)
    assert sha(native) == native_hash
    for f in reused: assert sha(f) == result['reused_source_files'][f.relative_to(REPO).as_posix()]
    result.update(success=True, package_reference_only=True, ordinary_build_run_without_rid=True, old_consumer_executed=False, old_rust_tests_executed=False, binaries=[output_record(p) for p in sorted(binary.rglob('*')) if p.is_file()])
except BaseException as error:
    result['failure'] = {'type':type(error).__name__, 'message':str(error)}
    (OUT/'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
    raise
finally:
    result['ended_utc'] = utc()
    result['commands'] = records
    result['binaries'] = [output_record(p) for p in sorted((OUT/'binaries').rglob('*')) if p.is_file()]
    dump(OUT/'result.json', result)
    # Preserve even a failure's real inputs, stdout/stderr and result. Successful binaries
    # are copied above; temporary build output never modifies the recovered source tree.
    shutil.rmtree(WORK, ignore_errors=True)
