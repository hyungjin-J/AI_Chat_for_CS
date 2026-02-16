@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 50_generate_gitignore.cmd
>> "%WORKLOG%" echo - Step: generate project .gitignore
>> "%WORKLOG%" echo - CMD: python "tools\scaffold_writer.py" gitignore

python "tools\scaffold_writer.py" gitignore
if errorlevel 1 (
    echo [ERROR] .gitignore generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: scaffold_writer.py gitignore action failed
    exit /b 1
)

>> "%WORKLOG%" echo - File: .gitignore
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 60_generate_readme.cmd

echo [OK] 50_generate_gitignore done
exit /b 0
