"""Record isolated .NET 11 invalid-UCO behavior, without assuming which stage rejects it."""
import datetime, hashlib, json, os, platform, resource, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / 'verification/interop-completion/uco-invalid-linux'
WORK = HERE / '.work/uco-invalid'
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
ENV = os.environ.copy()
ENV.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1', LD_LIBRARY_PATH=str(WORK))
COMMANDS = []

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def no_core(): resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
def run(label, argv, fatal=False):
    start = stamp()
    result = subprocess.run(argv, cwd=HERE, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=180, preexec_fn=no_core if fatal else None)
    stdout, stderr = OUT / (label+'.stdout'), OUT / (label+'.stderr')
    stdout.write_bytes(result.stdout); stderr.write_bytes(result.stderr)
    COMMANDS.append(dict(label=label, argv=argv, exit_code=result.returncode, started_utc=start,
                         ended_utc=stamp(), stdout_sha256=digest(stdout), stderr_sha256=digest(stderr)))
    (OUT/'commands.json').write_text(json.dumps(COMMANDS, indent=2)+'\n')
    return result

native = run('rust-build', ['rustc','--edition=2024','--crate-type=cdylib','uco_invalid.rs','-o',str(WORK/'libnw_uco_invalid.so')])
if native.returncode: raise SystemExit(native.returncode)
results = []
for label, aot in [('normal',False), ('aot',True)]:
    target = WORK / label
    args = ['dotnet','publish','UcoInvalid.csproj','-c','Release','-o',str(target), '--disable-build-servers']
    if aot: args += ['-p:PublishAot=true']
    build = run(label+'-build',args)
    if build.returncode:
        results.append(dict(profile=label, observed='compile_or_publish_rejection', exit_code=build.returncode))
        continue
    binary = target / ('UcoInvalid' if aot else 'UcoInvalid.dll')
    process = run(label+'-execute', [str(binary)] if aot else ['dotnet',str(binary)], fatal=True)
    body = b'INVALID_CALLBACK_BODY_ENTERED' in process.stdout
    results.append(dict(profile=label, observed='process_rejection' if process.returncode and not body else 'body_entered_or_returned',
                        exit_code=process.returncode, body_entered=body, binary_sha256=digest(binary)))

success = all(x['observed'] in ['compile_or_publish_rejection','process_rejection'] for x in results)
manifest = dict(schema_version='1.0.0', source_commit=None,
    baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    platform=platform.platform(), success=success, cases=results,
    source_files={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),HERE/'UcoInvalid.cs',HERE/'UcoInvalid.csproj',HERE/'uco_invalid.rs',HERE/'Directory.Build.props',HERE/'global.json',HERE/'rust-toolchain.toml']},
    independent_review=False, scope='Deliberately invalid bool/char UCO with runtime marshalling enabled; isolated research child processes only.')
(OUT/'result.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
raise SystemExit(0 if success else 1)
