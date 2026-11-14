import datetime, json, os, pathlib, subprocess
root=pathlib.Path('/home/sammiller/nativeweave-local-validation-20261114/NativeWeave-Design')
out=root/'verification/local-host/2026-11-14/linux'
env=os.environ.copy()
env.update(PATH='/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/opt/rustup/bin:'+env['PATH'],DOTNET_ROOT='/home/linuxbrew/.linuxbrew/opt/dotnet/libexec',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
commands=[('engine-attempt-2',['python3','experiments/engine-completion/run.py','--out',str(out/'engine-attempt-2'),'--aot']),('platform-attempt-2',['python3','experiments/platform-completion/run.py','--out',str(out/'platform-attempt-2'),'--aot'])]
records=[]
for name,command in commands:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (out/(name+'-runner.stdout')).open('wb') as stdout,(out/(name+'-runner.stderr')).open('wb') as stderr:
        try: code=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=1200).returncode
        except subprocess.TimeoutExpired: code=124
    records.append(dict(name=name,command=command,exit_code=code,started_at_utc=started,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (out/'retry-orchestration.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),kind='local MCP host research replication after installing link prerequisites',records=records),indent=2)+'\n')
    print(name,code,flush=True)
