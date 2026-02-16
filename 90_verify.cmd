@echo off
setlocal EnableExtensions
chcp 65001 > nul
cd /d "%~dp0"
set "ROOT=%~dp0"

set "WORKLOG=docs\ops\CODEX_WORKLOG.md"
set "VERIFY_FAILED=0"

>> "%WORKLOG%" echo ## [%date% %time%] 90_verify.cmd
>> "%WORKLOG%" echo - Step: backend build + frontend install + docker file validation

if exist "backend\gradlew.bat" (
    >> "%WORKLOG%" echo - CMD: cd /d backend ^&^& gradlew.bat clean build -x test
    cd /d "%ROOT%backend"
    call "gradlew.bat" clean build -x test
    if errorlevel 1 (
        set "VERIFY_FAILED=1"
        >> "%WORKLOG%" echo - backend verification: failed
    ) else (
        >> "%WORKLOG%" echo - backend verification: success
    )
    cd /d "%ROOT%"
) else (
    set "VERIFY_FAILED=1"
    >> "%WORKLOG%" echo - backend verification: failed; gradlew.bat missing
)

if exist "frontend\package.json" (
    >> "%WORKLOG%" echo - CMD: cd /d frontend ^&^& npm install
    cd /d "%ROOT%frontend"
    call npm install
    if errorlevel 1 (
        set "VERIFY_FAILED=1"
        >> "%WORKLOG%" echo - frontend verification: failed
    ) else (
        >> "%WORKLOG%" echo - frontend verification: success
    )
    cd /d "%ROOT%"
) else (
    set "VERIFY_FAILED=1"
    >> "%WORKLOG%" echo - frontend verification: failed; package.json missing
)

if exist "infra\docker-compose.yml" (
    >> "%WORKLOG%" echo - docker-compose file check: success
) else (
    set "VERIFY_FAILED=1"
    >> "%WORKLOG%" echo - docker-compose file check: failed
)

where docker > nul 2>&1
if errorlevel 1 (
    >> "%WORKLOG%" echo - docker CLI check: not installed; file-only validation performed
) else (
    >> "%WORKLOG%" echo - CMD: docker compose -f "infra\docker-compose.yml" config
    docker compose -f "infra\docker-compose.yml" config > nul
    if errorlevel 1 (
        set "VERIFY_FAILED=1"
        >> "%WORKLOG%" echo - docker compose config: failed
    ) else (
        >> "%WORKLOG%" echo - docker compose config: success
    )
)

if "%VERIFY_FAILED%"=="1" (
    >> "%WORKLOG%" echo - Result: failed
    >> "%WORKLOG%" echo - Next: fix failed items and rerun 90_verify.cmd
    echo [ERROR] verification failed. see WORKLOG.
    exit /b 1
)

>> "%WORKLOG%" echo - Result: success
>> "%WORKLOG%" echo - Next: run 99_git_init_commit_push.cmd
echo [OK] 90_verify done
exit /b 0
