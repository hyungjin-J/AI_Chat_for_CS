@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
if not exist "docs\ops" mkdir "docs\ops"
if not exist "%WORKLOG%" (
    python "tools\scaffold_writer.py" worklog_init
)

>> "%WORKLOG%" echo ## [%date% %time%] 10_generate_backend.cmd
>> "%WORKLOG%" echo - Step: generate backend via Spring Initializr
>> "%WORKLOG%" echo - CMD: curl + tar

if exist "backend\gradlew.bat" (
    echo [INFO] backend already exists. generation skipped.
    >> "%WORKLOG%" echo - Result: skipped; backend already exists
    >> "%WORKLOG%" echo - Next: run 11_backend_skeleton.cmd
    exit /b 0
)

if exist "backend.zip" del /f /q "backend.zip"

curl -fsSL -G "https://start.spring.io/starter.zip" ^
  --data-urlencode "type=gradle-project" ^
  --data-urlencode "language=java" ^
  --data-urlencode "baseDir=backend" ^
  --data-urlencode "groupId=com.aichatbot" ^
  --data-urlencode "artifactId=backend" ^
  --data-urlencode "name=backend" ^
  --data-urlencode "packageName=com.aichatbot" ^
  --data-urlencode "packaging=jar" ^
  --data-urlencode "javaVersion=17" ^
  --data-urlencode "dependencies=web,actuator,security,validation" ^
  -o "backend.zip"
if errorlevel 1 (
    echo [ERROR] Spring Initializr download failed
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: network or URL issue. verify curl URL.
    >> "%WORKLOG%" echo - Manual CMD: curl -L ^<start.spring.io URL^> -o backend.zip
    exit /b 1
)

tar -xf "backend.zip"
if errorlevel 1 (
    echo [ERROR] failed to extract backend.zip
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: tar command failure. verify Windows tar availability.
    >> "%WORKLOG%" echo - Manual CMD: tar -xf "backend.zip"
    exit /b 1
)

del /f /q "backend.zip"

if not exist "backend\gradlew.bat" (
    echo [ERROR] gradlew.bat missing after generation
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Cause/Fix: check starter zip structure
    exit /b 1
)

>> "%WORKLOG%" echo - Files: backend/** Spring base project
>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 11_backend_skeleton.cmd

echo [OK] 10_generate_backend done
exit /b 0
