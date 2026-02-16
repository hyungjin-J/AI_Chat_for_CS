@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0..\.."

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 30_generate_infra.cmd
>> "%WORKLOG%" echo - Step: generate Postgres/Redis docker-compose
>> "%WORKLOG%" echo - CMD: python "tools\scaffold_writer.py" infra

python "tools\scaffold_writer.py" infra
if errorlevel 1 (
    echo [ERROR] infra generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: scaffold_writer.py infra action failed
    exit /b 1
)

if not exist "infra\docker-compose.yml" (
    echo [ERROR] infra\docker-compose.yml missing
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: verify path/permission
    exit /b 1
)

>> "%WORKLOG%" echo - File: infra/docker-compose.yml
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 40_install_skills.cmd

echo [OK] 30_generate_infra done
exit /b 0
