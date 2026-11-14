@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
set "PATH=C:\Users\J7Rdm\scoop\apps\dotnet-sdk\current;C:\Users\J7Rdm\scoop\apps\rustup\current\.cargo\bin;C:\Users\J7Rdm\scoop\apps\python\current;C:\Users\J7Rdm\scoop\shims;%PATH%"
set "DOTNET_ROOT=C:\Users\J7Rdm\scoop\apps\dotnet-sdk\current"
set "DOTNET_CLI_TELEMETRY_OPTOUT=1"
set "DOTNET_NOLOGO=1"
set "DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1"
cd /d "C:\MyFile\Projects\IzuSharp\NativeWeave-Design\.worktree\local-host-validation"
python experiments\server-completion\run.py protocol --output verification\local-host\2026-11-14\windows\protocol-attempt-1
exit /b %errorlevel%
