import datetime, hashlib, json, os, pathlib, subprocess
root=pathlib.Path('/home/sammiller/nativeweave-local-validation-20261114/NativeWeave-Design')
out=root/'verification/local-host/2026-11-14/linux'
out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(PATH='/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/opt/rustup/bin:'+env['PATH'],DOTNET_ROOT='/home/linuxbrew/.linuxbrew/opt/dotnet/libexec',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
commands=[('protocol',['python3','experiments/server-completion/run.py','protocol','--output',str(out/'protocol')]),('engine',['python3','experiments/engine-completion/run.py','--out',str(out/'engine'),'--aot']),('platform',['python3','experiments/platform-completion/run.py','--out',str(out/'platform'),'--aot']),('metadata',['python3','experiments/database-completion/run.py','--suite','metadata','--out',str(out/'metadata')])]
records=[]
for name,command in commands:
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (out/(name+'-runner.stdout')).open('wb') as stdout,(out/(name+'-runner.stderr')).open('wb') as stderr:
        try: code=subprocess.run(command,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=1200).returncode
        except subprocess.TimeoutExpired: code=124
    records.append(dict(name=name,command=command,exit_code=code,started_at_utc=started,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (out/'orchestration.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),kind='local MCP host research replication',records=records),indent=2)+'\n')
    print(name,code,flush=True)
