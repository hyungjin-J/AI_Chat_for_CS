@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

if not exist "docs\ops" mkdir "docs\ops"
if not exist ".agents" mkdir ".agents"
if not exist "infra" mkdir "infra"
if not exist "tools" mkdir "tools"

python "tools\scaffold_writer.py" worklog_init
if errorlevel 1 (
    echo [ERROR] worklog initialization failed
    exit /b 1
)

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 00_bootstrap.cmd
>> "%WORKLOG%" echo - Step: environment check + base directory setup + UTF-8 console mode
>> "%WORKLOG%" echo - CMD: chcp 65001, mkdir docs\ops/.agents/infra/tools
>> "%WORKLOG%" echo - Files/Folders: docs\ops, .agents, infra, tools

for %%T in (git java node npm python docker) do (
    where %%T > nul 2>&1
    if errorlevel 1 (
        echo [WARN] %%T not found
        >> "%WORKLOG%" echo - Check: %%T not found
    ) else (
        >> "%WORKLOG%" echo - Check: %%T found
    )
)

>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 10_generate_backend.cmd

echo [OK] 00_bootstrap done
exit /b 0
