@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 20_generate_frontend.cmd
>> "%WORKLOG%" echo - Step: generate frontend via Vite React-TS
>> "%WORKLOG%" echo - CMD: npm create vite@latest frontend -- --template react-ts

if exist "frontend\package.json" (
    echo [INFO] frontend already exists. generation skipped.
    >> "%WORKLOG%" echo - Result: skipped; frontend already exists
    >> "%WORKLOG%" echo - Next: run 21_frontend_skeleton.cmd
    exit /b 0
)

set "npm_config_yes=true"
call npm create vite@latest frontend -- --template react-ts
if errorlevel 1 (
    echo [ERROR] frontend generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: npm create vite failed
    >> "%WORKLOG%" echo - Manual CMD: npm create vite@latest frontend -- --template react-ts
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend package.json not found after generation
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: verify output path
    exit /b 1
)

>> "%WORKLOG%" echo - Files: frontend/** Vite base project
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 21_frontend_skeleton.cmd

echo [OK] 20_generate_frontend done
exit /b 0
