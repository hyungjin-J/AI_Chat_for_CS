@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0..\.."

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 60_generate_readme.cmd
>> "%WORKLOG%" echo - Step: generate README with CMD run guide
>> "%WORKLOG%" echo - CMD: python "tools\scaffold_writer.py" readme

python "tools\scaffold_writer.py" readme
if errorlevel 1 (
    echo [ERROR] README.md generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: scaffold_writer.py readme action failed
    exit /b 1
)

>> "%WORKLOG%" echo - File: README.md
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 90_verify.cmd

echo [OK] 60_generate_readme done
exit /b 0
