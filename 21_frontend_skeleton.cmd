@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 21_frontend_skeleton.cmd
>> "%WORKLOG%" echo - Step: apply SSE parser + minimal UI + PII masking skeleton
>> "%WORKLOG%" echo - CMD: python "tools\scaffold_writer.py" frontend

if not exist "frontend\package.json" (
    echo [ERROR] frontend project not found. run 20_generate_frontend.cmd first.
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: frontend not generated
    exit /b 1
)

python "tools\scaffold_writer.py" frontend
if errorlevel 1 (
    echo [ERROR] frontend skeleton generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: scaffold_writer.py frontend action failed
    exit /b 1
)

>> "%WORKLOG%" echo - Files updated:
>> "%WORKLOG%" echo   - frontend/src/App.tsx
>> "%WORKLOG%" echo   - frontend/src/types/sse.ts
>> "%WORKLOG%" echo   - frontend/src/utils/sseParser.ts
>> "%WORKLOG%" echo   - frontend/src/utils/piiMasking.ts
>> "%WORKLOG%" echo   - frontend/src/index.css
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 30_generate_infra.cmd

echo [OK] 21_frontend_skeleton done
exit /b 0
