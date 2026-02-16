@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0..\.."

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
>> "%WORKLOG%" echo ## [%date% %time%] 11_backend_skeleton.cmd
>> "%WORKLOG%" echo - Step: apply trace_id/tenant_key/error/SSE backend skeleton
>> "%WORKLOG%" echo - CMD: python "tools\scaffold_writer.py" backend

if not exist "backend\gradlew.bat" (
    echo [ERROR] backend project not found. run 10_generate_backend.cmd first.
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: backend not generated
    exit /b 1
)

python "tools\scaffold_writer.py" backend
if errorlevel 1 (
    echo [ERROR] backend skeleton generation failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: scaffold_writer.py backend action failed
    exit /b 1
)

>> "%WORKLOG%" echo - Files updated:
>> "%WORKLOG%" echo   - backend/src/main/java/com/aichatbot/global/** 
>> "%WORKLOG%" echo   - backend/src/main/java/com/aichatbot/message/presentation/MessageStreamController.java
>> "%WORKLOG%" echo   - backend/src/main/resources/application.properties
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 20_generate_frontend.cmd

echo [OK] 11_backend_skeleton done
exit /b 0
